import sys
import os
import time
import signal
import socket
import re
import json
import httpx
from pathlib import Path
from xml.sax.saxutils import quoteattr

# Garante encerramento imediato em SIGINT e SIGTERM
signal.signal(signal.SIGINT, lambda s, f: sys.exit(130))
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(130))

# Prioriza IPv4 para evitar hang de DNS/IPv6 em redes sem rota IPv6 externa
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        res = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        if res:
            return res
    except Exception:
        pass
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Executa um comando shell/bash no terminal Linux e retorna o resultado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "O comando bash a ser executado."
                    }
                },
                "required": ["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lê o conteúdo de um arquivo no sistema de arquivos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Caminho do arquivo a ser lido."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Cria ou sobrescreve um arquivo com o conteúdo informado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Caminho do arquivo a ser gravado."
                    },
                    "content": {
                        "type": "string",
                        "description": "Conteúdo completo a ser gravado."
                    }
                },
                "required": ["path", "content"]
            }
        }
    }
]

def load_env():
    paths = [
        Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.home() / "Metis" / ".env",
        Path.home() / ".ZSH" / "ai" / ".env_local",
    ]
    for env_path in paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        val = val.strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if val:
                            os.environ[key.strip()] = val

    # Se OPENROUTER_API_KEY ou OPENROUTER_MODEL não estiverem no .env, carrega de custom_servers em config_models.json
    for cfg_file in [Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / "config_models.json", Path.home() / "Metis" / "config_models.json", Path.home() / ".ZSH" / "ai" / "config_models.json"]:
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                for srv in cfg.get("custom_servers", []):
                    if str(srv.get("id", "")).lower() == "openrouter":
                        if not os.getenv("OPENROUTER_API_KEY") and srv.get("api_key"):
                            os.environ["OPENROUTER_API_KEY"] = srv["api_key"]
                        if not os.getenv("OPENROUTER_MODEL") and srv.get("modelo_atual"):
                            os.environ["OPENROUTER_MODEL"] = srv["modelo_atual"]
                        break
            except Exception:
                pass

def normalizar_prompt_enviado(texto: str) -> str:
    """
    Normaliza o texto antes de processar.
    Une quebras de linha automáticas de tela mantendo blocos de código (```),
    parágrafos explícitos (\n\n) e itens de listas (- , * , 1.).
    """
    if not texto or "\n" not in texto:
        return (texto or "").strip()

    if "```" in texto or "\n\n" in texto:
        return texto.strip()

    linhas = texto.splitlines()
    if any(re.match(r"^\s*([-*•>]|\d+\.)\s+", l) for l in linhas):
        return texto.strip()

    return " ".join(texto.split())

TAG_SEARCH_RE = re.compile(
    r'\[(?:Assistente|Usuário|Sistema|Instruções|Instrução do Agente)\]:'
)

TAG_SPLIT_RE = re.compile(
    r'(\[(?:Assistente|Usuário|Sistema|Instruções|Instrução do Agente)\]:)'
)

def parse_messages(prompt: str):
    prompt = prompt or ""

    if not TAG_SEARCH_RE.search(prompt):
        return [{"role": "user", "content": normalizar_prompt_enviado(prompt)}]

    messages = []
    parts = TAG_SPLIT_RE.split(prompt)

    initial_text = parts[0].strip()
    if initial_text:
        messages.append({
            "role": "user",
            "content": normalizar_prompt_enviado(initial_text)
        })

    for i in range(1, len(parts), 2):
        tag = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""

        if not content:
            continue

        if "Assistente" in tag:
            if "<tool_result>" in content:
                asst_part = content.split("<tool_result>", 1)[0].strip()
                result_part = content.split("<tool_result>", 1)[1]
                result_part = result_part.replace("</tool_result>", "").strip()

                if asst_part:
                    messages.append({"role": "assistant", "content": asst_part})

                if result_part:
                    messages.append({"role": "user", "content": result_part})
            else:
                messages.append({"role": "assistant", "content": content})

        elif "Sistema" in tag or "Instruç" in tag:
            messages.append({"role": "system", "content": content})

        else:
            messages.append({
                "role": "user",
                "content": normalizar_prompt_enviado(content)
            })

    if messages and not any(m.get("role") == "user" for m in messages):
        messages.append({"role": "user", "content": "Execute as instruções acima."})

    return messages if messages else [
        {"role": "user", "content": normalizar_prompt_enviado(prompt)}
    ]

