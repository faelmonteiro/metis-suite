"""
Gerenciador de Modelos e Provedores do Metis Vision.
Wrapper fino que re-exporta do módulo centralizado agente.models.
"""

import logging
logger = logging.getLogger(__name__)

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Adiciona path do Metis principal para importar agente.models
metis_root = Path(__file__).parent.parent
if str(metis_root) not in sys.path:
    sys.path.insert(0, str(metis_root))

# Re-exporta tudo do módulo centralizado
from agente.models import (
    # Storage
    load_config as load_models_config,
    save_config as save_models_config,
    CONFIG_FILE,
    # Builtin models
    BUILTIN_MODELS as DEFAULT_MODELS_DATA,
    get_builtin_models,
    get_models_for_provider,
    get_all_providers,
    _canonical_provider_name,
    # Custom servers CRUD
    get_custom_servers,
    get_custom_server,
    update_custom_server,
    add_model_to_server,
    remove_model_from_server,
    set_server_active_model,
    get_server_models,
    # Preferences & .env
    get_preference as get_user_setting,
    set_preference as set_user_setting,
    get_provider_active_model,
    set_provider_active_model,
    get_removed_servers,
    is_server_removed,
    remove_server as remove_provider,
    restore_server as restore_provider,
    get_env_var,
    save_env_var,
    remove_env_var,
)

# Aliases de compatibilidade
CONFIG_PATH = CONFIG_FILE


def get_config_path() -> str:
    """Retorna o caminho do arquivo de configuração central (config_models.json)."""
    return str(CONFIG_FILE)

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
    return PROVIDER_ICONS.get(provider.lower(), "🤖")


def get_active_model() -> Tuple[str, str]:
    """Retorna (provedor_ativo, modelo_ativo) sincronizado com o Metis.

    Prioridade: estado da GUI do Metis (last_active_*), depois o modelo global
    compartilhado (active_model/active_models) e por fim variáveis de ambiente.
    """
    cfg = load_models_config()
    prefs = cfg.get("preferences", {}) or {}

    def _find_provider(model_id: str) -> str:
        if not model_id:
            return "nvidia"
        for p, models in get_builtin_models().items():
            if model_id in models:
                return _canonical_provider_name(p).lower()
        am = prefs.get("active_models") or {}
        for prov, mod in am.items():
            if str(prov).lower() != "default_provider" and mod == model_id:
                return str(prov).lower()
        return "nvidia"

    # 1. Estado gravado pela GUI do Metis (sincronização bidirecional)
    prov = str(prefs.get("last_active_provider") or "").strip().lower().replace("custom:", "")
    model = str(prefs.get("last_active_model") or "").strip()

    # 2. Fallback: modelo global compartilhado
    if not prov or not model:
        global_model = str(prefs.get("active_model") or "").strip()
        if global_model:
            model = global_model
            prov = _find_provider(global_model)

    # 3. Fallback: provedor por variável de ambiente (ignorando valores numéricos)
    if not prov:
        env_prov = os.getenv("DEFAULT_PROVIDER", "").strip().lower().replace("custom:", "")
        if env_prov and env_prov not in {"1", "2", "3", "4", "5", "6"}:
            prov = env_prov

    if not model:
        try:
            from . import config
            model = config.DEFAULT_MODELS.get(prov, "meta/llama-3.2-11b-vision-instruct")
        except Exception:
            model = "meta/llama-3.2-11b-vision-instruct"

    return (prov or "nvidia"), (model or "meta/llama-3.2-11b-vision-instruct")


def set_active_model(provider: str, model_id: str) -> None:
    """Salva o modelo ativo selecionado no config compartilhado com o Metis.

    Grava o mesmo conjunto de chaves usadas pela GUI do Metis
    (last_active_*, active_model, active_models) para manter a sincronização.
    """
    cfg = load_models_config()
    prefs = cfg.setdefault("preferences", {})
    if not isinstance(prefs, dict):
        prefs = {}
        cfg["preferences"] = prefs
    prefs["active_model"] = model_id
    prefs.setdefault("active_models", {})[provider.strip().lower()] = model_id
    prefs["last_active_provider"] = provider.strip().lower()
    prefs["last_active_model"] = model_id
    save_models_config(cfg)


def get_grouped_model_list() -> List[Dict]:
    """
    Retorna lista estruturada de provedores com seus respectivos modelos.
    Garante deduplicação estrita (ex: OpenRouter nunca duplicado).
    """
    cfg = load_models_config()
    grouped = []
    grouped_by_key = {}
    removed = [str(s).strip().lower() for s in get_removed_servers()]

    # 1. Provedores reais em builtin_models do config
    cfg_builtin = cfg.get("builtin_models", {})
    for prov_name, models_list in cfg_builtin.items():
        canon_name = _canonical_provider_name(prov_name)
        prov_key = canon_name.lower()
        if prov_key in removed or prov_name.lower() in removed:
            continue
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

    # 2. Modelos em custom_servers (sempre incluídos conforme cadastrados pelo usuário)
    for srv in get_custom_servers():
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
            # Já existe esse provedor: mescla modelos sem duplicar o menu
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


def get_removed_providers() -> List[str]:
    return get_removed_servers()


