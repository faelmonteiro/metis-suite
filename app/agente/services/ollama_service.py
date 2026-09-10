import json
import re

import httpx

from agente import config
from agente.services.base import BaseService


import time

_ollama_status_cache = {"ok": None, "timestamp": 0.0}

def verificar_status() -> bool:
    agora = time.monotonic()
    if _ollama_status_cache["ok"] is not None:
        if (agora - _ollama_status_cache["timestamp"]) < getattr(config, "OLLAMA_STATUS_TTL", 30):
            return _ollama_status_cache["ok"]

    try:
        res = httpx.get(f"{config.OLLAMA_HOST}/api/tags", timeout=2.0)
        ok = res.status_code == 200
        _ollama_status_cache.update(ok=ok, timestamp=agora)
        return ok
    except Exception:
        _ollama_status_cache.update(ok=False, timestamp=agora)
        return False


def listar_modelos() -> list:
    try:
        res = httpx.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5.0)

        if res.status_code == 200:
            return [m.get("name", "") for m in res.json().get("models", [])]

    except Exception:
        pass

    return []


# ---------------------------------------------------------------------------
# Heurística de intenção: detecta se a mensagem do usuário é uma
# CONSULTA conceitual (não requer tools) ou uma AÇÃO (requer tools).
# ---------------------------------------------------------------------------
_CONSULTA_PATTERNS = re.compile(
    r"(?i)"
    r"(?:quais?\s+(?:s[aã]o|comandos?|fun[cç][oõ]es?))"       # "quais são", "quais comandos"
    r"|(?:(?:me\s+)?(?:liste|explique|ensine|mostre)\s+(?:comandos?|como))"  # "me liste comandos"
    r"|(?:comandos?\s+(?:b[aá]sicos?|simples|[uú]teis|para|do|de|no)\b)"   # "comandos básicos para linux"
    r"|(?:como\s+(?:fa[cç]o|funciona|usar?|instalar?))"        # "como faço para..."
    r"|(?:o\s+que\s+[eé])"                                     # "o que é"
    r"|(?:diferen[cç]a\s+entre)"                               # "diferença entre"
    r"|(?:para\s+que\s+serve)"                                 # "para que serve"
    r"|(?:me\s+(?:diga|fale|conte)\b)"                         # "me diga", "me fale"
    r"|(?:quando\s+(?:usar?|devo))"                            # "quando usar"
    r"|(?:por\s*que\s+(?:o|a|usar?))"                          # "por que o..." / "por que usar"
)

_ACAO_PATTERNS = re.compile(
    r"(?i)"
    r"(?:(?:^|\s)(?:leia|lê|abra|abre|veja|cria|crie|salve|salva|"
    r"escreva|edite|edita|apague|delete|gere|gera)\s+"
    r"(?:o\s+)?(?:arquivo|diretório|diretorio|pasta|script|pdf|código|codigo|teste))"
    r"|(?:(?:^|\s)(?:rode|roda|execute|executa)\s+(?:o\s+)?(?:comando|teste|script))"
    r"|(?:(?:^|\s)(?:liste|mostra|mostre)\s+(?:o\s+)?(?:arquivo|diretório|diretorio|pasta|script))"
    r"|(?:na\s+(?:minha\s+)?pasta)"
    r"|(?:o\s+que\s+tem\s+(?:na|no|em))"
    r"|(?:(?:na|do|no)\s+(?:meu|minha)\s)"
    r"|(?:(?:meu|minha)\s+(?:pasta|diretório|arquivo))"
    r"|(?:(?:mem[oó]ria|ram|disco|armazenamento|cpu|processador|processo|processos|bateria|temperatura|hardware))"
    r"|(?:(?:espa[cç]o\s+livre|quanto\s+espa[cç]o|quanta\s+mem[oó]ria|quanto\s+de\s+ram|uso\s+de\s+ram|uso\s+de\s+cpu))"
    r"|(?:(?:hyprland|waybar|workspace|workspaces|janela|janelas|monitor|monitores|tela|telas))"
    r"|(?:(?:volume|som|áudio|audio|mudo|mute|brilho))"
    r"|(?:(?:verifique|verifica|cheque|checa|consulte|consulta|como\s+est[aá])\s+(?:o\s+|a\s+|meu\s+|minha\s+)?(?:sistema|pc|computador|m[aá]quina|status))"
)


