"""
Hermetização da suíte (pytest).

Roda ANTES da coleta dos módulos de teste, garantindo que agente.config e
agente.models.storage sejam importados com METIS_CONFIG_DIR isolado e chaves
de API fictícias — sem depender de .env ou do ambiente da máquina.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

_MISSING = object()

# Diretório isolado por sessão — criado antes de QUALQUER import de agente.*
_TEST_CONFIG_DIR = Path(tempfile.mkdtemp(prefix="metis-test-config-"))

os.environ.setdefault("METIS_CONFIG_DIR", str(_TEST_CONFIG_DIR))
os.environ.setdefault("GROQ_API_KEY", "test-key-groq")
os.environ.setdefault("GEMINI_API_KEY", "test-key-gemini")
os.environ.setdefault("NVIDIA_API_KEY", "test-key-nvidia")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-openrouter")

_CONFIG_MODELS_PATH = _TEST_CONFIG_DIR / "config_models.json"
if not _CONFIG_MODELS_PATH.exists():
    _CONFIG_MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_MODELS_PATH.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "builtin_models": {},
                "custom_servers": [
                    {
                        "id": "openrouter",
                        "nome": "OpenRouter",
                        "base_url": "https://openrouter.ai/api/v1",
                        "api_key_env": "OPENROUTER_API_KEY",
                        "modelos": [],
                        "modelo_atual": "",
                    }
                ],
                "preferences": {},
                "removed_servers": [],
                "removed_models": {},
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _restaura_estado_modular():
    """Snapshot e restaura variáveis de módulo que os testes mutam."""
    from agente import config as config_mod
    from agente.services import tools_defs

    alvos = {
        config_mod: [
            "DEFAULT_PROVIDER",
            "GROQ_MODEL",
            "ENABLE_COMMAND_TOOL",
            "OLLAMA_MODEL",
        ],
        tools_defs: ["AUTO_APPROVE_MODE"],
    }
    salvo = {}
    for mod, nomes in alvos.items():
        for nome in nomes:
            salvo[(mod, nome)] = vars(mod).get(nome, _MISSING)
    yield
    for (mod, nome), valor in salvo.items():
        if valor is _MISSING:
            vars(mod).pop(nome, None)
        else:
            setattr(mod, nome, valor)


@pytest.fixture(autouse=True)
def _chaves_de_api_fixas(monkeypatch):
    """Garante chaves de API mesmo com ordem de import variável."""
    from agente import config as config_mod

    monkeypatch.setattr(config_mod, "GROQ_API_KEY", "test-key-groq")
    monkeypatch.setattr(config_mod, "NVIDIA_API_KEY", "test-key-nvidia")


@pytest.fixture(autouse=True)
def _command_tool_por_marca(request, monkeypatch):
    """Habilita ENABLE_COMMAND_TOOL apenas nos testes marcados `command_tool`."""
    if request.node.get_closest_marker("command_tool"):
        from agente import config as config_mod

        monkeypatch.setattr(config_mod, "ENABLE_COMMAND_TOOL", True)


@pytest.fixture()
def command_tool(monkeypatch):
    """Fixture direta para testes que exercitam executar_comando."""
    from agente import config as config_mod

    monkeypatch.setattr(config_mod, "ENABLE_COMMAND_TOOL", True)
    yield