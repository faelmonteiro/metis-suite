#!/usr/bin/env python3
import sys
import os
import json
import re
from pathlib import Path

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def clean_string(val: str) -> str:
    if not val:
        return ""
    val = ANSI_ESCAPE_RE.sub('', str(val))
    return val.strip()

def get_metis_config_path() -> Path:
    canonical = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / "config_models.json"
    if canonical.exists() and canonical.is_file():
        return canonical

    canonical.parent.mkdir(parents=True, exist_ok=True)
    # Migração automática de locais legados se encontrados
    candidates = [
        Path(os.getenv("METIS_INSTALL_DIR", Path.home() / ".local" / "share" / "metis")) / "app" / "config_models.json",
        Path.home() / "Metis" / "config_models.json",
        Path.home() / ".ZSH" / "ai" / "config_models.json",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            try:
                import shutil
                shutil.copy2(p, canonical)
                return canonical
            except Exception:
                pass
    return canonical

LOCAL_CONFIG_FILE = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / "config_models.json"
GLOBAL_CONFIG_FILE = get_metis_config_path()
ENV_LOCAL = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / ".env"

DEFAULT_MODELS = {
    "Groq": [],
    "Gemini": [],
    "NVIDIA": [],
    "OpenRouter": [],
    "G4F": [],
    "Ollama": []
}

PROVIDER_ENV_MAP = {
    "GROQ": "GROQ_MODEL",
    "GEMINI": "GEMINI_MODEL",
    "NVIDIA": "NVIDIA_MODEL",
    "OPENROUTER": "OPENROUTER_MODEL",
    "OLLAMA": "OLLAMA_MODEL",
    "G4F": "G4F_MODEL"
}

def _basic_provider_key(name: str) -> str:
    p = (name or "").upper().strip()

    if "GROQ" in p:
        return "Groq"
    if "GEMINI" in p:
        return "Gemini"
    if "NVIDIA" in p:
        return "NVIDIA"
    if "OPENROUTER" in p:
        return "OpenRouter"
    if "G4F" in p or "WEB" in p:
        return "G4F"
    if "OLLAMA" in p or "LOCAL" in p:
        return "Ollama"

    return (name or "").strip()

def _env_safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(name or "").upper()).strip("_")

def load_local_data():
    if LOCAL_CONFIG_FILE.exists():
        try:
            with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "builtin_models" not in d:
                    d["builtin_models"] = {}
                if "removed_models" not in d:
                    d["removed_models"] = {}
                if "removed_servers" not in d:
                    d["removed_servers"] = []
                return d
        except Exception:
            pass
    return {"builtin_models": {}, "removed_models": {}, "removed_servers": []}

def save_local_data(data):
    try:
        LOCAL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar {LOCAL_CONFIG_FILE}: {e}", file=sys.stderr)

def get_custom_servers():
    servers = []
    local_data = load_local_data()
    removed_servers = set(s.lower() for s in local_data.get("removed_servers", []))

    for cfg_file in [GLOBAL_CONFIG_FILE, LOCAL_CONFIG_FILE]:
        if not cfg_file.exists():
            continue

        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            for srv in cfg.get("custom_servers", []):
                srv_id = srv.get("id", srv.get("nome", ""))
                srv_nome = srv.get("nome", srv_id)
                key = _basic_provider_key(srv_id)

                if (
                    srv_id
                    and srv_id.lower() not in removed_servers
                    and srv_nome.lower() not in removed_servers
                    and key.lower() not in removed_servers
                    and not any(s["id"].lower() == srv_id.lower() for s in servers)
                ):
                    servers.append({
                        "id": srv.get("id", srv_id),
                        "nome": srv.get("nome", srv_id),
                        "base_url": srv.get("base_url", ""),
                        "modelo_atual": srv.get("modelo_atual", ""),
                        "modelos": srv.get("modelos", [])
                    })
        except Exception:
            pass

    return servers

def get_provider_key(prov_name: str) -> str:
    basic = _basic_provider_key(prov_name)
    p = (prov_name or "").upper().strip()

    for srv in get_custom_servers():
        if srv.get("id", "").upper() == p or srv.get("nome", "").upper() == p:
            if srv.get("id", "").lower() in ["groq", "gemini", "nvidia", "openrouter", "g4f", "ollama"]:
                return basic
            return srv.get("id", prov_name)

    return basic

