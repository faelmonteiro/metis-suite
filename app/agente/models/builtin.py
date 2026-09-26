"""
Catálogo de modelos builtin (nativos) do Metis.
Fonte única de verdade para modelos padrão por provedor.
"""
from typing import Dict, List, Any


# Modelos builtin por provedor (canônicos)
BUILTIN_MODELS: Dict[str, List[str]] = {
    "NVIDIA": [
        "meta/llama-3.2-11b-vision-instruct",
        "meta/llama-3.2-90b-vision-instruct",
        "deepseek-ai/deepseek-r1",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "nvidia/nemotron-3-ultra",
        "google/gemma-2-27b-it",
    ],
    "Gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-1.5-flash-8b",
    ],
    "OpenRouter": [
        "liquid/lfm-2.5-2.6b:free",
        "inclusionai/ling-3.0-flash-fin:free",
        "minimax/minimax-m3:free",
        "poolside/laguna-s-2.1:free",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
    ],
    "Ollama": [
        "llama3.2-vision:11b",
        "qwen3.5:9b",
        "qwen3.5:4b",
        "llama3.2:3b",
        "llama3.1:8b",
        "deepseek-r1:7b",
        "deepseek-r1:14b",
        "codellama:7b",
    ],
    "Groq": [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "G4F": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4",
    ],
}


# Servidores customizados padrão
DEFAULT_CUSTOM_SERVERS: List[Dict] = [
    {
        "id": "openrouter",
        "nome": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "modelos": [],
        "modelo_atual": "",
    },
    {
        "id": "deepseek",
        "nome": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "modelos": [],
        "modelo_atual": "",
    },
]


def get_builtin_models() -> Dict[str, List[str]]:
    """Retorna copia do catalogo builtin mesclado com os overrides persistidos.

    O config_models.json e autoritativo: provedores presentes no config
    substituem os padroes, refletindo remocoes e adicoes do usuario.
    Modelos marcados como removidos (removed_models) nunca reaparecem.
    """
    removed = _persisted_removed_models()
    result = {k: list(v) for k, v in BUILTIN_MODELS.items()}
    for provider, models in _persisted_builtin_models().items():
        result[_canonical_provider_name(provider)] = list(models)
    _apply_removed_filter(result, removed)
    return {k: v for k, v in result.items() if v}


def _apply_removed_filter(result: Dict[str, List[str]], removed: Dict[str, List[str]]) -> None:
    """Remove de `result` os modelos que o usuário já excluiu (por provedor)."""
    for canon, mlist in list(result.items()):
        removed_set = {m.strip().lower() for m in removed.get(canon, [])}
        if not removed_set:
            continue
        result[canon] = [m for m in mlist if m.strip().lower() not in removed_set]


def get_models_for_provider(provider: str) -> List[str]:
    """Retorna modelos de um provedor.

    Prioriza a lista persistida no config (autoritativa), com fallback para o
    catalogo padrao e mesclagem de modelos de servidores customizados que
    correspondam ao provedor (ex: OpenRouter).
    """
    provider_norm = provider.strip().lower()
    result: List[str] = []

    found = False
    for pkey, mlist in _persisted_builtin_models().items():
        if _canonical_provider_name(pkey).lower() == provider_norm or pkey.strip().lower() == provider_norm:
            result = list(mlist)
            found = True
            break
    if not found:
        for k, v in BUILTIN_MODELS.items():
            if k.lower() == provider_norm:
                result = list(v)
                break

    # Remove modelos que o usuário marcou como excluídos (legado), p/ não ressuscitar
    removed = _persisted_removed_models()
    if removed.get(_canonical_provider_name(provider)):
        removed_set = {m.strip().lower() for m in removed[_canonical_provider_name(provider)]}
        result = [m for m in result if m.strip().lower() not in removed_set]

    # Mescla modelos de servidores customizados correspondentes (deduplicado)
    for srv in _persisted_custom_servers():
        srv_nome = (srv.get("nome") or "").strip()
        srv_id = (srv.get("id") or "").strip().lower()
        srv_url = (srv.get("base_url") or "").strip().lower()

        is_match = False
        if provider_norm == "openrouter":
            is_match = (
                "openrouter" in srv_id
                or "openrouter" in srv_nome.lower()
                or "openrouter.ai" in srv_url
            )
        elif _canonical_provider_name(srv_nome).lower() == provider_norm or srv_id == provider_norm:
            is_match = True

        if is_match:
            for m in srv.get("modelos", []):
                if m not in result:
                    result.append(m)

    return result


def get_all_providers() -> List[str]:
    """Retorna lista de todos os provedores builtin."""
    return list(BUILTIN_MODELS.keys())


def add_builtin_model(provider: str, model: str) -> bool:
    """Adiciona modelo ao builtin (persiste no config via custom.py)."""
    provider_canon = _canonical_provider_name(provider)
    if provider_canon in BUILTIN_MODELS:
        if model not in BUILTIN_MODELS[provider_canon]:
            BUILTIN_MODELS[provider_canon].append(model)
            return True
    return False


def remove_builtin_model(provider: str, model: str) -> bool:
    """Remove modelo do builtin."""
    provider_canon = _canonical_provider_name(provider)
    if provider_canon in BUILTIN_MODELS:
        if model in BUILTIN_MODELS[provider_canon]:
            BUILTIN_MODELS[provider_canon].remove(model)
            return True
    return False


def _persisted_builtin_models() -> Dict[str, List[str]]:
    """Carrega a lista persistida de modelos por provedor do config (com fallback)."""
    try:
        from .storage import load_config
        return dict(load_config().get("builtin_models", {}))
    except Exception:
        return {}


def _persisted_custom_servers() -> List[Dict[str, Any]]:
    """Carrega servidores customizados persistidos do config (com fallback)."""
    try:
        from .storage import load_config
        return list(load_config().get("custom_servers", []))
    except Exception:
        return []


def _persisted_removed_models() -> Dict[str, List[str]]:
    """Carrega o registro legado de modelos removidos (dict provider->modelos)."""
    try:
        from .storage import load_config
        rm = load_config().get("removed_models", {})
        return dict(rm) if isinstance(rm, dict) else {}
    except Exception:
        return {}


def _canonical_provider_name(name: str) -> str:
    """Normaliza nome do provedor para forma canônica."""
    name_lower = name.strip().lower()
    mapping = {
        "nvidia": "NVIDIA",
        "gemini": "Gemini",
        "openrouter": "OpenRouter",
        "openrouter.ai": "OpenRouter",
        "ollama": "Ollama",
        "groq": "Groq",
        "g4f": "G4F",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "mistral": "Mistral",
        "deepseek": "DeepSeek",
    }
    return mapping.get(name_lower, name.strip().title())


def merge_builtin_with_config(config_builtin: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Mescla builtin padrão com o que veio do config (modelos adicionados pelo usuário).
    O config vence para modelos customizados.
    """
    result = get_builtin_models()
    for provider, models in config_builtin.items():
        provider_canon = _canonical_provider_name(provider)
        if provider_canon not in result:
            result[provider_canon] = []
        # Adiciona modelos do config que não estão no builtin padrão
        for m in models:
            if m not in result[provider_canon]:
                result[provider_canon].append(m)
    return result