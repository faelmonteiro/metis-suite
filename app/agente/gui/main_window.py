"""Janela principal do Metis (PyQt6).

Composta por mixins de `agente/gui/pages/`, um por dominio de
funcionalidade. A classe em si fica so com `init_ui`, que monta as seis
paginas chamando o `setup_*_ui` de cada mixin.

Os mixins NAO sao independentes: compartilham estado de instancia via
`self.<attr>`, e quem cria o atributo pode ser outro mixin. Essa e a
estrutura original preservada — nenhum corpo de metodo mudou.

`agente/ui/gui_app.py` reexporta `MetisMainWindow` e `main` daqui, para
que `gui.py` e `agente/main.py` continuem importando do mesmo lugar.
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStackedWidget,
)

from agente.gui.pages.ai import AiMixin
from agente.gui.pages.appearance import AppearanceMixin
from agente.gui.pages.chat import ChatMixin
from agente.gui.pages.dashboard import DashboardMixin
from agente.gui.pages.dialogs import DialogsMixin
from agente.gui.pages.oracles import OraclesMixin
from agente.gui.pages.platform import PlatformMixin
from agente.gui.pages.sessions import SessionsMixin

class MetisMainWindow(PlatformMixin, DashboardMixin, SessionsMixin, AppearanceMixin, OraclesMixin, DialogsMixin, AiMixin, ChatMixin, QMainWindow):

    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        self.stack = QStackedWidget()
        self.stack.currentChanged.connect(self._on_page_changed)
        root_layout.addWidget(self.stack, 1)

        # 0. Dashboard Principal
        self.page_dashboard = QWidget()
        self.setup_dashboard_ui(self.page_dashboard)
        self.stack.addWidget(self.page_dashboard)

        # 1. Chat Interativo
        self.page_chat = QWidget()
        self.setup_chat_ui(self.page_chat)
        self.stack.addWidget(self.page_chat)

        # 2. Busca Direta SearXNG (Visão do Mundo)
        self.page_search = QWidget()
        self.setup_search_ui(self.page_search)
        self.stack.addWidget(self.page_search)

        # 3. Painel de Oráculos & Modelos (Integrado e Completo)
        self.page_oracles = QWidget()
        self.setup_oracles_ui(self.page_oracles)
        self.stack.addWidget(self.page_oracles)

        # 4. Painel de Sessões & Gerenciamento Avançado de Memória
        self.page_sessions = QWidget()
        self.setup_sessions_ui(self.page_sessions)
        self.stack.addWidget(self.page_sessions)

        # 5. Painel de Aparência, Temas & Estilos
        self.page_appearance = QWidget()
        self.setup_appearance_ui(self.page_appearance)
        self.stack.addWidget(self.page_appearance)

        self.stack.setCurrentIndex(0)
