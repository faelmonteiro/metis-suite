"""Gerenciamento de chaves de API e servidores provedores."""

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
from agente.providers_manager import (
    salvar_variavel_env,
    is_servidor_removido,
    restaurar_servidor_provedor,
)
from agente.ui.theme_manager import get_current_font_sizes

# -----------------------------------------------------------------------------
# Os 4 campos de chave. `origem` e ("config"|"env", NOME) e nao o valor: a
# chave e lida por `_valor_atual` no momento em que o dialogo abre, e nao no
# import do modulo. Ler direto aqui congelaria a chave no primeiro import do
# processo, e quem abre o dialogo depois de trocar a config veria o valor velho.
#
# A ordem e a original e importa: cada `_add_api_field` da um `addWidget` no
# scroll, e a posicao do campo na tela e a ordem desta tupla.
_CAMPOS_API = (
    ("input_gemini", "GOOGLE GEMINI API KEY", "✨", "GEMINI_API_KEY",
     ("config", "GEMINI_API_KEY"),
     "Obtenha gratuitamente no Google AI Studio (aistudio.google.com)", "gemini"),
    ("input_groq", "GROQ CLOUD API KEY", "⚡", "GROQ_API_KEY",
     ("config", "GROQ_API_KEY"),
     "Obtenha gratuitamente no console da Groq (console.groq.com)", "groq"),
    ("input_nvidia", "NVIDIA NIM API KEY", "🟢", "NVIDIA_API_KEY",
     ("config", "NVIDIA_API_KEY"),
     "Chave de inferência da NVIDIA (build.nvidia.com)", "nvidia"),
    ("input_openrouter", "OPENROUTER API KEY", "🌐", "OPENROUTER_API_KEY",
     ("env", "OPENROUTER_API_KEY"),
     "Chave unificada para centenas de modelos comerciais e gratuitos (openrouter.ai/keys)",
     "openrouter"),
)


def _valor_atual(origem):
    """Le a chave do provider. `getattr` cobre o caso de o atributo faltar."""
    tipo, nome = origem
    if tipo == "config":
        return getattr(config, nome, "")
    return os.getenv(nome, "").strip()


