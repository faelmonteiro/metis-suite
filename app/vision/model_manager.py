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
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro"
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

def _canonical_provider_name(name_or_id: str) -> str:
    """Normaliza nomes/IDs de provedores conhecidos para seu padrão canônico."""
    val = (name_or_id or "").strip().lower()
    if "openrouter" in val:
        return "OpenRouter"
    if "gemini" in val:
        return "Gemini"
    if "groq" in val:
        return "Groq"
    if "nvidia" in val:
        return "NVIDIA"
    if "ollama" in val:
        return "Ollama"
    if "g4f" in val:
        return "G4F"
    return (name_or_id or "").strip()

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
    content = json.dumps(data, indent=2, ensure_ascii=False)
    p.write_text(content, encoding="utf-8")

    # Mantém réplicas existentes sincronizadas
    replicas = [
        Path.home() / ".local/share/metis/app/config_models.json",
        Path.home() / "Metis" / "config_models.json",
        Path(__file__).resolve().parent.parent / "config_models.json",
    ]
    for rep in replicas:
        if rep != p and rep.exists() and rep.is_file():
            try:
                rep.write_text(content, encoding="utf-8")
            except Exception:
                pass

def get_providers() -> List[str]:
    """Retorna a lista de provedores/categorias disponíveis sem duplicações (incluindo servidores customizados)."""
    cfg = load_models_config(force_reload=True)
    provs = []
    seen_lower = set()

    for p in cfg.get("builtin_models", {}).keys():
        norm = _canonical_provider_name(p)
        key = norm.lower()
        if key not in seen_lower:
            seen_lower.add(key)
            provs.append(norm)

    for srv in cfg.get("custom_servers", []):
        nome = (srv.get("nome") or "").strip()
        srv_id = (srv.get("id") or "").strip()
        base_url = (srv.get("base_url") or "").strip().lower()

        # Identifica se é OpenRouter ou outra IA nativa mapeada em servidores customizados
        if "openrouter" in srv_id.lower() or "openrouter" in nome.lower() or "openrouter.ai" in base_url:
            canonical = "OpenRouter"
        else:
            canonical = _canonical_provider_name(nome or srv_id)

        if canonical and canonical.lower() not in seen_lower:
            seen_lower.add(canonical.lower())
            provs.append(canonical)

    return provs

def get_models_for_provider(provider: str) -> List[str]:
    """Retorna a lista de modelos de uma categoria específica (mesclando builtin e custom_servers se aplicável)."""
    cfg = load_models_config(force_reload=True)
    prov_canon = _canonical_provider_name(provider)
    prov_lower = prov_canon.lower()

    models = []
    seen = set()

    # 1. Procura em builtin_models
    builtin = cfg.get("builtin_models", {})
    for k, v in builtin.items():
        if _canonical_provider_name(k).lower() == prov_lower:
            for m in v:
                if m not in seen:
                    seen.add(m)
                    models.append(m)

    # 2. Procura em custom_servers (mescla para OpenRouter e outros servidores mapeados)
    for srv in cfg.get("custom_servers", []):
        srv_nome = (srv.get("nome") or "").strip()
        srv_id = (srv.get("id") or "").strip().lower()
        srv_url = (srv.get("base_url") or "").strip().lower()
        is_match = False
        if prov_lower == "openrouter" and ("openrouter" in srv_id or "openrouter" in srv_nome.lower() or "openrouter.ai" in srv_url):
            is_match = True
        elif _canonical_provider_name(srv_nome).lower() == prov_lower or srv_id == prov_lower:
            is_match = True

        if is_match:
            for m in srv.get("modelos", []):
                if m not in seen:
                    seen.add(m)
                    models.append(m)

    return models

def add_model_to_provider(provider: str, model_id: str) -> bool:
    """Adiciona um novo modelo a uma categoria (builtin ou custom_servers)."""
    model_id = model_id.strip()
    if not model_id:
        return False
    cfg = load_models_config(force_reload=True)
    if "builtin_models" not in cfg:
        cfg["builtin_models"] = {}

    prov_canon = _canonical_provider_name(provider)
    prov_lower = prov_canon.lower()
    added = False

    # 1. Verifica se existe em builtin_models
    matched_prov = None
    for k in cfg["builtin_models"].keys():
        if _canonical_provider_name(k).lower() == prov_lower:
            matched_prov = k
            break

    if matched_prov:
        if model_id not in cfg["builtin_models"][matched_prov]:
            cfg["builtin_models"][matched_prov].append(model_id)
            added = True

    # 2. Verifica se é um servidor customizado (ou se OpenRouter está em ambos)
    for srv in cfg.get("custom_servers", []):
        srv_nome = (srv.get("nome") or "").strip()
        srv_id = (srv.get("id") or "").strip().lower()
        srv_url = (srv.get("base_url") or "").strip().lower()
        is_match = False
        if prov_lower == "openrouter" and ("openrouter" in srv_id or "openrouter" in srv_nome.lower() or "openrouter.ai" in srv_url):
            is_match = True
        elif _canonical_provider_name(srv_nome).lower() == prov_lower or srv_id == prov_lower:
            is_match = True

        if is_match:
            if "modelos" not in srv:
                srv["modelos"] = []
            if model_id not in srv["modelos"]:
                srv["modelos"].append(model_id)
                added = True

    # 3. Se não existe em nenhum lugar, cria em builtin_models
    if not matched_prov and not added:
        cfg["builtin_models"][prov_canon] = [model_id]
        added = True

    if added:
        save_models_config(cfg)
        return True
    return False

