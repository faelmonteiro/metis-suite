"""Pagina 4, historico de conversas e gerenciamento de memoria.

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QMessageBox,
    QInputDialog,
    QComboBox,
)

from PyQt6.QtCore import Qt

from PyQt6.QtGui import QFont

from agente import config
from agente.history import HistoryManager
from datetime import datetime
from pathlib import Path

class SessionsMixin:
    """Historico de conversas e gerenciamento de memoria.

    Lista de sessoes, criar/renomear, renderizar os turnos no chat e apagar
    turnos ou o arquivo inteiro da sessao.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def setup_sessions_ui(self, parent: QWidget):
        """Monta a pagina. So orquestra; os tres topicos tem builders.

        A ordem das chamadas NAO e cosmetics: `tests/gui_impressao_digital.txt`
        fixa a ordem de criacao dos objetos, e quem define a geometria final e
        a ordem de insercao no layout, nao a ordem do codigo.
        """
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addLayout(self._build_sessions_header())

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        layout.addWidget(div)

        layout.addWidget(self._build_session_manager_card())
        layout.addWidget(self._build_memory_actions_card())

        layout.addWidget(self._build_timeline_label())
        layout.addWidget(self._build_timeline_scroll(), 1)

    def _build_sessions_header(self):
        """Voltar, titulo e atalho para o chat."""
        header = QHBoxLayout()
        header.setSpacing(12)

        btn_back = QPushButton("← Voltar")
        btn_back.setProperty("class", "SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(btn_back)

        lbl_t = QLabel("📜 TÁBULA DE MÉTIS • REGISTROS & TURNOS")
        lbl_t.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: #fad094;")
        header.addWidget(lbl_t)

        header.addStretch()

        btn_continue = QPushButton("💬 Ir para o Chat ↵")
        btn_continue.setProperty("class", "PrimaryBtn")
        btn_continue.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        header.addWidget(btn_continue)

        return header

    def _build_session_manager_card(self):
        """Tópico 1: o combo de sessões e os botoes de criar/renomear/excluir."""
        card_sess = QFrame()
        card_sess.setProperty("class", "HelpCard")
        l_sess = QVBoxLayout(card_sess)
        l_sess.setContentsMargins(12, 10, 12, 10)
        l_sess.setSpacing(8)

        lbl_head_sess = QLabel("📁 TÓPICO 1 • SELEÇÃO & GERENCIAMENTO DE SESSÕES")
        lbl_head_sess.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_head_sess.setStyleSheet("color: #f0a85d; background: transparent;")
        l_sess.addWidget(lbl_head_sess)

        row_sess = QHBoxLayout()
        row_sess.setSpacing(8)

        lbl_sess_tag = QLabel("Sessão:")
        lbl_sess_tag.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sess_tag.setStyleSheet("color: #94a3b8; background: transparent;")
        row_sess.addWidget(lbl_sess_tag)

        self.combo_sessions = QComboBox()
        self.combo_sessions.setMinimumWidth(240)
        self.combo_sessions.currentIndexChanged.connect(self.on_session_selected)
        row_sess.addWidget(self.combo_sessions, 1)

        btn_new_sess = QPushButton("➕ Nova Sessão")
        btn_new_sess.setProperty("class", "ActionChip")
        btn_new_sess.clicked.connect(self.create_new_session)
        row_sess.addWidget(btn_new_sess)

        btn_rename_sess = QPushButton("✏️ Renomear")
        btn_rename_sess.setProperty("class", "ActionChip")
        btn_rename_sess.clicked.connect(self.rename_current_session)
        row_sess.addWidget(btn_rename_sess)

        btn_del_session = QPushButton("🗑️ Excluir Sessão")
        btn_del_session.setProperty("class", "DangerBtn")
        btn_del_session.clicked.connect(self.delete_current_session_file)
        row_sess.addWidget(btn_del_session)

        l_sess.addLayout(row_sess)

        self.lbl_sess_info = QLabel("Sessão ativa: - • 0 turnos registrados")
        self.lbl_sess_info.setFont(QFont("Monospace", 8))
        self.lbl_sess_info.setStyleSheet("color: #67e8f9; background: transparent;")
        l_sess.addWidget(self.lbl_sess_info)

        return card_sess

    def _build_memory_actions_card(self):
        """Tópico 2: desfazer turno, excluir N turnos, exportar."""
        card_ops = QFrame()
        card_ops.setProperty("class", "HelpCard")
        l_ops = QVBoxLayout(card_ops)
        l_ops.setContentsMargins(12, 10, 12, 10)
        l_ops.setSpacing(8)

        lbl_head_ops = QLabel("⚡ TÓPICO 2 • OPERAÇÕES & EXPORTAÇÃO DA MEMÓRIA")
        lbl_head_ops.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_head_ops.setStyleSheet("color: #f0a85d; background: transparent;")
        l_ops.addWidget(lbl_head_ops)

        row_ops = QHBoxLayout()
        row_ops.setSpacing(8)

        btn_del_last = QPushButton("⏪ Desfazer Último Turno")
        btn_del_last.setProperty("class", "ActionChip")
        btn_del_last.clicked.connect(self.delete_last_turn)
        row_ops.addWidget(btn_del_last)

        btn_del_n = QPushButton("✂️ Excluir N Turnos...")
        btn_del_n.setProperty("class", "ActionChip")
        btn_del_n.clicked.connect(self.delete_n_turns)
        row_ops.addWidget(btn_del_n)

        btn_export = QPushButton("📤 Exportar para Markdown")
        btn_export.setProperty("class", "ActionChip")
        btn_export.clicked.connect(self.export_current_session)
        row_ops.addWidget(btn_export)

        row_ops.addStretch()

        l_ops.addLayout(row_ops)
        return card_ops

    def _build_timeline_label(self):
        """Tópico 3: o cabecalho da linha do tempo.

        Fica em metodo proprio (e nao junto do scroll) porque sao dois widgets
        irmaos no layout do pai — um container artificial aqui acrescentaria um
        nodo a arvore e mudaria a geometria.
        """
        lbl_timeline = QLabel("📜 HISTÓRICO VISUAL DOS TURNOS (LINHA DO TEMPO)")
        lbl_timeline.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_timeline.setStyleSheet("color: #fad094; margin-top: 2px;")
        return lbl_timeline

    def _build_timeline_scroll(self):
        """Tópico 3: o QScrollArea que abriga os cards de turno.

        Os tres atributos ficam expostos porque `render_current_turns`
        reconstroi a lista a cada navegacao.
        """
        self.turns_scroll = QScrollArea()
        self.turns_scroll.setWidgetResizable(True)
        self.turns_container = QWidget()
        self.turns_layout = QVBoxLayout(self.turns_container)
        self.turns_layout.setContentsMargins(0, 0, 0, 0)
        self.turns_layout.setSpacing(8)
        self.turns_layout.addStretch()
        self.turns_scroll.setWidget(self.turns_container)
        return self.turns_scroll

    def open_sessions_page(self):
        self.refresh_sessions_dropdown()
        self.render_current_turns()
        self.stack.setCurrentIndex(4)

    def refresh_sessions_dropdown(self):
        self.combo_sessions.blockSignals(True)
        self.combo_sessions.clear()

        hist_dir = Path(config.HISTORICO_DIR)
        arquivos = sorted(list(hist_dir.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True) if hist_dir.exists() else []

        curr_sess = getattr(self.history_manager, "sessao", "")
        curr_idx = 0

        for i, f in enumerate(arquivos):
            if f.name.startswith("."):
                continue
            s_name = f.stem
            self.combo_sessions.addItem(f"💬 {s_name}", s_name)
            if s_name == curr_sess:
                curr_idx = i

        if not arquivos and curr_sess:
            self.combo_sessions.addItem(f"💬 {curr_sess}", curr_sess)

        self.combo_sessions.setCurrentIndex(curr_idx)
        self.combo_sessions.blockSignals(False)

    def on_session_selected(self, index: int):
        s_name = self.combo_sessions.itemData(index)
        if s_name and s_name != self.history_manager.sessao:
            self.history_manager = HistoryManager(s_name)
            self.clear_chat_view()
            for msg in self.history_manager.historico:
                self.add_chat_bubble(msg.get("role", "user"), msg.get("content", ""))
            self.refresh_telemetry()
            self.render_current_turns()

    def create_new_session(self):
        nova_sess = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.history_manager = HistoryManager(nova_sess)
        self.clear_chat_view()
        self.refresh_telemetry()
        self.refresh_sessions_dropdown()
        self.render_current_turns()
        self.stack.setCurrentIndex(1)
        self.chat_input.setFocus()

    def rename_current_session(self):
        novo_nome, ok = QInputDialog.getText(
            self,
            "Renomear Sessão",
            "Digite o novo nome para esta sessão de conversa:",
            text=self.history_manager.sessao
        )
        if ok and novo_nome.strip():
            if self.history_manager.renomear_sessao(novo_nome.strip()):
                self.refresh_sessions_dropdown()
                self.render_current_turns()
                self.refresh_telemetry()
                QMessageBox.information(self, "Metis", "Sessão renomeada com sucesso!")
            else:
                QMessageBox.warning(self, "Metis", "Não foi possível renomear a sessão (nome inválido ou já existente).")

    def render_current_turns(self):
        while self.turns_layout.count() > 1:
            item = self.turns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        turnos = self.history_manager.listar_turnos()
        total = len(turnos)
        self.lbl_sess_info.setText(f"Sessão ativa: {self.history_manager.sessao} • {total} turnos registrados")

        if not turnos:
            lbl_empty = QLabel("Histórico desta sessão está vazio. Inicie uma nova conversa no chat!")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 11px; padding: 20px;")
            self.turns_layout.insertWidget(0, lbl_empty)
            return

        for idx, t in enumerate(turnos):
            card = QFrame()
            card.setProperty("class", "TurnCard")
            l_t = QVBoxLayout(card)
            l_t.setContentsMargins(14, 12, 14, 12)
            l_t.setSpacing(8)

            head_row = QHBoxLayout()
            lbl_num = QLabel(f"TURNO #{idx + 1:02d}")
            lbl_num.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
            lbl_num.setStyleSheet("color: #fad094;")
            head_row.addWidget(lbl_num)
            head_row.addStretch()

            btn_rewind = QPushButton("⏪ Continuar daqui (Apagar posteriores)")
            btn_rewind.setProperty("class", "ActionChip")
            def rewind_to(_checked, i=idx):
                # `False == 0` em Python: sem o `_checked` explicito, o PyQt
                # entregava o bool do `clicked` em `i` e "Continuar daqui"
                # truncava sempre no turno 0, apagando o resto da conversa.
                if self.history_manager.truncar_ate(i):
                    self.clear_chat_view()
                    for msg in self.history_manager.historico:
                        self.add_chat_bubble(msg.get("role", "user"), msg.get("content", ""))
                    self.refresh_telemetry()
                    self.stack.setCurrentIndex(1)
                    self.chat_input.setFocus()
            btn_rewind.clicked.connect(rewind_to)
            head_row.addWidget(btn_rewind)

            btn_del_t = QPushButton("🗑️ Excluir Turno")
            btn_del_t.setProperty("class", "DangerBtn")
            def delete_single(_checked, i=idx):
                # Mesmo `False == 0`: "Excluir Turno" apagava o turno 0 em vez
                # do turno da linha, sem nenhum aviso.
                if self.history_manager.remover_turno(i):
                    self.render_current_turns()
                    self.refresh_telemetry()
            btn_del_t.clicked.connect(delete_single)
            head_row.addWidget(btn_del_t)

            l_t.addLayout(head_row)

            # User Prompt
            user_text = t.get("user", "")
            l_u = QLabel(f"👤 <b>Você:</b> {user_text}")
            l_u.setFont(QFont("Sans Serif", 10))
            l_u.setStyleSheet("color: #7dd3fc; background-color: #101c2e; padding: 8px 12px; border-radius: 6px;")
            l_u.setWordWrap(True)
            l_u.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            l_t.addWidget(l_u)

            # Assistant Response
            assist_text = t.get("assistant", "")
            l_a = QLabel(f"🏛️ <b>Metis:</b> {assist_text}")
            l_a.setFont(QFont("Sans Serif", 11))
            l_a.setStyleSheet("color: #f8fafc; background-color: #0c1422; padding: 10px 14px; border-radius: 6px;")
            l_a.setWordWrap(True)
            l_a.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            l_t.addWidget(l_a)

            self.turns_layout.insertWidget(self.turns_layout.count() - 1, card)

    def delete_last_turn(self):
        if self.history_manager.deletar_ultimos(1):
            self.render_current_turns()
            self.refresh_telemetry()

    def delete_n_turns(self):
        val, ok = QInputDialog.getInt(self, "Excluir Turnos", "Quantos turnos finais deseja excluir?", 1, 1, 100, 1)
        if ok:
            if self.history_manager.deletar_ultimos(val):
                self.render_current_turns()
                self.refresh_telemetry()

    def delete_current_session_file(self):
        res = QMessageBox.warning(
            self,
            "Deletar Sessão",
            f"Tem certeza que deseja excluir o arquivo da sessão '{self.history_manager.sessao}' permanentemente do PC?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.history_manager.deletar_sessao()

            # Seleciona a próxima sessão existente ou gera uma nova limpa
            hist_dir = Path(config.HISTORICO_DIR)
            arquivos = sorted(list(hist_dir.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True) if hist_dir.exists() else []
            sessoes_validas = [f.stem for f in arquivos if not f.name.startswith(".")]

            if sessoes_validas:
                proxima_sess = sessoes_validas[0]
                self.history_manager = HistoryManager(proxima_sess)
            else:
                nova_sess = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.history_manager = HistoryManager(nova_sess)

            self.clear_chat_view()
            for msg in self.history_manager.historico:
                self.add_chat_bubble(msg.get("role", "user"), msg.get("content", ""))

            self.refresh_telemetry()
            self.refresh_sessions_dropdown()
            self.render_current_turns()
            # Permanece na mesma tela de Arquivos da Memória
            self.stack.setCurrentIndex(4)
            QMessageBox.information(self, "Metis", "Sessão deletada com sucesso!")
