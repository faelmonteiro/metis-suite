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

def get_config_file_path() -> Path:
    """Retorna o caminho canônico do config_models.json priorizando ~/.config/metis."""
    metis_cfg_dir = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis"))
    canonical = metis_cfg_dir / "config_models.json"
    if canonical.exists():
        return canonical
    # Migração automática de arquivos legados caso existam
    for p in [config.PROJECT_ROOT / "config_models.json", Path.home() / "Metis" / "config_models.json", Path.home() / ".ZSH" / "ai" / "config_models.json"]:
        if p.exists() and p.is_file():
            try:
                metis_cfg_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(p, canonical)
                return canonical
            except Exception:
                pass
    metis_cfg_dir.mkdir(parents=True, exist_ok=True)
    return canonical


CONFIG_FILE = get_config_file_path()

DEFAULT_MODELS: Dict[str, List[str]] = {
    "Groq": [],
    "Gemini": [],
    "NVIDIA": [],
    "G4F": [],
    "OpenRouter": [],
    "Ollama": []
}

DEFAULT_CUSTOM_SERVERS: List[dict] = []


def carregar_dados() -> dict:
    """Carrega o arquivo config_models.json ou inicializa com valores padrão."""
    config_file = get_config_file_path()
    if not config_file.exists():
        default_file_candidates = [
            config.PROJECT_ROOT.parent / "config" / "config_models.default.json",
            Path(os.getenv("METIS_INSTALL_DIR", Path.home() / ".local" / "share" / "metis")) / "config" / "config_models.default.json",
        ]
        dados_iniciais = None
        for df in default_file_candidates:
            if df.exists():
                try:
                    with open(df, "r", encoding="utf-8") as f:
                        dados_iniciais = json.load(f)
                        break
                except Exception:
                    pass

        if not dados_iniciais:
            dados_iniciais = {
                "builtin_models": dict(DEFAULT_MODELS),
                "custom_servers": list(DEFAULT_CUSTOM_SERVERS),
                "preferences": {
                    "last_active_provider": "ollama",
                    "last_active_model": "llama3.2:3b"
                }
            }
        salvar_dados(dados_iniciais)
        return dados_iniciais

    try:
        with open(config_file, "r", encoding="utf-8") as f:
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
        logger.error(f"Erro ao ler {config_file}: {e}")
        return {
            "builtin_models": dict(DEFAULT_MODELS),
            "custom_servers": list(DEFAULT_CUSTOM_SERVERS)
        }


def salvar_dados(dados: dict) -> None:
    """Salva os dados no arquivo config_models.json e replica para outros locais existentes."""
    config_file = get_config_file_path()
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar {config_file}: {e}")

    app_cfg = config.PROJECT_ROOT / "config_models.json"
    if app_cfg.exists() and app_cfg.resolve() != config_file.resolve():
        try:
            with open(app_cfg, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def get_target_env_files() -> List[Path]:
    """Retorna a lista de arquivos .env que devem ser sincronizados."""
    candidates = [
        Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / ".env",
        config.PROJECT_ROOT / ".env",
        Path.home() / "Metis" / ".env",
        Path.home() / ".ZSH" / "ai" / ".env_local",
    ]
    target_files = []
    seen = set()
    for p in candidates:
        try:
            resolved = p.resolve()
        except Exception:
            resolved = p
        if resolved not in seen:
            seen.add(resolved)
            if p.exists() or p.parent.exists():
                target_files.append(p)
    return target_files


def _atualizar_conteudo_env(conteudo: str, chave: str, valor: str) -> str:
    """
    Atualiza com segurança uma variável no conteúdo do arquivo .env:
    - Suporta 'CHAVE=...', 'export CHAVE=...'
    - Preserva comentários inline e espaços
    - Adiciona aspas adequadas ao valor
    - Se não existir, anexa no final
    """
    val_str = str(valor).strip()
    if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
        val_str = val_str[1:-1]

    val_escaped = val_str.replace('"', '\\"')
    padrao = rf"^(?P<prefix>[ \t]*(?:export[ \t]+)?{re.escape(chave)}[ \t]*=[ \t]*)(?:\"(?:\\\"|[^\"])*\"|'(?:\\'|[^'])*'|[^#\r\n]*)(?P<suffix>[ \t]*#.*)?$"

    if re.search(padrao, conteudo, flags=re.MULTILINE):
        def _subst(m):
            suffix = m.group("suffix") or ""
            return f'{m.group("prefix")}"{val_escaped}"{suffix}'
        return re.sub(padrao, _subst, conteudo, flags=re.MULTILINE)
    else:
        conteudo_base = conteudo.rstrip()
        prefixo = f"{conteudo_base}\n" if conteudo_base else ""
        return f'{prefixo}{chave}="{val_escaped}"\n'


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
        with open(file_selected, "w", encoding="utf-8") as f:
            f.write(f"{label}\n")
        with open(file_last, "w", encoding="utf-8") as f:
            f.write(f"{num}\n")
    except Exception as e:
        logger.debug(f"Não foi possível sincronizar estado ZSH: {e}")


def sincronizar_config(chave: str, valor: str) -> None:
    """
    Sincroniza uma configuração em TODAS as camadas:
    1. Variáveis de ambiente do processo (os.environ)
    2. Atributos do módulo config em memória
    3. Arquivos .env em disco (~/.config/metis/.env, app/.env, etc.)
    4. Estado do ZSH se for DEFAULT_PROVIDER
    """
    valor_str = str(valor).strip()

    # 1. Atualiza os.environ
    os.environ[chave] = valor_str

    # 2. Atualiza em memória no config
    if hasattr(config, chave):
        attr_atual = getattr(config, chave)
        if isinstance(attr_atual, bool):
            setattr(config, chave, valor_str.lower() in {"1", "true", "yes", "on"})
        elif isinstance(attr_atual, int):
            try:
                setattr(config, chave, int(valor_str))
            except ValueError:
                setattr(config, chave, valor_str)
        elif isinstance(attr_atual, float):
            try:
                setattr(config, chave, float(valor_str))
            except ValueError:
                setattr(config, chave, valor_str)
        else:
            setattr(config, chave, valor_str)

    # 3. Grava nos arquivos .env alvo
    for env_path in get_target_env_files():
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            conteudo = ""
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    conteudo = f.read()

            novo_conteudo = _atualizar_conteudo_env(conteudo, chave, valor_str)
            temp_path = env_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(novo_conteudo)
            os.replace(temp_path, env_path)
            try:
                os.chmod(env_path, 0o600)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Erro ao salvar {env_path}: {e}")

    # 4. Se for DEFAULT_PROVIDER, sincroniza arquivos do ZSH
    if chave == "DEFAULT_PROVIDER":
        _salvar_estado_zsh_provider(valor_str)


def salvar_variavel_env(chave: str, valor: str) -> None:
    """Salva ou atualiza uma variável no arquivo .env (chama sincronizar_config)."""
    sincronizar_config(chave, valor)


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
        existing_ids = {s.get("id") for s in dados.get("custom_servers", [])}
        idx = 1
        while f"custom_server_{idx}" in existing_ids:
            idx += 1
        server_id = f"custom_server_{idx}"

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
