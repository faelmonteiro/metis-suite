"""
Gerenciador de Modelos e Provedores do Metis / ScreenAI.
Permite carregar, salvar, adicionar, editar e remover modelos por categoria com persistência em JSON.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config_models.json"
METIS_CONFIG_PATHS = [
    Path.home() / "Metis" / "config_models.json",
    Path.home() / ".ZSH" / "ai" / "config_models.json"
]

# Nota de arquitetura: A chave 'builtin_models' armazena tanto modelos nativos quanto
# modelos adicionados/customizados pelo usuário para garantir compatibilidade.
DEFAULT_MODELS_DATA = {
    "schema_version": 1,
    "builtin_models": {
        "NVIDIA": [
            "meta/llama-3.2-11b-vision-instruct",
            "meta/llama-3.2-90b-vision-instruct",
            "deepseek-ai/deepseek-r1",
            "meta/llama-3.1-70b-instruct"
        ],
        "Gemini": [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash-lite-preview-02-05"
        ],
        "OpenRouter": [
            "liquid/lfm-2.5-2.6b:free",
            "inclusionai/ling-3.0-flash-fin:free",
            "minimax/minimax-m3:free",
            "poolside/laguna-s-2.1:free"
        ],
        "Ollama": [
            "llama3.2-vision:11b",
            "qwen3.5:9b",
            "qwen3.5:4b",
            "llama3.2:3b",
            "qwen2.5-coder:7b"
        ],
        "Groq": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ],
        "G4F": [
            "gpt-4o-mini",
            "gpt-4o",
            "deepseek-r1",
            "llama-3.3-70b",
            "qwen-2.5-coder-32b"
        ]
    },
    "active_provider": "nvidia",
    "active_model": "meta/llama-3.2-11b-vision-instruct"
}

def get_config_path() -> Path:
    """Retorna o caminho canônico do config_models.json (~/.config/metis/config_models.json)."""
    canonical = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / "config_models.json"
    if canonical.exists():
        return canonical

    canonical.parent.mkdir(parents=True, exist_ok=True)
    # Migração automática se houver cópia em caminho antigo
    candidates = [
        Path.home() / ".local/share/metis/app/config_models.json",
        Path(__file__).resolve().parent.parent / "config_models.json",
        Path.home() / "Metis" / "config_models.json",
    ]
    for leg in candidates:
        if leg.exists() and leg.is_file():
            try:
                import shutil
                shutil.copy2(leg, canonical)
                return canonical
            except Exception:
                pass

    return canonical

def ensure_config_exists() -> Path:
    """Garante que o arquivo de configuração existe, inicializando ou mesclando se necessário."""
    target_path = get_config_path()
    if not target_path.exists():
        save_models_config(DEFAULT_MODELS_DATA)
    return target_path

_CONFIG_CACHE: Optional[dict] = None

def load_models_config(force_reload: bool = False) -> dict:
    """Carrega o JSON de modelos com cache in-memory para alto desempenho."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not force_reload:
        return _CONFIG_CACHE
    p = ensure_config_exists()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if "builtin_models" not in data:
            data["builtin_models"] = DEFAULT_MODELS_DATA["builtin_models"]
        _CONFIG_CACHE = data
        return data
    except Exception:
        _CONFIG_CACHE = dict(DEFAULT_MODELS_DATA)
        return _CONFIG_CACHE

def save_models_config(data: dict):
    """Salva a configuração no arquivo JSON compartilhado e atualiza cache."""
    global _CONFIG_CACHE
    p = get_config_path()
    
    # Preserva chaves existentes no JSON do Metis (como custom_servers, removed_models, preferences)
    if p.exists():
        try:
            existing = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                for k, v in existing.items():
                    if k not in data:
                        data[k] = v
        except Exception:
            pass

    _CONFIG_CACHE = data
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_providers() -> List[str]:
    """Retorna a lista de provedores/categorias disponíveis (incluindo servidores customizados)."""
    cfg = load_models_config(force_reload=True)
    provs = list(cfg.get("builtin_models", {}).keys())
    for srv in cfg.get("custom_servers", []):
        nome = srv.get("nome")
        if nome and nome not in provs:
            provs.append(nome)
    return provs

