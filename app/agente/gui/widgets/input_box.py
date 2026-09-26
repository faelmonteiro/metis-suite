"""Barra de digitacao: popup de comandos slash e o campo de texto com auto-ajuste."""

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
)

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QSize,
    pyqtSignal,
)

from PyQt6.QtGui import (
    QFont,
    QTextCursor,
    QTextOption,
)

from agente.gui.theme_bridge import build_dynamic_qss
from agente.ui.theme_manager import get_current_font_sizes

SLASH_COMMANDS = [
    ("/novo", "✨"),
    ("/web", "🌐"),
    ("/executar", "⚡"),
    ("/arquivo", "📎"),
    ("/oraculo", "🧠"),
    ("/tema", "🎨"),
    ("/retry", "🔁"),
    ("/limpar", "🧹"),
    ("/sessao", "📁"),
    ("/exportar", "💾"),
    ("/status", "📊"),
    ("/opcoes", "🤖"),
    ("/restaurar", "🔄"),
    ("/ajuda", "❓"),
]


class SlashCommandPopup(QFrame):
    """
    Menu compacto e minimalista de comandos slash (/) estilo CLI acoplado à barra de digitação.
    Totalmente integrado com as cores do tema e escala tipográfica em tempo real.
    """
    def __init__(self, parent_edit):
        parent_window = parent_edit.window() if parent_edit else None
        super().__init__(parent_window)
        self.parent_edit = parent_edit
        self.setObjectName("SlashCommandPopup")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(1)

        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("SlashCommandList")
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

        self.update_theme_style()
        self.hide()

    def update_theme_style(self):
        """Re-aplica as cores do tema ativo e sincroniza o tamanho da fonte."""
        self.setStyleSheet(build_dynamic_qss())
        f_sz = get_current_font_sizes()
        font = QFont("Sans Serif", f_sz.get("base", 11))
        self.list_widget.setFont(font)
        self.style().unpolish(self)
        self.style().polish(self)

    def populate_commands(self, filter_text: str = "") -> bool:
        self.list_widget.clear()
        f_txt = filter_text.lower().strip()

        f_sz = get_current_font_sizes()
        item_font = QFont("Sans Serif", f_sz.get("base", 11))
        item_h = max(20, f_sz.get("base", 11) + 12)

        count = 0
        for cmd, icon in SLASH_COMMANDS:
            if not f_txt or cmd.lower().startswith(f_txt):
                item = QListWidgetItem(f"{icon}  {cmd}")
                item.setFont(item_font)
                item.setSizeHint(QSize(130, item_h))
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                self.list_widget.addItem(item)
                count += 1

        if count > 0:
            self.list_widget.setCurrentRow(0)
            h = min(220, max(30, count * item_h + 8))
            self.setFixedHeight(h)
            return True
        return False

    def reposition(self):
        if not self.parent_edit:
            return
        window = self.parent_edit.window()
        if not window:
            return

        f_sz = get_current_font_sizes()
        popup_w = max(135, int(f_sz.get("base", 11) * 12))
        edit_pos = self.parent_edit.mapTo(window, QPoint(0, 0))
        popup_x = max(16, min(edit_pos.x(), window.width() - popup_w - 16))
        popup_y = edit_pos.y() - self.height() - 4

        if popup_y < 10:
            popup_y = edit_pos.y() + self.parent_edit.height() + 4

        self.setGeometry(popup_x, popup_y, popup_w, self.height())
        self.raise_()

    def on_item_clicked(self, item):
        if not item:
            return
        cmd = item.data(Qt.ItemDataRole.UserRole)
        if cmd and self.parent_edit:
            self.hide()
            self.parent_edit.insert_slash_command(cmd)


