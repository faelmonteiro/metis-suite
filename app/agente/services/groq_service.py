import json
import logging
import re

import httpx

from agente import config
from agente.services.base import BaseService

logger = logging.getLogger(__name__)

API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_request(mensagens: list, stream: bool = False, model: str = None) -> tuple:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY não configurada.")

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    from agente.services.tools_defs import OPENAI_TOOLS_DECLARATION
    import base64
    import mimetypes

    formatted_messages = []
    
    for m in mensagens:
        role_raw = m.get("role", "")

        if role_raw == "system":
            formatted_messages.append({"role": "system", "content": m.get("content", "")})
            continue

        if role_raw == "functionCall":
            args_data = m["functionCall"].get("args", {})
            args_str = json.dumps(args_data) if isinstance(args_data, dict) else str(args_data)
            tc_obj = {
                "id": m["functionCall"].get("id", "call_123"),
                "type": "function",
                "function": {
                    "name": m["functionCall"]["name"],
                    "arguments": args_str
                }
            }
            if formatted_messages and formatted_messages[-1].get("role") == "assistant" and "tool_calls" in formatted_messages[-1]:
                formatted_messages[-1]["tool_calls"].append(tc_obj)
            else:
                formatted_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc_obj]
                })
            continue
            
        if role_raw == "functionResponse":
            formatted_messages.append({
                "role": "tool",
                "tool_call_id": m.get("id", "call_123"),
                "name": m["name"],
                "content": str(m["content"])
            })
            continue

        role = "user" if role_raw == "user" else "assistant"
        
        content = []
        text_content = str(m.get("content", ""))
        if text_content:
            content.append({"type": "text", "text": text_content})
            
        if "media_paths" in m:
            for path in m["media_paths"]:
                try:
                    from agente.services.media_cache import get_base64_media
                    data = get_base64_media(path)
                    mime, _ = mimetypes.guess_type(path)
                    if not mime:
                        mime = "application/octet-stream"
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{data}"
                        }
                    })
                except Exception as e:
                    logger.error(f"Falha ao ler midia {path}: {e}")

        if len(content) == 1 and content[0]["type"] == "text":
            final_content = content[0]["text"]
        elif not content:
            continue
        else:
            final_content = content

        formatted_messages.append({
            "role": role,
            "content": final_content
        })

    payload = {
        "model": model or config.GROQ_MODEL,
        "messages": formatted_messages,
        "stream": stream,
        "max_tokens": getattr(config, "MAX_OUTPUT_TOKENS", 4096),
        "temperature": getattr(config, "OLLAMA_TEMPERATURE", 0.7),
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
        raise RuntimeError(f"Groq API ({res.status_code}): {msg}")




from agente.services.base import BaseService, parse_openai_sse_stream, process_tool_calls_map

def gerar_resposta_stream(mensagens: list, iteration: int = 0, max_iterations: int = 5, model: str = None):
    """Gera resposta via streaming SSE da Groq API (formato OpenAI)."""
    model_name = model or config.GROQ_MODEL
    headers, payload = _build_request(mensagens, stream=True, model=model_name)

    from agente.services.http_client import get_http_client
    retries = 5
    for attempt in range(retries):
        tool_calls_map = {}
        try:
            client = get_http_client()
            with client.stream("POST", API_URL, headers=headers, json=payload) as res:
                if res.status_code == 429 and attempt < retries - 1:
                    import time
                    espera = 3.0
                    try:
                        corpo = res.read().decode("utf-8")
                        m = re.search(r"try again in ([\d\.]+)s", corpo)
                        if m:
                            espera = max(float(m.group(1)) + 1.0, 3.0)
                    except Exception:
                        pass
                    time.sleep(espera)
                    continue
                _handle_error(res, model=model_name)

                yield from parse_openai_sse_stream(res.iter_lines(), tool_calls_map)
            break
        except httpx.RequestError as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Erro de conexão com Groq API: {e}")
            import time
            time.sleep(1.5)

    if tool_calls_map:
        if iteration >= max_iterations:
            yield f"\n[Aviso: Limite de {max_iterations} execuções de ferramentas atingido para esta rodada.]\n"
            return

        process_tool_calls_map(tool_calls_map, mensagens, iteration=iteration)
        yield from gerar_resposta_stream(mensagens, iteration=iteration + 1, max_iterations=max_iterations, model=model_name)

class GroqService(BaseService):
    def __init__(self, model: str = None):
        self.model = model or config.GROQ_MODEL

    @property
    def nome_provedor(self) -> str:
        return f"GROQ ({self.model})"

    def gerar_resposta_stream(self, mensagens: list):
        return gerar_resposta_stream(mensagens, model=self.model)