def get_models_for_provider(provider: str) -> List[str]:
    """Retorna a lista de modelos de uma categoria específica."""
    cfg = load_models_config(force_reload=True)
    builtin = cfg.get("builtin_models", {})
    for k, v in builtin.items():
        if k.lower() == provider.lower():
            return v
    
    for srv in cfg.get("custom_servers", []):
        if srv.get("nome", "").lower() == provider.lower() or srv.get("id", "").lower() == provider.lower():
            return srv.get("modelos", [])
            
    return []

def add_model_to_provider(provider: str, model_id: str) -> bool:
    """Adiciona um novo modelo a uma categoria (builtin ou custom_servers)."""
    model_id = model_id.strip()
    if not model_id:
        return False
    cfg = load_models_config(force_reload=True)
    if "builtin_models" not in cfg:
        cfg["builtin_models"] = {}

    added = False
    # 1. Verifica se existe em builtin_models
    matched_prov = None
    for k in cfg["builtin_models"].keys():
        if k.lower() == provider.lower():
            matched_prov = k
            break

    if matched_prov:
        if model_id not in cfg["builtin_models"][matched_prov]:
            cfg["builtin_models"][matched_prov].append(model_id)
            added = True

    # 2. Verifica se é um servidor customizado (ou se OpenRouter está em ambos)
    for srv in cfg.get("custom_servers", []):
        if srv.get("nome", "").lower() == provider.lower() or srv.get("id", "").lower() == provider.lower():
            if "modelos" not in srv:
                srv["modelos"] = []
            if model_id not in srv["modelos"]:
                srv["modelos"].append(model_id)
                added = True

    # 3. Se não existe em nenhum lugar, cria em builtin_models
    if not matched_prov and not added:
        cfg["builtin_models"][provider] = [model_id]
        added = True

    if added:
        save_models_config(cfg)
        return True
    return False

def remove_model_from_provider(provider: str, model_id: str) -> bool:
    """Remove um modelo de uma categoria (builtin ou custom_servers) e ajusta o modelo ativo se necessário."""
    cfg = load_models_config(force_reload=True)
    removed = False

    # 1. Tenta remover de builtin_models
    for k, mlist in cfg.get("builtin_models", {}).items():
        if k.lower() == provider.lower() and model_id in mlist:
            mlist.remove(model_id)
            removed = True

    # 2. Tenta remover de custom_servers
    for srv in cfg.get("custom_servers", []):
        if srv.get("nome", "").lower() == provider.lower() or srv.get("id", "").lower() == provider.lower():
            mlist = srv.get("modelos", [])
            if model_id in mlist:
                mlist.remove(model_id)
                removed = True

    if removed:
        # Se o modelo removido era o ativo, escolhe o próximo modelo disponível
        active_mod = cfg.get("active_model", "")
        if active_mod == model_id:
            # Tenta pegar outro modelo deste provedor
            remaining = get_models_for_provider(provider)
            if remaining:
                cfg["active_model"] = remaining[0]
            else:
                # Tenta qualquer outro modelo
                flat = get_flat_model_list()
                if flat:
                    cfg["active_provider"] = flat[0][1]
                    cfg["active_model"] = flat[0][2]
        save_models_config(cfg)
        return True
    return False

