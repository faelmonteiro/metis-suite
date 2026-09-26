"""Pagina 0, o painel inicial: atalhos para as paginas e resumo de estado.

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from PyQt6.QtCore import Qt

from PyQt6.QtGui import (
    QFont,
    QPixmap,
)

from agente import config
from agente.gui.constants import _INICIO_APP
from agente.gui.widgets.input_box import SmartPromptTextEdit
from agente.gui.widgets.menu_card import MenuCardWidget


class DashboardMixin:
    """Painel inicial: atalhos para as paginas e resumo de estado.

    Monta a grade de cartoes (MenuCardWidget) que navega entre as paginas, e a
    faixa de informacoes (modelo, provedor, sessao, memoria, web, horario de
    inicio). `select_card` e `navigate_menu` tratam o clique e o foco por
    teclado.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def setup_dashboard_ui(self, parent: QWidget):
        """Monta a pagina. So orquestra: cada faixa visual tem seu builder.

        A ordem das chamadas NAO e cosmetics. `tests/gui_impressao_digital.txt`
        fixa a ordem de criacao dos 348 objetos, e a ordem em que os widgets
        entram no layout e o que define a geometria final. Trocar duas linhas
        de codigo aqui troca a tela.
        """
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addLayout(self._build_header())

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        layout.addWidget(div)

        layout.addLayout(self._build_body())
        layout.addWidget(self._build_command_bar())
        layout.addLayout(self._build_prompt())

    def _build_header(self):
        """Logo + titulo + botao de tema, em linha."""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        lbl_logo = QLabel()
        logo_path = config.PROJECT_ROOT / "assets" / "icons" / "metis_glyph.png"
        if not logo_path.exists():
            logo_path = config.PROJECT_ROOT / "assets" / "icons" / "glyph_128x128.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
        else:
            lbl_logo.setText("🏛️")
            lbl_logo.setFont(QFont("Sans Serif", 22))
        header_layout.addWidget(lbl_logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_main_title = QLabel("M E T I S")
        self.lbl_main_title.setFont(QFont("Sans Serif", 16, QFont.Weight.Bold))
        self.lbl_main_title.setStyleSheet("color: #fad094;")
        title_box.addWidget(self.lbl_main_title)

        self.lbl_main_sub = QLabel("AGENTE DE INTELIGÊNCIA  •  ORÁCULO & ESTRATÉGIA")
        self.lbl_main_sub.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        self.lbl_main_sub.setStyleSheet("color: #75c45a; letter-spacing: 0.5px;")
        title_box.addWidget(self.lbl_main_sub)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_theme = QPushButton("🎨 Manto de Íris")
        btn_theme.setProperty("class", "SecondaryBtn")
        btn_theme.setToolTip("Manto de Íris: Personalizar Temas Visuais, Transparência, Tipografia e Estilos (/tema)")
        btn_theme.clicked.connect(self.open_appearance_page)
        header_layout.addWidget(btn_theme)

        return header_layout

    def _build_body(self):
        """Duas colunas: cartoes de menu a esquerda, painel de info a direita.

        `addLayout(left_column, 65)` vem ANTES de construir `info_frame`, e
        nao por acaso: e a ordem de criacao original. Preservar.
        """
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        body_layout.addLayout(self._build_menu_column(), 65)
        body_layout.addWidget(self._build_info_panel(), 35)

        return body_layout

    def _build_menu_column(self):
        """Os 6 MenuCardWidget, agrupados em duas secoes por um cabecalho."""
        left_column = QVBoxLayout()
        left_column.setSpacing(5)

        lbl_sec1 = QLabel("MENU PRINCIPAL")
        lbl_sec1.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec1.setStyleSheet("color: #f0a85d;")
        left_column.addWidget(lbl_sec1)

        self.cards = []

        card1 = MenuCardWidget(0, "01", "🦉", "CONSULTAR METIS", "Chat com Inteligência Artificial e pesquisa web integrada", "1")
        card2 = MenuCardWidget(1, "02", "🔮", "ORÁCULOS & MODELOS", "Modelos locais, nuvem e servidores customizados", "2")

        for c in (card1, card2):
            c.clicked.connect(self.handle_menu_action)
            c.hovered.connect(self.select_card)
            left_column.addWidget(c)
            self.cards.append(c)

        lbl_sec2 = QLabel("PESQUISA & MEMÓRIA")
        lbl_sec2.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec2.setStyleSheet("color: #f0a85d; margin-top: 2px;")
        left_column.addWidget(lbl_sec2)

        card3 = MenuCardWidget(2, "03", "📐", "BUSCAR CONHECIMENTO", "Pesquisa web direta sem usar IA", "3")
        card4 = MenuCardWidget(3, "04", "📜", "TÁBULA DE MÉTIS", "Histórico de turnos, memórias e sessões", "4")
        card5 = MenuCardWidget(4, "05", "🔥", "PURIFICAR MEMÓRIA", "Limpar todo o histórico e sessões", "5")
        card6 = MenuCardWidget(5, "06", "🗝️", "ENCERRAR SISTEMA", "Encerrar aplicação de forma segura", "6", is_danger=True)

        for c in (card3, card4, card5, card6):
            c.clicked.connect(self.handle_menu_action)
            c.hovered.connect(self.select_card)
            left_column.addWidget(c)
            self.cards.append(c)

        return left_column

    def _build_info_panel(self):
        """O painel INFORMAÇÕES: uma linha por estado, via `_create_info_item`."""
        info_frame = QFrame()
        info_frame.setObjectName("InfoPanel")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(5)

        lbl_info_title = QLabel("INFORMAÇÕES")
        lbl_info_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_info_title.setStyleSheet("color: #f0a85d;")
        info_layout.addWidget(lbl_info_title)

        self.val_oraculo = self._create_info_item(info_layout, "🦉  ORÁCULO ATUAL", config.OLLAMA_MODEL)
        self.val_provedor = self._create_info_item(info_layout, "🖧   PROVEDOR", "Ollama (Local)")
        self.val_web = self._create_info_item(info_layout, "📶  CONEXÃO COSMOS", "Online", color="#4ade80")
        self.val_sessao = self._create_info_item(info_layout, "⏳  SESSÃO", "Atual")
        self.val_memoria = self._create_info_item(info_layout, "📜  TÁBULA DE MÉTIS", "0 registros")
        self.val_inicio = self._create_info_item(info_layout, "☀️  DESPERTO EM", _INICIO_APP, color="#94a3b8")

        info_layout.addStretch()
        return info_frame

    def _build_command_bar(self):
        """A barra de chips de comando entre as duas pontas."""
        cmd_bar = QFrame()
        cmd_bar.setObjectName("CommandBar")
        cmd_layout = QHBoxLayout(cmd_bar)
        cmd_layout.setContentsMargins(10, 4, 10, 4)
        cmd_layout.setSpacing(6)

        lbl_cmd_title = QLabel("COMANDOS:")
        lbl_cmd_title.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_cmd_title.setStyleSheet("color: #f0a85d;")
        cmd_layout.addWidget(lbl_cmd_title)

        btn_cmd_web = QPushButton("/web <termo>")
        btn_cmd_web.setProperty("class", "CommandChip")
        btn_cmd_web.clicked.connect(lambda: self.prefill_prompt("/web "))
        cmd_layout.addWidget(btn_cmd_web)

        btn_cmd_status = QPushButton("/status")
        btn_cmd_status.setProperty("class", "CommandChip")
        btn_cmd_status.clicked.connect(self.show_status_dialog)
        cmd_layout.addWidget(btn_cmd_status)

        btn_cmd_help = QPushButton("/ajuda")
        btn_cmd_help.setProperty("class", "CommandChip")
        btn_cmd_help.clicked.connect(self.show_help_dialog)
        cmd_layout.addWidget(btn_cmd_help)

        cmd_layout.addSpacing(8)

        lbl_sess_title = QLabel("SESSÕES:")
        lbl_sess_title.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_sess_title.setStyleSheet("color: #f0a85d;")
        cmd_layout.addWidget(lbl_sess_title)

        btn_cmd_sess = QPushButton("/sessao")
        btn_cmd_sess.setProperty("class", "CommandChip")
        btn_cmd_sess.clicked.connect(self.open_sessions_page)
        cmd_layout.addWidget(btn_cmd_sess)

        btn_cmd_exp = QPushButton("/exportar")
        btn_cmd_exp.setProperty("class", "CommandChip")
        btn_cmd_exp.clicked.connect(self.export_current_session)
        cmd_layout.addWidget(btn_cmd_exp)

        cmd_layout.addStretch()

        lbl_ver = QLabel("v1.0.0 │ METIS ORACLE")
        lbl_ver.setFont(QFont("Monospace", 8))
        lbl_ver.setStyleSheet("color: #475569;")
        cmd_layout.addWidget(lbl_ver)

        return cmd_bar

    def _build_prompt(self):
        """A ultima linha: o campo de consulta e o botao que dispara."""
        prompt_layout = QHBoxLayout()
        prompt_layout.setSpacing(8)

        lbl_prompt = QLabel("<span style='color: #4ade80;'>&gt;_</span> <span style='color: #fad094;'>METIS AGUARDA SUA CONSULTA:</span>")
        lbl_prompt.setFont(QFont("Monospace", 10, QFont.Weight.Bold))
        lbl_prompt.setTextFormat(Qt.TextFormat.RichText)
        prompt_layout.addWidget(lbl_prompt)

        self.prompt_input = SmartPromptTextEdit(
            placeholder="Navegue com ↑ / ↓ e dê Enter, ou digite uma pergunta/comando... (Shift+Enter para pular linha)"
        )
        self.prompt_input.setObjectName("PromptInput")
        self.prompt_input.returnPressed.connect(self.handle_prompt_submit)
        self.prompt_input.cancelRequested.connect(self.stop_ai_generation)
        prompt_layout.addWidget(self.prompt_input, 1)

        btn_run = QPushButton("Consultar ↵")
        btn_run.setProperty("class", "PrimaryBtn")
        btn_run.clicked.connect(self.handle_prompt_submit)
        prompt_layout.addWidget(btn_run)

        return prompt_layout

    def _create_info_item(self, parent_layout, label_text: str, default_val: str, color: str = "#67e8f9"):
        lbl_head = QLabel(label_text)
        lbl_head.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_head.setStyleSheet("color: #f0a85d; background: transparent;")
        parent_layout.addWidget(lbl_head)

        lbl_val = QLabel(f"  {default_val}")
        lbl_val.setFont(QFont("Monospace", 9))
        lbl_val.setStyleSheet(f"color: {color}; background: transparent;")
        parent_layout.addWidget(lbl_val)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #142030;")
        parent_layout.addWidget(div)

        return lbl_val

    def select_card(self, index: int):
        if not self.cards:
            return
        self.selected_card_index = max(0, min(index, len(self.cards) - 1))
        for i, card in enumerate(self.cards):
            card.set_selected(i == self.selected_card_index)

    def navigate_menu(self, delta: int):
        if not self.cards:
            return
        new_idx = (self.selected_card_index + delta) % len(self.cards)
        self.select_card(new_idx)