class SmartPromptTextEdit(QTextEdit):
    """
    Campo de texto inteligente multi-linha com:
    - Shift + Enter para pular/quebrar linha
    - Enter sozinho para enviar
    - Menu minimalista acoplado para comandos slash (/) com navegação por setas (↑ / ↓)
    - Quebra de palavras inteiras (WordWrap) sem quebrar no meio
    - Auto-expansão dinâmica de altura (38px -> 115px)
    - Ctrl + C para interromper a IA quando não houver texto selecionado
    """
    returnPressed = pyqtSignal()
    cancelRequested = pyqtSignal()

    def __init__(self, parent=None, placeholder: str = ""):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(38)
        self.document().contentsChanged.connect(self.on_text_changed)
        self.slash_popup = None

    def _get_slash_popup(self):
        if self.slash_popup is None:
            self.slash_popup = SlashCommandPopup(self)
        return self.slash_popup

    def insert_slash_command(self, cmd: str):
        """Insere o comando slash e posiciona o cursor logo após o espaço no final."""
        if self.slash_popup:
            self.slash_popup.hide()
        self.setPlainText(f"{cmd} ")
        self.adjust_height()
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()
        self.setFocus()
        if self.slash_popup:
            self.slash_popup.hide()

    def on_text_changed(self):
        self.adjust_height()
        self.check_slash_command()

    def check_slash_command(self):
        txt = self.toPlainText()
        popup = self._get_slash_popup()

        if txt.startswith("/") and " " not in txt:
            has_items = popup.populate_commands(txt.strip())
            if has_items:
                popup.reposition()
                popup.show()
            else:
                popup.hide()
        else:
            popup.hide()

    def focusOutEvent(self, event):
        if self.slash_popup and self.slash_popup.isVisible():
            QTimer.singleShot(150, self._hide_popup_if_not_focused)
        super().focusOutEvent(event)

    def _hide_popup_if_not_focused(self):
        if self.slash_popup and not self.hasFocus():
            self.slash_popup.hide()

    def hideEvent(self, event):
        if self.slash_popup:
            self.slash_popup.hide()
        super().hideEvent(event)

    def adjust_height(self):
        doc_height = int(self.document().size().height()) + 8
        new_height = max(38, min(115, doc_height))
        if self.height() != new_height:
            self.setFixedHeight(new_height)
            if self.slash_popup and self.slash_popup.isVisible():
                self.slash_popup.reposition()

    def keyPressEvent(self, event):
        popup = self._get_slash_popup()

        if popup and popup.isVisible():
            count = popup.list_widget.count()
            if count > 0:
                if event.key() == Qt.Key.Key_Down:
                    curr = popup.list_widget.currentRow()
                    next_row = (curr + 1) % count
                    popup.list_widget.setCurrentRow(next_row)
                    popup.list_widget.scrollToItem(popup.list_widget.currentItem())
                    event.accept()
                    return

                if event.key() == Qt.Key.Key_Up:
                    curr = popup.list_widget.currentRow()
                    next_row = (curr - 1 + count) % count
                    popup.list_widget.setCurrentRow(next_row)
                    popup.list_widget.scrollToItem(popup.list_widget.currentItem())
                    event.accept()
                    return

                if event.key() == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    curr = popup.list_widget.currentRow()
                    next_row = (curr + 1) % count
                    popup.list_widget.setCurrentRow(next_row)
                    popup.list_widget.scrollToItem(popup.list_widget.currentItem())
                    event.accept()
                    return

                if event.key() == Qt.Key.Key_Tab and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    curr = popup.list_widget.currentRow()
                    next_row = (curr - 1 + count) % count
                    popup.list_widget.setCurrentRow(next_row)
                    popup.list_widget.scrollToItem(popup.list_widget.currentItem())
                    event.accept()
                    return

                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    item = popup.list_widget.currentItem()
                    if item:
                        popup.on_item_clicked(item)
                        event.accept()
                        return

            if event.key() == Qt.Key.Key_Escape:
                popup.hide()
                event.accept()
                return

        # 1. Shift + Enter -> Quebra de linha normal
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                self.adjust_height()
                return
            else:
                # Enter sozinho -> Submete
                event.accept()
                self.returnPressed.emit()
                return

        # 2. Ctrl + C -> Se nada estiver selecionado ou caixa vazia, solicita cancelamento da IA
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                self.cancelRequested.emit()
                return

        # 3. Escape -> Interrompe geração da IA imediatamente
        if event.key() == Qt.Key.Key_Escape:
            self.cancelRequested.emit()
            return

        super().keyPressEvent(event)

    def text(self) -> str:
        return self.toPlainText().strip()

    def setText(self, txt: str):
        self.setPlainText(txt)
        self.adjust_height()
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()

    def clear(self):
        super().clear()
        self.setFixedHeight(38)
        if self.slash_popup:
            self.slash_popup.hide()
