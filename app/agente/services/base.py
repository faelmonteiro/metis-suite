import json
import logging
from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Generator

logger = logging.getLogger(__name__)

class RetriableAPIError(RuntimeError):
    """Erro HTTP transitório (429 or 5xx) que merece nova tentativa."""
    pass


class NonRetriableAPIError(RuntimeError):
    """Erro HTTP definitivo (401/403/404/outros 4xx) exibido como mensagem amigável."""
    pass


def calcular_espera_retry_after(res, padrao: float = 3.0, teto: float = 90.0) -> float:
    """Respeita o header Retry-After (segundos ou data) com teto de `teto` segundos.

    Retorna `padrao` quando o header está ausente ou é inválido.
    """
    try:
        headers = getattr(res, "headers", None)
        raw = (headers.get("Retry-After", "") if headers else "").strip()
        if not raw:
            return padrao
        if raw.isdigit():
            return min(max(float(raw), padrao), teto)
        from email.utils import parsedate_to_datetime
        date_header = headers.get("Date", "") if headers else ""
        if date_header:
            diff = (parsedate_to_datetime(raw) - parsedate_to_datetime(date_header)).total_seconds()
            if diff > 0:
                return min(diff, teto)
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
    return padrao


class BaseService(ABC):
    def __init__(self):
        self._active_stream = None
        self._aborted = False

    def abort(self):
        """Interrompe qualquer conexão HTTP ou stream ativo imediatamente."""
        self._aborted = True
        if hasattr(self, "_active_stream") and self._active_stream is not None:
            try:
                self._active_stream.close()
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
            self._active_stream = None

    @abstractmethod
    def gerar_resposta_stream(self, mensagens: list) -> Iterator[str]:
        """Gera a resposta da LLM via streaming, fazendo yield de chunks de string."""
        pass
        
    @property
    @abstractmethod
    def nome_provedor(self) -> str:
        """Retorna o nome do provedor para exibição (ex: 'OLLAMA', 'GROQ', etc)."""
        pass


def parse_openai_sse_stream(
    lines_iterator: Iterator[str],
    tool_calls_map: Dict[int, Dict[str, Any]]
) -> Generator[str, None, None]:
    """
    Parseia linhas SSE no padrão OpenAI (data: {...}), fazendo yield de content e populando tool_calls_map.
    """
    for data in iter_sse_json(lines_iterator):
        choices = data.get("choices", [])
        if not choices:
            continue
        delta = choices[0].get("delta", {})
        
        content = delta.get("content")
        if content:
            yield content
            
        if "tool_calls" in delta:
            for tc in delta["tool_calls"]:
                tc_idx = tc.get("index", 0)
                if tc_idx not in tool_calls_map:
                    tool_calls_map[tc_idx] = {"id": "", "name": "", "args_str": ""}
                if tc.get("id"):
                    tool_calls_map[tc_idx]["id"] = tc["id"]
                if tc.get("function"):
                    if tc["function"].get("name"):
                        tool_calls_map[tc_idx]["name"] = tc["function"]["name"]
                    if tc["function"].get("arguments"):
                        tool_calls_map[tc_idx]["args_str"] += tc["function"]["arguments"]


def iter_sse_json(lines_iterator: Iterator[str]) -> Generator[dict, None, None]:
    """
    Produz objetos JSON a partir de um stream SSE baseado em linhas 'data: {...}'
    (formato OpenAI / Groq / NVIDIA / OpenRouter). Ignora linhas vazias ou inválidas
    e encerra ao encontrar 'data: [DONE]'.
    """
    for line in lines_iterator:
        if not line.startswith("data: "):
            continue
        if line.strip() == "data: [DONE]":
            break
        try:
            yield json.loads(line[6:])
        except json.JSONDecodeError:
            continue


def format_openai_messages(
    mensagens: list,
    descartar_tools: bool = False,
    incluir_midia: bool = True
) -> list:
    """
    Builder único de mensagens no formato OpenAI (chat/completions).

    - 'system' vira mensagem de sistema.
    - 'functionCall' vira assistant.tool_calls (mescla chamadas consecutivas).
    - 'functionResponse' vira mensagem role=tool.
    - Mídia (media_paths) vira image_url em base64 (data URI).
    - Com descartar_tools=True (ex.: NVIDIA NIM), mensagens de ferramenta são
      descartadas e apenas o texto é considerado.
    """
    import mimetypes

    formatted_messages = []

    for m in mensagens:
        role_raw = m.get("role", "")

        if role_raw == "system":
            formatted_messages.append({"role": "system", "content": m.get("content", "")})
            continue

        if role_raw == "functionCall":
            if descartar_tools:
                continue
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
            if descartar_tools:
                continue
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

        if incluir_midia and "media_paths" in m:
            from agente.services.media_cache import get_base64_media
            for path in m["media_paths"]:
                try:
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
                    logger.warning(f"Falha ao ler mídia {path}: {e}")

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

    return formatted_messages


def process_tool_calls_map(
    tool_calls_map: Dict[int, Dict[str, Any]],
    mensagens: list,
    iteration: int = 0
) -> bool:
    """
    Executa as ferramentas reconstruídas a partir de tool_calls_map e anexa as mensagens ao histórico.
    Retorna True se houve ferramentas executadas.
    """
    if not tool_calls_map:
        return False
    from agente.services.tool_executor import executar_tool
    has_executed = False
    for tc_idx in sorted(tool_calls_map.keys()):
        tc_data = tool_calls_map[tc_idx]
        name = tc_data.get("name")
        if not name:
            continue

        args = {}
        json_error = None
        if tc_data.get("args_str"):
            try:
                args = json.loads(tc_data["args_str"])
            except Exception as e:
                json_error = str(e)
                logger.warning(f"Erro ao decodificar JSON dos argumentos de {name}: {e}")

        call_id = tc_data.get("id") or f"call_{tc_idx}_{iteration}"
        func_call = {
            "id": call_id,
            "name": name,
            "args": args if json_error is None else {}
        }
        mensagens.append({
            "role": "functionCall",
            "functionCall": func_call
        })

        if json_error:
            result = (
                f"Erro: os argumentos enviados para a ferramenta '{name}' contêm JSON inválido ({json_error}). "
                f"Texto recebido: {tc_data.get('args_str')}. Por favor, envie novamente com argumentos formatados em JSON válido."
            )
        else:
            result = executar_tool(name, args)

        mensagens.append({
            "role": "functionResponse",
            "id": call_id,
            "name": name,
            "content": result
        })
        has_executed = True
    return has_executed
