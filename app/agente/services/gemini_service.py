import json
import logging

import httpx

from agente import config
from agente.services.base import BaseService

logger = logging.getLogger(__name__)


def _build_request(mensagens: list) -> tuple:
    """Constrói headers e payload a partir da lista de mensagens."""
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada.")

    headers = {
        "x-goog-api-key": config.GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    contents = []
    system_instruction = None

    import base64
    import mimetypes

    from agente.services.tools_defs import GEMINI_TOOLS_DECLARATION

    for m in mensagens:
        role_raw = m.get("role", "")

        if role_raw == "system":
            system_instruction = str(m.get("content", ""))
            continue

        if role_raw == "functionCall":
            contents.append({
                "role": "model",
                "parts": [{"functionCall": m["functionCall"]}]
            })
            continue
            
        if role_raw == "functionResponse":
            contents.append({
                "role": "function",
                "parts": [{"functionResponse": {"name": m["name"], "response": {"name": m["name"], "content": m["content"]}}}]
            })
            continue

        role = "user" if role_raw == "user" else "model"
        
        parts = []
        if "media_paths" in m:
            for path in m["media_paths"]:
                try:
                    from agente.services.media_cache import get_base64_media
                    data = get_base64_media(path)
                    mime, _ = mimetypes.guess_type(path)
                    if not mime:
                        mime = "application/octet-stream"
                    parts.append({
                        "inlineData": {
                            "mimeType": mime,
                            "data": data
                        }
                    })
                except Exception as e:
                    logger.error(f"Falha ao ler midia {path}: {e}")

        text_content = str(m.get("content", ""))
        if text_content:
            parts.append({"text": text_content})
            
        if parts:
            contents.append({
                "role": role,
                "parts": parts
            })

    payload = {
        "contents": contents,
        "tools": GEMINI_TOOLS_DECLARATION,
        "generationConfig": {
            "maxOutputTokens": getattr(config, "MAX_OUTPUT_TOKENS", 4096),
            "temperature": getattr(config, "GEMINI_TEMPERATURE", getattr(config, "OLLAMA_TEMPERATURE", 0.7))
        }
    }

    if system_instruction:
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }

    return headers, payload


def _handle_error(res):
    """Trata erros HTTP da Gemini API."""
    if res.status_code in {400, 401, 403}:
        raise RuntimeError("Erro de autenticação/permissão na Gemini API.")
    if res.status_code == 429:
        raise RuntimeError("Rate limit da Gemini API atingido.")
    res.raise_for_status()




def gerar_resposta_stream(mensagens: list, iteration: int = 0, max_iterations: int = 5, model: str = None):
    """Gera resposta via streaming SSE da Gemini API."""
    model_name = model or config.GEMINI_MODEL
    headers, payload = _build_request(mensagens)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:streamGenerateContent?alt=sse"
    )

    timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)

    function_calls_detected = []

    try:
        from agente.services.http_client import get_http_client
        client = get_http_client(timeout=timeout)
        with client.stream("POST", url, headers=headers, json=payload) as res:
                _handle_error(res)

                for line in res.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        parts = data["candidates"][0]["content"]["parts"]
                        for part in parts:
                            if "text" in part:
                                text = part["text"]
                                if text:
                                    yield text
                            elif "functionCall" in part:
                                function_calls_detected.append(part["functionCall"])
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
    except httpx.RequestError as e:
        raise RuntimeError(f"Erro de conexão com Gemini API: {e}")

    if function_calls_detected:
        if iteration >= max_iterations:
            yield f"\n[Aviso: Limite de {max_iterations} execuções de ferramentas atingido para esta rodada.]\n"
            return

        from agente.services.tool_executor import executar_tool
        for fc in function_calls_detected:
            name = fc.get("name")
            args = fc.get("args", {})
            
            mensagens.append({
                "role": "functionCall",
                "functionCall": fc
            })
            
            result = executar_tool(name, args)
                
            mensagens.append({
                "role": "functionResponse",
                "name": name,
                "content": result
            })
        
        yield from gerar_resposta_stream(mensagens, iteration=iteration + 1, max_iterations=max_iterations, model=model_name)

class GeminiService(BaseService):
    def __init__(self, model: str = None):
        self.model = model or config.GEMINI_MODEL

    @property
    def nome_provedor(self) -> str:
        return f"GEMINI ({self.model})"

    def gerar_resposta_stream(self, mensagens: list):
        return gerar_resposta_stream(mensagens, model=self.model)
