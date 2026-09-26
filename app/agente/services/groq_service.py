import logging
logger = logging.getLogger(__name__)
import json
import re

import httpx

from agente import config
from agente.services.base import (
    BaseService,
    NonRetriableAPIError,
    RetriableAPIError,
    calcular_espera_retry_after,
)

API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_request(mensagens: list, stream: bool = False, model: str = None) -> tuple:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY não configurada.")

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    from agente.services.base import format_openai_messages
    from agente.services.tools_defs import OPENAI_TOOLS_DECLARATION

    formatted_messages = format_openai_messages(mensagens)

    payload = {
        "model": model or config.GROQ_MODEL,
        "messages": formatted_messages,
        "stream": stream,
        "max_tokens": getattr(config, "MAX_OUTPUT_TOKENS", 4096),
        "temperature": getattr(config, "GROQ_TEMPERATURE", getattr(config, "DEFAULT_TEMPERATURE", 0.7)),
        "tools": OPENAI_TOOLS_DECLARATION,
        "tool_choice": "auto"
    }

    return headers, payload


def _handle_error(res, model: str = None):
    """Trata erros HTTP da Groq API com mensagem detalhada."""
    if res.status_code != 200:
        body = ""
        try:
            if hasattr(res, "read"):
                body = res.read().decode("utf-8")
            elif hasattr(res, "text"):
                body = res.text
        except Exception:
            try:
                body = b"".join(res.iter_bytes()).decode("utf-8", errors="replace")
            except Exception:
                body = ""
        try:
            err_json = json.loads(body)
            msg = err_json.get("error", {}).get("message", body)
        except Exception:
            msg = body or f"HTTP {res.status_code}"
        m_name = model or config.GROQ_MODEL
        if "content must be a string" in msg.lower():
            msg = f"{msg}\n[Dica] O modelo atual do Groq ({m_name}) é de texto puro e não suporta imagens. Use '/modelo gemini' para visão multimodal."
        if res.status_code == 429 or 500 <= res.status_code < 600:
            raise RetriableAPIError(f"Groq API ({res.status_code}): {msg}")
        raise NonRetriableAPIError(f"Groq API ({res.status_code}): {msg}")




from agente.services.base import parse_openai_sse_stream, process_tool_calls_map

def gerar_resposta_stream(mensagens: list, iteration: int = 0, max_iterations: int = 5, model: str = None, service=None):
    """Gera resposta via streaming SSE da Groq API (formato OpenAI)."""
    model_name = model or config.GROQ_MODEL
    headers, payload = _build_request(mensagens, stream=True, model=model_name)

    from agente.services.http_client import get_http_client
    import time
    retries = 5
    tentativas_deadline = time.monotonic() + 90.0

    def _espera_retry(espera: float, motivo: str, attempt: int) -> None:
        restante = tentativas_deadline - time.monotonic()
        if espera >= restante:
            espera = max(restante, 0.0)
        if espera > 0:
            logger.info("Groq: %s (tentativa %d/%d) — aguardando %.1fs", motivo, attempt + 1, retries, espera)
            time.sleep(espera)
        else:
            logger.debug("Groq: teto de 90s de retentativas atingido")
            raise RuntimeError("Groq: teto de 90s de retentativas atingido")

    for attempt in range(retries):
        if service and getattr(service, "_aborted", False):
            return
        tool_calls_map = {}
        try:
            client = get_http_client()
            with client.stream("POST", API_URL, headers=headers, json=payload) as res:
                if service:
                    service._active_stream = res
                try:
                    if res.status_code == 429 and attempt < retries - 1:
                        espera = calcular_espera_retry_after(res, padrao=3.0)
                        try:
                            corpo = res.read().decode("utf-8")
                            m = re.search(r"try again in ([\d\.]+)s", corpo)
                            if m:
                                espera = max(espera, float(m.group(1)) + 1.0)
                        except Exception as _silent_e:
                            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
                            # Corpo não consumido: descarta a conexão em vez de devolvê-la ao pool.
                            try:
                                res.close()
                            except Exception:
                                pass
                        try:
                            ra_raw = res.headers.get("Retry-After", "").strip()
                            if ra_raw.isdigit() and float(ra_raw) > 90.0:
                                logger.debug("Groq: Retry-After=%ss excede o teto de 90s", ra_raw)
                        except Exception as _silent_e:
                            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
                        _espera_retry(espera, "rate-limit (429)", attempt)
                        continue
                    _handle_error(res, model=model_name)

                    yield from parse_openai_sse_stream(res.iter_lines(), tool_calls_map)
                finally:
                    if service:
                        service._active_stream = None
            break
        except (httpx.RequestError, RetriableAPIError) as e:
            if service and getattr(service, "_aborted", False):
                return
            if attempt == retries - 1:
                if isinstance(e, RetriableAPIError):
                    raise
                raise RuntimeError(f"Erro de conexão com Groq API: {e}")
            _espera_retry(1.5, "falha de conexão/retry", attempt)

    if tool_calls_map:
        if service and getattr(service, "_aborted", False):
            return
        if iteration >= max_iterations:
            yield f"\n[Aviso: Limite de {max_iterations} execuções de ferramentas atingido para esta rodada.]\n"
            return

        process_tool_calls_map(tool_calls_map, mensagens, iteration=iteration)
        yield from gerar_resposta_stream(mensagens, iteration=iteration + 1, max_iterations=max_iterations, model=model_name, service=service)

class GroqService(BaseService):
    def __init__(self, model: str = None):
        super().__init__()
        self.model = model or config.GROQ_MODEL

    @property
    def nome_provedor(self) -> str:
        return f"GROQ ({self.model})"

    def gerar_resposta_stream(self, mensagens: list):
        self._aborted = False
        return gerar_resposta_stream(mensagens, model=self.model, service=self)
