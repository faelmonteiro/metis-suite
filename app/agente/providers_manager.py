"""
Gerenciador de modelos e servidores personalizados (OpenAI-compatible) para o Metis.
Wrapper fino sobre o módulo centralizado agente.models.
"""
import logging
from typing import List, Optional

from agente import config

logger = logging.getLogger(__name__)

# Re-exporta técnicas usadas do módulo centralizado
from agente.models import (
    # Storage
    load_config,
    save_config,
    purge_model_from_legacy_files,
    # Builtin models
    BUILTIN_MODELS,
    get_models_for_provider,
    add_builtin_model,
    _canonical_provider_name,
    # Custom servers CRUD
    get_custom_servers,
    get_custom_server,
    add_custom_server,
    remove_custom_server,
    add_model_to_server,
    remove_model_from_server,
    set_server_active_model,
    get_server_models,
    # Preferences & .env
    get_preference,
    set_preference,
    get_removed_servers,
    is_server_removed as _is_server_removed,
    remove_server,
    restore_server,
    save_env_var,
)

# Compatibilidade: alias para funções com nomes ligeiramente diferentes
DEFAULT_MODELS = BUILTIN_MODELS


def carregar_dados() -> dict:
    """Carrega o arquivo config_models.json (compatibilidade)."""
    return load_config()


def salvar_dados(dados: dict) -> None:
    """Salva os dados no arquivo config_models.json com gravação atômica (compatibilidade)."""
    save_config(dados)


def salvar_variavel_env(chave: str, valor: str) -> None:
    """Salva ou atualiza uma variável no arquivo .env (compatibilidade)."""
    save_env_var(chave, valor)
    # Sincroniza em memória para o processo atual
    val_str = str(valor)
    config.__dict__[chave] = val_str


# Preferências (mesmos nomes, delegam para agente.models)
def obter_preferencia(chave: str, default=None):
    return get_preference(chave, default)


def salvar_preferencia(chave: str, valor) -> None:
    set_preference(chave, valor)


# Modelos por provedor
def obter_modelos_provedor(provedor: str, server_id: Optional[str] = None) -> List[str]:
    """Retorna a lista de modelos salvos para um provedor ou servidor customizado."""
    if server_id:
        return get_server_models(server_id)
    return get_models_for_provider(provedor)


def adicionar_modelo_provedor(provedor: str, modelo: str, server_id: Optional[str] = None) -> None:
    """Adiciona um modelo à lista de modelos salvos."""
    modelo = modelo.strip()
    if not modelo:
        return

    if server_id:
        add_model_to_server(server_id, modelo)
        # Sincroniza no builtin se for OpenRouter
        if server_id == "openrouter":
            add_builtin_model("OpenRouter", modelo)
    else:
        # Adiciona ao builtin do provedor
        add_builtin_model(provedor, modelo)
        # Salva na config
        cfg = load_config()
        if "builtin_models" not in cfg:
            cfg["builtin_models"] = {}
        canon = _canonical_provider_name(provedor)
        if canon not in cfg["builtin_models"]:
            cfg["builtin_models"][canon] = []
        if modelo not in cfg["builtin_models"][canon]:
            cfg["builtin_models"][canon].append(modelo)
        save_config(cfg)


def remover_modelo_provedor(provedor: str, modelo: str, server_id: Optional[str] = None) -> bool:
    """Remove um modelo da lista de modelos salvos."""
    modelo = modelo.strip()
    if not modelo:
        return False

    if server_id:
        return remove_model_from_server(server_id, modelo)

    # Remove do builtin
    canon = _canonical_provider_name(provedor)
    cfg = load_config()
    removed = False
    if canon in cfg.get("builtin_models", {}):
        bmodels = cfg["builtin_models"][canon]
        new_models = [m for m in bmodels if m.strip().lower() != modelo.lower()]
        if len(new_models) != len(bmodels):
            cfg["builtin_models"][canon] = new_models
            removed = True

    # Remove de custom_servers com mesmo provedor
    for s in cfg.get("custom_servers", []):
        if s.get("nome", "").lower() == provedor.lower() or s.get("id", "").lower() == provedor.lower():
            mods = s.get("modelos", [])
            new_mods = [m for m in mods if m.strip().lower() != modelo.lower()]
            if len(new_mods) != len(mods):
                s["modelos"] = new_mods
                removed = True
            if s.get("modelo_atual", "").lower() == modelo.lower():
                s["modelo_atual"] = new_mods[0] if new_mods else ""

    if removed:
        save_config(cfg)
        purge_model_from_legacy_files(modelo)
    return removed


# Servidores customizados
def obter_servidores_customizados() -> List[dict]:
    return get_custom_servers()


def obter_servidor_customizado(server_id: str) -> Optional[dict]:
    return get_custom_server(server_id)


def salvar_servidor_customizado(
    nome: str,
    base_url: str,
    api_key: str = "",
    modelo_padrao: str = "",
    api_key_env: str = "",
    modelos_iniciais: Optional[List[str]] = None
) -> dict:
    """Adiciona ou atualiza um servidor customizado preservando modelos existentes."""
    server = add_custom_server(
        nome=nome,
        base_url=base_url,
        api_key=api_key,
        modelo_padrao=modelo_padrao,
        api_key_env=api_key_env,
        modelos_iniciais=modelos_iniciais,
    )
    return server


def remover_servidor_customizado(server_id: str) -> bool:
    return remove_custom_server(server_id)


def atualizar_modelo_ativo_servidor(server_id: str, modelo: str) -> None:
    set_server_active_model(server_id, modelo)


# Servidores removidos (soft delete)
def obter_servidores_removidos() -> List[str]:
    return get_removed_servers()


def is_servidor_removido(provedor_ou_id: str) -> bool:
    return _is_server_removed(provedor_ou_id)


def remover_servidor_provedor(provedor_ou_id: str) -> bool:
    """Remove permanentemente um provedor ou servidor customizado dos arquivos."""
    val = (provedor_ou_id or "").strip().lower()
    if not val:
        return False
    remove_server(val)
    cfg = load_config()
    changed = False
    if "builtin_models" in cfg:
        for k in list(cfg["builtin_models"].keys()):
            if k.lower() == val:
                del cfg["builtin_models"][k]
                changed = True
    if "custom_servers" in cfg:
        before = len(cfg["custom_servers"])
        cfg["custom_servers"] = [s for s in cfg["custom_servers"] if s.get("id", "").lower() != val and s.get("nome", "").lower() != val]
        if len(cfg["custom_servers"]) != before:
            changed = True
    if changed:
        save_config(cfg)
    return True


def restaurar_servidor_provedor(provedor_ou_id: str) -> bool:
    """Restaura um provedor ou servidor removido."""
    val = (provedor_ou_id or "").strip().lower()
    if not val:
        return False
    restore_server(val)
    return True