def _is_action_intent(mensagens: list) -> bool:
    """
    Retorna True SOMENTE se a mensagem do usuário pedir explicitamente uma ação no sistema.
    Para conversas gerais, saudações e dúvidas, retorna False para manter o Ollama 100% puro e veloz.
    """
    last_user_msg = ""
    for m in reversed(mensagens):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    if not last_user_msg:
        return False

    return bool(_ACAO_PATTERNS.search(last_user_msg))


# ---------------------------------------------------------------------------
# Sanitizador: remove blocos JSON de tool calls que vazam no texto
# em modelos pequenos que "alucinam" chamadas de ferramentas.
# ---------------------------------------------------------------------------
_JSON_TOOL_LEAK = re.compile(
    r'```(?:json)?\s*\n?\s*'
    r'\{\s*"name"\s*:\s*"(?:listar_diretorio|ler_arquivo|escrever_arquivo|'
    r'editar_arquivo|executar_comando|gerar_pdf)"'
    r'.*?'
    r'```',
    re.DOTALL
)

_BARE_JSON_TOOL_LEAK = re.compile(
    r'\{\s*"name"\s*:\s*"(?:listar_diretorio|ler_arquivo|escrever_arquivo|'
    r'editar_arquivo|executar_comando|gerar_pdf)"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}',
    re.DOTALL
)


def _sanitizar_json_tools_do_texto(texto: str) -> str:
    """Remove blocos JSON com chamadas de ferramentas que o modelo
    inseriu indevidamente no texto da resposta."""
    texto = _JSON_TOOL_LEAK.sub('', texto)
    texto = _BARE_JSON_TOOL_LEAK.sub('', texto)
    # Limpa linhas em branco consecutivas que ficam após a remoção
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

class OllamaService(BaseService):
    def __init__(self, model: str = None):
        self.model = model or config.OLLAMA_MODEL

    @property
    def nome_provedor(self) -> str:
        return f"OLLAMA ({self.model})"

    def gerar_resposta_stream(self, mensagens: list):
        return gerar_resposta_stream(mensagens, model=self.model)

