import json
import logging
from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Tuple, Generator

logger = logging.getLogger(__name__)

class BaseService(ABC):
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
    for line in lines_iterator:
        if not line.startswith("data: "):
            continue
        if line.strip() == "data: [DONE]":
            break
        try:
            data = json.loads(line[6:])
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
        except (json.JSONDecodeError, KeyError, IndexError):
            logger.debug("Linha SSE malformada ignorada no parse_openai_sse_stream", exc_info=True)


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
    calls = []
    responses = []

    for tc_idx in sorted(tool_calls_map.keys()):
        tc_data = tool_calls_map[tc_idx]
        name = tc_data.get("name")
        if not name:
            continue

        try:
            args = json.loads(tc_data["args_str"]) if tc_data.get("args_str") else {}
        except Exception:
            args = {}

        import uuid
        call_id = tc_data.get("id") or f"call_{tc_idx}_{iteration}_{uuid.uuid4().hex[:8]}"
        func_call = {
            "id": call_id,
            "name": name,
            "args": args
        }
        calls.append({
            "role": "functionCall",
            "functionCall": func_call
        })

        result = executar_tool(name, args)

        responses.append({
            "role": "functionResponse",
            "id": call_id,
            "name": name,
            "content": result
        })
        has_executed = True

    for c in calls:
        mensagens.append(c)
    for r in responses:
        mensagens.append(r)

    return has_executed