class ModernApisDialog(QDialog):
    keys_saved = pyqtSignal()

    def __init__(self, parent=None):
        """Monta o dialogo. Os 4 campos sao uma tabela, nao 4 blocos.

        A ordem de `_CAMPOS_API` importa: cada `addWidget` dentro de
        `_add_api_field` fixa a posicao do campo no scroll, e a ordem e a
        original (Gemini, Groq, NVIDIA, OpenRouter).
        """
        super().__init__(parent)
        self.setWindowTitle("Metis • Gerenciador de Chaves de API & Conexões")
        _constrain_dialog_to_parent(self, 700, 560, parent)
        self.setStyleSheet(build_dynamic_qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # `f_sz` so e usado no header; os campos usam tamanho fixo.
        root.addLayout(self._build_header(get_current_font_sizes()))

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        root.addWidget(div)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(12)

        for campo in _CAMPOS_API:
            (atributo, rotulo, icone, chave_env, origem, dica, provedor) = campo
            setattr(self, atributo, self._add_api_field(
                c_layout, rotulo, icone, chave_env, _valor_atual(origem), dica,
                provider_key=provedor,
            ))

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        root.addLayout(self._build_footer())

    def _build_header(self, f_sz):
        """Icone, titulo e a nota de que as chaves vao para o .env."""
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("🔑")
        lbl_icon.setFont(QFont("Sans Serif", f_sz.get("icon", 16)))
        lbl_icon.setStyleSheet("background: transparent;")
        h_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel("GERENCIAMENTO DE CHAVES DE API & SERVIÇOS")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 13), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel("As configurações são salvas com segurança no arquivo .env com permissão restrita")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5)))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)

        h_layout.addLayout(t_box)
        h_layout.addStretch()
        return h_layout

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
        btn_save.clicked.connect(self.save_all_keys)
        f_layout.addWidget(btn_save)

        return f_layout

    def _add_api_field(self, parent_layout, label_text: str, icon: str, env_name: str, current_value: str, hint: str, is_password: bool = True, provider_key: str = ""):
        card = QFrame()
        card.setProperty("class", "ApiCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(6)

        l.addLayout(self._cabecalho_do_campo_api(label_text, icon, current_value,
                                                 provider_key))
        input_row, inp = self._linha_de_entrada_api(current_value, env_name, is_password)
        l.addLayout(input_row)

        lbl_hint = QLabel(hint)
        lbl_hint.setFont(QFont("Sans Serif", 8))
        lbl_hint.setStyleSheet("color: #64748b; background: transparent;")
        l.addWidget(lbl_hint)

        parent_layout.addWidget(card)
        return inp

    def _cabecalho_do_campo_api(self, label_text, icon, current_value, provider_key):
        """Nome do campo, se ha chave configurada e, quando o provedor foi
        removido, o selo de ocultamento com o botao que reativa.

        O selo e o botao sao um par: o handler esconde o botao e troca a cor do
        selo ao reativar, entao vao juntos.
        """
        h_row = QHBoxLayout()

        lbl_head = QLabel(f"{icon}  {label_text}")
        lbl_head.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_head.setStyleSheet("color: #f0a85d; background: transparent;")
        h_row.addWidget(lbl_head)

        lbl_st = QLabel("● Configurada" if current_value else "○ Não configurada")
        lbl_st.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_st.setStyleSheet("color: #4ade80;" if current_value else "color: #64748b;")
        h_row.addStretch()
        h_row.addWidget(lbl_st)

        if provider_key and is_servidor_removido(provider_key):
            lbl_rem, btn_res = self._selo_de_servidor_removido(provider_key)
            h_row.addWidget(lbl_rem)
            h_row.addWidget(btn_res)

        return h_row

    def _selo_de_servidor_removido(self, provider_key):
        """O selo "Oculto da lista" e o botao que restaura o provedor.

        Devolve os dois para quem os coloca na linha: um QHBoxLayout aninhado
        aqui dentro acrescentaria um container com margens proprias e mudaria
        a geometria do cabecalho.
        """
        lbl_rem = QLabel("○ Oculto da lista")
        lbl_rem.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_rem.setStyleSheet("color: #f87171; background: #450a0a; border-radius: 4px; padding: 2px 6px;")

        btn_res = QPushButton("🔄 Reativar")
        btn_res.setProperty("class", "ActionChip")
        btn_res.setCursor(Qt.CursorShape.PointingHandCursor)

        def _res_prov(_checked, pk=provider_key, lr=lbl_rem, br=btn_res):
            # O `_checked` nao e opcional: `clicked` emite um bool, e sem um
            # primeiro parametro posicional o PyQt o entrega em `pk` — o botao
            # restaurava o provedor de chave `False`.
            restaurar_servidor_provedor(pk)
            lr.setText("● Reativado")
            lr.setStyleSheet("color: #4ade80; background: #14532d; border-radius: 4px; padding: 2px 6px;")
            br.setVisible(False)
            self.keys_saved.emit()

        btn_res.clicked.connect(_res_prov)
        return lbl_rem, btn_res

    def _linha_de_entrada_api(self, current_value, env_name, is_password):
        """O campo, o olho que mostra a chave e o X que limpa.

        Devolve tambem o `QLineEdit`, e nao so o layout: quem chama precisa do
        campo para ler o valor na hora de salvar.
        """
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        inp = QLineEdit()
        inp.setText(current_value or "")
        inp.setPlaceholderText(f"Digite ou cole sua {env_name}...")
        if is_password:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
        input_row.addWidget(inp, 1)

        if is_password:
            btn_toggle = QPushButton("👁️")
            btn_toggle.setFixedWidth(36)
            btn_toggle.setProperty("class", "ActionChip")

            def toggle_echo(_checked, field=inp):
                # Mesmo motivo do `_checked` em `_res_prov`. Sem ele, o PyQt
                # entregava o bool do `clicked` em `field` e o handler quebrava
                # com `AttributeError` — e excecao dentro de slot chamado do
                # C++ aborta o processo inteiro, nao so o botao.
                if field.echoMode() == QLineEdit.EchoMode.Password:
                    field.setEchoMode(QLineEdit.EchoMode.Normal)
                else:
                    field.setEchoMode(QLineEdit.EchoMode.Password)

            btn_toggle.clicked.connect(toggle_echo)
            input_row.addWidget(btn_toggle)

        btn_clear = QPushButton("✕")
        btn_clear.setFixedWidth(32)
        btn_clear.setProperty("class", "ActionChip")
        btn_clear.clicked.connect(lambda _, field=inp: field.clear())
        input_row.addWidget(btn_clear)

        return input_row, inp

    def save_all_keys(self):
        gemini_val = self.input_gemini.text().strip()
        groq_val = self.input_groq.text().strip()
        nvidia_val = self.input_nvidia.text().strip()
        openrouter_val = self.input_openrouter.text().strip()

        # Salva no .env
        salvar_variavel_env("GEMINI_API_KEY", gemini_val)
        salvar_variavel_env("GROQ_API_KEY", groq_val)
        salvar_variavel_env("NVIDIA_API_KEY", nvidia_val)
        salvar_variavel_env("OPENROUTER_API_KEY", openrouter_val)

        # Atualiza em memória no módulo config / os.environ
        config.GEMINI_API_KEY = gemini_val
        config.GROQ_API_KEY = groq_val
        config.NVIDIA_API_KEY = nvidia_val
        os.environ["OPENROUTER_API_KEY"] = openrouter_val

        self.keys_saved.emit()
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)
