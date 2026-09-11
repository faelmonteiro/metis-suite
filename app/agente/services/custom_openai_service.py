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
from agente.services.base import BaseService, parse_openai_sse_stream, process_tool_calls_map

logger = logging.getLogger(__name__)


class CustomOpenAIService(BaseService):
    def __init__(self, server_info: dict):
        self.server_info = server_info
        self.nome = server_info.get("nome", "Custom API")
        raw_base_url = server_info.get("base_url", "")
        if "openrouter.ai" in raw_base_url.lower() and not raw_base_url.endswith("/api/v1/chat/completions"):
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
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

        from agente.services.tools_defs import OPENAI_TOOLS_DECLARATION
        import mimetypes

        formatted_messages = []
        last_call_id = None

        for m in mensagens:
            role_raw = m.get("role", "")

            if role_raw == "system":
                formatted_messages.append({"role": "system", "content": m.get("content", "")})
                continue

            if role_raw == "functionCall":
                import uuid
                args_data = m["functionCall"].get("args", {})
                args_str = json.dumps(args_data) if isinstance(args_data, dict) else str(args_data)
                call_id = m["functionCall"].get("id") or f"call_{len(formatted_messages)}_{uuid.uuid4().hex[:8]}"
                m["functionCall"]["id"] = call_id
                last_call_id = call_id
                tc_obj = {
                    "id": call_id,
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
                import uuid
                call_id = m.get("id") or last_call_id or f"call_{len(formatted_messages)}_{uuid.uuid4().hex[:8]}"
                formatted_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
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
                        logger.error(f"Falha ao ler mídia {path}: {e}")

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
            "model": self.modelo,
            "messages": formatted_messages,
            "stream": stream,
            "max_tokens": getattr(config, "MAX_OUTPUT_TOKENS", 4096),
            "temperature": getattr(config, "CUSTOM_TEMPERATURE", getattr(config, "DEFAULT_TEMPERATURE", 0.7)),
        }

        # Adiciona ferramentas caso habilitadas
        try:
            if OPENAI_TOOLS_DECLARATION:
                payload["tools"] = OPENAI_TOOLS_DECLARATION
                payload["tool_choice"] = "auto"
        except Exception:
            pass

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
            raise RuntimeError(f"{self.nome} API ({res.status_code}): {msg}")

    def gerar_resposta_stream(self, mensagens: list, iteration: int = 0, max_iterations: int = 5) -> Iterator[str]:
        headers, payload = self._build_request(mensagens, stream=True)

        from agente.services.http_client import get_http_client
        retries = 3
        for attempt in range(retries):
            tool_calls_map = {}
            try:
                client = get_http_client()
                with client.stream("POST", self.base_url, headers=headers, json=payload) as res:
                    if res.status_code == 429 and attempt < retries - 1:
                        import time
                        time.sleep(3.0)
                        continue
                    self._handle_error(res)

                    yield from parse_openai_sse_stream(res.iter_lines(), tool_calls_map)
                break
            except httpx.RequestError as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"Erro de conexão com {self.nome} ({self.base_url}): {e}")
                import time
                time.sleep(1.5)

        if tool_calls_map:
            if iteration >= max_iterations:
                yield f"\n[Aviso: Limite de {max_iterations} execuções de ferramentas atingido para esta rodada.]\n"
                return

            process_tool_calls_map(tool_calls_map, mensagens, iteration=iteration)
            yield from self.gerar_resposta_stream(mensagens, iteration=iteration + 1, max_iterations=max_iterations)
