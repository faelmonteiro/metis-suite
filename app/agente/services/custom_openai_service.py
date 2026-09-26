"""
Serviço genérico compatível com OpenAI (OpenRouter, DeepSeek, LocalAI, vLLM, LM Studio, etc.)
com suporte completo a streaming, ferramentas (tool calling), visão/mídia e tratamento de erros.
"""
import json
import logging
import os
import re
from typing import Iterator

import httpx

from agente import config
from agente.services.base import (
    BaseService,
    NonRetriableAPIError,
    RetriableAPIError,
    calcular_espera_retry_after,
    parse_openai_sse_stream,
    process_tool_calls_map,
)

logger = logging.getLogger(__name__)


class CustomOpenAIService(BaseService):
    def __init__(self, server_info: dict):
        super().__init__()
        self.server_info = server_info
        self.nome = server_info.get("nome", "Custom API")
        raw_base_url = server_info.get("base_url", "").strip()
        if "openrouter.ai" in raw_base_url.lower():
            if not raw_base_url.endswith("/chat/completions"):
                self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            else:
                self.base_url = raw_base_url
        elif "groq.com" in raw_base_url.lower():
            if "console.groq.com" in raw_base_url.lower() or not raw_base_url.endswith("/chat/completions"):
                self.base_url = "https://api.groq.com/openai/v1/chat/completions"
            else:
                self.base_url = raw_base_url
        elif raw_base_url:
            clean_url = raw_base_url.rstrip("/")
            if not clean_url.endswith("/chat/completions"):
                self.base_url = f"{clean_url}/chat/completions"
            else:
                self.base_url = clean_url
        else:
            self.base_url = raw_base_url
        self.modelo = server_info.get("modelo_atual", "")
        self.api_key_env = server_info.get("api_key_env", "")
        self.api_key_direct = server_info.get("api_key", "")

    def _obter_api_key(self) -> str:
        if self.api_key_env:
            key = os.getenv(self.api_key_env, "").strip()
            if key:
                return key
        return self.api_key_direct.strip()

    @property
    def nome_provedor(self) -> str:
        return f"{self.nome.upper()} ({self.modelo})"

    def _build_request(self, mensagens: list, stream: bool = False) -> tuple:
        api_key = self._obter_api_key()

        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Headers recomendados para o OpenRouter
        if "openrouter" in self.base_url.lower():
            headers["HTTP-Referer"] = "https://github.com/reator/metis"
            headers["X-Title"] = "metis"

        from agente.services.base import format_openai_messages
        from agente.services.tools_defs import OPENAI_TOOLS_DECLARATION

        formatted_messages = format_openai_messages(mensagens)

        payload = {
            "model": self.modelo,
            "messages": formatted_messages,
            "stream": stream,
            "max_tokens": getattr(config, "MAX_OUTPUT_TOKENS", 4096),
            "temperature": getattr(config, "CUSTOM_TEMPERATURE", getattr(config, "DEFAULT_TEMPERATURE", 0.7)),
        }

        # Adiciona ferramentas caso habilitadas (NVIDIA NIM não suporta tool calling nesse formato)
        try:
            is_nvidia = "nvidia" in self.base_url.lower() or "nvidia" in str(self.server_info.get("id", "")).lower()
            if OPENAI_TOOLS_DECLARATION and not is_nvidia:
                payload["tools"] = OPENAI_TOOLS_DECLARATION
                payload["tool_choice"] = "auto"
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

        return headers, payload

    def _handle_error(self, res):
        """Trata erros HTTP com mensagens claras."""
        if res.status_code != 200:
            try:
                body = res.read().decode("utf-8")
                err_json = json.loads(body)
                err_obj = err_json.get("error", {})
                if isinstance(err_obj, dict):
                    msg = err_obj.get("metadata", {}).get("raw") or err_obj.get("message") or body
                else:
                    msg = str(err_obj) or body
            except Exception:
                msg = f"HTTP {res.status_code}"
            if res.status_code == 429 or 500 <= res.status_code < 600:
                raise RetriableAPIError(f"{self.nome} API ({res.status_code}): {msg}")
            raise NonRetriableAPIError(f"{self.nome} API ({res.status_code}): {msg}")

    def gerar_resposta_stream(self, mensagens: list, iteration: int = 0, max_iterations: int = 5) -> Iterator[str]:
        """Entrada pública: reseta o abort e delega ao loop interno."""
        self._aborted = False
        return self._stream_interno(mensagens, iteration=iteration, max_iterations=max_iterations)

    def _stream_interno(self, mensagens: list, iteration: int = 0, max_iterations: int = 5) -> Iterator[str]:
        headers, payload = self._build_request(mensagens, stream=True)

        from agente.services.http_client import get_http_client
        import time
        retries = 3
        tentativas_deadline = time.monotonic() + 90.0

        def _espera_retry(espera: float, motivo: str, attempt: int) -> None:
            restante = tentativas_deadline - time.monotonic()
            if espera >= restante:
                espera = max(restante, 0.0)
            if espera > 0:
                logger.info("%s: %s (tentativa %d/%d) — aguardando %.1fs", self.nome, motivo, attempt + 1, retries, espera)
                time.sleep(espera)
            else:
                logger.debug("%s: teto de 90s de retentativas atingido", self.nome)
                raise RuntimeError(f"{self.nome}: teto de 90s de retentativas atingido")

        for attempt in range(retries):
            if self._aborted:
                return
            tool_calls_map = {}
            try:
                client = get_http_client()
                with client.stream("POST", self.base_url, headers=headers, json=payload) as res:
                    self._active_stream = res
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
                                    logger.debug("%s: Retry-After=%ss excede o teto de 90s", self.nome, ra_raw)
                            except Exception as _silent_e:
                                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
                            _espera_retry(espera, "rate-limit (429)", attempt)
                            continue
                        if res.status_code in (400, 404) and "tools" in payload:
                            try:
                                body = res.read().decode("utf-8")
                                if "tool" in body.lower():
                                    logger.info(f"Modelo {self.modelo} não suporta ferramentas. Reenviando sem tools.")
                                    payload.pop("tools", None)
                                    payload.pop("tool_choice", None)
                                    continue
                            except Exception as _silent_e:
                                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
                        self._handle_error(res)

                        yield from parse_openai_sse_stream(res.iter_lines(), tool_calls_map)
                    finally:
                        self._active_stream = None
                break
            except (httpx.RequestError, RetriableAPIError) as e:
                if self._aborted:
                    return
                if attempt == retries - 1:
                    if isinstance(e, RetriableAPIError):
                        raise
                    raise RuntimeError(f"Erro de conexão com {self.nome} ({self.base_url}): {e}")
                _espera_retry(1.5, "falha de conexão/retry", attempt)

        if tool_calls_map:
            if iteration >= max_iterations:
                yield f"\n[Aviso: Limite de {max_iterations} execuções de ferramentas atingido para esta rodada.]\n"
                return

            process_tool_calls_map(tool_calls_map, mensagens, iteration=iteration)
            yield from self._stream_interno(mensagens, iteration=iteration + 1, max_iterations=max_iterations)