def gerar_resposta_stream(mensagens: list, iteration: int = 0, max_iterations: int = 5, model: str = None):
    from agente.services.tools_defs import OPENAI_TOOLS_DECLARATION
    import base64

    model_name = model or config.OLLAMA_MODEL
    formatted_messages = []
    
    for m in mensagens:
        role_raw = m.get("role", "")

        if role_raw == "system":
            formatted_messages.append({"role": "system", "content": m.get("content", "")})
            continue

        if role_raw == "functionCall":
            formatted_messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "function": {
                        "name": m["functionCall"]["name"],
                        "arguments": m["functionCall"].get("args", {})
                    }
                }]
            })
            continue
            
        if role_raw == "functionResponse":
            formatted_messages.append({
                "role": "tool",
                "name": m["name"],
                "content": str(m["content"])
            })
            continue

        role = "user" if role_raw == "user" else "assistant"
        
        msg_obj = {
            "role": role,
            "content": str(m.get("content", ""))
        }
        
        images = []
        if "media_paths" in m:
            for path in m["media_paths"]:
                try:
                    from agente.services.media_cache import get_base64_media
                    data = get_base64_media(path)
                    images.append(data)
                except Exception:
                    pass
        
        if images:
            msg_obj["images"] = images
            
        formatted_messages.append(msg_obj)

    # Só inclui tools no payload quando a intenção é de AÇÃO no sistema
    is_action = _is_action_intent(mensagens) or iteration > 0

    if is_action:
        temp_efetiva = min(config.OLLAMA_TEMPERATURE, 0.1)
        system_extra = "Para consultas e diagnósticos do sistema (RAM, disco, processos, janelas), chame imediatamente a ferramenta executar_comando."
        tem_system = False
        for msg in formatted_messages:
            if msg.get("role") == "system":
                msg["content"] = f"{msg.get('content', '')}\n{system_extra}".strip()
                tem_system = True
                break
        if not tem_system:
            formatted_messages.insert(0, {"role": "system", "content": system_extra})
    else:
        temp_efetiva = getattr(config, "OLLAMA_TEMPERATURE", 0.7)

    payload = {
        "model": model_name,
        "messages": formatted_messages,
        "stream": True,
        "options": {
            "num_ctx": config.OLLAMA_NUM_CTX,
            "num_thread": getattr(config, "OLLAMA_NUM_THREADS", 10),
            "temperature": temp_efetiva
        }
    }

    # Só inclui tools no payload quando a intenção é estritamente de AÇÃO
    if is_action:
        payload["tools"] = OPENAI_TOOLS_DECLARATION

    timeout = httpx.Timeout(
        connect=10.0,
        read=300.0,
        write=10.0,
        pool=10.0
    )

    function_calls_detected = []
    buffered_text = []  # Buffer para sanitização em modo CONSULTA

    try:
        from agente.services.http_client import get_http_client
        client = get_http_client(timeout=timeout)
        with client.stream(
            "POST",
            f"{config.OLLAMA_HOST}/api/chat",
            json=payload
        ) as res:
            if res.status_code != 200:
                body = res.read().decode("utf-8")
                raise RuntimeError(f"Erro do Ollama: {body}")

            for line in res.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        msg = data.get("message", {})

                        if "content" in msg and msg["content"]:
                            content_chunk = msg["content"]
                            if is_action:
                                # Em modo AÇÃO: emite direto
                                yield content_chunk
                            else:
                                # Em modo CONSULTA: acumula para sanitizar vazamento de JSON de tools
                                buffered_text.append(content_chunk)
                                # Emite texto acumulado que não pareça início de JSON
                                texto_acumulado = "".join(buffered_text)
                                if "```json" not in texto_acumulado and '{"name":' not in texto_acumulado:
                                    # Seguro emitir chunks liberados
                                    while len(buffered_text) > 1:
                                        yield buffered_text.pop(0)

                        if "tool_calls" in msg and msg["tool_calls"]:
                            for tool_call in msg["tool_calls"]:
                                if "function" in tool_call:
                                    function_calls_detected.append({
                                        "name": tool_call["function"]["name"],
                                        "args": tool_call["function"].get("arguments", {})
                                    })
                    except json.JSONDecodeError:
                        pass
    except httpx.RequestError as e:
        raise RuntimeError(f"Não foi possível conectar ao Ollama: {e}")

    # Flush final do buffer em modo CONSULTA (com sanitização)
    if buffered_text:
        texto_restante = "".join(buffered_text)
        texto_limpo = _sanitizar_json_tools_do_texto(texto_restante)
        if texto_limpo:
            yield texto_limpo

    if function_calls_detected:
        if iteration >= max_iterations:
            yield f"\n[Aviso: Limite de {max_iterations} execuções de ferramentas atingido para esta rodada.]\n"
            return

        from agente.services.tool_executor import executar_tool
        ultimo_resultado = ""
        for fc in function_calls_detected:
            name = fc["name"]
            args = fc.get("args", {})
            
            mensagens.append({
                "role": "functionCall",
                "functionCall": fc
            })
            
            result = executar_tool(name, args)
            ultimo_resultado = result
                
            mensagens.append({
                "role": "functionResponse",
                "name": name,
                "content": result
            })
        
        teve_chunk = False
        for chunk in gerar_resposta_stream(mensagens, iteration=iteration + 1, max_iterations=max_iterations, model=model_name):
            if chunk:
                teve_chunk = True
                yield chunk

        if not teve_chunk:
            if ultimo_resultado and str(ultimo_resultado).strip():
                yield f"\n\n**Resultado da consulta ao sistema:**\n```\n{str(ultimo_resultado).strip()}\n```\n"