def load_global_models(key: str):
    global_cfg = get_metis_config_path()
    if global_cfg and global_cfg.exists():
        try:
            with open(global_cfg, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "builtin_models" in d and isinstance(d["builtin_models"], dict):
                    for prov_k, mlist in d["builtin_models"].items():
                        if prov_k.lower() == key.lower() or _basic_provider_key(prov_k).lower() == key.lower():
                            if isinstance(mlist, list) and mlist:
                                return [clean_string(m) for m in mlist if clean_string(m)]

                if "custom_servers" in d and isinstance(d["custom_servers"], list):
                    for srv in d["custom_servers"]:
                        srv_id = str(srv.get("id", "")).lower()
                        srv_nome = str(srv.get("nome", "")).lower()
                        if key.lower() in [srv_id, srv_nome] or _basic_provider_key(srv_id).lower() == key.lower():
                            modelos = srv.get("modelos", [])
                            cur = clean_string(srv.get("modelo_atual", ""))
                            res = [clean_string(m) for m in modelos if clean_string(m)]
                            if cur and cur in res:
                                res = [cur] + [m for m in res if m != cur]
                            elif cur:
                                res = [cur] + res
                            if res:
                                return res
        except Exception:
            pass
    return []

def get_visible_models(provider: str):
    key = get_provider_key(provider)
    
    # 1. Metis global é a fonte de verdade primordial
    models_source = load_global_models(key)

    # 2. Se não encontrou no Metis global, usa o cache local
    if not models_source:
        local_data = load_local_data()
        local_models = local_data.get("builtin_models", {}).get(key, [])
        if local_models:
            models_source = [clean_string(m) for m in local_models if clean_string(m)]

    # 3. Fallback somente se nenhuma fonte possuir modelos
    if not models_source:
        models_source = list(DEFAULT_MODELS.get(key, []))

    # Filtra modelos removidos
    local_data = load_local_data()
    removed = set(clean_string(m) for m in local_data.get("removed_models", {}).get(key, []))

    global_cfg = get_metis_config_path()
    if global_cfg.exists():
        try:
            with open(global_cfg, "r", encoding="utf-8") as f:
                gdata = json.load(f)
                for rm in gdata.get("removed_models", {}).get(key, []):
                    removed.add(clean_string(rm))
        except Exception:
            pass

    combined = []
    seen = set()
    for m in models_source:
        m_clean = clean_string(m)
        if m_clean and m_clean not in seen and m_clean not in removed:
            seen.add(m_clean)
            combined.append(m_clean)

    return combined

def list_models(provider: str):
    for m in get_visible_models(provider):
        print(m)

_MEMO_CACHE = {}

def get_cached_env_map():
    if "env_map" in _MEMO_CACHE:
        return _MEMO_CACHE["env_map"]

    global_cfg = get_metis_config_path()
    env_map = {}
    for env_file in [ENV_LOCAL, global_cfg.parent / ".env", Path.home() / "Metis" / ".env"]:
        if not env_file.exists():
            continue
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v and k not in env_map:
                            env_map[k] = v
        except Exception:
            pass
    _MEMO_CACHE["env_map"] = env_map
    return env_map

def get_active(provider: str) -> str:
    key = get_provider_key(provider)
    env_var = PROVIDER_ENV_MAP.get(provider.upper(), f"{_env_safe(provider)}_MODEL")

    visible = get_visible_models(provider)
    fallback = visible[0] if visible else ""

    env_map = get_cached_env_map()
    candidate = ""
    if env_var in env_map and env_map[env_var]:
        candidate = env_map[env_var]
    elif f"{key.upper()}_MODEL" in env_map and env_map[f"{key.upper()}_MODEL"]:
        candidate = env_map[f"{key.upper()}_MODEL"]

    if candidate and candidate in visible:
        return candidate

    for srv in get_custom_servers():
        if srv["id"].lower() == key.lower() or srv["nome"].lower() == key.lower():
            if srv.get("modelo_atual") and srv["modelo_atual"] in visible:
                return srv["modelo_atual"]
            if srv.get("modelos"):
                for m in srv["modelos"]:
                    if m in visible:
                        return m

    return fallback

def list_api_providers_menu():
    lines = []
    gem_m = get_active("Gemini") or "não configurado"
    groq_m = get_active("Groq") or "não configurado"
    nvd_m = get_active("NVIDIA") or "não configurado"
    openrouter_m = get_active("OpenRouter") or "não configurado"

    lines.append(f"✨ 1. Gemini ({gem_m})|Gemini|{gem_m}")
    lines.append(f"🚀 2. Groq ({groq_m})|Groq|{groq_m}")
    lines.append(f"🟢 3. NVIDIA ({nvd_m})|NVIDIA|{nvd_m}")
    lines.append(f"🪐 4. OpenRouter ({openrouter_m})|OpenRouter|{openrouter_m}")

    idx = 5
    for srv in get_custom_servers():
        srv_id = srv["id"]
        if srv_id.lower() in ["gemini", "groq", "nvidia", "openrouter", "g4f", "ollama"]:
            continue
        srv_nome = srv["nome"] or srv_id
        srv_modelos = srv.get("modelos") or []
        fallback_m = srv_modelos[0] if (isinstance(srv_modelos, list) and srv_modelos) else ""
        cur_m = get_active(srv_id) or srv.get("modelo_atual") or fallback_m
        icon = "🌐"
        lines.append(f"{icon} {idx}. {srv_nome} ({cur_m})|{srv_id}|{cur_m}")
        idx += 1

    for line in lines:
        print(line)

def _salvar_estado_zsh_provider(provider: str) -> None:
    """Sincroniza o provedor ativo com os arquivos lidos pelo ZSH (Ctrl+G)."""
    metis_cfg_dir = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis"))
    if not metis_cfg_dir.exists():
        return
    file_selected = metis_cfg_dir / ".fix_ia_selected"
    file_last = metis_cfg_dir / ".last_provider"

    prov = (provider or "").strip().lower()
    label_map = {
        "ollama": ("Local: Ollama", "1"),
        "g4f": ("Web: G4F", "2"),
        "gemini": ("API: Gemini", "3"),
        "groq": ("API: Groq", "4"),
        "nvidia": ("API: NVIDIA", "5"),
        "openrouter": ("API: OpenRouter", "6"),
    }
    label, num = label_map.get(prov, (f"API: {provider}", provider))
    try:
        file_selected.write_text(f"{label}\n", encoding="utf-8")
        file_last.write_text(f"{num}\n", encoding="utf-8")
    except Exception:
        pass


def set_active_env(env_var: str, value: str):
    env_var = clean_string(env_var)
    value = clean_string(value)

    if not env_var:
        return

    if env_var == "DEFAULT_PROVIDER":
        _salvar_estado_zsh_provider(value)

    global_cfg = get_metis_config_path()
    target_files = [ENV_LOCAL, global_cfg.parent / ".env", Path(__file__).resolve().parent.parent / ".env", Path.home() / "Metis" / ".env"]
    unique_files = []
    for tf in target_files:
        if tf not in unique_files:
            unique_files.append(tf)

    for env_file in unique_files:
        try:
            env_file.parent.mkdir(parents=True, exist_ok=True)
            lines = []
            if env_file.exists():
                lines = env_file.read_text(encoding="utf-8").splitlines()

            found = False
            new_lines = []

            for line in lines:
                if line.startswith(f"{env_var}="):
                    new_lines.append(f'{env_var}="{value}"')
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f'{env_var}="{value}"')

            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            try:
                env_file.chmod(0o600)
            except Exception:
                pass
        except Exception:
            pass
    _MEMO_CACHE.pop("env_map", None)

