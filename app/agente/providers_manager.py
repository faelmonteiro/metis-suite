"""
Gerenciador de modelos e servidores personalizados (OpenAI-compatible) para o Metis.
Permite salvar histórico de modelos por provedor, alternar sem redigitar,
adicionar novos modelos, remover modelos, e adicionar/remover servidores personalizados (OpenRouter, DeepSeek, etc.).
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

from agente import config
from agente.colors import BOLD, RESET, YELLOW, GREEN, RED, CYAN, GRAY

logger = logging.getLogger(__name__)

CONFIG_FILE = config.PROJECT_ROOT / "config_models.json"

DEFAULT_MODELS: Dict[str, List[str]] = {
    "Groq": [
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ],
    "Gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-lite-preview-02-05"
    ],
    "NVIDIA": [
        "meta/llama-3.1-70b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "mistralai/mistral-large-2-instruct",
        "meta/llama-3.3-70b-instruct",
        "deepseek-ai/deepseek-r1"
    ],
    "G4F": [
        "gpt-4o-mini",
        "gpt-4o",
        "deepseek-r1",
        "claude-3.5-sonnet",
        "llama-3.3-70b",
        "blackboxai",
        "gemini-2.0-flash",
        "qwen-2.5-coder-32b"
    ],
    "OpenRouter": [
        "liquid/lfm-2.5-2.6b:free",
        "inclusionai/ling-3.0-flash-fin:free",
        "minimax/minimax-m3:free",
        "poolside/laguna-s-2.1:free"
    ]
}

DEFAULT_CUSTOM_SERVERS: List[dict] = [
    {
        "id": "openrouter",
        "nome": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "api_key": "",
        "modelo_atual": "liquid/lfm-2.5-2.6b:free",
        "modelos": [
            "liquid/lfm-2.5-2.6b:free",
            "inclusionai/ling-3.0-flash-fin:free",
            "minimax/minimax-m3:free",
            "poolside/laguna-s-2.1:free"
        ]
    }
]


def carregar_dados() -> dict:
    """Carrega o arquivo config_models.json ou inicializa com valores padrão."""
    if not CONFIG_FILE.exists():
        dados_iniciais = {
            "builtin_models": DEFAULT_MODELS,
            "custom_servers": list(DEFAULT_CUSTOM_SERVERS)
        }
        salvar_dados(dados_iniciais)
        return dados_iniciais

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if "builtin_models" not in dados:
                dados["builtin_models"] = dict(DEFAULT_MODELS)
            if "custom_servers" not in dados:
                dados["custom_servers"] = []
            
            # Garante que chaves de provedores padrão existam se forem novas
            for prov, models in DEFAULT_MODELS.items():
                if prov not in dados["builtin_models"]:
                    dados["builtin_models"][prov] = list(models)

            return dados
    except Exception as e:
        logger.error(f"Erro ao ler {CONFIG_FILE}: {e}")
        return {
            "builtin_models": dict(DEFAULT_MODELS),
            "custom_servers": list(DEFAULT_CUSTOM_SERVERS)
        }


def salvar_dados(dados: dict) -> None:
    """Salva os dados no arquivo config_models.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar {CONFIG_FILE}: {e}")


def salvar_variavel_env(chave: str, valor: str) -> None:
    """Salva ou atualiza uma variável no arquivo .env."""
    env_path = config.PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            conteudo = f.read()
    else:
        conteudo = ""

    padrao = rf"^{chave}=.*"
    if re.search(padrao, conteudo, flags=re.MULTILINE):
        novo_conteudo = re.sub(
            padrao,
            lambda m: f"{chave}={valor}",
            conteudo,
            flags=re.MULTILINE,
        )
    else:
        novo_conteudo = conteudo.rstrip() + f"\n{chave}={valor}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(novo_conteudo.strip() + "\n")
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Preferências do Usuário (Persistência de Configurações)
# ---------------------------------------------------------------------------

def obter_preferencia(chave: str, default=None):
    """Retorna uma preferência salva do usuário ou o valor default."""
    dados = carregar_dados()
    prefs = dados.get("preferences", {})
    return prefs.get(chave, default)


def salvar_preferencia(chave: str, valor) -> None:
    """Salva uma preferência do usuário no arquivo de configurações."""
    dados = carregar_dados()
    if "preferences" not in dados:
        dados["preferences"] = {}
    dados["preferences"][chave] = valor
    salvar_dados(dados)


# ---------------------------------------------------------------------------
# Gerenciamento de Modelos por Provedor
# ---------------------------------------------------------------------------

def obter_modelos_provedor(provedor: str, server_id: Optional[str] = None) -> List[str]:
    """Retorna a lista de modelos salvos para um provedor ou servidor customizado."""
    dados = carregar_dados()
    if server_id:
        for s in dados.get("custom_servers", []):
            if s.get("id") == server_id:
                return s.get("modelos", [])
        return []

    return dados.get("builtin_models", {}).get(provedor, DEFAULT_MODELS.get(provedor, []))


