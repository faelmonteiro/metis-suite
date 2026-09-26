"""
Gerenciamento de preferências do usuário e variáveis de ambiente.
"""

import logging
logger = logging.getLogger(__name__)

import os
import threading
from pathlib import Path
from typing import Any, Dict
from .storage import load_config, save_config, CONFIG_DIR


ENV_FILE = CONFIG_DIR / ".env"

# Serializa leitura-modificação-escrita do .env entre threads.
_env_lock = threading.RLock()


def get_preference(key: str, default: Any = None) -> Any:
    """Obtém uma preferência do usuário."""
    config = load_config()
    return config.get("preferences", {}).get(key, default)


def set_preference(key: str, value: Any) -> None:
    """Define uma preferência do usuário."""
    config = load_config()
    if "preferences" not in config:
        config["preferences"] = {}
    config["preferences"][key] = value
    save_config(config)


def get_active_model() -> str:
    """Retorna o modelo ativo global."""
    return get_preference("active_model", "")


def set_active_model(model: str) -> None:
    """Define o modelo ativo global."""
    set_preference("active_model", model)


def get_provider_active_model(provider: str) -> str:
    """Retorna modelo ativo para um provedor específico."""
    active_models = get_preference("active_models", {})
    provider_norm = provider.strip().lower()
    for k, v in active_models.items():
        if k.lower() == provider_norm:
            return v
    return ""


def set_provider_active_model(provider: str, model: str) -> None:
    """Define modelo ativo para um provedor."""
    config = load_config()
    if "preferences" not in config:
        config["preferences"] = {}
    if "active_models" not in config["preferences"]:
        config["preferences"]["active_models"] = {}
    config["preferences"]["active_models"][provider.strip().lower()] = model.strip()
    # Também atualiza o modelo global se for o primeiro
    if not config["preferences"].get("active_model"):
        config["preferences"]["active_model"] = model.strip()
    save_config(config)


def get_removed_servers() -> list:
    """Retorna lista de servidores removidos."""
    config = load_config()
    return config.get("removed_servers", [])


def is_server_removed(server_id: str) -> bool:
    """Verifica se um servidor está na lista de removidos."""
    removed = [s.strip().lower() for s in get_removed_servers()]
    return server_id.strip().lower() in removed


def remove_server(server_id: str) -> None:
    """Marca servidor como removido (soft delete)."""
    config = load_config()
    removed = config.get("removed_servers", [])
    server_lower = server_id.strip().lower()
    if server_lower not in removed:
        removed.append(server_lower)
        config["removed_servers"] = removed
        save_config(config)


def restore_server(server_id: str) -> None:
    """Restaura servidor removido."""
    config = load_config()
    removed = config.get("removed_servers", [])
    server_lower = server_id.strip().lower()
    if server_lower in removed:
        removed.remove(server_lower)
        config["removed_servers"] = removed
        save_config(config)


# --- Variáveis de ambiente (.env) ---

def _load_env_file() -> Dict[str, str]:
    """Carrega .env como dict."""
    with _env_lock:
        env_vars = {}
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def _save_env_file(env_vars: Dict[str, str]) -> None:
    """Salva .env atomicamente."""
    import tempfile
    lines = [f"{k}={v}" for k, v in sorted(env_vars.items())]
    content = "\n".join(lines) + "\n"

    with _env_lock:
        fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(ENV_FILE.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, str(ENV_FILE))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
            raise


def get_env_var(key: str, default: str = "") -> str:
    """Lê variável do .env (com fallback para os.environ)."""
    # Primeiro tenta os.environ (pode ter sido setado na sessão)
    val = os.getenv(key)
    if val is not None:
        return val

    env_vars = _load_env_file()
    return env_vars.get(key, default)


def save_env_var(key: str, value: str) -> None:
    """Salva variável no .env canônico."""
    env_vars = _load_env_file()
    env_vars[key] = value
    _save_env_file(env_vars)
    # Também atualiza os.environ para a sessão atual
    os.environ[key] = value


