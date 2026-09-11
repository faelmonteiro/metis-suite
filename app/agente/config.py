import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORICO_DIR = PROJECT_ROOT / "historico"

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    candidate_envs = [
        PROJECT_ROOT / ".env",
        Path.home() / "Metis" / ".env",
        Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / ".env",
        Path.home() / ".ZSH" / "ai" / ".env_local",
    ]
    for _env_p in candidate_envs:
        if _env_p.exists():
            load_dotenv(dotenv_path=_env_p, override=True)
    load_dotenv(override=False)


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    val = os.getenv(name, "").strip()

    if not val:
        return default

    try:
        val_int = int(val)
        return max(val_int, minimum)
    except ValueError:
        print(f"[Aviso] Variável {name} inválida no .env. Usando padrão: {default}")
        return default


def _env_float(name: str, default: float, minimum: float = 0.0, maximum: float = 2.0) -> float:
    val = os.getenv(name, "").strip()

    if not val:
        return default

    try:
        val_float = float(val)
        return max(minimum, min(val_float, maximum))
    except ValueError:
        print(f"[Aviso] Variável {name} inválida no .env. Usando padrão: {default}")
        return default


OLLAMA_HOST = (os.getenv("OLLAMA_HOST") or "").strip() or "http://127.0.0.1:11434"
OLLAMA_MODEL = (os.getenv("OLLAMA_MODEL") or "").strip() or "llama3.2:3b"
DEFAULT_PROVIDER = (os.getenv("DEFAULT_PROVIDER") or "").strip().lower() or "ollama"
SEARXNG_URL = (os.getenv("SEARXNG_URL") or "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct").strip()
NVIDIA_MAX_TOKENS = _env_int("NVIDIA_MAX_TOKENS", 4096, minimum=256)
G4F_MODEL = os.getenv("G4F_MODEL", "gpt-4o-mini").strip()
# Modelos válidos da Groq (verifique https://console.groq.com/docs/models):
# - llama-3.3-70b-versatile (recomendado, bom equilíbrio)
# - llama-3.1-8b-instant (rápido, menos preciso)
# - mixtral-8x7b-32768 (alternativa)
# - gemma2-9b-it (alternativa leve)



SYSTEM_PROMPT_CUSTOM = os.getenv("SYSTEM_PROMPT", "").strip()

MAX_SEARCH_RESULTS = _env_int("MAX_SEARCH_RESULTS", 5, minimum=1)
SEARCH_TIMEOUT = _env_int("SEARCH_TIMEOUT", 15, minimum=1)
API_TIMEOUT = _env_int("API_TIMEOUT", 120, minimum=1)

COMMAND_TIMEOUT = _env_int("COMMAND_TIMEOUT", 60, minimum=5)
MAX_OUTPUT_TOKENS = _env_int("MAX_OUTPUT_TOKENS", 4096, minimum=256)
MAX_HISTORY_MESSAGES = _env_int("MAX_HISTORY_MESSAGES", 30, minimum=0)
MAX_WEB_CONTENT_CHARS = _env_int("MAX_WEB_CONTENT_CHARS", 6000, minimum=100)
FETCH_PAGE_CONTENT = os.getenv("FETCH_PAGE_CONTENT", "0").strip().lower() in {"1", "true", "yes"}
OLLAMA_NUM_CTX = _env_int("OLLAMA_NUM_CTX", 4096, minimum=512)
OLLAMA_NUM_THREADS = _env_int("OLLAMA_NUM_THREADS", 4, minimum=1)
OLLAMA_TEMPERATURE = _env_float("OLLAMA_TEMPERATURE", 0.7, minimum=0.0, maximum=2.0)
GEMINI_TEMPERATURE = _env_float("GEMINI_TEMPERATURE", 0.7, minimum=0.0, maximum=2.0)
DEFAULT_TEMPERATURE = _env_float("DEFAULT_TEMPERATURE", 0.7, minimum=0.0, maximum=2.0)
OLLAMA_STATUS_TTL = _env_int("OLLAMA_STATUS_TTL", 30, minimum=1)

SEARXNG_STATUS_TTL = _env_int("SEARXNG_STATUS_TTL", 60, minimum=1)

_no_color_raw = os.getenv("NO_COLOR", "0").strip().lower()

if _no_color_raw in {"1", "true", "yes", "on"}:
    NO_COLOR = 1
else:
    NO_COLOR = 0

HYPRLAND_ENABLED = os.getenv("HYPRLAND_INSTANCE_SIGNATURE", "") != ""

_command_tool_raw = os.getenv("ENABLE_COMMAND_TOOL", "0").strip().lower()
ENABLE_COMMAND_TOOL = _command_tool_raw in {"1", "true", "yes", "on"}

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").strip().upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="[%(levelname)s] %(message)s",
)