def remove_model_from_provider(provider: str, model_id: str) -> bool:
    """Remove um modelo de uma categoria (builtin ou custom_servers) e ajusta o modelo ativo se necessário."""
    cfg = load_models_config(force_reload=True)
    prov_canon = _canonical_provider_name(provider)
    prov_lower = prov_canon.lower()
    removed = False

    # 1. Tenta remover de builtin_models
    for k, mlist in cfg.get("builtin_models", {}).items():
        if _canonical_provider_name(k).lower() == prov_lower and model_id in mlist:
            mlist.remove(model_id)
            removed = True

    # 2. Tenta remover de custom_servers
    for srv in cfg.get("custom_servers", []):
        srv_nome = (srv.get("nome") or "").strip()
        srv_id = (srv.get("id") or "").strip().lower()
        srv_url = (srv.get("base_url") or "").strip().lower()
        is_match = False
        if prov_lower == "openrouter" and ("openrouter" in srv_id or "openrouter" in srv_nome.lower() or "openrouter.ai" in srv_url):
            is_match = True
        elif _canonical_provider_name(srv_nome).lower() == prov_lower or srv_id == prov_lower:
            is_match = True

        if is_match:
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
    prov_canon = _canonical_provider_name(provider)
    prov_lower = prov_canon.lower()
    edited = False

    # 1. Tenta editar em builtin_models
    for k, mlist in cfg.get("builtin_models", {}).items():
        if _canonical_provider_name(k).lower() == prov_lower and old_model_id in mlist:
            idx = mlist.index(old_model_id)
            mlist[idx] = new_model_id
            edited = True
            break

    # 2. Tenta editar em custom_servers
    for srv in cfg.get("custom_servers", []):
        srv_nome = (srv.get("nome") or "").strip()
        srv_id = (srv.get("id") or "").strip().lower()
        srv_url = (srv.get("base_url") or "").strip().lower()
        is_match = False
        if prov_lower == "openrouter" and ("openrouter" in srv_id or "openrouter" in srv_nome.lower() or "openrouter.ai" in srv_url):
            is_match = True
        elif _canonical_provider_name(srv_nome).lower() == prov_lower or srv_id == prov_lower:
            is_match = True

        if is_match:
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
    Garante deduplicação estrita de provedores (ex: OpenRouter nunca duplicado).
    """
    cfg = load_models_config(force_reload=True)
    grouped = []
    grouped_by_key = {}

    # 1. Provedores em builtin_models
    for prov_name, models_list in cfg.get("builtin_models", {}).items():
        canon_name = _canonical_provider_name(prov_name)
        prov_key = canon_name.lower()
        icon = get_provider_icon(prov_key)
        
        if prov_key not in grouped_by_key:
            grp = {
                "provider": canon_name,
                "key": prov_key,
                "icon": icon,
                "models": list(models_list)
            }
            grouped.append(grp)
            grouped_by_key[prov_key] = grp
        else:
            cur_models = grouped_by_key[prov_key]["models"]
            for m in models_list:
                if m not in cur_models:
                    cur_models.append(m)

    # 2. Modelos em custom_servers
    for srv in cfg.get("custom_servers", []):
        srv_nome = (srv.get("nome") or "Custom").strip()
        srv_id = (srv.get("id") or srv_nome).strip().lower()
        srv_url = (srv.get("base_url") or "").strip().lower()

        if "openrouter" in srv_id or "openrouter" in srv_nome.lower() or "openrouter.ai" in srv_url:
            canon_key = "openrouter"
            canon_name = "OpenRouter"
        else:
            canon_name = _canonical_provider_name(srv_nome)
            canon_key = canon_name.lower()

        icon = get_provider_icon(canon_key)
        srv_models = list(srv.get("modelos", []))

        if canon_key in grouped_by_key:
            # Já existe esse provedor (ex: OpenRouter builtin): mescla modelos sem duplicar o menu!
            existing_models = grouped_by_key[canon_key]["models"]
            for m in srv_models:
                if m not in existing_models:
                    existing_models.append(m)
        else:
            grp = {
                "provider": canon_name,
                "key": canon_key,
                "icon": icon,
                "models": srv_models
            }
            grouped.append(grp)
            grouped_by_key[canon_key] = grp

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

