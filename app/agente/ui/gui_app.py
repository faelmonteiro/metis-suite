""" Fachada publica da GUI PyQt6 do Metis. A implementacao esta em
`agente/gui/`; este modulo existe so para preservar os imports antigos.

NAO MOVA NADA DAQUI PARA `agente/ui/`: este arquivo e a camada de
compatibilidade, e `agente/ui/` tambem serve a TUI.

Quem importa daqui (nao pode quebrar):
  - `gui.py:13`            `from agente.ui.gui_app import main`
  - `agente/main.py:47`    `from agente.ui.gui_app import main as gui_main`
  - `vision/theme_manager.py`  `build_dynamic_qss` (dentro de try/except:
    se o nome sumir, o Vision perde o QSS do menu em silencio)
  - `tests/test_utils.py`  `format_markdown_to_html`, `toggle_or_focus`
  - qualquer `from agente.ui.gui_app import QSS_STYLE` — avaliado no import,
    entao se `build_dynamic_qss` levantar, "import agente.ui.gui_app" quebra
    para todos, e nao so para quem usa o nome.

`QSS_STYLE` e avaliado no import de propósito: e o que `vision` e a TUI
consomem, e avaliar uma vez no import mantem o comportamento anterior ao mover
`gui_app.py` — antes o `QSS_STYLE` global vivia aqui.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

# --- Temas: `QSS_STYLE` e avaliado no import (ver docstring acima) ----------
from agente.gui.theme_bridge import (  # noqa: F401
    build_dynamic_qss,
    get_system_theme_colors,
    QSS_STYLE,
)
from agente.gui.constants import _INICIO_APP  # noqa: F401

# --- Widgets -----------------------------------------------------------------
from agente.gui.widgets.input_box import (  # noqa: F401
    SLASH_COMMANDS,
    SlashCommandPopup,
    SmartPromptTextEdit,
)
from agente.gui.widgets.checklist import AgentChecklistWidget  # noqa: F401
from agente.gui.widgets.menu_card import MenuCardWidget  # noqa: F401

# --- Workers -----------------------------------------------------------------
from agente.gui.workers import AIWorker, CommandWorker  # noqa: F401

# --- Dialogs -----------------------------------------------------------------
# MetisMainWindow os instancia (show_apis_dialog, prompt_remove_model, ...) e
# a camada `vision/` importa alguns. `_constrain_dialog_to_parent` tambem e
# reexportado: foi movido para dialogs/common.py para nao depender do Qt alem
# do proprio dialogo, mas continua sendo um nome publico deste modulo.
from agente.gui.dialogs.common import _constrain_dialog_to_parent  # noqa: F401
from agente.gui.dialogs.apis import ModernApisDialog  # noqa: F401
from agente.gui.dialogs.agent_options import ModernAgentOptionsDialog  # noqa: F401
from agente.gui.dialogs.providers import (  # noqa: F401
    CustomServerDialog,
    ModernAddModelDialog,
    ModernRemoveModelDialog,
    ModernRestoreServerDialog,
)
from agente.gui.dialogs.info import (  # noqa: F401
    ModernHelpDialog,
    ModernStatusDialog,
)

# --- Paginas (mixins) --------------------------------------------------------
from agente.gui.pages.platform import PlatformMixin  # noqa: F401
from agente.gui.pages.dashboard import DashboardMixin  # noqa: F401
from agente.gui.pages.sessions import SessionsMixin  # noqa: F401
from agente.gui.pages.appearance import AppearanceMixin  # noqa: F401
from agente.gui.pages.oracles import OraclesMixin  # noqa: F401
from agente.gui.pages.dialogs import DialogsMixin  # noqa: F401
from agente.gui.pages.ai import AiMixin  # noqa: F401
from agente.gui.pages.chat import ChatMixin  # noqa: F401

# --- Utilidades de texto -----------------------------------------------------
from agente.gui.text.markdown import format_markdown_to_html  # noqa: F401
from agente.gui.text.commands import (  # noqa: F401
    copiar_para_area_de_transferencia,
    extrair_itens_comandos,
    resolver_comando_instantaneo,
)

# --- Janela e ponto de entrada ------------------------------------------------
from agente.gui.main_window import MetisMainWindow  # noqa: F401
from agente.gui.app import main  # noqa: F401

__all__ = [
    "build_dynamic_qss", "get_system_theme_colors", "QSS_STYLE", "_INICIO_APP",
    "SLASH_COMMANDS", "SlashCommandPopup", "SmartPromptTextEdit",
    "AgentChecklistWidget", "MenuCardWidget", "AIWorker", "CommandWorker",
    "_constrain_dialog_to_parent", "ModernApisDialog",
    "ModernAgentOptionsDialog", "CustomServerDialog", "ModernAddModelDialog",
    "ModernRemoveModelDialog", "ModernRestoreServerDialog", "ModernHelpDialog",
    "ModernStatusDialog", "PlatformMixin", "DashboardMixin", "SessionsMixin",
    "AppearanceMixin", "OraclesMixin", "DialogsMixin", "AiMixin", "ChatMixin",
    "format_markdown_to_html", "copiar_para_area_de_transferencia",
    "extrair_itens_comandos", "resolver_comando_instantaneo",
    "MetisMainWindow", "main",
]