def add_model(provider: str, model_id: str):
    model_id = clean_string(model_id)
    if not model_id:
        return
    key = get_provider_key(provider)
    local_data = load_local_data()
    models = local_data.setdefault("builtin_models", {}).setdefault(key, [])
    removed = local_data.setdefault("removed_models", {}).setdefault(key, [])

    if model_id in removed:
        removed.remove(model_id)
    if model_id not in models:
        models.insert(0, model_id)

    save_local_data(local_data)

    # Compartilha a adição com o Metis
    global_cfg = get_metis_config_path()
    if global_cfg.exists():
        try:
            with open(global_cfg, "r", encoding="utf-8") as f:
                gdata = json.load(f)
            if key in ["Groq", "Gemini", "NVIDIA", "Ollama", "G4F", "OpenRouter"]:
                gmodels = gdata.setdefault("builtin_models", {}).setdefault(key, [])
                if model_id not in gmodels:
                    gmodels.insert(0, model_id)
                if "removed_models" in gdata and key in gdata["removed_models"]:
                    if model_id in gdata["removed_models"][key]:
                        gdata["removed_models"][key].remove(model_id)
                with open(global_cfg, "w", encoding="utf-8") as f:
                    json.dump(gdata, f, indent=2, ensure_ascii=False)
            elif "custom_servers" in gdata and isinstance(gdata["custom_servers"], list):
                updated = False
                for srv in gdata["custom_servers"]:
                    if str(srv.get("id", "")).lower() == key.lower() or str(srv.get("nome", "")).lower() == key.lower():
                        smodels = srv.setdefault("modelos", [])
                        if model_id not in smodels:
                            smodels.insert(0, model_id)
                        updated = True
                        break
                if updated:
                    with open(global_cfg, "w", encoding="utf-8") as f:
                        json.dump(gdata, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    env_var = PROVIDER_ENV_MAP.get(provider.upper(), f"{_env_safe(provider)}_MODEL")
    if env_var:
        set_active_env(env_var, model_id)

def remove_model(provider: str, model_id: str):
    model_id = clean_string(model_id)
    if not model_id:
        return
    key = get_provider_key(provider)
    local_data = load_local_data()

    models = local_data.setdefault("builtin_models", {}).setdefault(key, [])
    removed = local_data.setdefault("removed_models", {}).setdefault(key, [])

    if model_id in models:
        models.remove(model_id)

    if model_id not in removed:
        removed.append(model_id)

    save_local_data(local_data)

    # Compartilha a remoção com o Metis
    global_cfg = get_metis_config_path()
    if global_cfg.exists():
        try:
            with open(global_cfg, "r", encoding="utf-8") as f:
                gdata = json.load(f)
            if key in ["Groq", "Gemini", "NVIDIA", "Ollama", "G4F", "OpenRouter"]:
                gmodels = gdata.setdefault("builtin_models", {}).setdefault(key, [])
                if model_id in gmodels:
                    gmodels.remove(model_id)
                gremoved = gdata.setdefault("removed_models", {}).setdefault(key, [])
                if model_id not in gremoved:
                    gremoved.append(model_id)
                with open(global_cfg, "w", encoding="utf-8") as f:
                    json.dump(gdata, f, indent=2, ensure_ascii=False)
            elif "custom_servers" in gdata and isinstance(gdata["custom_servers"], list):
                updated = False
                for srv in gdata["custom_servers"]:
                    if str(srv.get("id", "")).lower() == key.lower() or str(srv.get("nome", "")).lower() == key.lower():
                        smodels = srv.setdefault("modelos", [])
                        if model_id in smodels:
                            smodels.remove(model_id)
                        updated = True
                        break
                if updated:
                    with open(global_cfg, "w", encoding="utf-8") as f:
                        json.dump(gdata, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    env_var = PROVIDER_ENV_MAP.get(provider.upper(), f"{_env_safe(provider)}_MODEL")
    remaining = get_visible_models(provider)

    if remaining:
        set_active_env(env_var, remaining[0])

def sync_models():
    global_cfg = get_metis_config_path()
    if not global_cfg.exists():
        print(f"⚠️ Arquivo global {global_cfg} não encontrado.", file=sys.stderr)
        return False

    try:
        with open(global_cfg, "r", encoding="utf-8") as f:
            global_data = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler {global_cfg}: {e}", file=sys.stderr)
        return False

    # Preserva preferências e outras configurações existentes no Metis
    local_data = dict(global_data)
    local_data["builtin_models"] = {}
    local_data["removed_models"] = {}
    local_data["removed_servers"] = list(global_data.get("removed_servers", []))
    local_data["custom_servers"] = []

    synced_counts = {}

    # 1. Sincroniza exatamente os builtin_models do Metis (espelha fielmente os modelos reais)
    if "builtin_models" in global_data and isinstance(global_data["builtin_models"], dict):
        for prov, mlist in global_data["builtin_models"].items():
            if isinstance(mlist, list):
                key = _basic_provider_key(prov)
                models_cleaned = [clean_string(m) for m in mlist if clean_string(m)]
                existentes = local_data["builtin_models"].get(key, [])
                for m in models_cleaned:
                    if m not in existentes:
                        existentes.append(m)
                local_data["builtin_models"][key] = existentes
                synced_counts[key] = len(existentes)

    # 2. Sincroniza removed_models do Metis
    if "removed_models" in global_data and isinstance(global_data["removed_models"], dict):
        for prov, rlist in global_data["removed_models"].items():
            if isinstance(rlist, list):
                key = _basic_provider_key(prov)
                local_data["removed_models"][key] = [clean_string(m) for m in rlist if clean_string(m)]

    # 3. Sincroniza custom_servers do Metis
    if "custom_servers" in global_data and isinstance(global_data["custom_servers"], list):
        for srv in global_data["custom_servers"]:
            srv_id = srv.get("id", srv.get("nome", "Custom"))
            key = _basic_provider_key(srv_id)
            modelos = [clean_string(m) for m in srv.get("modelos", []) if clean_string(m)]
            modelo_atual = clean_string(srv.get("modelo_atual", ""))
            api_key = srv.get("api_key", "")
            api_key_env = srv.get("api_key_env", f"{_env_safe(key)}_API_KEY")

            local_data["custom_servers"].append({
                "id": srv.get("id", srv_id),
                "nome": srv.get("nome", srv_id),
                "base_url": srv.get("base_url", ""),
                "modelo_atual": modelo_atual,
                "modelos": modelos,
                "api_key_env": api_key_env
            })

            # Servidores customizados independentes (não nativos)
            if key.lower() not in ["gemini", "groq", "nvidia", "g4f", "ollama", "openrouter"]:
                if modelos:
                    local_data["builtin_models"][key] = list(modelos)
                    synced_counts[key] = len(modelos)
                if modelo_atual:
                    env_var = PROVIDER_ENV_MAP.get(key.upper(), f"{_env_safe(key)}_MODEL")
                    set_active_env(env_var, modelo_atual)
            elif key.lower() == "openrouter":
                curr_builtin = local_data["builtin_models"].get("OpenRouter", [])
                for m in modelos:
                    if m not in curr_builtin and m not in local_data.get("removed_models", {}).get("OpenRouter", []):
                        curr_builtin.append(m)
                local_data["builtin_models"]["OpenRouter"] = curr_builtin
                synced_counts["OpenRouter"] = len(curr_builtin)

            if api_key and api_key_env:
                set_active_env(api_key_env, api_key)

    # 4. Sincroniza variáveis de ambiente do Metis (.env)
    for env_path in [global_cfg.parent / ".env", Path.home() / "Metis" / ".env"]:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k.endswith("_API_KEY") or k.endswith("_MODEL") or k == "DEFAULT_PROVIDER":
                                set_active_env(k, v)
            except Exception:
                pass

    # 5. Higienização: garante que os modelos ativos no ambiente pertençam aos modelos reais e válidos
    _MEMO_CACHE.pop("env_map", None)
    env_map = get_cached_env_map()
    for prov in ["Groq", "Gemini", "NVIDIA", "OpenRouter", "G4F", "Ollama"]:
        env_var = PROVIDER_ENV_MAP.get(prov.upper(), f"{_env_safe(prov)}_MODEL")
        visible = local_data.get("builtin_models", {}).get(prov, [])
        removed = set(local_data.get("removed_models", {}).get(prov, []))
        valid = [m for m in visible if m not in removed]

        cur = env_map.get(env_var, "")
        if (not cur or cur not in valid) and valid:
            set_active_env(env_var, valid[0])

    total_models = sum(synced_counts.values())

    save_local_data(local_data)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔄 SINCRONIZAÇÃO COM METIS CONCLUÍDA!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for prov, count in synced_counts.items():
        print(f"  • {prov}: {count} modelo(s) real(is) sincronizado(s)")
    print(f"  • Total de modelos reais: {total_models}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return True

def remove_custom_server(server_id: str):
    sid = server_id.lower().strip()
    key = get_provider_key(server_id)

    local_data = load_local_data()
    removed_servers = local_data.setdefault("removed_servers", [])

    if sid not in [s.lower() for s in removed_servers]:
        removed_servers.append(server_id.strip())
    if key.lower() not in [s.lower() for s in removed_servers]:
        removed_servers.append(key)

    if "custom_servers" in local_data and isinstance(local_data["custom_servers"], list):
        local_data["custom_servers"] = [
            s for s in local_data["custom_servers"]
            if s.get("id", "").lower() != sid and s.get("nome", "").lower() != sid
        ]

    if "builtin_models" in local_data and key in local_data["builtin_models"]:
        del local_data["builtin_models"][key]

    save_local_data(local_data)

    if ENV_LOCAL.exists():
        try:
            lines = ENV_LOCAL.read_text(encoding="utf-8").splitlines()
            new_lines = [
                l for l in lines
                if not l.upper().startswith(f"{sid.upper()}_") and not l.upper().startswith(f"{key.upper()}_")
            ]
            ENV_LOCAL.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    print(f"🗑️ Servidor '{server_id}' ocultado do menu local ZSH (o Metis foi mantido intacto)!")
    return True

def cmd_read_input(prompt_text: str = ""):
    try:
        import readline
    except Exception:
        pass

    old_stdin = sys.stdin
    old_stdout = sys.stdout

    try:
        with open("/dev/tty", "r") as tty_in, open("/dev/tty", "w") as tty_out:
            sys.stdin = tty_in
            sys.stdout = tty_out

            try:
                user_val = input(prompt_text)
            except (EOFError, KeyboardInterrupt):
                sys.exit(130)

        sys.stdout = old_stdout
        print(user_val.strip(), flush=True)

    except Exception:
        sys.stdin = old_stdin
        sys.stdout = old_stdout

        try:
            user_val = input(prompt_text)
            print(user_val.strip(), flush=True)
        except (EOFError, KeyboardInterrupt):
            sys.exit(130)
        except Exception:
            sys.exit(1)

def main():
    if len(sys.argv) < 2:
        sys.exit(0)
    cmd = sys.argv[1].lower()
    if cmd == "list" and len(sys.argv) >= 3:
        list_models(sys.argv[2])
    elif cmd == "add" and len(sys.argv) >= 4:
        add_model(sys.argv[2], sys.argv[3])
    elif cmd in ["remove", "rem", "delete"] and len(sys.argv) >= 4:
        for m in sys.argv[3:]:
            remove_model(sys.argv[2], m)
    elif cmd in ["remove_server", "remove_provider", "del_server"] and len(sys.argv) >= 3:
        for s in sys.argv[2:]:
            remove_custom_server(s)
    elif cmd == "set_active" and len(sys.argv) >= 4:
        prov_arg = sys.argv[2].strip()
        val_arg = sys.argv[3].strip()
        if prov_arg.upper() == "DEFAULT_PROVIDER":
            env_var = "DEFAULT_PROVIDER"
        else:
            env_var = PROVIDER_ENV_MAP.get(prov_arg.upper(), f"{_env_safe(prov_arg)}_MODEL")
        set_active_env(env_var, val_arg)
    elif cmd == "get_active" and len(sys.argv) >= 3:
        print(get_active(sys.argv[2]))
    elif cmd in ["list_api_menu", "api_menu"]:
        list_api_providers_menu()
    elif cmd in ["read_input", "input"]:
        prompt_text = sys.argv[2] if len(sys.argv) >= 3 else ""
        cmd_read_input(prompt_text)
    elif cmd in ["sync", "update", "atualizar"]:
        sync_models()

if __name__ == "__main__":
    main()
