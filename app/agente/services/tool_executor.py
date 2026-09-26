"""
Executor centralizado de ferramentas (tools).

Evita a duplicação do loop de busca e execução de ferramentas
entre os diferentes serviços de LLM (Ollama, Groq, Gemini).
"""
import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

_tool_listeners = []
_listeners_lock = threading.Lock()


def register_tool_listener(callback: Callable[[str, dict], None]):
    """Registra um ouvinte para eventos de execução de ferramentas ('tool_started', 'tool_finished')."""
    with _listeners_lock:
        if callback not in _tool_listeners:
            _tool_listeners.append(callback)


def unregister_tool_listener(callback: Callable[[str, dict], None]):
    """Remove um ouvinte de eventos de execução de ferramentas."""
    with _listeners_lock:
        if callback in _tool_listeners:
            _tool_listeners.remove(callback)


def _notify_event(event_type: str, data: dict):
    """Notifica todos os ouvintes registrados sobre eventos de ferramentas de forma segura."""
    with _listeners_lock:
        listeners_copy = list(_tool_listeners)
    for listener in listeners_copy:
        try:
            listener(event_type, data)
        except Exception as e:
            logger.debug(f"Erro em ouvinte de ferramenta ({event_type}): {e}")


def executar_tool(name: str, args: dict) -> str:
    """
    Executa uma ferramenta registrada pelo nome passando os argumentos fornecidos.
    Notifica ouvintes registrados sobre início e fim da execução.
    Retorna o resultado da execução como string.
    """
    from agente.services.tools_defs import AVAILABLE_TOOLS_CALLABLE

    if not isinstance(args, dict):
        args = {}

    start_t = time.monotonic()
    _notify_event("tool_started", {
        "name": name,
        "args": args,
        "start_time": start_t
    })

    if name not in AVAILABLE_TOOLS_CALLABLE:
        logger.warning(f"Ferramenta solicitada não encontrada: {name}")
        err_msg = f"Erro: Ferramenta '{name}' não encontrada no catálogo de ferramentas disponíveis."
        _notify_event("tool_finished", {
            "name": name,
            "args": args,
            "result": err_msg,
            "duration": time.monotonic() - start_t,
            "success": False
        })
        return err_msg

    func = AVAILABLE_TOOLS_CALLABLE[name]
    try:
        resultado = func(**args)
        res_str = str(resultado)
        dur = time.monotonic() - start_t
        is_err = res_str.startswith("Erro:") or res_str.startswith("Acesso negado")
        _notify_event("tool_finished", {
            "name": name,
            "args": args,
            "result": res_str,
            "duration": dur,
            "success": not is_err
        })
        return res_str
    except TypeError as e:
        logger.error(f"Erro nos argumentos da ferramenta {name}: {e}")
        err_msg = f"Erro nos argumentos da ferramenta '{name}': {e}"
        _notify_event("tool_finished", {
            "name": name,
            "args": args,
            "result": err_msg,
            "duration": time.monotonic() - start_t,
            "success": False
        })
        return err_msg
    except Exception as e:
        logger.error(f"Exceção durante execução da ferramenta {name}: {e}")
        err_msg = f"Erro na execução de {name}: {e}"
        _notify_event("tool_finished", {
            "name": name,
            "args": args,
            "result": err_msg,
            "duration": time.monotonic() - start_t,
            "success": False
        })
        return err_msg
