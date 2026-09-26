"""Cartao do menu lateral, com suporte a selecao por teclado."""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QFrame,
)

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtGui import (
    QFont,
    QCursor,
)

from agente.gui.theme_bridge import get_system_theme_colors

# -----------------------------------------------------------------------------
class MenuCardWidget(QFrame):
    clicked = pyqtSignal(str)
    hovered = pyqtSignal(int)

    def __init__(self, index: int, numero: str, icone: str, titulo: str, subtitulo: str, code: str, is_danger: bool = False):
        super().__init__()
        self.index = index
        self.code = code
        self.is_danger = is_danger
        self.numero = numero
        self.is_selected = False
        self.setObjectName("MenuCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 12, 0)
        layout.setSpacing(8)

        # Indicador › + Número
        self.lbl_num = QLabel(f"  {numero}")
        self.lbl_num.setFont(QFont("Monospace", 10, QFont.Weight.Bold))
        self.lbl_num.setFixedWidth(36)
        layout.addWidget(self.lbl_num)

        # Ícone
        self.lbl_icon = QLabel(icone)
        self.lbl_icon.setFont(QFont("Sans Serif", 12))
        self.lbl_icon.setStyleSheet("background: transparent;")
        self.lbl_icon.setFixedWidth(24)
        layout.addWidget(self.lbl_icon)

        # Título
        self.title_color = "#f87171" if is_danger else "#f8fafc"
        self.lbl_title = QLabel(titulo)
        self.lbl_title.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        layout.addWidget(self.lbl_title)

        layout.addStretch(1)

        # Subtítulo
        self.lbl_sub = QLabel(subtitulo)
        self.lbl_sub.setFont(QFont("Sans Serif", 9))
        layout.addWidget(self.lbl_sub)

        self.update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        prefix = "› " if selected else "  "
        self.lbl_num.setText(f"{prefix}{self.numero}")
        self.update_style()

    def update_style(self):
        c = get_system_theme_colors()
        if self.is_selected:
            border_color = "#f87171" if self.is_danger else c["accent_gold"]
            bg_color = "#2b1215" if self.is_danger else c["bg_input"]
            num_color = "#fca5a5" if self.is_danger else c["accent_gold"]
            title_color = "#fca5a5" if self.is_danger else c["accent_gold"]

            self.setStyleSheet(f"""
                QFrame#MenuCard {{
                    background-color: {bg_color};
                    border: 1.5px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            self.lbl_num.setStyleSheet(f"color: {num_color}; background: transparent;")
            self.lbl_title.setStyleSheet(f"color: {title_color}; background: transparent;")
            self.lbl_sub.setStyleSheet(f"color: {c['fg_sub']}; background: transparent;")
        else:
            num_color = "#f87171" if self.is_danger else c["accent_cyan"]
            self.setStyleSheet(f"""
                QFrame#MenuCard {{
                    background-color: {c['bg_card']};
                    border: 1px solid {c['border']};
                    border-radius: 8px;
                }}
            """)
            self.lbl_num.setStyleSheet(f"color: {num_color}; background: transparent;")
            self.lbl_title.setStyleSheet(f"color: {self.title_color}; background: transparent;")
            self.lbl_sub.setStyleSheet(f"color: {c['fg_sub']}; background: transparent;")

    def enterEvent(self, event):
        self.hovered.emit(self.index)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.code)
        super().mousePressEvent(event)
