"""
Módulo centralizado de gerenciamento de modelos do Metis.
Single source of truth para config_models.json (~/.config/metis/).
"""

# Storage (atomic load/save)
from .storage import load_config, save_config, CONFIG_FILE, CONFIG_DIR, purge_model_from_legacy_files

# Schema (data models)
from .schema import ConfigModel, CustomServer, Preferences, validate_provider_name, validate_model_id

# Builtin models (catalog)
from .builtin import (
    BUILTIN_MODELS,
    DEFAULT_CUSTOM_SERVERS,
    get_builtin_models,
    get_models_for_provider,
    get_all_providers,
    add_builtin_model,
    remove_builtin_model,
    merge_builtin_with_config,
    _canonical_provider_name,
)

# Custom servers CRUD
from .custom import (
    get_custom_servers,
    get_custom_server,
    add_custom_server,
    remove_custom_server,
    update_custom_server,
    add_model_to_server,
    remove_model_from_server,
    set_server_active_model,
    get_server_models,
)

# Preferences & .env
from .preferences import (
    get_preference,
    set_preference,
    get_active_model,
    set_active_model,
    get_provider_active_model,
    set_provider_active_model,
    get_removed_servers,
    is_server_removed,
    remove_server,
    restore_server,
    get_env_var,
    save_env_var,
    remove_env_var,
    save_provider_state,
)

__all__ = [
    # Storage
    "load_config",
    "save_config",
    "CONFIG_FILE",
    "CONFIG_DIR",
    "purge_model_from_legacy_files",
    # Schema
    "ConfigModel",
    "CustomServer",
    "Preferences",
    "validate_provider_name",
    "validate_model_id",
    "is_server_removed",
    # Builtin
    "BUILTIN_MODELS",
    "DEFAULT_CUSTOM_SERVERS",
    "get_builtin_models",
    "get_models_for_provider",
    "get_all_providers",
    "add_builtin_model",
    "remove_builtin_model",
    "merge_builtin_with_config",
    "_canonical_provider_name",
    # Custom servers
    "get_custom_servers",
    "get_custom_server",
    "add_custom_server",
    "remove_custom_server",
    "update_custom_server",
    "add_model_to_server",
    "remove_model_from_server",
    "set_server_active_model",
    "get_server_models",
    # Preferences & .env
    "get_preference",
    "set_preference",
    "get_active_model",
    "set_active_model",
    "get_provider_active_model",
    "set_provider_active_model",
    "get_removed_servers",
    "remove_server",
    "restore_server",
    "get_env_var",
    "save_env_var",
    "remove_env_var",
    "save_provider_state",
]