"""Dialogos de provedores: servidor custom, adicionar/remover/restaurar modelos."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QScrollArea,
    QDialog,
    QMessageBox,
    QCheckBox,
)

from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
)

from PyQt6.QtGui import (
    QFont,
    QCursor,
)

from typing import Optional

import logging, os

from agente import config
from agente.gui.dialogs.common import _constrain_dialog_to_parent
from agente.gui.theme_bridge import build_dynamic_qss
from agente.providers_manager import (
    obter_modelos_provedor,
    obter_servidores_customizados,
    obter_servidor_customizado,
    remover_servidor_customizado,
    salvar_variavel_env,
    obter_servidores_removidos,
    remover_servidor_provedor,
    remover_modelo_provedor,
    restaurar_servidor_provedor,
    salvar_servidor_customizado,
)
from agente.ui.theme_manager import (
    get_current_theme_colors,
    get_current_font_sizes,
    get_window_opacity_setting,
)

logger = logging.getLogger(__name__)




# -----------------------------------------------------------------------------
class CustomServerDialog(QDialog):
    server_saved = pyqtSignal()

    def __init__(self, parent=None, server_to_edit: Optional[dict] = None):
        """Formulario de cadastro/edicao de servidor OpenAI-compatible.

        Monta cabecalho, os 4 campos (de `_CAMPOS_SERVIDOR`) e o botao. Os
        widgets ficam em `self.inp_*` porque `save_server` os le.
        """
        super().__init__(parent)
        self.setWindowTitle("Metis • Novo Servidor API" if not server_to_edit else "Metis • Editar Servidor")
        _constrain_dialog_to_parent(self, 540, 480, parent)
        self.setStyleSheet(build_dynamic_qss())

        self.server_to_edit = server_to_edit

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        root.addLayout(self._build_header(get_current_font_sizes()))
        root.addWidget(self._build_fields(get_current_font_sizes()), 1)
        root.addLayout(self._build_footer())

    def _build_header(self, f_sz):
        """Titulo e subtitulo. O texto muda entre criar e editar."""
        editando = bool(self.server_to_edit)
        t_box = QVBoxLayout()
        t_box.setSpacing(2)

        lbl_title = QLabel("➕ NOVO SERVIDOR API (OpenAI Compatible)" if not editando else "✏️ EDITAR SERVIDOR")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 12), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel("Cadastre OpenRouter, DeepSeek, LocalAI, vLLM, LM Studio ou endpoints compatíveis")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5)))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)
        return t_box

    def _build_fields(self, f_sz):
        """O cartao com os 4 campos, na ordem de `_CAMPOS_SERVIDOR`."""
        f_card = QFrame()
        f_card.setProperty("class", "ApiCard")
        f_layout = QVBoxLayout(f_card)
        f_layout.setContentsMargins(14, 12, 14, 12)
        f_layout.setSpacing(6)

        for attr, rotulo, chave, fonte, dica, senha in _CAMPOS_SERVIDOR:
            tam = f_sz.get(fonte, 9) if fonte else 9
            lbl = QLabel(rotulo)
            lbl.setFont(QFont("Sans Serif", tam, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #cbd5e1; background: transparent;")
            f_layout.addWidget(lbl)

            inp = QLineEdit()
            if senha:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            # So a URL tem padrao; as demais caem em string vazia.
            padrao = _URL_PADRAO_SERVIDOR if chave == "base_url" else ""
            inp.setText(self.server_to_edit.get(chave, padrao) if self.server_to_edit else padrao)
            inp.setPlaceholderText(dica)
            f_layout.addWidget(inp)
            setattr(self, attr, inp)

        return f_card

    def _build_footer(self):
        """Cancelar a esquerda (via stretch), salvar a direita."""
        f_btns = QHBoxLayout()
        f_btns.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "SecondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        f_btns.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Salvar Servidor")
        btn_save.setProperty("class", "PrimaryBtn")
        btn_save.clicked.connect(self.save_server)
        f_btns.addWidget(btn_save)
        return f_btns


    def save_server(self):
        nome = self.inp_name.text().strip()
        url = self.inp_url.text().strip()
        key = self.inp_key.text().strip()
        modelo = self.inp_model.text().strip() or "default"

        if not nome or not url:
            QMessageBox.warning(self, "Campos Obrigatórios", "Informe ao menos o Nome e a URL da API.")
            return

        salvar_servidor_customizado(
            nome=nome,
            base_url=url,
            api_key=key,
            modelo_padrao=modelo
        )

        self.server_saved.emit()
        self.accept()


_URL_PADRAO_SERVIDOR = "https://openrouter.ai/api/v1/chat/completions"

# Os 4 campos do formulario de servidor, na ordem em que aparecem.
# (atributo, rotulo, chave em `server_to_edit`, chave de fonte, dica, senha)
#
# `fonte` vai na tabela porque o campo 1 usa `card_title` e os outros 3, 9
# fixo — no codigo antigo isso aparecia como um `f_sz.get(...)` num e um
# literal `9` no outro, e nao como um padrao. `senha` marca o unico campo com
# `echoMode`. A ordem importa: cada `addWidget` empilha, e a posicao do campo
# na tela e a ordem desta tupla.
_CAMPOS_SERVIDOR = (
    ("inp_name", "1. Nome do Provedor / Servidor:", "nome", "card_title",
     "Ex: OpenRouter, DeepSeek, LocalAI...", False),
    ("inp_url", "2. URL do Endpoint (Base URL):", "base_url", None,
     "https://openrouter.ai/api/v1/chat/completions", False),
    ("inp_key", "3. Chave de API (Authorization Bearer):", "api_key", None,
     "sk-... (deixe vazio se for servidor local sem auth)", True),
    ("inp_model", "4. Identificador do Modelo Inicial:", "modelo_atual", None,
     "Ex: deepseek/deepseek-chat, mistralai/mistral-large...", False),
)

# -----------------------------------------------------------------------------
class ModernAddModelDialog(QDialog):
    def __init__(self, provider_name: str, parent=None):
        super().__init__(parent)
        self.provider_name = provider_name.replace("custom:", "").capitalize() if provider_name.startswith("custom:") else provider_name
        self.result_model_name = ""
        self._drag_pos = None

        self.setWindowTitle(f"Adicionar Modelo • {self.provider_name}")
        self.setFixedSize(480, 205)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(build_dynamic_qss())

        # Sincroniza opacidade com o tema do Metis
        op = get_window_opacity_setting()
        alpha = max(0.4, min(1.0, op / 100.0))
        try:
            self.setWindowOpacity(alpha)
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

        self.init_ui()

        # Centraliza sobre a janela pai caso disponível
        if parent:
            try:
                geo = parent.geometry()
                x = geo.x() + (geo.width() - 480) // 2
                y = geo.y() + (geo.height() - 205) // 2
                self.move(max(20, x), max(20, y))
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    def init_ui(self):
        """Monta o dialogo de adicionar modelo: cabecalho, campo e botoes.

        O `QTimer` do fim foca o campo depois que o dialogo aparece; fica
        aqui porque depende de `inp_model`, que `_build_input` cria.
        """
        c = get_current_theme_colors()
        f_sz = get_current_font_sizes()

        # Layout raiz sem margens para que o CentralWidget envolva completamente o diálogo
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Container idêntico ao CentralWidget do Metis (fundo, borda temática e border-radius)
        central = QWidget(self)
        central.setObjectName("CentralWidget")
        root.addWidget(central)

        inner = QVBoxLayout(central)
        inner.setContentsMargins(20, 16, 20, 16)
        inner.setSpacing(12)


        inner.addLayout(self._build_header(c, f_sz))

        inner.addWidget(self._build_divider(c))

        inner.addWidget(self._build_input())

        inner.addLayout(self._build_footer())

        QTimer.singleShot(50, self.inp_model.setFocus)

    def _build_header(self, c, f_sz):
        """Icone, titulo com a cor do tema, subtitulo e o botao [X]."""
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_icon = QLabel("🔮")
        lbl_icon.setFont(QFont("Sans Serif", 16))
        lbl_icon.setStyleSheet("background: transparent;")
        header.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)

        lbl_title = QLabel("ADICIONAR NOVO MODELO")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 11), QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {c.get('accent_gold', '#fad094')}; letter-spacing: 0.5px; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel(f"Insira o identificador oficial do modelo para {self.provider_name}")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5), QFont.Weight.Medium))
        lbl_sub.setStyleSheet(f"color: {c.get('accent_cyan', '#67e8f9')}; background: transparent;")
        t_box.addWidget(lbl_sub)

        header.addLayout(t_box)
        header.addStretch()

        # Botão discreto de fechar [✕]
        btn_close_x = QPushButton("✕")
        btn_close_x.setFixedSize(26, 26)
        btn_close_x.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close_x.setStyleSheet(f"""
            QPushButton {{
                color: {c.get('fg_sub', '#94a3b8')};
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: bold;
                border-radius: 13px;
            }}
            QPushButton:hover {{
                color: {c.get('accent_gold', '#fad094')};
                background: rgba(255, 255, 255, 0.08);
            }}
        """)
        btn_close_x.clicked.connect(self.reject)
        header.addWidget(btn_close_x)

        return header


    def _build_divider(self, c):
        """Fio de 1px com a cor de borda do tema."""
        # Divisor fino no tema do Metis
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c.get('border', '#162234')};")
        return div


    def _build_input(self):
        """O campo do identificador. `submit_model` le via `self.inp_model`."""
        # Campo de entrada com estilo e placeholder
        self.inp_model = QLineEdit()
        self.inp_model.setFixedHeight(36)
        self.inp_model.setPlaceholderText("ex: deepseek/deepseek-chat ou meta-llama/llama-3.3-70b-instruct")
        self.inp_model.returnPressed.connect(self.submit_model)
        return self.inp_model


    def _build_footer(self):
        """Cancelar e adicionar, a direita."""
        # Botões de Ação
        f_btns = QHBoxLayout()
        f_btns.setSpacing(10)
        f_btns.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "SecondaryBtn")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        f_btns.addWidget(btn_cancel)

        btn_save = QPushButton("➕ Adicionar Modelo")
        btn_save.setProperty("class", "PrimaryBtn")
        btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self.submit_model)
        f_btns.addWidget(btn_save)

        return f_btns


    def submit_model(self):
        nome = self.inp_model.text().strip()
        if not nome:
            return
        self.result_model_name = nome
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)


# -----------------------------------------------------------------------------
class ModernRemoveModelDialog(QDialog):
    models_updated = pyqtSignal()

    def __init__(self, provider_name: str, server_id: Optional[str] = None, current_active_model: str = "", parent=None):
        super().__init__(parent)
        self.provider_name = provider_name
        self.server_id = server_id
        self.current_active_model = current_active_model

        # Determina a variável de ambiente / chave de API correspondente
        if self.server_id:
            srv = obter_servidor_customizado(self.server_id) or {}
            self.env_name = srv.get("api_key_env", f"{self.server_id.upper()}_API_KEY")
            self.current_key = os.getenv(self.env_name, "").strip() or srv.get("api_key", "").strip()
            self.is_password = True
        elif self.provider_name == "Gemini":
            self.env_name = "GEMINI_API_KEY"
            self.current_key = config.GEMINI_API_KEY
            self.is_password = True
        elif self.provider_name == "Groq":
            self.env_name = "GROQ_API_KEY"
            self.current_key = config.GROQ_API_KEY
            self.is_password = True
        elif self.provider_name == "NVIDIA":
            self.env_name = "NVIDIA_API_KEY"
            self.current_key = getattr(config, "NVIDIA_API_KEY", "")
            self.is_password = True
        elif self.provider_name == "OpenRouter":
            self.env_name = "OPENROUTER_API_KEY"
            self.current_key = os.getenv("OPENROUTER_API_KEY", "").strip()
            self.is_password = True
        elif self.provider_name == "Ollama":
            self.env_name = "OLLAMA_HOST"
            self.current_key = getattr(config, "OLLAMA_HOST", "http://localhost:11434")
            self.is_password = False
        else:
            self.env_name = None
            self.current_key = ""
            self.is_password = True

        self.setWindowTitle(f"Metis • Gerenciar Perfil, Chaves & Modelos • {provider_name}")
        _constrain_dialog_to_parent(self, 640, 520, parent)
        self.setStyleSheet(build_dynamic_qss())

        self.init_ui()
        self.load_models()

    def init_ui(self):
        """Monta o gerenciador de perfil: cabecalho, chave, modelos e rodape.

        O `__init__` ja resolveu `env_name`/`current_key`/`is_password`; aqui
        so vira layout. Os widgets ficam em `self` porque `load_models` e
        os `delete_*` os usam.
        """
        f_sz = get_current_font_sizes()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)


        root.addLayout(self._build_header(f_sz))
        root.addWidget(self._build_divider())

        if self.env_name:
            root.addWidget(self._build_api_key_card(f_sz))

        lbl_sec, scroll_modelos = self._build_models_section(f_sz)
        root.addWidget(lbl_sec)
        root.addWidget(scroll_modelos, 1)

        root.addLayout(self._build_footer())

    def _build_header(self, f_sz):
        """Icone, provider em caixa alta e o subtitulo."""
        # Header
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("⚙️")
        lbl_icon.setFont(QFont("Sans Serif", f_sz.get("icon", 16)))
        lbl_icon.setStyleSheet("background: transparent;")
        h_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel(f"GERENCIAMENTO • {self.provider_name.upper()}")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 13), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel(f"Configure a chave de API e gerencie a lista de modelos do perfil {self.provider_name}:")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5)))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)

        h_layout.addLayout(t_box)
        h_layout.addStretch()
        return h_layout

    def _build_divider(self):
        """Fio de 1px entre o cabecalho e o corpo."""
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        return div

    def _build_api_key_card(self, f_sz):
        """O cartao da chave so existe quando ha `env_name`; o guarda fica no `init_ui`."""
        card_key = QFrame()
        card_key.setProperty("class", "ApiCard")
        l_key = QVBoxLayout(card_key)
        l_key.setContentsMargins(14, 10, 14, 10)
        l_key.setSpacing(8)

        row_top = QHBoxLayout()
        lbl_k_title = QLabel(f"🔑 Chave de Conexão ({self.env_name})")
        lbl_k_title.setFont(QFont("Sans Serif", f_sz.get("card_title", 9), QFont.Weight.Bold))
        lbl_k_title.setStyleSheet("color: #fad094; background: transparent;")
        row_top.addWidget(lbl_k_title)

        has_k = bool(self.current_key)
        self.lbl_key_status = QLabel("● Configurada" if has_k else "○ Não configurada")
        self.lbl_key_status.setProperty("class", "StatusPillActive" if has_k else "StatusPillInactive")
        row_top.addStretch()
        row_top.addWidget(self.lbl_key_status)
        l_key.addLayout(row_top)

        row_inp = QHBoxLayout()
        row_inp.setSpacing(6)

        self.inp_api_key = QLineEdit()
        self.inp_api_key.setText(self.current_key)
        self.inp_api_key.setPlaceholderText(f"Cole sua chave ou URL para {self.env_name}...")
        if self.is_password:
            self.inp_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        row_inp.addWidget(self.inp_api_key, 1)

        if self.is_password:
            btn_toggle = QPushButton("👁️")
            btn_toggle.setFixedWidth(36)
            btn_toggle.setProperty("class", "ActionChip")
            def toggle_echo():
                if self.inp_api_key.echoMode() == QLineEdit.EchoMode.Password:
                    self.inp_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
                else:
                    self.inp_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            btn_toggle.clicked.connect(toggle_echo)
            row_inp.addWidget(btn_toggle)

        btn_save_key = QPushButton("💾 Salvar Chave")
        btn_save_key.setProperty("class", "PrimaryBtn")
        btn_save_key.clicked.connect(self.save_api_key)
        row_inp.addWidget(btn_save_key)

        l_key.addLayout(row_inp)
        return card_key

    def _build_models_section(self, f_sz):
        """Rotulo da secao e o scroll que `load_models` preenche. Devolve os dois, na ordem."""
        lbl_sec_models = QLabel("🤖 MODELOS SALVOS NESTE PERFIL:")
        lbl_sec_models.setFont(QFont("Sans Serif", f_sz.get("card_title", 9), QFont.Weight.Bold))
        lbl_sec_models.setStyleSheet("color: #67e8f9; margin-top: 4px;")

        # Scroll Area with model cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        return lbl_sec_models, self.scroll

    def _build_footer(self):
        """Excluir selecionados, excluir servidor, concluir."""
        # Footer Actions
        f_layout = QHBoxLayout()

        self.btn_del_selected = QPushButton("🗑️ Excluir Selecionados")
        self.btn_del_selected.setProperty("class", "DangerBtn")
        self.btn_del_selected.clicked.connect(self.delete_selected_models)
        f_layout.addWidget(self.btn_del_selected)

        self.btn_del_server = QPushButton("🗑️ Excluir Servidor Definitivamente")
        self.btn_del_server.setProperty("class", "SecondaryBtn")
        self.btn_del_server.setStyleSheet("color: #f87171; border: 1px solid #7f1d1d;")
        self.btn_del_server.setToolTip(f"Exclui permanentemente o servidor {self.provider_name} dos arquivos de configuração")
        self.btn_del_server.clicked.connect(self.delete_current_server)
        f_layout.addWidget(self.btn_del_server)

        f_layout.addStretch()

        btn_close = QPushButton("Concluído (ESC)")
        btn_close.setProperty("class", "PrimaryBtn")
        btn_close.clicked.connect(self.accept)
        f_layout.addWidget(btn_close)

        return f_layout


    def delete_current_server(self):
        removed = obter_servidores_removidos()
        all_builtin = ["ollama", "gemini", "groq", "nvidia", "g4f"]
        custom_s = obter_servidores_customizados()
        remaining_count = sum(1 for p in all_builtin if p not in removed) + len(custom_s)
        if remaining_count <= 1:
            QMessageBox.warning(
                self,
                "Aviso",
                "Não é possível excluir o único servidor restante. Mantenha ao menos um servidor ativo."
            )
            return

        res = QMessageBox.warning(
            self,
            "Excluir Servidor Definitivamente",
            f"Deseja realmente excluir permanentemente o servidor '{self.provider_name}' dos arquivos de configuração?\n\n"
            "Ele será apagado definitivamente e não ficará oculto para restaurar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            if self.server_id:
                remover_servidor_customizado(self.server_id)
            else:
                remover_servidor_provedor(self.provider_name)
            self.models_updated.emit()
            self.accept()

    def save_api_key(self):
        if not self.env_name:
            return
        new_val = self.inp_api_key.text().strip()
        salvar_variavel_env(self.env_name, new_val)
        os.environ[self.env_name] = new_val
        self.current_key = new_val

        if self.env_name == "GEMINI_API_KEY":
            config.GEMINI_API_KEY = new_val
        elif self.env_name == "GROQ_API_KEY":
            config.GROQ_API_KEY = new_val
        elif self.env_name == "NVIDIA_API_KEY":
            config.NVIDIA_API_KEY = new_val
        elif self.env_name == "OLLAMA_HOST":
            config.OLLAMA_HOST = new_val

        if self.server_id:
            srv = obter_servidor_customizado(self.server_id)
            if srv:
                srv["api_key"] = new_val
                salvar_servidor_customizado(
                    nome=srv.get("nome", self.provider_name),
                    base_url=srv.get("base_url", ""),
                    api_key=new_val,
                    modelo_padrao=srv.get("modelo_atual", ""),
                    api_key_env=self.env_name,
                    modelos_iniciais=srv.get("modelos", [])
                )

        has_k = bool(new_val)
        self.lbl_key_status.setText("● Configurada" if has_k else "○ Não configurada")
        self.lbl_key_status.setProperty("class", "StatusPillActive" if has_k else "StatusPillInactive")
        self.lbl_key_status.style().unpolish(self.lbl_key_status)
        self.lbl_key_status.style().polish(self.lbl_key_status)

        self.models_updated.emit()
        QMessageBox.information(self, "Chave Salva", f"Chave de API para {self.provider_name} ({self.env_name}) salva com sucesso no .env!")

    def load_models(self):
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.checkboxes = {}
        modelos = obter_modelos_provedor(self.provider_name, server_id=self.server_id)

        if not modelos:
            lbl_empty = QLabel(f"Nenhum modelo salvo para {self.provider_name}.")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 11px; padding: 20px;")
            self.cards_layout.addWidget(lbl_empty)
            self.btn_del_selected.setEnabled(False)
            return

        self.btn_del_selected.setEnabled(True)

        for m in modelos:
            card = QFrame()
            card.setProperty("class", "TurnCard")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(12, 10, 12, 10)
            c_layout.setSpacing(10)

            # Checkbox
            chk = QCheckBox()
            chk.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
            c_layout.addWidget(chk)
            self.checkboxes[m] = chk

            # Model Name & Active badge
            f_sz = get_current_font_sizes()
            t_col = QVBoxLayout()
            t_col.setSpacing(2)
            lbl_name = QLabel(m)
            lbl_name.setFont(QFont("Monospace", f_sz.get("base", 10), QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: #67e8f9; background: transparent;")
            t_col.addWidget(lbl_name)

            if m == self.current_active_model:
                lbl_active = QLabel("● Ativo atualmente neste perfil")
                lbl_active.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8), QFont.Weight.Bold))
                lbl_active.setStyleSheet("color: #4ade80; background: transparent;")
                t_col.addWidget(lbl_active)

            c_layout.addLayout(t_col, 1)

            # Delete single button
            btn_del = QPushButton("🗑️ Excluir")
            btn_del.setProperty("class", "DangerBtn")
            btn_del.clicked.connect(lambda _, mod=m: self.delete_single_model(mod))
            c_layout.addWidget(btn_del)

            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def delete_single_model(self, model_name: str):
        modelos = obter_modelos_provedor(self.provider_name, server_id=self.server_id)
        if len(modelos) <= 1:
            QMessageBox.warning(
                self,
                "Aviso",
                f"A lista possui apenas 1 modelo ({model_name}). Não é possível remover o único modelo deste perfil."
            )
            return

        res = QMessageBox.question(
            self,
            "Remover Modelo",
            f"Deseja realmente remover o modelo '{model_name}' do perfil {self.provider_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            remover_modelo_provedor(self.provider_name, model_name, server_id=self.server_id)
            self.models_updated.emit()
            self.load_models()

    def delete_selected_models(self):
        selected = [m for m, chk in self.checkboxes.items() if chk.isChecked()]
        if not selected:
            QMessageBox.information(self, "Seleção", "Marque ao menos uma caixa de seleção para remover.")
            return

        modelos = obter_modelos_provedor(self.provider_name, server_id=self.server_id)
        if len(selected) >= len(modelos):
            QMessageBox.warning(
                self,
                "Aviso",
                "Você não pode remover todos os modelos da lista. Pelo menos 1 modelo deve permanecer no perfil."
            )
            return

        res = QMessageBox.question(
            self,
            "Remover Modelos",
            f"Deseja remover os {len(selected)} modelos selecionados do perfil {self.provider_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            for mod in selected:
                remover_modelo_provedor(self.provider_name, mod, server_id=self.server_id)
            self.models_updated.emit()
            self.load_models()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        super().keyPressEvent(event)


# -----------------------------------------------------------------------------
class ModernRestoreServerDialog(QDialog):
    """
    Diálogo para visualizar e restaurar servidores nativos (Gemini, Groq, NVIDIA, Ollama, G4F)
    ou customizados que foram removidos ou desativados pelo usuário.
    """
    server_restored = pyqtSignal()

    BUILTIN_META = {
        "gemini": {
            "name": "Google Gemini",
            "icon": "✨",
            "category": "NUVEM / GOOGLE",
            "desc": "Modelos multimodais de alto desempenho do Google com suporte a imagens e janela de contexto estendida.",
        },
        "groq": {
            "name": "Groq Cloud",
            "icon": "⚡",
            "category": "INFERÊNCIA ULTRA-RÁPIDA",
            "desc": "Inferência ultra-rápida em chips LPU com Llama 3.3, DeepSeek R1 e Qwen.",
        },
        "nvidia": {
            "name": "NVIDIA NIM",
            "icon": "🟢",
            "category": "GPU MICROSSERVIÇOS",
            "desc": "Inferência acelerada em GPUs NVIDIA (Llama 3.1 70B, Vision, Nemotron).",
        },
        "ollama": {
            "name": "Ollama Local",
            "icon": "🏛️",
            "category": "LOCAL / OFFLINE",
            "desc": "Modelos open-source locais sem envio de dados para a nuvem.",
        },
        "g4f": {
            "name": "IA Web (G4F)",
            "icon": "🌍",
            "category": "COMUNITÁRIO / FREE",
            "desc": "Provedor comunitário para múltiplos modelos sem necessidade de chaves pagas.",
        },
        "openrouter": {
            "name": "OpenRouter",
            "icon": "🌐",
            "category": "OPENAI COMPATÍVEL",
            "desc": "Servidor com acesso a centenas de modelos livres e comerciais.",
        }
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Metis • Restaurar Servidores de IA")
        _constrain_dialog_to_parent(self, 640, 480, parent)
        self.setStyleSheet(build_dynamic_qss())

        self.init_ui()
        self.load_removed_servers()

    def init_ui(self):
        f_sz = get_current_font_sizes()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Header
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("🔄")
        lbl_icon.setFont(QFont("Sans Serif", f_sz.get("icon", 16)))
        lbl_icon.setStyleSheet("background: transparent;")
        h_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel("RESTAURAR SERVIDORES DE IA")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 13), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel("Reative provedores nativos ou customizados removidos anteriormente:")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5)))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)

        h_layout.addLayout(t_box)
        h_layout.addStretch()
        root.addLayout(h_layout)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        root.addWidget(div)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        # Footer
        f_layout = QHBoxLayout()
        f_layout.addStretch()
        btn_close = QPushButton("Fechar (ESC)")
        btn_close.setProperty("class", "PrimaryBtn")
        btn_close.clicked.connect(self.accept)
        f_layout.addWidget(btn_close)
        root.addLayout(f_layout)

    def load_removed_servers(self):
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        removed = obter_servidores_removidos()
        f_sz = get_current_font_sizes()

        if not removed:
            card_empty = QFrame()
            card_empty.setProperty("class", "HelpCard")
            l_e = QVBoxLayout(card_empty)
            l_e.setContentsMargins(20, 24, 20, 24)
            lbl_empty = QLabel("🎉 Todos os servidores de IA estão ativos!\nNenhum provedor está desativado ou oculto no momento.")
            lbl_empty.setFont(QFont("Sans Serif", 10))
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #4ade80; background: transparent;")
            l_e.addWidget(lbl_empty)
            self.cards_layout.addWidget(card_empty)
            return

        for srv_id in removed:
            meta = self.BUILTIN_META.get(srv_id.lower(), {
                "name": srv_id.capitalize(),
                "icon": "🌐",
                "category": "SERVIDOR CUSTOM",
                "desc": "Servidor de API cadastrado pelo usuário."
            })

            card = QFrame()
            card.setProperty("class", "TurnCard")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(14, 12, 14, 12)
            c_layout.setSpacing(12)

            lbl_ico = QLabel(meta["icon"])
            lbl_ico.setFont(QFont("Sans Serif", 18))
            lbl_ico.setStyleSheet("background: transparent;")
            c_layout.addWidget(lbl_ico)

            t_col = QVBoxLayout()
            t_col.setSpacing(3)

            h_title = QHBoxLayout()
            lbl_n = QLabel(meta["name"])
            lbl_n.setFont(QFont("Sans Serif", f_sz.get("card_title", 10), QFont.Weight.Bold))
            lbl_n.setStyleSheet("color: #fad094; background: transparent;")
            h_title.addWidget(lbl_n)

            lbl_tag = QLabel(meta["category"])
            lbl_tag.setProperty("class", "ProviderTag")
            h_title.addWidget(lbl_tag)
            h_title.addStretch()
            t_col.addLayout(h_title)

            lbl_d = QLabel(meta["desc"])
            lbl_d.setFont(QFont("Sans Serif", 8))
            lbl_d.setStyleSheet("color: #94a3b8; background: transparent;")
            lbl_d.setWordWrap(True)
            t_col.addWidget(lbl_d)

            c_layout.addLayout(t_col, 1)

            btn_res = QPushButton("🔄 Restaurar")
            btn_res.setProperty("class", "PrimaryBtn")
            btn_res.setFixedHeight(34)
            btn_res.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_res.clicked.connect(lambda _, sid=srv_id: self.restore_server(sid))
            c_layout.addWidget(btn_res)

            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def restore_server(self, srv_id: str):
        restaurar_servidor_provedor(srv_id)
        self.server_restored.emit()
        self.load_removed_servers()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        super().keyPressEvent(event)