def edit_model_in_provider(provider: str, old_model_id: str, new_model_id: str) -> bool:
    """Edita um modelo existente (builtin ou custom_servers)."""
    new_model_id = new_model_id.strip()
    if not new_model_id:
        return False
    cfg = load_models_config(force_reload=True)
    edited = False

    # 1. Tenta editar em builtin_models
    for k, mlist in cfg.get("builtin_models", {}).items():
        if k.lower() == provider.lower() and old_model_id in mlist:
            idx = mlist.index(old_model_id)
            mlist[idx] = new_model_id
            edited = True
            break

    # 2. Tenta editar em custom_servers
    if not edited:
        for srv in cfg.get("custom_servers", []):
            if srv.get("nome", "").lower() == provider.lower() or srv.get("id", "").lower() == provider.lower():
                mlist = srv.get("modelos", [])
                if old_model_id in mlist:
                    idx = mlist.index(old_model_id)
                    mlist[idx] = new_model_id
                    edited = True
                    break

    if edited:
        if cfg.get("active_model") == old_model_id:
            cfg["active_model"] = new_model_id
        save_models_config(cfg)
        return True
    return False

def get_active_model() -> Tuple[str, str]:
    """Retorna (provedor_ativo, modelo_ativo)."""
    cfg = load_models_config()
    prov = cfg.get("active_provider", "nvidia")
    mod = cfg.get("active_model", "meta/llama-3.2-11b-vision-instruct")
    return prov, mod

def set_active_model(provider: str, model_id: str):
    """Salva o modelo ativo selecionado."""
    cfg = load_models_config(force_reload=True)
    cfg["active_provider"] = provider.lower()
    cfg["active_model"] = model_id
    save_models_config(cfg)

def get_user_setting(key: str, default=None):
    """Obtém uma preferência persistida do usuário."""
    cfg = load_models_config()
    return cfg.get("user_settings", {}).get(key, default)

def set_user_setting(key: str, value):
    """Salva uma preferência do usuário no arquivo de configuração."""
    cfg = load_models_config(force_reload=True)
    if "user_settings" not in cfg or not isinstance(cfg["user_settings"], dict):
        cfg["user_settings"] = {}
    cfg["user_settings"][key] = value
    save_models_config(cfg)

PROVIDER_ICONS = {
    "nvidia": "⚡",
    "gemini": "💎",
    "openrouter": "🌐",
    "ollama": "🦙",
    "groq": "🚀",
    "g4f": "🤖",
    "anthropic": "🧠",
    "openai": "🔮",
    "mistral": "🌪️",
    "deepseek": "🐳"
}

def get_provider_icon(provider: str) -> str:
    """Retorna o ícone amigável associado a um provedor."""
    return PROVIDER_ICONS.get(provider.lower(), "🤖")

def get_grouped_model_list() -> List[Dict]:
    """
    Retorna lista estruturada de provedores com seus respectivos modelos e metadados.
    Ideal para construção de menus hierárquicos (Submenus de IAs por Provedor).
    """
    cfg = load_models_config(force_reload=True)
    grouped = []
    
    # 1. Provedores em builtin_models
    for prov_name, models_list in cfg.get("builtin_models", {}).items():
        prov_key = prov_name.lower()
        icon = get_provider_icon(prov_key)
        grouped.append({
            "provider": prov_name,
            "key": prov_key,
            "icon": icon,
            "models": list(models_list)
        })
        
    # 2. Modelos em custom_servers
    for srv in cfg.get("custom_servers", []):
        srv_nome = srv.get("nome", "Custom")
        srv_id = srv.get("id", srv_nome).lower()
        icon = get_provider_icon(srv_id)
        if not any(g["key"] == srv_id for g in grouped):
            grouped.append({
                "provider": srv_nome,
                "key": srv_id,
                "icon": icon,
                "models": list(srv.get("modelos", []))
            })
            
    return grouped

def get_flat_model_list() -> List[Tuple[str, str, str]]:
    """
    Retorna lista plana de todos os modelos para retrocompatibilidade:
    [(Nome Exibição, provedor_key, model_id), ...]
    """
    grouped = get_grouped_model_list()
    items = []
    for g in grouped:
        prov_name = g["provider"]
        prov_key = g["key"]
        icon = g["icon"]
        for m in g["models"]:
            short_name = m.split("/")[-1]
            display_name = f"{icon} {prov_name} • {short_name}"
            items.append((display_name, prov_key, m))
    return items