def remove_env_var(key: str) -> None:
    """Remove variável do .env."""
    env_vars = _load_env_file()
    if key in env_vars:
        del env_vars[key]
        _save_env_file(env_vars)
    # Remove de os.environ se existir
    os.environ.pop(key, None)


# --- Provider State Persistence (sync with Go SaveProviderAndModel) ---

PROVIDER_LABELS = {
    "ollama": "Local: Ollama",
    "g4f": "Web: G4F",
    "gemini": "API: Gemini",
    "groq": "API: Groq",
    "nvidia": "API: NVIDIA",
    "openrouter": "API: OpenRouter",
}

PROVIDER_NUMS = {
    "ollama": "1",
    "g4f": "2",
    "gemini": "3",
    "groq": "4",
    "nvidia": "5",
    "openrouter": "6",
}

PROVIDER_ENV_VARS = {
    "ollama": "OLLAMA_MODEL",
    "g4f": "G4F_MODEL",
    "gemini": "GEMINI_MODEL",
    "groq": "GROQ_MODEL",
    "nvidia": "NVIDIA_MODEL",
    "openrouter": "OPENROUTER_MODEL",
}


PROVIDER_DEFAULTS = {
    "ollama": "ollama",
    "g4f": "g4f",
    "gemini": "gemini",
    "groq": "groq",
    "nvidia": "nvidia",
    "openrouter": "custom:openrouter",
}


def _get_provider_dirs() -> list:
    """Retorna todos os diretórios onde salvar estado do provedor."""
    return [
        Path.home() / ".config" / "metis",
        Path.home() / ".ZSH" / "ai",
        Path.home() / ".local" / "share" / "metis" / "zsh",
    ]


def save_provider_state(provider: str, model: str = "") -> None:
    """
    Salva estado do provedor ativo (igual ao Go SaveProviderAndModel).
    Atualiza: .fix_ia_selected, .last_provider, .last_theme, .env files e preferences.
    """
    provider_norm = provider.strip().lower()
    clean_key = provider_norm[7:] if provider_norm.startswith("custom:") else provider_norm
    label = PROVIDER_LABELS.get(clean_key, f"API: {provider}")
    num = PROVIDER_NUMS.get(clean_key, clean_key)
    env_var = PROVIDER_ENV_VARS.get(clean_key, f"{clean_key.upper()}_MODEL")
    default_prov = PROVIDER_DEFAULTS.get(clean_key, f"custom:{clean_key}")

    # 1. Salva nos arquivos .fix_ia_selected e .last_provider em todos os diretórios
    for d in _get_provider_dirs():
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / ".fix_ia_selected").write_text(f"{label}\n", encoding="utf-8")
            (d / ".last_provider").write_text(f"{num}\n", encoding="utf-8")
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    # 2. Salva variável DEFAULT_PROVIDER e modelo no .env canônico
    env_vars = _load_env_file()
    env_vars["DEFAULT_PROVIDER"] = default_prov
    if model:
        env_vars[env_var] = model
    _save_env_file(env_vars)

    # 3. Atualiza preferences em config_models.json
    #    Não engole exceções: falha de persistência deve propagar ao chamador.
    config = load_config()
    if "preferences" not in config:
        config["preferences"] = {}
    config["preferences"]["last_active_provider"] = default_prov
    if model:
        config["preferences"]["last_active_model"] = model
        if "active_models" not in config["preferences"]:
            config["preferences"]["active_models"] = {}
        config["preferences"]["active_models"][clean_key] = model
        config["preferences"]["active_models"]["default_provider"] = clean_key
    config["active_provider"] = clean_key
    if model:
        config["active_model"] = model
    save_config(config)

    # 4. Atualiza os.environ para a sessão atual
    os.environ["DEFAULT_PROVIDER"] = default_prov
    if model:
        os.environ[env_var] = model