def format_gemini_request(messages):
    system_parts = []
    contents = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            if content:
                system_parts.append(content)
        else:
            gemini_role = "model" if role == "assistant" else "user"
            # Se a última mensagem adicionada tiver a mesma role, mescla as partes (evita erro 400 do Gemini)
            if contents and contents[-1]["role"] == gemini_role:
                if content:
                    contents[-1]["parts"].append({"text": content})
            else:
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content or ""}]
                })

    if not contents:
        contents = [{"role": "user", "parts": [{"text": ""}]}]
    elif contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "Inicie o atendimento."}]})

    req = {"contents": contents}

    if system_parts:
        req["system_instruction"] = {
            "parts": [{"text": "\n\n".join(system_parts)}]
        }

    return req

def clean_cmd_string(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        if len(val) >= 3 and str(val[0]) in ["bash", "sh", "zsh"] and str(val[1]) in ["-c", "-lc", "-cl"]:
            return str(val[2]).strip()
        if len(val) >= 2 and str(val[0]) in ["bash", "sh", "zsh"] and str(val[1]).startswith("-c"):
            return str(val[-1]).strip()
        return " ".join(str(x) for x in val).strip()
    if isinstance(val, dict):
        return clean_cmd_string(val.get("cmd") or val.get("command") or val.get("content") or "")

    s = str(val).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            import ast
            parsed_list = ast.literal_eval(s)
            if isinstance(parsed_list, (list, tuple)):
                return clean_cmd_string(parsed_list)
        except Exception:
            pass
        m = re.search(r"['\"]([^'\"]+)['\"]\s*\]\s*$", s)
        if m:
            return m.group(1).strip()
    return s

def format_tool_call_xml(name: str, args_obj) -> str:
    name = str(name or "bash").strip() or "bash"

    if isinstance(args_obj, list):
        value = clean_cmd_string(args_obj)
        if not value:
            return ""
        if "read" in name or name == "cat":
            return f'<tool_call name="read_file" path={quoteattr(value)}>\n</tool_call>'
        if name in ["bash", "exec", "run_command", "tool.exec"] or "bash" in name:
            return f'<tool_call name="bash">\n{value}\n</tool_call>'
        return f'<tool_call name={quoteattr(name)}>\n{value}\n</tool_call>'

    if not isinstance(args_obj, dict):
        value = clean_cmd_string(args_obj)
        if not value:
            return ""

        if "read" in name or name == "cat":
            return f'<tool_call name="read_file" path={quoteattr(value)}>\n</tool_call>'

        return f'<tool_call name={quoteattr(name)}>\n{value}\n</tool_call>'

    cmd = clean_cmd_string(
        args_obj.get("cmd")
        or args_obj.get("command")
        or args_obj.get("args")
        or ""
    )

    path = str(
        args_obj.get("path")
        or args_obj.get("filepath")
        or ""
    ).strip()

    raw_content = args_obj.get("content")
    if raw_content is None:
        raw_content = cmd or ""

    if not isinstance(raw_content, str):
        raw_content = clean_cmd_string(raw_content)

    if not cmd and not path and not str(raw_content):
        return ""

    if name in ["bash", "exec", "run_command", "tool.exec"] or "bash" in name:
        return f'<tool_call name="bash">\n{cmd or raw_content}\n</tool_call>'

    if "read" in name or name == "cat":
        if not path:
            return ""
        return f'<tool_call name="read_file" path={quoteattr(path)}>\n</tool_call>'

    if "write" in name or name == "create":
        if not path:
            return ""
        return f'<tool_call name="write_file" path={quoteattr(path)}>\n{raw_content}\n</tool_call>'

    if "append" in name:
        if not path:
            return ""
        return f'<tool_call name="append_file" path={quoteattr(path)}>\n{raw_content}\n</tool_call>'

    return f'<tool_call name={quoteattr(name)}>\n{cmd or raw_content}\n</tool_call>'

def extract_tool_from_json(raw_json: str) -> str:
    if not raw_json:
        return ""

    try:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            return ""
        if "error" in data and "name" not in data and "function" not in data:
            return ""
        name = data.get("name") or (data.get("function", {}).get("name") if isinstance(data.get("function"), dict) else "")
        args = data.get("arguments") or (data.get("function", {}).get("arguments") if isinstance(data.get("function"), dict) else data.get("args"))
        if not name and not args and not any(k in data for k in ["cmd", "command", "path", "content"]):
            return ""
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {"cmd": args}
        elif args is None and any(k in data for k in ["cmd", "command", "path", "content"]):
            args = data
        return format_tool_call_xml(name or "bash", args or {})
    except Exception:
        pass

    try:
        fixed = raw_json.strip()
        open_b = fixed.count('{')
        close_b = fixed.count('}')
        if open_b > close_b:
            fixed += '}' * (open_b - close_b)
        data = json.loads(fixed)
        if isinstance(data, dict) and ("error" not in data or "name" in data or "function" in data):
            name = data.get("name") or (data.get("function", {}).get("name") if isinstance(data.get("function"), dict) else "")
            args = data.get("arguments") or (data.get("function", {}).get("arguments") if isinstance(data.get("function"), dict) else data.get("args"))
            if name or args or any(k in data for k in ["cmd", "command", "path", "content"]):
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"cmd": args}
                elif args is None:
                    args = data
                return format_tool_call_xml(name or "bash", args or {})
    except Exception:
        pass

    name_match = re.search(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', raw_json)
    name = name_match.group(1) if name_match else ""

    path_match = re.search(r'["\']path["\']\s*:\s*["\']([^"\']+)["\']', raw_json)
    path = path_match.group(1) if path_match else ""

    content = ""
    content_match = re.search(r'["\']content["\']\s*:\s*"(.*)', raw_json, re.DOTALL)
    if content_match:
        content = content_match.group(1)
        content = re.sub(r'"\s*}\s*}\s*$', '', content)
        content = re.sub(r'"\s*}\s*$', '', content)
        content = re.sub(r'"\s*$', '', content)
        content = content.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
    elif '"cmd":' in raw_json or "'cmd':" in raw_json:
        cmd_match = re.search(r'["\']cmd["\']\s*:\s*"(.*)', raw_json, re.DOTALL)
        if cmd_match:
            content = cmd_match.group(1)
            content = re.sub(r'"\s*}\s*}\s*$', '', content)
            content = re.sub(r'"\s*}\s*$', '', content)
            content = re.sub(r'"\s*$', '', content)
            content = content.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")

    if path or content:
        return format_tool_call_xml(name or "write_file", {"path": path, "content": content})

    return ""

def main():
    if len(sys.argv) < 3:
        print("Uso: python api_ask.py <provider> <prompt>", file=sys.stderr)
        sys.exit(1)

    provider = sys.argv[1].upper()
    prompt = " ".join(sys.argv[2:]).strip()

    load_env()

    try:
        messages = parse_messages(prompt)

        is_agent_prompt = any(k in prompt for k in ["<tool_call", "FERRAMENTAS DISPONÍVEIS", "Instrução do Agente", "/auto", "auto_prompt"])

        api_key = None
        url = None
        headers = {}
        data = {}

        if provider == "GROQ":
            api_key = os.getenv("GROQ_API_KEY")
            model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {"model": model, "messages": messages, "max_tokens": 4096}
            if is_agent_prompt:
                data["tools"] = TOOLS_SCHEMA
        elif provider == "NVIDIA":
            api_key = os.getenv("NVIDIA_API_KEY")
            model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {"model": model, "messages": messages, "max_tokens": 4096}
            if is_agent_prompt:
                data["tools"] = TOOLS_SCHEMA
        elif provider == "OPENROUTER":
            api_key = os.getenv("OPENROUTER_API_KEY")
            model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/reator/Metis",
                "X-Title": "Terminal AI Assistant"
            }
            data = {"model": model, "messages": messages, "max_tokens": 4096}
            if is_agent_prompt:
                data["tools"] = TOOLS_SCHEMA
        elif provider == "GEMINI":
            api_key = os.getenv("GEMINI_API_KEY")
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": api_key or ""
            }
            data = format_gemini_request(messages)
        else:
            found_custom = False
            for cfg_file in [Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / "config_models.json", Path.home() / "Metis" / "config_models.json", Path.home() / ".ZSH" / "ai" / "config_models.json"]:
                if cfg_file.exists():
                    try:
                        with open(cfg_file, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        for srv in cfg.get("custom_servers", []):
                            srv_id = str(srv.get("id", "")).upper()
                            srv_nome = str(srv.get("nome", "")).upper()
                            if provider in [srv_id, srv_nome] or provider.replace(" ", "_") in [srv_id, srv_nome]:
                                url = srv.get("base_url", "")
                                if url and not url.endswith("/chat/completions") and not url.endswith("/generateContent"):
                                    if "openrouter.ai" in url.lower():
                                        url = "https://openrouter.ai/api/v1/chat/completions"
                                    elif url.endswith("/v1") or url.endswith("/v1/"):
                                        url = url.rstrip("/") + "/chat/completions"
                                    else:
                                        url = url.rstrip("/") + "/v1/chat/completions"
                                api_key = srv.get("api_key") or os.getenv(srv.get("api_key_env", f"{provider}_API_KEY"))
                                srv_modelos = srv.get("modelos") or []
                                fallback_m = srv_modelos[0] if (isinstance(srv_modelos, list) and srv_modelos) else ""
                                model = os.getenv(f"{provider}_MODEL") or srv.get("modelo_atual") or fallback_m
                                headers = {
                                    "Authorization": f"Bearer {api_key}",
                                    "Content-Type": "application/json",
                                    "HTTP-Referer": "https://github.com/reator/Metis",
                                    "X-Title": "Terminal AI Assistant"
                                }
                                data = {"model": model, "messages": messages, "max_tokens": 4096}
                                if is_agent_prompt:
                                    data["tools"] = TOOLS_SCHEMA
                                found_custom = True
                                break
                    except Exception:
                        pass
                if found_custom:
                    break

            if not found_custom:
                print(f"Provider {provider} não suportado.", file=sys.stderr)
                sys.exit(1)

        if not api_key:
            print(f"Erro: Chave de API para {provider} não encontrada no .env ou .env_local.", file=sys.stderr)
            sys.exit(1)
        if not url:
            print(f"Erro: URL para o provider {provider} não configurada.", file=sys.stderr)
            sys.exit(1)

        max_retries = 2
        last_error = None
        with httpx.Client(timeout=60.0) as client:
            for attempt in range(max_retries + 1):
                try:
                    resp = client.post(url, headers=headers, json=data)

                    if resp.status_code == 429 and attempt < max_retries:
                        wait_time = 3.0
                        try:
                            err_data = resp.json()
                            msg = err_data.get("error", {}).get("message", "")
                            match = re.search(r'try again in ([0-9\.]+)s', msg)
                            if match:
                                wait_time = float(match.group(1)) + 0.5
                        except Exception:
                            pass
                        time.sleep(wait_time)
                        continue

                    if resp.status_code in [500, 502, 503, 504] and attempt < max_retries:
                        time.sleep(2.0 * (attempt + 1))
                        continue

                    if resp.status_code == 400 and provider == "GROQ":
                        try:
                            err_json = resp.json()
                            failed_gen = err_json.get("error", {}).get("failed_generation", "")
                            tool_xml = extract_tool_from_json(failed_gen)
                            if not tool_xml:
                                tool_xml = extract_tool_from_json(resp.text)
                            if tool_xml:
                                print(tool_xml)
                                sys.exit(0)

                            if "tools" in data:
                                data_fallback = dict(data)
                                data_fallback.pop("tools", None)
                                fb_resp = client.post(url, headers=headers, json=data_fallback)
                                if fb_resp.is_success:
                                    fb_js = fb_resp.json()
                                    fb_msg = fb_js["choices"][0]["message"]["content"]
                                    print(fb_msg)
                                    sys.exit(0)
                        except Exception:
                            pass

                    resp.raise_for_status()
                    js = resp.json()

                    if provider == "GEMINI":
                        candidates = js.get("candidates", [])
                        texts = []
                        if candidates and isinstance(candidates[0], dict):
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if isinstance(part, dict) and part.get("text"):
                                    texts.append(part["text"])

                        if texts:
                            print("\n".join(texts))
                            sys.exit(0)

                        print("Sem resposta do Gemini.", file=sys.stderr)
                        sys.exit(1)
                    else:
                        choices = js.get("choices", [])
                        if choices and "message" in choices[0]:
                            msg = choices[0]["message"]

                            tool_calls = msg.get("tool_calls", [])
                            if tool_calls:
                                xml_parts = []
                                for t in tool_calls:
                                    func = t.get("function", {}) if isinstance(t, dict) else {}
                                    f_name = func.get("name", "bash")
                                    f_args_raw = func.get("arguments", "{}")
                                    try:
                                        f_args = json.loads(f_args_raw) if isinstance(f_args_raw, str) else f_args_raw
                                    except Exception:
                                        f_args = {"cmd": f_args_raw}
                                    xml_res = format_tool_call_xml(f_name, f_args)
                                    if xml_res:
                                        xml_parts.append(xml_res)

                                if xml_parts:
                                    print("\n".join(xml_parts))
                                    sys.exit(0)

                            content = msg.get("content")
                            if content:
                                print(content)
                                sys.exit(0)

                        print(f"Sem resposta de {provider}.", file=sys.stderr)
                        sys.exit(1)

                except (httpx.TimeoutException, httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as net_err:
                    if attempt < max_retries:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    last_error = net_err
                    break
                except httpx.HTTPStatusError as http_err:
                    if http_err.response.status_code in [500, 502, 503, 504] and attempt < max_retries:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    last_error = http_err
                    break

        if last_error:
            if isinstance(last_error, httpx.TimeoutException):
                print(f"⚠️ Erro de Conexão: Tempo limite excedido (Timeout ao comunicar com {provider}). A resposta demorou muito ou a conexão oscilou.", file=sys.stderr)
            elif isinstance(last_error, (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError)):
                print(f"⚠️ Erro de Rede: Falha ao conectar ao servidor de {provider}. Verifique sua conexão com a internet.", file=sys.stderr)
            elif isinstance(last_error, httpx.HTTPStatusError):
                e = last_error
                if e.response.status_code == 400 and provider == "GROQ":
                    try:
                        err_json = e.response.json()
                        failed_gen = err_json.get("error", {}).get("failed_generation", "")
                        if failed_gen:
                            tool_xml = extract_tool_from_json(failed_gen)
                            if tool_xml:
                                print(tool_xml)
                                sys.exit(0)
                    except Exception:
                        pass
                if e.response.status_code == 401:
                    print(f"⚠️ Erro de Autenticação na API {provider} (401): Chave de API inválida ou expirada.", file=sys.stderr)
                elif e.response.status_code == 429:
                    print(f"⚠️ Limite Excedido na API {provider} (429): Cota ou taxa máxima de requisições atingida.", file=sys.stderr)
                elif e.response.status_code in [502, 503, 504]:
                    print(f"⚠️ Servidor Indisponível ({e.response.status_code}) na API {provider}. O provedor pode estar instável ou sobrecarregado no momento.", file=sys.stderr)
                else:
                    print(f"⚠️ Erro HTTP na API {provider} ({e.response.status_code}): {e.response.text}", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"⚠️ Erro na API {provider}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