# Funções de sincronização com o Metis
def sync_with_metis() -> dict:
    """
    Sincroniza a Vision com o Metis no arquivo canônico.

    O config compartilhado (~/.config/metis/config_models.json) é a fonte única.
    NÃO mescla mais o config legado da Vision aqui — isso ressuscitava modelos
    que o usuário já tinha excluído. O arquivo legado obsoleto é removido, e só
    os modelos do Ollama local (novos) são sincronizados.
    """
    cfg = load_models_config()

    # 1. Remove o config legado da Vision (schema v1, obsoleto): se ficar no
    #    disco pode voltar a "reviver" modelos excluídos. A fonte única agora é
    #    o config compartilhado do Metis.
    legacy = Path(__file__).parent / "config_models.json"
    if legacy.exists():
        try:
            legacy.unlink()
        except OSError as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    # 2. Sincroniza modelos do Ollama local (apenas modelos novos instalados)
    merged = False
    ollama_synced = False
    try:
        import urllib.request
        host = get_env_var("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ollama_models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        if ollama_models:
            canon = _canonical_provider_name("Ollama")
            cur = cfg.setdefault("builtin_models", {}).setdefault(canon, [])
            for m in ollama_models:
                if m not in cur:
                    cur.append(m)
                    merged = True
            ollama_synced = True
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    if merged:
        save_models_config(cfg)

    return {
        "custom_servers_count": len(get_custom_servers()),
        "servers_count": len(get_custom_servers()),
        "providers_count": len(get_all_providers()),
        "ollama_synced": ollama_synced,
    }


# Compatibilidade: funções que a Vision usa
def get_providers() -> List[str]:
    return [g["provider"] for g in get_grouped_model_list()]


def add_model_to_provider(provider: str, model_id: str) -> bool:
    """Adiciona um modelo à lista de um provedor no config compartilhado com o Metis."""
    cfg = load_models_config()
    if "builtin_models" not in cfg:
        cfg["builtin_models"] = {}
    canon = _canonical_provider_name(provider)
    if canon not in cfg["builtin_models"]:
        cfg["builtin_models"][canon] = []
    if model_id not in cfg["builtin_models"][canon]:
        cfg["builtin_models"][canon].append(model_id)
        save_models_config(cfg)
        return True
    return False


def remove_model_from_provider(provider: str, model_id: str) -> bool:
    """Remove um modelo de um provedor e de servidores customizados correspondentes."""
    cfg = load_models_config()
    prov_canon = _canonical_provider_name(provider)
    prov_lower = prov_canon.lower()
    removed = False

    # 1. builtin_models
    for k, mlist in cfg.get("builtin_models", {}).items():
        if _canonical_provider_name(k).lower() == prov_lower and model_id in mlist:
            mlist.remove(model_id)
            removed = True

    # 2. custom_servers
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
        save_models_config(cfg)
        try:
            from agente.models.storage import purge_model_from_legacy_files
            purge_model_from_legacy_files(model_id)
        except ImportError as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
    return removed


def get_models_for_provider_vision(provider: str) -> List[str]:
    """Wrapper com nome diferente para evitar conflito com importação."""
    return get_models_for_provider(provider)


def add_model_to_provider_vision(provider: str, model_id: str) -> bool:
    """Alias de retrocompatibilidade."""
    return add_model_to_provider(provider, model_id)


def remove_model_from_provider_vision(provider: str, model_id: str) -> bool:
    """Alias de retrocompatibilidade."""
    return remove_model_from_provider(provider, model_id)


def edit_model_in_provider(provider: str, old_model_id: str, new_model_id: str) -> bool:
    cfg = load_models_config()
    prov_canon = _canonical_provider_name(provider)
    prov_lower = prov_canon.lower()
    edited = False

    # 1. builtin_models
    for k, mlist in cfg.get("builtin_models", {}).items():
        if _canonical_provider_name(k).lower() == prov_lower and old_model_id in mlist:
            idx = mlist.index(old_model_id)
            mlist[idx] = new_model_id
            edited = True
            break

    # 2. custom_servers
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
        if cfg.get("preferences", {}).get("active_model") == old_model_id:
            cfg["preferences"]["active_model"] = new_model_id
        save_models_config(cfg)
        return True
    return False


# Exporta tudo
__all__ = [
    "load_models_config",
    "save_models_config",
    "get_config_path",
    "CONFIG_PATH",
    "DEFAULT_MODELS_DATA",
    "get_builtin_models",
    "get_models_for_provider",
    "get_models_for_provider_vision",
    "get_all_providers",
    "get_providers",
    "_canonical_provider_name",
    "get_custom_servers",
    "get_custom_server",
    "add_model_to_provider",
    "add_model_to_provider_vision",
    "remove_model_from_provider",
    "remove_model_from_provider_vision",
    "update_custom_server",
    "add_model_to_server",
    "remove_model_from_server",
    "set_server_active_model",
    "get_server_models",
    "get_user_setting",
    "set_user_setting",
    "get_active_model",
    "set_active_model",
    "get_provider_active_model",
    "set_provider_active_model",
    "get_removed_servers",
    "get_removed_providers",
    "is_server_removed",
    "remove_provider",
    "restore_provider",
    "get_env_var",
    "save_env_var",
    "remove_env_var",
    "get_provider_icon",
    "get_grouped_model_list",
    "get_flat_model_list",
    "sync_with_metis",
    "edit_model_in_provider",
    "PROVIDER_ICONS",
]
