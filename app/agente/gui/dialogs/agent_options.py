"""Opcoes de comportamento do agente (ferramentas, confirmacoes, auto-approve)."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QDialog,
    QCheckBox,
    QComboBox,
    QPlainTextEdit,
)

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtGui import QFont

import os

from agente import config
from agente.gui.dialogs.common import _constrain_dialog_to_parent
from agente.gui.theme_bridge import build_dynamic_qss
from agente.providers_manager import salvar_variavel_env
from agente.ui.theme_manager import get_current_font_sizes

# -----------------------------------------------------------------------------
class ModernAgentOptionsDialog(QDialog):
    options_saved = pyqtSignal()

    def __init__(self, parent=None):
        """Monta o dialogo. So orquestra; cada secao tem seu builder.

        `scroll.setWidget(container)` vem DEPOIS das quatro cartas: enquanto o
        container nao tem pai, os cards nao entram na arvore. A ordem das
        chamadas e o que a impressao digital fixa.
        """
        super().__init__(parent)
        self.setWindowTitle("Metis • Opções do Agente")
        _constrain_dialog_to_parent(self, 720, 580, parent)
        self.setStyleSheet(build_dynamic_qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # `f_sz` so e usado no header; as secoes usam tamanho fixo.
        root.addLayout(self._build_header(get_current_font_sizes()))

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        root.addWidget(div)

        # Scroll Area para rolagem suave se a janela for pequena
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(12)

        c_layout.addWidget(self._build_personality_card())
        c_layout.addWidget(self._build_tools_card())
        c_layout.addWidget(self._build_web_card())
        c_layout.addWidget(self._build_memory_card())

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        root.addLayout(self._build_footer())

    def _build_header(self, f_sz):
        """Icone, titulo e subtitulo do dialogo."""
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("🤖")
        lbl_icon.setFont(QFont("Sans Serif", f_sz.get("icon", 16)))
        lbl_icon.setStyleSheet("background: transparent;")
        h_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel("OPÇÕES DO AGENTE")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 13), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel("Personalize diretrizes, ferramentas de sistema, busca na web e memória do assistente")
        lbl_sub.setFont(QFont("Sans Serif", int(f_sz.get("card_sub", 9))))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)

        h_layout.addLayout(t_box)
        h_layout.addStretch()
        return h_layout

    def _build_personality_card(self):
        """SEÇÃO 1: system prompt customizado e temperatura."""
        card_behav = QFrame()
        card_behav.setProperty("class", "ApiCard")
        l_behav = QVBoxLayout(card_behav)
        l_behav.setContentsMargins(14, 12, 14, 12)
        l_behav.setSpacing(8)

        lbl_sec1 = QLabel("🧠  PERSONALIDADE & DIRETRIZES DO AGENTE")
        lbl_sec1.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec1.setStyleSheet("color: #f0a85d; background: transparent;")
        l_behav.addWidget(lbl_sec1)

        lbl_sp = QLabel("Instruções personalizadas (System Prompt Customizado):")
        lbl_sp.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sp.setStyleSheet("color: #cbd5e1; background: transparent;")
        l_behav.addWidget(lbl_sp)

        self.txt_system_prompt = QPlainTextEdit()
        self.txt_system_prompt.setFixedHeight(75)
        self.txt_system_prompt.setPlaceholderText(
            "Ex: Responda em português brasileiro de forma técnica e objetiva. Priorize atalhos e comandos para Hyprland e Arch Linux..."
        )
        curr_sys_prompt = getattr(config, "SYSTEM_PROMPT_CUSTOM", "") or os.getenv("SYSTEM_PROMPT", "")
        self.txt_system_prompt.setPlainText(curr_sys_prompt)
        l_behav.addWidget(self.txt_system_prompt)

        lbl_sp_hint = QLabel("💡 Deixe em branco para usar as diretrizes automáticas inteligentes do Metis.")
        lbl_sp_hint.setFont(QFont("Sans Serif", 8))
        lbl_sp_hint.setStyleSheet("color: #64748b; background: transparent;")
        l_behav.addWidget(lbl_sp_hint)

        div_b = QFrame()
        div_b.setFixedHeight(1)
        div_b.setStyleSheet("background-color: #1a2638;")
        l_behav.addWidget(div_b)

        h_temp = QHBoxLayout()
        lbl_temp_title = QLabel("Nível de Criatividade (Temperatura):")
        lbl_temp_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_temp_title.setStyleSheet("color: #cbd5e1; background: transparent;")
        h_temp.addWidget(lbl_temp_title)

        self.combo_temp = QComboBox()
        self.combo_temp.addItem("🎯 Preciso & Determinístico (0.2) - Código e comandos", 0.2)
        self.combo_temp.addItem("⚖️ Equilibrado (0.7) - Padrão recomendado", 0.7)
        self.combo_temp.addItem("💡 Criativo & Detalhado (1.0) - Ideias e textos longos", 1.0)

        # O config pode traz um valor fora da grade; o combo e trilho de 0.2,
        # 0.7 e 1.0, entao escolhe a faixa mais proxima em vez de zerar.
        curr_temp = getattr(config, "DEFAULT_TEMPERATURE", 0.7)
        if curr_temp <= 0.3:
            self.combo_temp.setCurrentIndex(0)
        elif curr_temp >= 0.9:
            self.combo_temp.setCurrentIndex(2)
        else:
            self.combo_temp.setCurrentIndex(1)

        h_temp.addWidget(self.combo_temp, 1)
        l_behav.addLayout(h_temp)

        return card_behav

    def _build_tools_card(self):
        """SEÇÃO 2: execucao de comandos e checklist visual."""
        card_tools = QFrame()
        card_tools.setProperty("class", "ApiCard")
        l_tools = QVBoxLayout(card_tools)
        l_tools.setContentsMargins(14, 12, 14, 12)
        l_tools.setSpacing(8)

        lbl_sec2 = QLabel("⚡  FERRAMENTAS & EXECUÇÃO NO SISTEMA")
        lbl_sec2.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec2.setStyleSheet("color: #f0a85d; background: transparent;")
        l_tools.addWidget(lbl_sec2)

        self.chk_enable_cmd = QCheckBox("Permitir execução segura de comandos no terminal (ENABLE_COMMAND_TOOL)")
        self.chk_enable_cmd.setChecked(bool(config.ENABLE_COMMAND_TOOL))
        self.chk_enable_cmd.setStyleSheet("color: #fad094; font-size: 11px; font-weight: bold;")
        l_tools.addWidget(self.chk_enable_cmd)

        lbl_cmd_hint = QLabel("Habilita o agente a executar comandos seguros no sistema operacional para diagnósticos e tarefas locais.")
        lbl_cmd_hint.setFont(QFont("Sans Serif", 8))
        lbl_cmd_hint.setStyleSheet("color: #64748b; background: transparent; padding-left: 20px;")
        lbl_cmd_hint.setWordWrap(True)
        l_tools.addWidget(lbl_cmd_hint)

        div_t = QFrame()
        div_t.setFixedHeight(1)
        div_t.setStyleSheet("background-color: #1a2638;")
        l_tools.addWidget(div_t)

        self.chk_visual_checklist = QCheckBox("Exibir checklist visual de execução em tempo real (AGENT_VISUAL_CHECKLIST)")
        self.chk_visual_checklist.setChecked(bool(getattr(config, "AGENT_VISUAL_CHECKLIST", True)))
        self.chk_visual_checklist.setStyleSheet("color: #fad094; font-size: 11px; font-weight: bold;")
        l_tools.addWidget(self.chk_visual_checklist)

        lbl_check_hint = QLabel("Mostra um painel interativo na mensagem do chat com as ações e ferramentas executadas pelo agente.")
        lbl_check_hint.setFont(QFont("Sans Serif", 8))
        lbl_check_hint.setStyleSheet("color: #64748b; background: transparent; padding-left: 20px;")
        lbl_check_hint.setWordWrap(True)
        l_tools.addWidget(lbl_check_hint)

        return card_tools

    def _build_web_card(self):
        """SEÇÃO 3: extracao de pagina inteira e quantos resultados ler."""
        card_web = QFrame()
        card_web.setProperty("class", "ApiCard")
        l_web = QVBoxLayout(card_web)
        l_web.setContentsMargins(14, 12, 14, 12)
        l_web.setSpacing(8)

        lbl_sec3 = QLabel("🌐  PESQUISA NA WEB & ENRIQUECIMENTO")
        lbl_sec3.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec3.setStyleSheet("color: #f0a85d; background: transparent;")
        l_web.addWidget(lbl_sec3)

        self.chk_fetch_page = QCheckBox("Extrair conteúdo completo de páginas na busca web (FETCH_PAGE_CONTENT)")
        self.chk_fetch_page.setChecked(bool(config.FETCH_PAGE_CONTENT))
        self.chk_fetch_page.setStyleSheet("color: #fad094; font-size: 11px; font-weight: bold;")
        l_web.addWidget(self.chk_fetch_page)

        lbl_fetch_hint = QLabel("Lê e sintetiza o corpo textual completo das páginas encontradas, gerando respostas mais ricas.")
        lbl_fetch_hint.setFont(QFont("Sans Serif", 8))
        lbl_fetch_hint.setStyleSheet("color: #64748b; background: transparent; padding-left: 20px;")
        lbl_fetch_hint.setWordWrap(True)
        l_web.addWidget(lbl_fetch_hint)

        div_w = QFrame()
        div_w.setFixedHeight(1)
        div_w.setStyleSheet("background-color: #1a2638;")
        l_web.addWidget(div_w)

        h_search_res = QHBoxLayout()
        lbl_res_title = QLabel("Resultados consultados por pesquisa:")
        lbl_res_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_res_title.setStyleSheet("color: #cbd5e1; background: transparent;")
        h_search_res.addWidget(lbl_res_title)

        self.combo_search_res = QComboBox()
        self.combo_search_res.addItem("3 resultados (Rápido e econômico)", 3)
        self.combo_search_res.addItem("5 resultados (Padrão balanceado)", 5)
        self.combo_search_res.addItem("8 resultados (Pesquisa aprofundada)", 8)

        curr_max_s = getattr(config, "MAX_SEARCH_RESULTS", 5)
        if curr_max_s <= 3:
            self.combo_search_res.setCurrentIndex(0)
        elif curr_max_s >= 8:
            self.combo_search_res.setCurrentIndex(2)
        else:
            self.combo_search_res.setCurrentIndex(1)

        h_search_res.addWidget(self.combo_search_res, 1)
        l_web.addLayout(h_search_res)

        return card_web

    def _build_memory_card(self):
        """SEÇÃO 4: quantas mensagens ficam na memória ativa."""
        card_mem = QFrame()
        card_mem.setProperty("class", "ApiCard")
        l_mem = QVBoxLayout(card_mem)
        l_mem.setContentsMargins(14, 12, 14, 12)
        l_mem.setSpacing(8)

        lbl_sec4 = QLabel("📜  MEMÓRIA & CONTEXTO DA CONVERSA")
        lbl_sec4.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec4.setStyleSheet("color: #f0a85d; background: transparent;")
        l_mem.addWidget(lbl_sec4)

        h_mem = QHBoxLayout()
        lbl_mem_title = QLabel("Mensagens mantidas na memória ativa:")
        lbl_mem_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_mem_title.setStyleSheet("color: #cbd5e1; background: transparent;")
        h_mem.addWidget(lbl_mem_title)

        self.combo_mem = QComboBox()
        self.combo_mem.addItem("10 mensagens (Mais veloz, menor uso de RAM)", 10)
        self.combo_mem.addItem("20 mensagens (Padrão recomendado)", 20)
        self.combo_mem.addItem("30 mensagens (Memória estendida)", 30)
        self.combo_mem.addItem("50 mensagens (Contexto de longo prazo)", 50)

        curr_max_m = getattr(config, "MAX_HISTORY_MESSAGES", 20)
        if curr_max_m <= 10:
            self.combo_mem.setCurrentIndex(0)
        elif curr_max_m <= 20:
            self.combo_mem.setCurrentIndex(1)
        elif curr_max_m <= 30:
            self.combo_mem.setCurrentIndex(2)
        else:
            self.combo_mem.setCurrentIndex(3)

        h_mem.addWidget(self.combo_mem, 1)
        l_mem.addLayout(h_mem)

        return card_mem

    def _build_footer(self):
        """Cancelar e Salvar, alinhados a direita."""
        f_layout = QHBoxLayout()
        f_layout.addStretch()

        btn_cancel = QPushButton("Cancelar (ESC)")
        btn_cancel.setProperty("class", "SecondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        f_layout.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Salvar Configurações")
        btn_save.setProperty("class", "PrimaryBtn")
        btn_save.clicked.connect(self.save_options)
        f_layout.addWidget(btn_save)

        return f_layout

    def save_options(self):
        cmd_val = "1" if self.chk_enable_cmd.isChecked() else "0"
        fetch_val = "1" if self.chk_fetch_page.isChecked() else "0"
        checklist_val = "1" if self.chk_visual_checklist.isChecked() else "0"
        sys_prompt_val = self.txt_system_prompt.toPlainText().strip()
        temp_val = float(self.combo_temp.currentData())
        max_search_val = int(self.combo_search_res.currentData())
        max_mem_val = int(self.combo_mem.currentData())

        # Salva no .env
        salvar_variavel_env("ENABLE_COMMAND_TOOL", cmd_val)
        salvar_variavel_env("FETCH_PAGE_CONTENT", fetch_val)
        salvar_variavel_env("AGENT_VISUAL_CHECKLIST", checklist_val)
        salvar_variavel_env("SYSTEM_PROMPT", sys_prompt_val)
        salvar_variavel_env("DEFAULT_TEMPERATURE", str(temp_val))
        salvar_variavel_env("OLLAMA_TEMPERATURE", str(temp_val))
        salvar_variavel_env("GEMINI_TEMPERATURE", str(temp_val))
        salvar_variavel_env("MAX_SEARCH_RESULTS", str(max_search_val))
        salvar_variavel_env("MAX_HISTORY_MESSAGES", str(max_mem_val))

        # Atualiza em memória
        config.ENABLE_COMMAND_TOOL = (cmd_val == "1")
        config.FETCH_PAGE_CONTENT = (fetch_val == "1")
        config.AGENT_VISUAL_CHECKLIST = (checklist_val == "1")
        config.SYSTEM_PROMPT_CUSTOM = sys_prompt_val
        config.DEFAULT_TEMPERATURE = temp_val
        config.OLLAMA_TEMPERATURE = temp_val
        config.GEMINI_TEMPERATURE = temp_val
        config.MAX_SEARCH_RESULTS = max_search_val
        config.MAX_HISTORY_MESSAGES = max_mem_val

        self.options_saved.emit()
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)
