#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Auto re-exec dentro do ambiente virtual .venv se não estiver ativo
_project_root = Path(__file__).resolve().parent
_venv_python = _project_root / ".venv" / "bin" / "python"
if _venv_python.exists() and sys.executable != str(_venv_python):
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

from agente.ui.gui_app import main

if __name__ == "__main__":
    main()
