"""Pagina 1, o chat, e a pagina 2 de busca direta (SearXNG).

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QScrollArea,
    QMessageBox,
    QCheckBox,
    QFileDialog,
    QMenu,
)

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPoint,
)

from PyQt6.QtGui import (
    QFont,
    QFontMetrics,
)

import mimetypes, shutil

from agente import config
from agente.gui.text.commands import (
    copiar_para_area_de_transferencia,
    extrair_itens_comandos,
)
from agente.gui.text.markdown import format_markdown_to_html
from agente.gui.theme_bridge import (
    get_current_font_sizes,
    build_dynamic_qss,
)
from agente.gui.widgets.input_box import SmartPromptTextEdit
from agente.providers_manager import (
    obter_preferencia,
    salvar_preferencia,
)
from agente.services import file_reader
from agente.utils import (
    verificar_conexao_internet,
    logger,
)
from pathlib import Path

# O estilo da caixa de comandos extraidos. Literal, com a indentacao de dentro
# exatamente como estava no `setStyleSheet` original: a impressao digital
# compara `styleSheet` como texto, e reindentar acie de mudar o valor.
_QSS_CHIPS_BOX = """
            QFrame#CommandExtractionBox {
                background-color: rgba(15, 20, 32, 0.75);
                border: 1px solid rgba(250, 208, 148, 0.25);
                border-left: 3.5px solid #fad094;
                border-radius: 8px;
                padding: 8px 12px;
                margin-top: 6px;
            }
        """

class ChatMixin:
    """Interface de conversa: bubbles, anexos e menus.

    Monta o chat e a pagina de busca, desenha os bubbles (com os chips dos
    comandos executados), trata anexos, e abre os menus de contexto.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def setup_chat_ui(self, parent: QWidget):
        """Monta a pagina. So orquestra; cada faixa tem seu builder.

        A ordem das chamadas NAO e cosmetics: `tests/gui_impressao_digital.txt`
        fixa a ordem de criacao dos objetos, e quem define a geometria final e
        a ordem de insercao no layout, nao a ordem do codigo.
        """
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addLayout(self._build_chat_header())
        layout.addWidget(self._build_message_area(), 1)
        layout.addWidget(self._build_attachment_bar())
        layout.addLayout(self._build_chat_input_bar())

    def _build_chat_header(self):
        """Header do Chat (Clean, Minimalista & Sofisticado)."""
        chat_header = QHBoxLayout()
        chat_header.setSpacing(10)

        btn_back = QPushButton("← Voltar")
        btn_back.setProperty("class", "SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        chat_header.addWidget(btn_back)

        icone, prov_tipo, modelo_nome = self.get_active_oracle_info()
        self.lbl_chat_model = QPushButton(f"{icone} {prov_tipo} • {modelo_nome} ▾")
        self.lbl_chat_model.setProperty("class", "ModelBtn")
        self.lbl_chat_model.setToolTip("Clique para abrir o painel de Oráculos e trocar de modelo")
        self.lbl_chat_model.clicked.connect(self.open_oracles_page)
        chat_header.addWidget(self.lbl_chat_model)

        self.chk_web = QCheckBox("🌐 Web")
        web_pref = obter_preferencia("web_search_enabled", True)
        self.chk_web.setChecked(bool(web_pref))
        self.chk_web.setToolTip("Ativar ou desativar pesquisa web automática")
        self.chk_web.setStyleSheet("color: #fad094; font-weight: bold; padding-left: 4px;")
        self.chk_web.toggled.connect(lambda checked: salvar_preferencia("web_search_enabled", checked))
        chat_header.addWidget(self.chk_web)

        self.btn_agent_options = QPushButton("🤖 Opções do Agente")
        self.btn_agent_options.setProperty("class", "SecondaryBtn")
        self.btn_agent_options.setToolTip("Opções do Agente (Terminal, Busca Web Profunda)")
        self.btn_agent_options.clicked.connect(self.show_agent_options_dialog)
        chat_header.addWidget(self.btn_agent_options)

        chat_header.addStretch()

        self.btn_chat_settings = QPushButton("⚙️ Opções ▾")
        self.btn_chat_settings.setProperty("class", "SecondaryBtn")
        self.btn_chat_settings.setToolTip("Configurações, Chaves, Histórico, Exportação e Ações")
        self.btn_chat_settings.clicked.connect(self.show_chat_options_menu)
        chat_header.addWidget(self.btn_chat_settings)

        return chat_header

    def _build_message_area(self):
        """O QScrollArea que recebe os baloes.

        O `addStretch` no fim e o que mantem a conversa colada no fundo quando
        ela e curta; sem ele o primeiro balao sobe.
        """
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background: transparent; border: none;")
        self.chat_scroll.viewport().setStyleSheet("background: transparent;")
        self.chat_container = QWidget()
        self.chat_container.setObjectName("ChatContainer")
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_container)
        return self.chat_scroll

    def _build_attachment_bar(self):
        """Barra de anexo, escondida ate haver arquivo."""
        self.attachment_bar = QFrame()
        self.attachment_bar.setObjectName("AttachmentChip")
        self.attachment_bar.setVisible(False)
        att_layout = QHBoxLayout(self.attachment_bar)
        att_layout.setContentsMargins(8, 4, 8, 4)
        att_layout.setSpacing(6)

        self.lbl_attachment_name = QLabel("📎 arquivo.py")
        self.lbl_attachment_name.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        self.lbl_attachment_name.setStyleSheet("color: #67e8f9; background: transparent;")
        att_layout.addWidget(self.lbl_attachment_name)

        att_layout.addStretch()

        btn_rem_att = QPushButton("✕ Remover")
        btn_rem_att.setProperty("class", "ActionChip")
        btn_rem_att.clicked.connect(self.clear_attachment)
        att_layout.addWidget(btn_rem_att)

        return self.attachment_bar

    def _build_chat_input_bar(self):
        """Input & Ações do Chat (Barra de Digitação Limpa)."""
        chat_input_layout = QHBoxLayout()
        chat_input_layout.setSpacing(8)

        btn_attach = QPushButton("📎")
        btn_attach.setProperty("class", "SecondaryBtn")
        btn_attach.setToolTip("Anexar Arquivo, Imagem ou PDF para Análise (/arquivo)")
        btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_attach.setFixedWidth(38)
        btn_attach.clicked.connect(self.open_file_dialog)
        chat_input_layout.addWidget(btn_attach)

        self.chat_input = SmartPromptTextEdit(
            placeholder="Digite sua mensagem ou comando... (Shift+Enter para pular linha)"
        )
        self.chat_input.setObjectName("PromptInput")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        self.chat_input.cancelRequested.connect(self.stop_ai_generation)
        # O filtro fica no proprio widget, nao na janela: e o campo que precisa
        # saber de Esc/Ctrl+Enter, e nao a janela inteira.
        self.chat_input.installEventFilter(self)
        chat_input_layout.addWidget(self.chat_input, 1)

        self.btn_stop = QPushButton("⏹️ Parar")
        self.btn_stop.setProperty("class", "DangerBtn")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self.stop_ai_generation)
        chat_input_layout.addWidget(self.btn_stop)

        self.btn_send = QPushButton("Consultar ↵")
        self.btn_send.setProperty("class", "PrimaryBtn")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.btn_send)

        return chat_input_layout

    def setup_search_ui(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QHBoxLayout()
        btn_back = QPushButton("← Voltar")
        btn_back.setProperty("class", "SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(btn_back)

        lbl = QLabel("🔍 BUSCA DIRETA DE CONHECIMENTO (WEB NATIVA)")
        lbl.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #fad094;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        search_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("PromptInput")
        self.search_input.setPlaceholderText("O que você deseja pesquisar na web?")
        self.search_input.returnPressed.connect(self.execute_direct_search)
        search_bar.addWidget(self.search_input, 1)

        btn_search = QPushButton("Pesquisar")
        btn_search.setProperty("class", "PrimaryBtn")
        btn_search.clicked.connect(self.execute_direct_search)
        search_bar.addWidget(btn_search)
        layout.addLayout(search_bar)

        self.search_scroll = QScrollArea()
        self.search_scroll.setWidgetResizable(True)
        self.search_results_container = QWidget()
        self.search_results_layout = QVBoxLayout(self.search_results_container)
        self.search_results_layout.setSpacing(10)
        self.search_results_layout.addStretch()
        self.search_scroll.setWidget(self.search_results_container)
        layout.addWidget(self.search_scroll, 1)

    def _exec_menu_aligned(self, menu: QMenu, btn: QPushButton):
        """Posiciona o menu suspenso perfeitamente alinhado e contido dentro dos limites visíveis da janela."""
        menu.setStyleSheet(build_dynamic_qss())
        f_sz = get_current_font_sizes()
        menu.setFont(QFont("Sans Serif", f_sz.get("base", 11)))

        btn_global_tl = btn.mapToGlobal(QPoint(0, 0))
        btn_global_br = btn.mapToGlobal(QPoint(btn.width(), btn.height()))
        win_global_tl = self.mapToGlobal(QPoint(0, 0))
        win_global_br = self.mapToGlobal(QPoint(self.width(), self.height()))

        menu_hint = menu.sizeHint()
        menu_w = max(180, menu_hint.width())
        menu_h = menu_hint.height()

        # Alinhamento horizontal: se sair da janela pela direita, ancora pela direita do botão
        if btn_global_tl.x() + menu_w > win_global_br.x() - 8:
            pos_x = max(win_global_tl.x() + 8, btn_global_br.x() - menu_w)
        else:
            pos_x = btn_global_tl.x()

        # Alinhamento vertical: se sair pelo rodapé da janela, abre para cima do botão
        if btn_global_br.y() + menu_h > win_global_br.y() - 8:
            pos_y = max(win_global_tl.y() + 8, btn_global_tl.y() - menu_h)
        else:
            pos_y = btn_global_br.y() + 2

        menu.exec(QPoint(pos_x, pos_y))

    def show_chat_options_menu(self):
        menu = QMenu(self)

        act_oracle = menu.addAction("🧠 Trocar Oráculo & Modelos")
        act_oracle.triggered.connect(self.open_oracles_page)

        act_themes = menu.addAction("🎨 Manto de Íris (/tema)")
        act_themes.triggered.connect(self.open_appearance_page)

        act_sessions = menu.addAction("📑 Gerenciar Turnos & Histórico")
        act_sessions.triggered.connect(self.open_sessions_page)

        act_apis = menu.addAction("🔑 Configurar Chaves de API")
        act_apis.triggered.connect(self.show_apis_dialog)

        act_agent_opt = menu.addAction("🤖 Opções do Agente")
        act_agent_opt.triggered.connect(self.show_agent_options_dialog)

        menu.addSeparator()

        act_retry = menu.addAction("🔁 Repetir Último Turno (/retry)")
        act_retry.triggered.connect(self.retry_last_query)

        act_export = menu.addAction("📤 Exportar Conversa (Markdown)")
        act_export.triggered.connect(self.export_current_session)

        act_clear = menu.addAction("🗑️ Limpar Chat da Tela")
        act_clear.triggered.connect(self.clear_chat_view)

        menu.addSeparator()

        act_help = menu.addAction("📖 Guia de Ajuda & Comandos (/ajuda)")
        act_help.triggered.connect(self.show_help_dialog)

        act_status = menu.addAction("📊 Telemetria do Sistema (/status)")
        act_status.triggered.connect(self.show_status_dialog)

        self._exec_menu_aligned(menu, self.btn_chat_settings)

    def show_oracle_settings_menu(self):
        menu = QMenu(self)

        act_themes = menu.addAction("🎨 Manto de Íris (/tema)")
        act_themes.triggered.connect(self.open_appearance_page)

        act_add = menu.addAction("➕ Cadastrar Novo Servidor / API (OpenAI)...")
        act_add.triggered.connect(self.show_add_server_dialog)

        act_apis = menu.addAction("🔑 Configurar Chaves de API...")
        act_apis.triggered.connect(self.show_apis_dialog)

        menu.addSeparator()

        act_status = menu.addAction("📊 Diagnóstico & Status dos Serviços...")
        act_status.triggered.connect(self.show_status_dialog)

        menu.addSeparator()

        act_restore = menu.addAction("🔄 Restaurar Servidores Removidos...")
        act_restore.triggered.connect(self.show_restore_server_dialog)

        self._exec_menu_aligned(menu, self.btn_oracle_settings)

    def show_provider_options_menu(self, btn: QPushButton, provider_key: str):
        menu = QMenu(self)

        act_add = menu.addAction("➕ Adicionar Novo Modelo...")
        act_add.triggered.connect(lambda: self.prompt_add_model(provider_key))

        act_manage = menu.addAction("🗑️ Gerenciar / Excluir Modelos...")
        act_manage.triggered.connect(lambda: self.prompt_remove_model(provider_key))

        if provider_key in ["Gemini", "Groq", "NVIDIA"]:
            menu.addSeparator()
            act_keys = menu.addAction("🔑 Configurar Chaves de API...")
            act_keys.triggered.connect(self.show_apis_dialog)

        menu.addSeparator()
        act_del = menu.addAction("🗑️ Excluir Servidor Definitivamente")
        act_del.triggered.connect(lambda: self.delete_builtin_server(provider_key))

        self._exec_menu_aligned(menu, btn)

    def show_custom_server_options_menu(self, btn: QPushButton, srv: dict):
        srv_id = srv.get("id", "custom")
        srv_nome = srv.get("nome", "Custom API")

        menu = QMenu(self)

        act_add = menu.addAction("➕ Adicionar Novo Modelo...")
        act_add.triggered.connect(lambda: self.prompt_add_model(srv_nome, server_id=srv_id))

        act_manage = menu.addAction("🗑️ Gerenciar / Excluir Modelos...")
        act_manage.triggered.connect(lambda: self.prompt_remove_model(srv_nome, server_id=srv_id))

        menu.addSeparator()

        act_edit = menu.addAction("✏️ Editar Configurações do Servidor...")
        act_edit.triggered.connect(lambda: self.prompt_edit_custom_server(srv))

        act_del = menu.addAction("🗑️ Excluir Servidor Definitivamente")
        act_del.triggered.connect(lambda: self.delete_custom_server(srv_id))

        self._exec_menu_aligned(menu, btn)

    def refresh_telemetry(self):
        icone, prov_tipo, modelo_nome = self.get_active_oracle_info()

        self.val_oraculo.setText(f"  {modelo_nome}")
        self.val_provedor.setText(f"  {prov_tipo}")
        self.lbl_chat_model.setText(f"{icone} {prov_tipo} • {modelo_nome} ▾")
        if hasattr(self, "lbl_oracle_badge"):
            self.lbl_oracle_badge.setText(f"{icone} Ativo: {prov_tipo} ({modelo_nome})")

        try:
            internet_ok = verificar_conexao_internet()
        except Exception:
            internet_ok = False

        if internet_ok:
            self.val_web.setText("  Online")
            self.val_web.setStyleSheet("color: #4ade80; background: transparent;")
        else:
            self.val_web.setText("  Offline")
            self.val_web.setStyleSheet("color: #f87171; background: transparent;")

        sessao_str = self.history_manager.sessao if hasattr(self.history_manager, "sessao") else "Atual"
        self.val_sessao.setText(f"  {sessao_str}")

        total_reg = len(self.history_manager.historico)
        self.val_memoria.setText(f"  {total_reg} registros na sessão")

    def prefill_prompt(self, text: str):
        self.prompt_input.setText(text)
        self.prompt_input.setFocus()

    def handle_menu_action(self, code: str):
        if code in ("1", "01"):
            self.stack.setCurrentIndex(1)
            self.chat_input.setFocus()

        elif code in ("2", "02"):
            self.open_oracles_page()

        elif code in ("3", "03"):
            self.stack.setCurrentIndex(2)
            self.search_input.setFocus()

        elif code in ("4", "04"):
            self.open_sessions_page()

        elif code in ("5", "05"):
            res = QMessageBox.warning(
                self,
                "Purificar Memória",
                "Tem certeza que deseja apagar todas as conversas gravadas no disco?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                dir_path = Path(config.HISTORICO_DIR)
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    dir_path.mkdir(exist_ok=True)
                self.history_manager.limpar()
                self.clear_chat_view()
                self.refresh_telemetry()
                QMessageBox.information(self, "Metis", "Histórico purificado com sucesso!")

        elif code in ("6", "06", "7", "07", "8", "08"):
            self.close()

    def handle_prompt_submit(self):
        text = self.prompt_input.text().strip()
        if not text:
            if 0 <= self.selected_card_index < len(self.cards):
                self.handle_menu_action(self.cards[self.selected_card_index].code)
            return

        self.prompt_input.clear()
        self.process_text_command_or_query(text)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Anexar Arquivo, Código, PDF ou Imagem",
            str(Path.home()),
            "Todos os Arquivos (*.*);;Imagens (*.png *.jpg *.jpeg *.webp);;Documentos & Código (*.py *.js *.json *.txt *.md *.pdf *.sh)"
        )
        if file_path:
            self.set_attachment(file_path)

    def set_attachment(self, file_path_str: str):
        try:
            path = Path(file_path_str).expanduser().resolve()
            if not path.exists():
                QMessageBox.warning(self, "Anexo", f"Arquivo não encontrado: {file_path_str}")
                return

            mime, _ = mimetypes.guess_type(str(path))
            is_media = mime and (mime.startswith("image/") or mime.startswith("audio/"))

            self.current_attachment_path = str(path)
            self.current_media_paths = [str(path)] if is_media else []

            if not is_media:
                conteudo = file_reader.ler_arquivo(str(path), max_chars=30000)
                self.current_attachment_text_context = (
                    f"Conteúdo anexado do arquivo '{path.name}':\n"
                    f"```\n{conteudo}\n```\n"
                )
            else:
                self.current_attachment_text_context = f"[Imagem/Mídia anexada: {path.name}]"

            self.lbl_attachment_name.setText(f"📎 {path.name} ({mime or 'arquivo'})")
            self.attachment_bar.setVisible(True)

        except Exception as e:
            QMessageBox.warning(self, "Anexo", f"Erro ao anexar arquivo: {e}")

    def clear_attachment(self):
        self.current_attachment_path = None
        self.current_media_paths = []
        self.current_attachment_text_context = ""
        self.attachment_bar.setVisible(False)

    def _set_bubble_content(self, label: QLabel, text: str):
        label._raw_text = text
        label.setText(format_markdown_to_html(text))

    def _render_command_chips_for_bubble(self, bubble: QFrame, b_layout: QVBoxLayout, resposta: str):
        """Renderiza cartoes de comandos executaveis e codigos com botoes de copia no rodape do balao."""
        if not resposta or "Pensando..." in resposta or "Buscando informações" in resposta:
            return

        old_box = bubble.findChild(QFrame, "CommandExtractionBox")
        if old_box:
            old_box.deleteLater()

        itens = extrair_itens_comandos(resposta)
        if not itens:
            return

        self.last_extracted_commands = itens

        cmd_box = QFrame(bubble)
        cmd_box.setObjectName("CommandExtractionBox")
        cmd_box.setStyleSheet(_QSS_CHIPS_BOX)
        cb_layout = QVBoxLayout(cmd_box)
        cb_layout.setContentsMargins(8, 6, 8, 6)
        cb_layout.setSpacing(4)

        comandos_puros = [item[1] for item in itens if item[0] == "comando"]
        cb_layout.addLayout(self._build_chips_header(comandos_puros))

        div_cmd = QFrame()
        div_cmd.setFixedHeight(1)
        div_cmd.setStyleSheet("background-color: rgba(250, 208, 148, 0.15);")
        cb_layout.addWidget(div_cmd)

        for i, (tipo, conteudo, desc) in enumerate(itens, 1):
            cb_layout.addLayout(self._build_chip_row(i, tipo, conteudo, desc))

        b_layout.addWidget(cmd_box)

    def _build_chips_header(self, comandos_puros: list):
        """Rotulo a esquerda e, so ha mais de um comando, o botao de copiar todos."""
        head_cmd = QHBoxLayout()
        lbl_cmd_tag = QLabel("⚡ COMANDOS DISPONÍVEIS:")
        lbl_cmd_tag.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_cmd_tag.setStyleSheet("color: #fad094; background: transparent; letter-spacing: 0.5px;")
        head_cmd.addWidget(lbl_cmd_tag)
        head_cmd.addStretch()

        if len(comandos_puros) > 1:
            btn_copy_all = QPushButton("❐ Copiar Todos")
            btn_copy_all.setProperty("class", "ActionChip")

            def copy_all_action(_checked, cmds=comandos_puros, b=btn_copy_all):
                # `_checked` primeiro: `clicked` emite um bool e o PyQt o
                # entregaria em `cmds`, e `"\n".join(False)` levanta TypeError
                # — que, vindo de um slot, aborta o processo.
                texto_junto = "\n".join(cmds)
                if copiar_para_area_de_transferencia(texto_junto):
                    b.setText("✓ Todos Copiados!")
                    QTimer.singleShot(2000, lambda: b.setText("❐ Copiar Todos"))

            btn_copy_all.clicked.connect(copy_all_action)
            head_cmd.addWidget(btn_copy_all)

        return head_cmd

    def _build_chip_row(self, i: int, tipo: str, conteudo: str, desc: str):
        """Uma linha: indice, conteudo (com a descricao abaixo, nos comandos) e o botao de copiar."""
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl_idx = QLabel(f"[{i:02d}]")
        lbl_idx.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        lbl_idx.setStyleSheet("color: #fad094; background: transparent;")
        row.addWidget(lbl_idx)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)

        lbl_c = QLabel(conteudo if tipo == "comando" else f"📄 {desc}")
        lbl_c.setFont(QFont("Monospace", 10, QFont.Weight.Bold if tipo == "comando" else QFont.Weight.Normal))
        lbl_c.setStyleSheet("color: #fde047; background: transparent;")
        lbl_c.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_c.setWordWrap(True)
        t_col.addWidget(lbl_c)

        if desc and tipo == "comando":
            lbl_d = QLabel(desc)
            lbl_d.setFont(QFont("Sans Serif", 8))
            lbl_d.setStyleSheet("color: #94a3b8; background: transparent;")
            t_col.addWidget(lbl_d)

        row.addLayout(t_col, 1)

        btn_cp = QPushButton("❐")
        btn_cp.setProperty("class", "IconActionBtn")
        btn_cp.setToolTip("Copiar comando")
        btn_cp.setCursor(Qt.CursorShape.PointingHandCursor)

        def make_cp(txt=conteudo, b=btn_cp):
            def _do():
                if copiar_para_area_de_transferencia(txt):
                    b.setText("✓")
                    b.setToolTip("Copiado!")
                    QTimer.singleShot(2000, lambda: (b.setText("❐"), b.setToolTip("Copiar comando")))
            return _do

        btn_cp.clicked.connect(make_cp(conteudo, btn_cp))
        row.addWidget(btn_cp)

        return row


    def add_chat_bubble(self, role: str, text: str, is_queued: bool = False):
        """Cria e insere um balão no fim do chat. Devolve (balão, label, layout).

        As duas formas — usuário e IA — são bem diferentes; o que compartilham é
        a creation do `QFrame`, o `QVBoxLayout` e o `return`. Cada branch monta
        o seu e insere; o scroll para o fim e o retorno ficam aqui.
        """
        bubble = QFrame()
        b_layout = QVBoxLayout(bubble)
        b_layout.setSpacing(2)

        if role == "user":
            lbl_content = self._build_user_bubble(bubble, b_layout, text, is_queued)
        else:
            lbl_content = self._build_ai_bubble(bubble, b_layout, text)

        self.scroll_chat_to_bottom()
        return bubble, lbl_content, b_layout

    def _make_content_label(self, text: str, extra_style: str = ""):
        """O `QLabel` de texto do balão, com o comportamento que os dois usam.

        `_raw_text` é o texto antes do markdown: os botões de copiar leem ele, e
        não o resultado da renderização. O `extra_style` cobre só a diferença
        entre os dois balões (o do usuário zera `padding`/`margin`).
        """
        lbl_content = QLabel()
        lbl_content._raw_text = text
        self._set_bubble_content(lbl_content, text)
        lbl_content.setFont(QFont("Sans Serif", 11))
        lbl_content.setStyleSheet("color: #f8fafc; background: transparent;" + extra_style)
        lbl_content.setWordWrap(True)
        lbl_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        lbl_content.setOpenExternalLinks(True)
        return lbl_content

    def _build_user_bubble(self, bubble, b_layout, text: str, is_queued: bool):
        """Balão do usuário: largura medida e alinhado à direita (estilo ChatGPT)."""
        bubble.setProperty("class", "UserBubble")
        b_layout.setContentsMargins(0, 0, 0, 0)

        lbl_content = self._make_content_label(text, " padding: 0px; margin: 0px;")
        b_layout.addWidget(lbl_content)

        bubble._queue_badge = None
        if is_queued:
            lbl_queue = QLabel("⏳ Na fila de espera...")
            lbl_queue.setFont(QFont("Sans Serif", 8, QFont.Weight.Medium))
            lbl_queue.setStyleSheet("color: #fad094; background: transparent; font-style: italic; margin-top: 4px;")
            b_layout.addWidget(lbl_queue)
            bubble._queue_badge = lbl_queue

        # Mede a largura exata para o Qt não quebrar a linha antes da hora.
        fm = QFontMetrics(lbl_content.font())
        max_limit = 620
        linhas = text.split("\n")
        max_linha_w = max(fm.horizontalAdvance(l) for l in linhas) if linhas else 100
        ideal_w = min(max_limit, max_linha_w + 30)

        if max_linha_w + 30 <= max_limit:
            bubble.setFixedWidth(ideal_w)
        else:
            bubble.setMaximumWidth(max_limit)
            bubble.setMinimumWidth(360)

        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(0)
        row_layout.addStretch(1)
        row_layout.addWidget(bubble, 0)

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, row_widget)
        return lbl_content

    def _build_ai_bubble(self, bubble, b_layout, text: str):
        """Balão da IA: cabeçalho com provedor e relógio, texto, chips e ações."""
        bubble.setProperty("class", "AIBubble")
        b_layout.setContentsMargins(2, 2, 2, 8)
        b_layout.setSpacing(4)

        b_layout.addLayout(self._build_ai_header(bubble))

        lbl_content = self._make_content_label(text)
        b_layout.addWidget(lbl_content)

        # Chips de comando: some enquanto a IA ainda está pensando ou buscando.
        if "Pensando..." not in text and "Buscando informações" not in text:
            self._render_command_chips_for_bubble(bubble, b_layout, text)

        b_layout.addLayout(self._build_ai_actions(lbl_content))
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        return lbl_content

    def _build_ai_header(self, bubble):
        """Provedor à esquerda, relógio de resposta à direita."""
        prov_label = getattr(self.current_service, "nome_provedor", "METIS ORACLE")
        head_row = QHBoxLayout()
        head_row.setContentsMargins(0, 0, 0, 0)
        head_row.setSpacing(6)

        lbl_role = QLabel(f"🏛️ {prov_label.upper()}")
        lbl_role.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_role.setStyleSheet("color: #fad094; background: transparent;")
        head_row.addWidget(lbl_role)

        head_row.addStretch()

        lbl_timer = QLabel("⏱️ 0.0s")
        lbl_timer.setFont(QFont("Sans Serif", 8, QFont.Weight.Medium))
        lbl_timer.setStyleSheet("color: #64748b; background: transparent; font-size: 8pt;")
        head_row.addWidget(lbl_timer)
        # `_lbl_timer` é lido por fora, ao cronometrar a resposta.
        bubble._lbl_timer = lbl_timer
        return head_row

    def _build_ai_actions(self, lbl_content):
        """Barra de copiar/regenerar embaixo da resposta."""
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 4, 0, 0)
        actions_row.setSpacing(6)

        btn_copy = QPushButton("❐")
        btn_copy.setProperty("class", "IconActionBtn")
        btn_copy.setToolTip("Copiar resposta")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)

        def copy_text(_checked):
            try:
                # `_raw_text`, não o texto renderizado: markdown vira HTML e
                # copiaria as tags junto.
                raw = getattr(lbl_content, "_raw_text", lbl_content.text())
                if copiar_para_area_de_transferencia(raw):
                    btn_copy.setText("✓")
                    btn_copy.setToolTip("Copiado!")
                    QTimer.singleShot(2000, lambda: (btn_copy.setText("❐"), btn_copy.setToolTip("Copiar resposta")))
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

        btn_copy.clicked.connect(copy_text)
        actions_row.addWidget(btn_copy)

        btn_retry = QPushButton("↻")
        btn_retry.setProperty("class", "IconActionBtn")
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.setToolTip("Regerar resposta")
        btn_retry.clicked.connect(self.retry_last_query)
        actions_row.addWidget(btn_retry)

        actions_row.addStretch()
        return actions_row


    def clear_chat_view(self):
        if hasattr(self, "query_queue") and self.query_queue:
            self.query_queue.clear()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def scroll_chat_to_bottom(self):
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))
