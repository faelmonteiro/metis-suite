import logging
logger = logging.getLogger(__name__)
import atexit
import os
import sys
from pathlib import Path

# Auto re-exec dentro do ambiente virtual .venv se não estiver ativo
_project_root = Path(__file__).resolve().parent
_venv_python = _project_root / ".venv" / "bin" / "python"
if _venv_python.exists() and sys.executable != str(_venv_python):
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

# readline/histórico do terminal é carregado e configurado em agente/completer
# (configurar_readline, chamado por main). Imports duplicados aqui seriam
# redundantes e silenciados como "unused" — mantemos a responsabilidade única lá.
from agente.main import main
from agente.services.http_client import close_http_client
atexit.register(close_http_client)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSaindo do sistema...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Erro Fatal Inesperado]: {e}")
        import logging
        logging.exception("Falha crítica na aplicação")
        sys.exit(1)