def adicionar_modelo_provedor(provedor: str, modelo: str, server_id: Optional[str] = None) -> None:
    """Adiciona um modelo à lista de modelos salvos."""
    modelo = modelo.strip()
    if not modelo:
        return

    dados = carregar_dados()
    if server_id:
        for s in dados.get("custom_servers", []):
            if s.get("id") == server_id:
                if "modelos" not in s:
                    s["modelos"] = []
                if modelo not in s["modelos"]:
                    s["modelos"].append(modelo)
                
                # Se for provedor também mapeado em builtin_models (ex: OpenRouter), mantém sincronizado
                prov_key = s.get("nome", provedor)
                if "builtin_models" in dados:
                    for bk in dados["builtin_models"]:
                        if bk.lower() == prov_key.lower() or bk.lower() == server_id.lower():
                            if modelo not in dados["builtin_models"][bk]:
                                dados["builtin_models"][bk].append(modelo)
                            break
                salvar_dados(dados)
                return
        return

    if "builtin_models" not in dados:
        dados["builtin_models"] = {}
    if provedor not in dados["builtin_models"]:
        dados["builtin_models"][provedor] = []

    if modelo not in dados["builtin_models"][provedor]:
        dados["builtin_models"][provedor].append(modelo)
        # Se for OpenRouter ou outro com custom_server, mantém sincronizado lá também
        for s in dados.get("custom_servers", []):
            if s.get("nome", "").lower() == provedor.lower() or s.get("id", "").lower() == provedor.lower():
                if "modelos" not in s:
                    s["modelos"] = []
                if modelo not in s["modelos"]:
                    s["modelos"].append(modelo)
        salvar_dados(dados)


def remover_modelo_provedor(provedor: str, modelo: str, server_id: Optional[str] = None) -> bool:
    """Remove um modelo da lista de modelos salvos."""
    dados = carregar_dados()
    removed = False
    if server_id:
        for s in dados.get("custom_servers", []):
            if s.get("id") == server_id:
                if modelo in s.get("modelos", []):
                    s["modelos"].remove(modelo)
                    removed = True
                prov_key = s.get("nome", provedor)
                if "builtin_models" in dados:
                    for bk, bmodels in dados["builtin_models"].items():
                        if (bk.lower() == prov_key.lower() or bk.lower() == server_id.lower()) and modelo in bmodels:
                            bmodels.remove(modelo)
                            removed = True
                if removed:
                    salvar_dados(dados)
                return removed
        return False

    if provedor in dados.get("builtin_models", {}):
        if modelo in dados["builtin_models"][provedor]:
            dados["builtin_models"][provedor].remove(modelo)
            removed = True
        for s in dados.get("custom_servers", []):
            if s.get("nome", "").lower() == provedor.lower() or s.get("id", "").lower() == provedor.lower():
                if modelo in s.get("modelos", []):
                    s["modelos"].remove(modelo)
                    removed = True
        if removed:
            salvar_dados(dados)
            return True
    return False


# ---------------------------------------------------------------------------
# Gerenciamento de Servidores Customizados (OpenRouter, DeepSeek, etc.)
# ---------------------------------------------------------------------------

def obter_servidores_customizados() -> List[dict]:
    """Retorna todos os servidores de API customizados cadastrados."""
    dados = carregar_dados()
    return dados.get("custom_servers", [])


def obter_servidor_customizado(server_id: str) -> Optional[dict]:
    """Busca um servidor customizado pelo ID."""
    for s in obter_servidores_customizados():
        if s.get("id") == server_id:
            return s
    return None


def salvar_servidor_customizado(
    nome: str,
    base_url: str,
    api_key: str = "",
    modelo_padrao: str = "",
    api_key_env: str = "",
    modelos_iniciais: Optional[List[str]] = None
) -> dict:
    """Adiciona ou atualiza um servidor customizado."""
    dados = carregar_dados()
    
    server_id = re.sub(r"[^a-zA-Z0-9_]", "_", nome.strip().lower()).strip("_")
    if not server_id:
        server_id = f"custom_server_{len(dados.get('custom_servers', [])) + 1}"

    if not api_key_env:
        api_key_env = f"{server_id.upper()}_API_KEY"

    # Salva no .env se foi informada chave
    if api_key:
        salvar_variavel_env(api_key_env, api_key)
        os.environ[api_key_env] = api_key

    # Normaliza base_url
    url_limpa = base_url.strip().rstrip("/")
    if "openrouter.ai" in url_limpa.lower():
        url_limpa = "https://openrouter.ai/api/v1/chat/completions"
    elif not url_limpa.endswith("/chat/completions"):
        if url_limpa.endswith("/v1"):
            url_limpa = f"{url_limpa}/chat/completions"
        else:
            url_limpa = f"{url_limpa}/v1/chat/completions" if "deepseek" in url_limpa.lower() else f"{url_limpa}/chat/completions"

    modelos = list(modelos_iniciais or [])
    if modelo_padrao and modelo_padrao not in modelos:
        modelos.insert(0, modelo_padrao)

    if not modelos:
        modelos = [modelo_padrao or "default"]

    novo_servidor = {
        "id": server_id,
        "nome": nome.strip(),
        "base_url": url_limpa,
        "api_key_env": api_key_env,
        "api_key": "",
        "modelo_atual": modelo_padrao or modelos[0],
        "modelos": modelos
    }

    # Atualiza se já existir ou adiciona
    substituido = False
    for i, s in enumerate(dados.get("custom_servers", [])):
        if s.get("id") == server_id:
            dados["custom_servers"][i] = novo_servidor
            substituido = True
            break

    if not substituido:
        dados["custom_servers"].append(novo_servidor)

    salvar_dados(dados)
    return novo_servidor


def remover_servidor_customizado(server_id: str) -> bool:
    """Remove um servidor customizado da lista."""
    dados = carregar_dados()
    custom_servers = dados.get("custom_servers", [])
    for i, s in enumerate(custom_servers):
        if s.get("id") == server_id:
            custom_servers.pop(i)
            salvar_dados(dados)
            return True
    return False


def atualizar_modelo_ativo_servidor(server_id: str, modelo: str) -> None:
    """Atualiza o modelo ativo de um servidor customizado."""
    dados = carregar_dados()
    for s in dados.get("custom_servers", []):
        if s.get("id") == server_id:
            s["modelo_atual"] = modelo
            if "modelos" not in s:
                s["modelos"] = []
            if modelo not in s["modelos"]:
                s["modelos"].append(modelo)
            salvar_dados(dados)
            return
