"""
Configurações e gerenciamento de ambiente do ScreenAI.
Carrega chaves e preferências dos arquivos .env e variáveis do sistema.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def _env(key: str, default: str = "") -> str:
    """Lê variável de ambiente com strip, encapsulando o padrão repetido."""
    return os.getenv(key, default).strip()


# Carrega variáveis de ambientes conhecidos se existirem
# Nota: .env_local usa override=True para sobrescrever valores dos .env genéricos
_env_paths = [
    Path(__file__).parent / ".env",
    Path.home() / "Metis" / ".env",
    Path.home() / ".config" / "screenai" / ".env",
    Path.home() / ".ZSH" / "ai" / ".env_local",  # carregado por último com override
]

for _path in _env_paths:
    if _path.exists():
        # .env_local deve sobrescrever variáveis definidas anteriormente
        _override = (_path.name == ".env_local")
        load_dotenv(dotenv_path=_path, override=_override)

# Provedor e Chaves
GEMINI_API_KEY = _env("GEMINI_API_KEY")
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
NVIDIA_API_KEY = _env("NVIDIA_API_KEY")
GROQ_API_KEY = _env("GROQ_API_KEY")

OLLAMA_HOST = _env("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_VISION_MODEL = _env("OLLAMA_VISION_MODEL", "llama3.2-vision:11b")

# Seleção automática do melhor provedor disponível
def get_default_provider() -> str:
    pref = os.getenv("SCREENAI_PROVIDER", "").lower()
    if pref in ["gemini", "nvidia", "openrouter", "ollama", "groq"]:
        return pref
    if NVIDIA_API_KEY:
        return "nvidia"
    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIzaSy"):
        return "gemini"
    if OPENROUTER_API_KEY:
        return "openrouter"
    return "nvidia"

DEFAULT_PROVIDER = get_default_provider()

# Modelos padrão por provedor
DEFAULT_MODELS = {
    "nvidia": os.getenv("NVIDIA_VISION_MODEL", "meta/llama-3.2-11b-vision-instruct"),
    "gemini": os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash"),
    "openrouter": os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free"),
    "groq": os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scenic-17b"),
    "ollama": OLLAMA_VISION_MODEL,
}

# Configurações de Captura & Otimização
IMAGE_MAX_DIMENSION = 1920
IMAGE_JPEG_QUALITY = 75

# Prompts do Sistema
SYSTEM_PROMPT = """Você é o Metis Vision, um assistente inteligente de desktop de alta precisão para visão e análise de arquivos.
Você recebe a captura de tela do usuário ou o conteúdo de arquivos/pastas locais e uma solicitação.
Diretrizes fundamentais:
1. Seja direto, claro e conciso. Vá direto ao ponto sem enrolações.
2. Formate sua resposta em Markdown limpo (use títulos curtos, listas com marcadores e blocos de código com a sintaxe correta quando houver código).
3. Ao analisar erros ou problemas, aponte a causa exata e dê a solução prática passo a passo.
4. Ao fazer resumos de arquivos ou telas, baseie-se estritamente no conteúdo real fornecido.
5. Se o usuário pedir para ler ou resumir um arquivo específico que não foi fornecido e não está visível na tela, NUNCA invente ou alucine conteúdos fictícios; informe educadamente que o arquivo não foi localizado e peça para o usuário indicar o caminho completo ou arrastá-lo para a janela.
"""

QUICK_ACTIONS = {
    "resumo": "Faça um resumo executivo claro e bem estruturado do que está visível nesta tela, destacando os pontos principais.",
    "explicar": "Analise esta tela em busca de mensagens de erro, problemas ou códigos. Explique o que está acontecendo e forneça a solução prática.",
    "traduzir": "Identifique os textos principais visíveis na tela e forneça uma tradução clara e natural para o Português do Brasil.",
    "extrair": "Extraia e transcreva com máxima fidelidade todo o texto ou código importante contido nesta tela, sem comentários adicionais.",
}
