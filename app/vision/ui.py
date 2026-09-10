"""
Interface Gráfica Flutuante e Moderna (Metis Oracle • HUD Style) em PyQt6.
Inclui:
  1. Barra lateral recolhível (Collapsible Sidebar) com ícones temáticos clássicos/ouro e tipografia espaçosa.
  2. Pré-visualização compacta e elegante da captura com transição para chat/markdown.
  3. Suporte completo a Wayland / Hyprland e X11 com posicionamento inteligente.
  4. Extrator de comandos bash, streaming de IA e histórico contínuo de conversação.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QRect, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import (
    QKeyEvent, QGuiApplication,
    QPixmap, QImage, QCursor, QIcon, QDragEnterEvent, QDropEvent, QDragLeaveEvent,
    QTextCursor
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QLabel,
    QFrame,
    QComboBox,
    QFileDialog,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QSizePolicy,
    QAbstractItemView,
    QMenu
)

_vision_dir = str(Path(__file__).resolve().parent)
if _vision_dir not in sys.path:
    sys.path.insert(0, _vision_dir)

import config
import model_manager
from capture import capture_screen
from ai_engine import VisionAIEngine
from folder_analyzer import (
    format_folder_context, format_file_context, detect_and_attach_local_files,
    get_active_window_cwd, detect_save_target_path
)
import theme_manager

PROVIDER_ICONS = {
    "nvidia": "⚡ NVIDIA",
    "gemini": "💎 Gemini",
    "openrouter": "🌐 OpenRouter",
    "ollama": "🦙 Ollama",
    "groq": "🚀 Groq",
    "g4f": "🤖 G4F (Gratuito)",
    "anthropic": "🧠 Anthropic",
    "openai": "🔮 OpenAI",
}


class ModernInputDialog(QDialog):
    """Diálogo modal customizado com StaysOnTopHint e tema Metis para entrada de texto sem conflitos em Wayland/Hyprland."""
    def __init__(self, parent=None, title: str = "Editar Modelo", label: str = "ID do modelo:", default_text: str = "", placeholder: str = ""):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(460, 195)
        self.drag_position = QPoint()

        t = theme_manager.get_theme_palette()
        
        # Centraliza sobre a janela pai caso disponível
        if parent:
            try:
                p_geo = parent.geometry()
                x = p_geo.x() + (p_geo.width() - 460) // 2
                y = p_geo.y() + (p_geo.height() - 195) // 2
                self.move(max(10, x), max(10, y))
            except Exception:
                pass

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        card = QFrame()
        card.setObjectName("ModernModalCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        # Header com título
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {t['accent']}; font-size: 13.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        card_layout.addWidget(title_lbl)

        # Label de instrução
        desc_lbl = QLabel(label)
        desc_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent;")
        desc_lbl.setWordWrap(True)
        card_layout.addWidget(desc_lbl)

        # Input
        self.input_field = QLineEdit()
        self.input_field.setText(default_text)
        if placeholder:
            self.input_field.setPlaceholderText(placeholder)
        self.input_field.selectAll()
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t['inner_box_bg']};
                color: {t['text_primary']};
                border: 1.2px solid {t['border_col']};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 12px;
                font-family: {t['font_family']};
            }}
            QLineEdit:focus {{
                border: 1.4px solid {t['accent']};
                background-color: {t['inner_box_hover']};
            }}
        """)
        self.input_field.returnPressed.connect(self.accept)
        card_layout.addWidget(self.input_field)

        # Botões na barra inferior
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['inner_box_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t['inner_box_hover']};
                border-color: {t['accent']};
                color: {t['accent']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("✓ Salvar")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['accent_btn_bg']};
                color: {t['accent_btn_fg']};
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 11.5px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background-color: {t['accent_btn_hover']};
                color: #ffffff;
            }}
        """)
        save_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        card_layout.addLayout(btn_row)

        card.setStyleSheet(f"""
            QFrame#ModernModalCard {{
                background-color: {t['card_bg_rgba']};
                border: {t['card_border_style']};
                border-radius: 12px;
            }}
        """)
        main_layout.addWidget(card)

    def get_text(self) -> str:
        return self.input_field.text().strip()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


class ModernConfirmDialog(QDialog):
    """Diálogo modal de confirmação com StaysOnTopHint e tema Metis para exclusão segura de modelos."""
    def __init__(self, parent=None, title: str = "Remover Modelo", message: str = "Tem certeza?", danger_text: str = "🗑️ Excluir", cancel_text: str = "Cancelar"):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(450, 190)
        self.drag_position = QPoint()

        t = theme_manager.get_theme_palette()
        
        # Centraliza sobre a janela pai caso disponível
        if parent:
            try:
                p_geo = parent.geometry()
                x = p_geo.x() + (p_geo.width() - 450) // 2
                y = p_geo.y() + (p_geo.height() - 190) // 2
                self.move(max(10, x), max(10, y))
            except Exception:
                pass

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        card = QFrame()
        card.setObjectName("ModernModalCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # Header com título
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #f87171; font-size: 13.5px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        card_layout.addWidget(title_lbl)

        # Mensagem
        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"color: {t['text_primary']}; font-size: 11.5px; line-height: 1.4; background: transparent;")
        msg_lbl.setWordWrap(True)
        card_layout.addWidget(msg_lbl)

        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton(cancel_text)
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['inner_box_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t['inner_box_hover']};
                border-color: {t['accent']};
                color: {t['accent']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        danger_btn = QPushButton(danger_text)
        danger_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        danger_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #f87171;
                border: 1px solid #ef4444;
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 11.5px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        danger_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(danger_btn)
        card_layout.addLayout(btn_row)

        card.setStyleSheet(f"""
            QFrame#ModernModalCard {{
                background-color: {t['card_bg_rgba']};
                border: {t['card_border_style']};
                border-radius: 12px;
            }}
        """)
        main_layout.addWidget(card)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


class PromptTextEdit(QPlainTextEdit):
    """Editor de prompt moderno que suporta Shift+Enter para quebra de linha e navegação por setas no menu."""
    returnPressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchInput")
        self.setTabChangesFocus(True)
        self.document().setDocumentMargin(1)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        self._adjust_height()
        p = self.window()
        if hasattr(p, 'clear_sidebar_highlight') and self.toPlainText().strip():
            p.clear_sidebar_highlight()

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str):
        self.setPlainText(text)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._adjust_height()

    def _adjust_height(self):
        doc = self.document()
        layout = doc.documentLayout()
        doc_height = int(layout.documentSize().height()) + 4
        target_height = max(30, min(85, doc_height))
        if self.height() != target_height:
            self.setFixedHeight(target_height)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        # Setas para Cima / Baixo quando o campo está vazio ou com Alt
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if not self.toPlainText().strip() or (event.modifiers() & Qt.KeyboardModifier.AltModifier):
                direction = 1 if key == Qt.Key.Key_Down else -1
                p = self.window()
                if hasattr(p, 'navigate_sidebar'):
                    p.navigate_sidebar(direction)
                    event.accept()
                    return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                self._adjust_height()
                return
            else:
                p = self.window()
                # Se o campo de texto está vazio e um item do menu está selecionado pelas setas, executa o item
                if not self.toPlainText().strip() and hasattr(p, 'execute_selected_sidebar_action'):
                    if p.execute_selected_sidebar_action():
                        event.accept()
                        return
                self.returnPressed.emit()
                event.accept()
                return
        super().keyPressEvent(event)


class ChatWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished_stream = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        messages: List[Dict[str, str]],
        image_bytes: Optional[bytes] = None,
        text_context: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        super().__init__()
        self.messages = messages
        self.image_bytes = image_bytes
        self.text_context = text_context
        self.engine = VisionAIEngine(provider=provider, model=model)
        self._chunks: List[str] = []
        self._is_stopped = False

    def stop(self):
        """Sinaliza para parar a geração de streaming imediatamente."""
        self._is_stopped = True

    def run(self):
        try:
            generator = (
                self.engine.analyze_text_stream(self.messages[-1]["content"] if self.messages else "", context=self.text_context)
                if self.text_context
                else self.engine.chat_multiturn_stream(self.messages, image_bytes=self.image_bytes)
            )
            for chunk in generator:
                if self._is_stopped:
                    break
                self._chunks.append(chunk)
                self.chunk_received.emit(chunk)
            
            if not self._is_stopped:
                final_text = "".join(self._chunks)
                self.finished_stream.emit(final_text)
        except Exception as e:
            if not self._is_stopped:
                self.error_occurred.emit(str(e))


class ScreenAIOverlay(QWidget):
    def __init__(self, capture_mode: str = "fullscreen", target_path: Optional[str] = None):
        super().__init__()
        self.capture_mode = capture_mode
        self.target_path = target_path
        self.text_context: Optional[str] = None
        self.captured_image: Optional[bytes] = None
        
        # Provedor e modelo ativos selecionados
        self.current_provider, self.current_model = model_manager.get_active_model()

        # Estado da barra lateral (expandida ou recolhida) persistido
        self.is_sidebar_collapsed = bool(model_manager.get_user_setting("is_sidebar_collapsed", False))
        self.sidebar_items_widgets: List[Tuple[QFrame, QLabel, QLabel, str]] = []
        self.selected_sidebar_idx: int = -1

        # Histórico de Conversação (Chat Contínuo)
        self.chat_history: List[Dict[str, str]] = []
        self.rendered_markdown_history = ""
        self.current_stream_chunk = ""
        
        self.worker: Optional[ChatWorker] = None
        self.drag_position = QPoint()
        self.active_window_cwd: Optional[Path] = get_active_window_cwd()
        self.pending_save_path: Optional[Path] = None
        self.last_failed_prompt: Optional[str] = None

        # Timer de renderização suave de Markdown (Throttle de 40ms)
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(40)
        self._render_timer.timeout.connect(self._flush_markdown_render)

        self.init_ui()
        self.setup_initial_context()

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Metis Vision")
        self.setAcceptDrops(True)
        # Dimensões compactas exatas (585x385)
        self.resize(585, 385)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self.theme = theme_manager.get_theme_palette()
        self.current_stylesheet = theme_manager.generate_main_stylesheet(self.theme)

        self.card = QFrame()
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet(self.current_stylesheet)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. Cabeçalho Superior
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Configuração de Ícone Multi-Resolução para o Wayland / Hyprland / Taskbar
        assets_dir = Path(__file__).parent / "assets"
        app_icon = QIcon()
        for sz in [16, 24, 32, 48, 64, 128, 256, 512]:
            png_sz = assets_dir / f"icon_{sz}x{sz}.png"
            if png_sz.exists():
                app_icon.addFile(str(png_sz))
        if app_icon.isNull():
            fallback_png = assets_dir / "metis_app_icon.png"
            if fallback_png.exists():
                app_icon.addFile(str(fallback_png))
        self.setWindowIcon(app_icon)

        # Logotipo do Cabeçalho Superior
        header_logo_path = assets_dir / "icon_64x64.png"
        if not header_logo_path.exists():
            header_logo_path = assets_dir / "metis_app_icon.png"
        if not header_logo_path.exists():
            header_logo_path = assets_dir / "glyph_64x64.png"

        self.logo_label = QLabel()
        if header_logo_path.exists():
            pix = QPixmap(str(header_logo_path)).scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(pix)
        else:
            self.logo_label.setText("🏛️")
            self.logo_label.setStyleSheet("font-size: 22px; color: #f59e0b;")
        header_layout.addWidget(self.logo_label)

        # Título "Metis Vision"
        self.title_label = QLabel("Metis Vision")
        self.title_label.setObjectName("HeaderTitle")
        header_layout.addWidget(self.title_label)

        # Miniatura da Captura (Thumbnail Pill)
        self.thumb_label = QLabel()
        self.thumb_label.setObjectName("ThumbnailLabel")
        self.thumb_label.setFixedSize(38, 24)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setToolTip("📸 Clique para recortar uma nova área da tela")
        self.thumb_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.thumb_label.mousePressEvent = lambda e: self.trigger_action("region_capture")
        header_layout.addWidget(self.thumb_label)

        # Modo Atual Badge Pill com pontinho colorido
        self.mode_label = QLabel()
        self.mode_label.setObjectName("ModeBadge")
        self.set_mode_badge(self.capture_mode)
        header_layout.addWidget(self.mode_label)

        # Seletor Inteligente de Provedores e Modelos (Menu Hierárquico)
        self.model_btn = QPushButton()
        self.model_btn.setObjectName("ModelSelector")
        self.model_btn.setToolTip("Selecione o modelo de IA por Provedor")
        self.model_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.model_combo = self.model_btn  # Retrocompatibilidade
        self.refresh_model_menu()
        header_layout.addWidget(self.model_btn)

        header_layout.addStretch()

        # Botões Circulares: 🔄 (Novo Chat), ? (Ajuda), ⚙ (Configurações), ✕ (Fechar)
        self.reset_chat_btn = QPushButton("🔄")
        self.reset_chat_btn.setProperty("class", "CircleIconBtn")
        self.reset_chat_btn.setFixedSize(28, 28)
        self.reset_chat_btn.setToolTip("Novo Chat / Limpar Histórico")
        self.reset_chat_btn.clicked.connect(self.reset_conversation)
        self.reset_chat_btn.hide()
        header_layout.addWidget(self.reset_chat_btn)

        help_btn = QPushButton("?")
        help_btn.setProperty("class", "CircleIconBtn")
        help_btn.setFixedSize(28, 28)
        help_btn.setToolTip("Guia de recursos e atalhos")
        help_btn.clicked.connect(self.show_help)
        header_layout.addWidget(help_btn)

        settings_btn = QPushButton("⚙")
        settings_btn.setProperty("class", "CircleIconBtn")
        settings_btn.setFixedSize(28, 28)
        settings_btn.setToolTip("Configurações: Gerenciar modelos por categoria")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)

        close_btn = QPushButton("✕")
        close_btn.setProperty("class", "CircleIconBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        card_layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # 2. Corpo Principal: Barra Lateral Recolhível + Conteúdo à Direita
        # -------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        body_layout.setContentsMargins(0, 2, 0, 2)

        # Barra Lateral (Sidebar)
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("SidebarContainer")
        self.sidebar_frame.setFixedWidth(172)
        
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(4)

        # Topo da barra lateral com botão recolhível « / »
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(4, 0, 2, 2)
        
        self.sidebar_header_title = QLabel("MENU")
        self.sidebar_header_title.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        toggle_row.addWidget(self.sidebar_header_title)
        toggle_row.addStretch()

        self.sidebar_toggle_btn = QPushButton("«")
        self.sidebar_toggle_btn.setObjectName("SidebarToggleBtn")
        self.sidebar_toggle_btn.setFixedSize(24, 20)
        self.sidebar_toggle_btn.setToolTip("Recolher / Expandir menu lateral")
        self.sidebar_toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        toggle_row.addWidget(self.sidebar_toggle_btn)
        sidebar_layout.addLayout(toggle_row)

        # Lista de Ações da Barra Lateral
        actions_list = [
            ("Resumo", "Alt+R", "⚡", "resumo"),
            ("Explicar Erro", "Alt+E", "🦉", "explicar"),
            ("Traduzir", "Alt+T", "🏛️", "traduzir"),
            ("Extrair OCR", "Alt+O", "📜", "extrair"),
            ("Recortar Área", "Alt+C", "⛶", "region_capture"),
            ("Mais Ações", "Alt+M", "⋯", "settings"),
        ]

        for title, shortcut, icon_str, act_key in actions_list:
            item_widget = self.create_sidebar_item(title, shortcut, icon_str, act_key)
            sidebar_layout.addWidget(item_widget)

        sidebar_layout.addStretch()
        body_layout.addWidget(self.sidebar_frame)
        self.apply_sidebar_state()

        # Conteúdo Central / Direito com QStackedWidget (Tela Principal + Configurações Integradas)
        self.content_stack = QStackedWidget()

        # ---------------------------------------------------------
        # Página 0: Visão Principal (Preview / Chat / Entrada de Texto)
        # ---------------------------------------------------------
        self.main_view_widget = QWidget()
        content_vbox = QVBoxLayout(self.main_view_widget)
        content_vbox.setSpacing(6)
        content_vbox.setContentsMargins(0, 0, 0, 0)

        # Título da Seção (ex: 📸 CAPTURA DE TELA)
        self.section_title = QLabel("📸 CAPTURA DE TELA")
        self.section_title.setObjectName("SectionTitleLabel")
        content_vbox.addWidget(self.section_title)

        # Área Central: Preview da Imagem OU Navegador de Respostas
        self.preview_container = QFrame()
        self.preview_container.setObjectName("PreviewContainer")
        self.preview_container.setMinimumHeight(110)
        self.preview_container.setMaximumHeight(175)
        
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 12)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setStyleSheet("color: #94a3b8; font-size: 13px; background: transparent;")
        preview_layout.addWidget(self.image_preview_label)
        content_vbox.addWidget(self.preview_container, 1)

        # Área de Resposta e Chat (Markdown)
        self.response_browser = QTextBrowser()
        self.response_browser.setObjectName("ResponseBrowser")
        self.response_browser.setOpenExternalLinks(True)
        self.response_browser.setMinimumHeight(220)
        self.response_browser.hide()
        content_vbox.addWidget(self.response_browser, 1)

        # Campo de Entrada com Borda Glow e Badge ↵ Enter
        search_container = QFrame()
        search_container.setObjectName("SearchContainer")
        search_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 3, 10, 3)
        search_layout.setSpacing(8)

        sparkle_icon = QLabel("✨")
        sparkle_icon.setStyleSheet("color: #f59e0b; font-size: 15px; background: transparent;")
        search_layout.addWidget(sparkle_icon)

        self.search_input = PromptTextEdit()
        self.search_input.setPlaceholderText("Pergunte algo sobre a tela (Shift+Enter para pular linha)...")
        self.search_input.returnPressed.connect(self.on_submit_query)
        search_layout.addWidget(self.search_input)

        enter_badge = QLabel("↵ Enter")
        enter_badge.setObjectName("EnterBadge")
        enter_badge.setToolTip("Pressione Enter para enviar • Shift+Enter para pular linha")
        search_layout.addWidget(enter_badge)

        content_vbox.addWidget(search_container)
        self.content_stack.addWidget(self.main_view_widget)

        # ---------------------------------------------------------
        # Página 1: Visão de Configurações & Gerenciador de Modelos
        # ---------------------------------------------------------
        self.settings_view_widget = QWidget()
        settings_vbox = QVBoxLayout(self.settings_view_widget)
        settings_vbox.setSpacing(8)
        settings_vbox.setContentsMargins(0, 0, 0, 0)

        # Barra de Cabeçalho das Configurações
        set_header_frame = QFrame()
        set_header_frame.setObjectName("SettingsHeaderBar")
        set_header = QHBoxLayout(set_header_frame)
        set_header.setContentsMargins(8, 4, 8, 4)
        set_header.setSpacing(8)
        
        set_title_box = QVBoxLayout()
        set_title_box.setSpacing(1)
        set_title = QLabel("⚙️ MODELOS & PROVEDORES")
        set_title.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        set_sub = QLabel("Gerencie provedores e modelos de visão do Metis")
        set_sub.setStyleSheet("color: #94a3b8; font-size: 10.5px; background: transparent;")
        set_title_box.addWidget(set_title)
        set_title_box.addWidget(set_sub)
        set_header.addLayout(set_title_box)
        set_header.addStretch()

        back_btn = QPushButton("← Voltar")
        back_btn.setObjectName("SettingsBackBtn")
        back_btn.setToolTip("Voltar para a visão de tela e chat")
        back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back_btn.clicked.connect(self.close_settings)
        set_header.addWidget(back_btn)
        settings_vbox.addWidget(set_header_frame)

        # Duas Colunas: Provedores à esquerda, Modelos à direita
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(8)

        # Provedores
        p_box = QVBoxLayout()
        p_box.setSpacing(4)
        p_lbl = QLabel("⚡ PROVEDORES")
        p_lbl.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        self.settings_provider_list = QListWidget()
        self.settings_provider_list.setFixedWidth(145)
        self.settings_provider_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_provider_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_provider_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.settings_provider_list.currentRowChanged.connect(self.on_settings_category_selected)
        p_box.addWidget(p_lbl)
        p_box.addWidget(self.settings_provider_list)
        cols_layout.addLayout(p_box)

        # Modelos
        m_box = QVBoxLayout()
        m_box.setSpacing(4)
        self.settings_model_lbl = QLabel("🤖 MODELOS DISPONÍVEIS")
        self.settings_model_lbl.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        self.settings_models_list = QListWidget()
        self.settings_models_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_models_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_models_list.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.settings_models_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.settings_models_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.settings_models_list.setToolTip("Dica: Use Ctrl ou Shift para selecionar múltiplos modelos para excluir")
        self.settings_models_list.itemDoubleClicked.connect(self.edit_selected_model)
        self.settings_models_list.itemSelectionChanged.connect(self._update_delete_button_label)
        m_box.addWidget(self.settings_model_lbl)
        m_box.addWidget(self.settings_models_list)
        cols_layout.addLayout(m_box, 1)
        settings_vbox.addLayout(cols_layout, 1)

        # Botões de Ação de Modelos
        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        add_btn = QPushButton("➕ Novo")
        add_btn.setObjectName("SettingsAddBtn")
        add_btn.setToolTip("Adicionar um novo modelo ao provedor selecionado")
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.clicked.connect(self.add_model_dialog)

        edit_btn = QPushButton("✏️ Editar")
        edit_btn.setObjectName("SettingsEditBtn")
        edit_btn.setToolTip("Editar o ID do modelo selecionado")
        edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        edit_btn.clicked.connect(self.edit_selected_model)

        self.settings_rem_btn = QPushButton("🗑️ Excluir")
        self.settings_rem_btn.setObjectName("SettingsDeleteBtn")
        self.settings_rem_btn.setToolTip("Remover o(s) modelo(s) selecionado(s) (Ctrl/Shift+Clique para múltiplos)")
        self.settings_rem_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_rem_btn.clicked.connect(self.remove_selected_model)

        set_active_btn = QPushButton("⭐ Usar Este Modelo")
        set_active_btn.setObjectName("SettingsActiveBtn")
        set_active_btn.setToolTip("Definir o modelo selecionado como padrão ativo")
        set_active_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        set_active_btn.clicked.connect(self.set_selected_as_active)

        act_row.addWidget(add_btn)
        act_row.addWidget(edit_btn)
        act_row.addWidget(self.settings_rem_btn)
        act_row.addStretch()
        act_row.addWidget(set_active_btn)
        settings_vbox.addLayout(act_row)

        self.content_stack.addWidget(self.settings_view_widget)

        body_layout.addWidget(self.content_stack, 1)
        card_layout.addLayout(body_layout, 1)

        # -------------------------------------------------------------
        # 3. Barra Inferior (Status + Botões de Ação)
        # -------------------------------------------------------------
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(4, 2, 4, 2)

        status_left = QHBoxLayout()
        status_left.setSpacing(6)
        
        spk_label = QLabel("✨")
        spk_label.setStyleSheet("color: #f59e0b; font-size: 12px; background: transparent;")
        
        self.status_label = QLabel("Pronto para ajudar")
        self.status_label.setObjectName("FooterStatus")

        self.dot_label = QLabel("●")
        self.dot_label.setStyleSheet("color: #10b981; font-size: 9px; background: transparent;")

        status_left.addWidget(spk_label)
        status_left.addWidget(self.status_label)
        status_left.addWidget(self.dot_label)
        self.footer_layout.addLayout(status_left)

        self.footer_layout.addStretch()

        self.copy_cmd_btn = QPushButton("▶ Copiar Comandos")
        self.copy_cmd_btn.setObjectName("CmdBtn")
        self.copy_cmd_btn.clicked.connect(self.copy_commands_only)
        self.copy_cmd_btn.hide()
        self.footer_layout.addWidget(self.copy_cmd_btn)

        self.copy_btn = QPushButton("📋 Copiar Tudo")
        self.copy_btn.setObjectName("SecondaryBtn")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.hide()
        self.footer_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton("💾 Salvar")
        self.save_btn.setObjectName("SecondaryBtn")
        self.save_btn.setToolTip("Salvar resposta em um arquivo no disco")
        self.save_btn.clicked.connect(self.save_to_file_dialog)
        self.save_btn.hide()
        self.footer_layout.addWidget(self.save_btn)

        card_layout.addLayout(self.footer_layout)

        main_layout.addWidget(self.card)
        self.center_on_screen()
        QTimer.singleShot(60, self.center_on_screen)

    def create_sidebar_item(self, title: str, shortcut: str, icon_str: str, act_key: str) -> QFrame:
        """Cria um botão de ação com ícone e título espaçoso sem cortes."""
        item = QFrame()
        item.setProperty("class", "SidebarItem")
        item.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        item.setFixedHeight(38)
        item.setToolTip(f"{title} ({shortcut})")

        layout = QHBoxLayout(item)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(6)

        icon_lbl = QLabel(icon_str)
        icon_lbl.setObjectName("SidebarIcon")
        icon_lbl.setFixedWidth(20)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("SidebarLabel")
        layout.addWidget(title_lbl)
        layout.addStretch()

        item.mousePressEvent = lambda e: self.trigger_action(act_key)

        # Guarda referências para alternar visibilidade ao recolher/expandir
        self.sidebar_items_widgets.append((item, icon_lbl, title_lbl, act_key))
        return item

    def highlight_sidebar_item(self, index: int):
        """Destaca visualmente o item da barra lateral selecionado pelas setas do teclado."""
        self.selected_sidebar_idx = index
        for i, (item, icon_lbl, title_lbl, act_key) in enumerate(self.sidebar_items_widgets):
            is_sel = (i == index)
            item.setProperty("selected", "true" if is_sel else "false")
            item.style().unpolish(item)
            item.style().polish(item)
            item.update()
        
        if 0 <= index < len(self.sidebar_items_widgets):
            title = self.sidebar_items_widgets[index][2].text()
            self.status_label.setText(f"▶ {title}  •  Pressione Enter para executar")

    def clear_sidebar_highlight(self):
        """Remove o destaque de seleção da barra lateral."""
        if self.selected_sidebar_idx == -1:
            return
        self.selected_sidebar_idx = -1
        for item, _, _, _ in self.sidebar_items_widgets:
            item.setProperty("selected", "false")
            item.style().unpolish(item)
            item.style().polish(item)
            item.update()
        self.status_label.setText("Pronto para ajudar")

    def navigate_sidebar(self, direction: int):
        """Navega pelos itens do menu com as setas para Cima (-1) ou para Baixo (+1)."""
        if not self.sidebar_items_widgets:
            return
        count = len(self.sidebar_items_widgets)
        if self.selected_sidebar_idx == -1:
            new_idx = 0 if direction > 0 else count - 1
        else:
            new_idx = (self.selected_sidebar_idx + direction) % count
        self.highlight_sidebar_item(new_idx)

    def execute_selected_sidebar_action(self) -> bool:
        """Executa a ação do menu atualmente selecionada via teclado."""
        if 0 <= self.selected_sidebar_idx < len(self.sidebar_items_widgets):
            _, _, _, act_key = self.sidebar_items_widgets[self.selected_sidebar_idx]
            self.clear_sidebar_highlight()
            self.trigger_action(act_key)
            return True
        return False

    def set_mode_badge(self, mode: str, label_text: Optional[str] = None):
        """Atualiza a pílula de modo com bolinha colorida indicadora de atividade."""
        mode_colors = {
            "active_window": "#4ade80",  # Verde Terminal / Ativo
            "region": "#38bdf8",         # Azul Celeste / Recorte
            "fullscreen": "#fbbf24",     # Ouro / Âmbar / Tela Cheia
            "file": "#a78bfa",           # Roxo / Arquivo
            "folder": "#f472b6",         # Rosa / Pasta
        }
        
        mode_key = mode.lower()
        color = mode_colors.get(mode_key, "#4ade80")
        
        display = label_text if label_text is not None else mode
        self.mode_label.setText(f'<span style="color: {color}; font-size: 13px; font-weight: bold;">●</span> {display}')

    def apply_sidebar_state(self):
        """Aplica visualmente o estado recolhido/expandido da barra lateral."""
        if self.is_sidebar_collapsed:
            self.sidebar_frame.setFixedWidth(46)
            self.sidebar_toggle_btn.setText("»")
            self.sidebar_header_title.hide()
            for item, icon_lbl, title_lbl, _ in self.sidebar_items_widgets:
                title_lbl.hide()
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                item.layout().setContentsMargins(4, 2, 4, 2)
        else:
            self.sidebar_frame.setFixedWidth(172)
            self.sidebar_toggle_btn.setText("«")
            self.sidebar_header_title.show()
            for item, icon_lbl, title_lbl, _ in self.sidebar_items_widgets:
                title_lbl.show()
                item.layout().setContentsMargins(6, 2, 4, 2)

    def toggle_sidebar(self):
        """Alterna e persiste o estado da barra lateral entre expandida e recolhida."""
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        self.apply_sidebar_state()
        model_manager.set_user_setting("is_sidebar_collapsed", self.is_sidebar_collapsed)
        QTimer.singleShot(20, self.update_preview_image)

    def update_preview_image(self):
        """Atualiza a imagem na área central com escala suave proporcional e centralizada."""
        if self.captured_image:
            img = QImage.fromData(self.captured_image)
            if not img.isNull():
                target_size = self.preview_container.size()
                w = max(50, target_size.width() - 4)
                h = max(50, target_size.height() - 14)
                pix = QPixmap.fromImage(img).scaled(
                    w, h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview_label.setPixmap(pix)
                self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.image_preview_label.show()
                return

        if self.target_path:
            p = Path(self.target_path)
            if p.is_dir():
                self.image_preview_label.setText(f"📁 Pasta do Projeto: {p.name}\n\n{p}")
            else:
                self.image_preview_label.setText(f"📄 Arquivo: {p.name}\n\n{p}")
        else:
            self.image_preview_label.setText("📸 Captura de Tela Ativa")
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(15, self.update_preview_image)

    def get_hyprland_address(self) -> Optional[str]:
        """Obtém o endereço da janela atual no Hyprland."""
        if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            return None
        if getattr(self, "_cached_hypr_addr", None):
            return self._cached_hypr_addr
        try:
            my_pid = os.getpid()
            r = subprocess.run(["hyprctl", "clients", "-j"], stdout=subprocess.PIPE, text=True, timeout=0.6)
            if r.returncode == 0 and r.stdout.strip():
                clients = json.loads(r.stdout)
                for c in clients:
                    if c.get("pid") == my_pid:
                        self._cached_hypr_addr = c.get("address")
                        return self._cached_hypr_addr
                for c in clients:
                    title = (c.get("title") or "").lower()
                    initial_title = (c.get("initialTitle") or "").lower()
                    cls = (c.get("class") or "").lower()
                    initial_cls = (c.get("initialClass") or "").lower()
                    if any(x in title or x in initial_title or x in cls or x in initial_cls for x in ["metis", "screenai"]):
                        self._cached_hypr_addr = c.get("address")
                        return self._cached_hypr_addr
        except Exception:
            pass
        return None

    def get_active_monitor_workarea(self) -> tuple[int, int, int, int]:
        """Calcula com precisão a área útil do monitor ativo no Hyprland."""
        if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            return (0, 0, 1920, 1080)
        try:
            r = subprocess.run(["hyprctl", "monitors", "-j"], stdout=subprocess.PIPE, text=True, timeout=0.5)
            if r.returncode == 0 and r.stdout.strip():
                monitors = json.loads(r.stdout)
                focused_mon = next((m for m in monitors if m.get("focused")), monitors[0])
                mx = int(focused_mon.get("x", 0))
                my = int(focused_mon.get("y", 0))
                mw = int(focused_mon.get("width", 1920))
                mh = int(focused_mon.get("height", 1080))
                scale = float(focused_mon.get("scale", 1.0))
                
                if scale > 0 and scale != 1.0:
                    mw = int(mw / scale)
                    mh = int(mh / scale)

                reserved = focused_mon.get("reserved", [0, 0, 0, 0])
                r_left = int(reserved[0] / scale if scale > 0 else reserved[0])
                r_top = int(reserved[1] / scale if scale > 0 else reserved[1])
                r_right = int(reserved[2] / scale if scale > 0 else reserved[2])
                r_bottom = int(reserved[3] / scale if scale > 0 else reserved[3])

                work_x = mx + r_left
                work_y = my + r_top
                work_w = mw - r_left - r_right
                work_h = mh - r_top - r_bottom
                return work_x, work_y, work_w, work_h
        except Exception:
            pass

        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            return geo.x(), geo.y(), geo.width(), geo.height()
        return 0, 0, 1920, 1080

    def showEvent(self, event):
        super().showEvent(event)
        if not self.chat_history:
            QTimer.singleShot(40, self.center_on_screen)

    def center_on_screen(self):
        work_x, work_y, work_w, work_h = self.get_active_monitor_workarea()
        w = min(640, work_w - 48)
        h = min(400, work_h - 48)
        self.setFixedSize(w, h)

        actual_w = max(w, self.frameGeometry().width(), self.width())
        actual_h = max(h, self.frameGeometry().height(), self.height())
        x = work_x + (work_w - actual_w) // 2
        y = work_y + max((work_h - actual_h) // 3, 20)
        self.setGeometry(x, y, actual_w, actual_h)

        addr = self.get_hyprland_address()
        if addr:
            batch = f"dispatch moveoutofgroup address:{addr} ; dispatch setfloating address:{addr} ; dispatch resizewindowpixel exact {actual_w} {actual_h},address:{addr} ; dispatch movewindowpixel exact {x} {y},address:{addr}"
            subprocess.run(["hyprctl", "--batch", batch], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def animate_to_bottom_right(self):
        """Desloca e expande a janela suavemente para o canto inferior direito sem cortar bordas."""
        work_x, work_y, work_w, work_h = self.get_active_monitor_workarea()
        margin_x = 24
        margin_y = 24

        target_w = min(780, work_w - (margin_x * 2))
        target_h = min(540, work_h - (margin_y * 2))

        self.setFixedSize(target_w, target_h)

        # Garante que o cálculo use exatamente a largura e altura reais no compositor
        actual_w = max(target_w, self.frameGeometry().width(), self.width())
        actual_h = max(target_h, self.frameGeometry().height(), self.height())

        target_x = max(work_x + margin_x, work_x + work_w - actual_w - margin_x)
        target_y = max(work_y + margin_y, work_y + work_h - actual_h - margin_y)

        self.setGeometry(target_x, target_y, actual_w, actual_h)

        addr = self.get_hyprland_address()
        if addr:
            batch = f"dispatch moveoutofgroup address:{addr} ; dispatch setfloating address:{addr} ; dispatch resizewindowpixel exact {actual_w} {actual_h},address:{addr} ; dispatch movewindowpixel exact {target_x} {target_y},address:{addr}"
            subprocess.run(["hyprctl", "--batch", batch], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(240)
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(QRect(target_x, target_y, actual_w, actual_h))
            self.anim.start()

    def animate_to_center(self):
        """Retorna suavemente para a posição compacta central."""
        self.center_on_screen()

    def update_thumbnail(self):
        """Atualiza a miniatura visual no canto superior da janela."""
        if self.captured_image:
            img = QImage.fromData(self.captured_image)
            if not img.isNull():
                pix = QPixmap.fromImage(img).scaled(
                    38, 24,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumb_label.setPixmap(pix)
                self.thumb_label.show()
                return
        self.thumb_label.setText("📁")

    def load_target_path(self, path_str: str):
        """Carrega e analisa arquivo ou pasta solta na janela."""
        p = Path(path_str).resolve()
        if not p.exists():
            self.status_label.setText(f"⚠️ Caminho não encontrado: {path_str}")
            return

        self.chat_history.clear()
        self.rendered_markdown_history = ""
        self.response_browser.clear()
        self.response_browser.hide()
        self.preview_container.show()
        self.reset_chat_btn.hide()
        self.copy_btn.hide()
        self.copy_cmd_btn.hide()

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".svg", ".ico"}

        if p.is_dir():
            self.target_path = str(p)
            self.captured_image = None
            try:
                self.text_context = format_folder_context(p)
                self.set_mode_badge("folder", f"📁 {p.name}")
                self.section_title.setText(f"📁 PASTA DO PROJETO: {p.name.upper()}")
                self.thumb_label.setText("📁")
                self.status_label.setText(f"📁 Pasta '{p.name}' carregada! Pressione Enter para resumir.")
                self.search_input.setPlaceholderText(f"💬 Pergunte algo sobre {p.name}...")
                self.search_input.setFocus()
            except Exception as e:
                self.status_label.setText(f"⚠️ Erro ao ler pasta: {str(e)}")
        elif p.suffix.lower() in image_extensions:
            try:
                self.captured_image = p.read_bytes()
                self.text_context = None
                self.target_path = str(p)
                self.set_mode_badge("active_window", f"🖼️ {p.name}")
                self.section_title.setText(f"🖼️ IMAGEM: {p.name.upper()}")
                self.update_thumbnail()
                self.update_preview_image()
                self.status_label.setText(f"🖼️ Imagem '{p.name}' carregada! O que deseja analisar?")
                self.search_input.setPlaceholderText(f"💬 Pergunte algo sobre {p.name}...")
                self.search_input.setFocus()
            except Exception as e:
                self.status_label.setText(f"⚠️ Erro ao ler imagem: {str(e)}")
        else:
            try:
                self.target_path = str(p)
                self.captured_image = None
                self.text_context = format_file_context(p)
                self.set_mode_badge("file", f"📄 {p.name}")
                self.section_title.setText(f"📄 ARQUIVO: {p.name.upper()}")
                self.thumb_label.setText("📄")
                self.status_label.setText(f"📄 Arquivo '{p.name}' carregado! O que deseja saber?")
                self.search_input.setPlaceholderText(f"💬 Pergunte algo sobre {p.name}...")
                self.search_input.setFocus()
            except Exception as e:
                self.status_label.setText(f"⚠️ Erro ao ler arquivo: {str(e)}")
        
        self.update_preview_image()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.card.setStyleSheet(self.current_stylesheet + f"""
            QWidget#MainCard {{
                border: 2px dashed #fbbf24;
                background-color: rgba(245, 158, 11, 0.12);
            }}
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.card.setStyleSheet(self.current_stylesheet)

    def dropEvent(self, event: QDropEvent):
        self.card.setStyleSheet(self.current_stylesheet)
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.load_target_path(local_path)
                event.acceptProposedAction()

    def setup_initial_context(self):
        """Carrega pasta, arquivo ou tira print da tela."""
        if self.target_path:
            self.load_target_path(self.target_path)
            self.search_input.setText(config.QUICK_ACTIONS["resumo"])
            self.execute_analysis(config.QUICK_ACTIONS["resumo"])
        else:
            self.take_initial_screenshot()

    def take_initial_screenshot(self):
        try:
            self.status_label.setText("📸 Capturando tela...")
            self.captured_image = capture_screen(self.capture_mode)
            self.update_thumbnail()
            self.update_preview_image()
            self.status_label.setText("Tela capturada. Digite sua pergunta ou pressione Enter.")
            self.search_input.setFocus()
        except Exception as e:
            self.status_label.setText(f"⚠️ Erro na captura: {str(e)}")

    def reset_conversation(self):
        """Reinicia o histórico da conversa para começar um novo chat."""
        self.content_stack.setCurrentIndex(0)
        self.chat_history.clear()
        self.rendered_markdown_history = ""
        self.response_browser.clear()
        self.response_browser.hide()
        self.preview_container.show()
        self.copy_btn.hide()
        self.copy_cmd_btn.hide()
        self.save_btn.hide()
        self.reset_chat_btn.hide()
        self.pending_save_path = None
        self.search_input.clear()
        self.search_input.setPlaceholderText("Pergunte algo sobre a tela ou pressione Enter para Resumo...")
        self.set_mode_badge(self.capture_mode)
        self.animate_to_center()
        self.status_label.setText("Pronto para ajudar")
        self.search_input.setEnabled(True)
        self.search_input.setFocus()
        self.update_preview_image()

    def trigger_action(self, action_key: str):
        if action_key == "settings":
            if self.content_stack.currentIndex() == 1:
                self.close_settings()
            else:
                self.open_settings()
            return

        self.content_stack.setCurrentIndex(0)
        if action_key == "region_capture":
            self.hide()
            try:
                self.captured_image = capture_screen("region")
                self.text_context = None
                self.set_mode_badge("region", "region")
                self.update_thumbnail()
                self.update_preview_image()
                self.preview_container.show()
                self.response_browser.hide()
                self.show()
                self.center_on_screen()
                self.search_input.setEnabled(True)
                self.search_input.clear()
                self.search_input.setFocus()
                self.status_label.setText("✓ Área selecionada. Escolha uma ação ou digite sua pergunta.")
            except Exception as e:
                self.show()
                self.status_label.setText(f"Seleção cancelada: {str(e)}")
            return

        prompt = config.QUICK_ACTIONS.get(action_key, config.QUICK_ACTIONS["resumo"])
        
        # Evita cliques duplos rápidos acidentais na mesma ação se já estiver em processamento
        if self.worker and self.worker.isRunning() and self.chat_history and self.chat_history[-1].get("content") == prompt:
            return

        self.search_input.setText(prompt)
        self.execute_analysis(prompt)

    def open_settings(self):
        """Alterna para a página de configurações e gerenciamento de modelos na mesma janela."""
        self.content_stack.setCurrentIndex(1)
        self.load_settings_categories()
        self.status_label.setText("⚙️ Gerenciador de Modelos • Escolha o provedor e modelo")

    def close_settings(self):
        """Retorna para a visão principal de captura e chat."""
        self.content_stack.setCurrentIndex(0)
        self.search_input.setFocus()
        if not getattr(self, 'last_failed_prompt', None):
            self.status_label.setText("✓ Pronto para análise.")

    def load_settings_categories(self):
        self.settings_provider_list.clear()
        providers = model_manager.get_providers()
        active_prov, _ = model_manager.get_active_model()

        active_row = 0
        for i, prov in enumerate(providers):
            display_name = PROVIDER_ICONS.get(prov.lower(), f"⚡ {prov.upper()}")
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, prov)
            self.settings_provider_list.addItem(item)
            if prov.lower() == active_prov.lower():
                active_row = i

        if providers:
            self.settings_provider_list.setCurrentRow(active_row)

    def on_settings_category_selected(self, row: int):
        if row < 0:
            return
        item = self.settings_provider_list.item(row)
        provider = item.data(Qt.ItemDataRole.UserRole) or item.text()
        display_name = PROVIDER_ICONS.get(provider.lower(), provider.upper())
        self.settings_model_lbl.setText(f"Modelos de {display_name}")
        self.load_settings_models_for_category(provider)

    def load_settings_models_for_category(self, provider: str):
        self.settings_models_list.clear()
        models = model_manager.get_models_for_provider(provider)
        active_prov, active_mod = model_manager.get_active_model()

        target_row = 0
        for i, m in enumerate(models):
            is_active = (provider.lower() == active_prov.lower() and m == active_mod)
            display_text = f"⭐  {m}   (Ativo)" if is_active else f"🤖  {m}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, m)
            item.setToolTip(f"ID completo: {m}")
            self.settings_models_list.addItem(item)
            if is_active:
                target_row = i

        if models:
            self.settings_models_list.setCurrentRow(target_row)
        self._update_delete_button_label()

    def _update_delete_button_label(self):
        if not hasattr(self, 'settings_rem_btn'):
            return
        count = len(self.settings_models_list.selectedItems())
        if count > 1:
            self.settings_rem_btn.setText(f"🗑️ Excluir ({count})")
            self.settings_rem_btn.setToolTip(f"Remover os {count} modelos selecionados")
        else:
            self.settings_rem_btn.setText("🗑️ Excluir")
            self.settings_rem_btn.setToolTip("Remover o modelo selecionado (Ctrl/Shift+Clique para múltiplos)")

    def add_model_dialog(self):
        curr_row = self.settings_provider_list.currentRow()
        if curr_row < 0:
            self.status_label.setText("⚠️ Selecione um provedor primeiro.")
            return
        item = self.settings_provider_list.item(curr_row)
        provider = item.data(Qt.ItemDataRole.UserRole) or item.text()

        dlg = ModernInputDialog(
            parent=self,
            title="➕ Adicionar Modelo",
            label=f"Digite o nome ou ID do modelo para {provider}:",
            placeholder="ex: meta/llama-3.2-11b-vision-instruct"
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            model_id = dlg.get_text().strip()
            if model_id:
                if model_manager.add_model_to_provider(provider, model_id):
                    self.load_settings_models_for_category(provider)
                    self.refresh_model_combo()
                    self.status_label.setText(f"✓ Modelo '{model_id}' adicionado a {provider}!")
                else:
                    self.status_label.setText(f"⚠️ O modelo já existe na categoria {provider}.")

    def edit_selected_model(self):
        curr_cat_row = self.settings_provider_list.currentRow()
        if curr_cat_row < 0:
            self.status_label.setText("⚠️ Selecione um provedor primeiro.")
            return

        selected_items = self.settings_models_list.selectedItems()
        if len(selected_items) > 1:
            self.status_label.setText("ℹ️ Selecione apenas 1 modelo para editar.")
            return

        curr_model_row = self.settings_models_list.currentRow()
        if curr_model_row < 0:
            if self.settings_models_list.count() > 0:
                self.settings_models_list.setCurrentRow(0)
                curr_model_row = 0
            else:
                self.status_label.setText("⚠️ Nenhum modelo disponível para editar neste provedor.")
                return

        cat_item = self.settings_provider_list.item(curr_cat_row)
        provider = cat_item.data(Qt.ItemDataRole.UserRole) or cat_item.text()
        old_model = self.settings_models_list.item(curr_model_row).data(Qt.ItemDataRole.UserRole)

        dlg = ModernInputDialog(
            parent=self,
            title="✏️ Editar Modelo",
            label=f"Editar ID do modelo em {provider}:",
            default_text=old_model
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_model = dlg.get_text().strip()
            if new_model and new_model != old_model:
                if model_manager.edit_model_in_provider(provider, old_model, new_model):
                    self.load_settings_models_for_category(provider)
                    self.refresh_model_combo()
                    self.status_label.setText(f"✓ Modelo atualizado para '{new_model}'!")
                else:
                    self.status_label.setText(f"⚠️ Erro ao atualizar o modelo '{old_model}'.")

    def remove_selected_model(self):
        curr_cat_row = self.settings_provider_list.currentRow()
        if curr_cat_row < 0:
            self.status_label.setText("⚠️ Selecione um provedor primeiro.")
            return

        selected_items = self.settings_models_list.selectedItems()
        if not selected_items:
            curr_model_row = self.settings_models_list.currentRow()
            if curr_model_row >= 0:
                item = self.settings_models_list.item(curr_model_row)
                if item:
                    selected_items = [item]

        if not selected_items:
            self.status_label.setText("⚠️ Selecione um ou mais modelos para remover.")
            return

        cat_item = self.settings_provider_list.item(curr_cat_row)
        provider = cat_item.data(Qt.ItemDataRole.UserRole) or cat_item.text()
        model_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items if item.data(Qt.ItemDataRole.UserRole)]
        if not model_ids:
            return

        if len(model_ids) == 1:
            m_id = model_ids[0]
            title = "🗑️ Remover Modelo"
            msg = f"Tem certeza que deseja remover o modelo:\n\n'{m_id}'\n\nda categoria {provider}?"
            danger_text = "Excluir"
        else:
            title = f"🗑️ Remover {len(model_ids)} Modelos"
            preview_items = [f"• {mid}" for mid in model_ids[:5]]
            preview = "\n".join(preview_items)
            if len(model_ids) > 5:
                preview += f"\n... e mais {len(model_ids) - 5} modelo(s)"
            msg = f"Tem certeza que deseja remover os {len(model_ids)} modelos selecionados da categoria {provider}?\n\n{preview}"
            danger_text = f"Excluir ({len(model_ids)})"

        dlg = ModernConfirmDialog(
            parent=self,
            title=title,
            message=msg,
            danger_text=danger_text,
            cancel_text="Cancelar"
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            success_count = 0
            for m_id in model_ids:
                if model_manager.remove_model_from_provider(provider, m_id):
                    success_count += 1

            self.load_settings_models_for_category(provider)
            self.refresh_model_combo()
            self._update_delete_button_label()

            if success_count == 1:
                self.status_label.setText(f"✓ Modelo '{model_ids[0]}' removido.")
            else:
                self.status_label.setText(f"✓ {success_count} modelos removidos da categoria {provider}.")

    def set_selected_as_active(self):
        curr_cat_row = self.settings_provider_list.currentRow()
        if curr_cat_row < 0:
            self.status_label.setText("⚠️ Selecione um provedor primeiro.")
            return

        current_item = self.settings_models_list.currentItem()
        if not current_item and self.settings_models_list.selectedItems():
            current_item = self.settings_models_list.selectedItems()[0]

        if not current_item:
            if self.settings_models_list.count() > 0:
                self.settings_models_list.setCurrentRow(0)
                current_item = self.settings_models_list.item(0)
            else:
                self.status_label.setText("⚠️ Nenhum modelo selecionado.")
                return

        cat_item = self.settings_provider_list.item(curr_cat_row)
        provider = cat_item.data(Qt.ItemDataRole.UserRole) or cat_item.text()
        model_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not model_id:
            return

        model_manager.set_active_model(provider, model_id)
        self.load_settings_models_for_category(provider)
        self.refresh_model_combo()

        # Retorna imediatamente para a tela de chat/captura onde o usuário estava
        self.close_settings()

        short_mod = model_id.split('/')[-1]
        if getattr(self, 'last_failed_prompt', None):
            self.search_input.setText(self.last_failed_prompt)
            self.search_input.selectAll()
            self.status_label.setText(f"⭐ Ativo: {short_mod} • Pressione Enter para reenviar ao novo modelo")
        else:
            self.status_label.setText(f"⭐ Modelo ativo: {provider.upper()} • {short_mod}")

    def reload_theme(self):
        """Sincroniza o tema do Metis ativo e reaplica os estilos no HUD."""
        self.theme = theme_manager.get_theme_palette()
        self.current_stylesheet = theme_manager.generate_main_stylesheet(self.theme)
        self.card.setStyleSheet(self.current_stylesheet)
        return self.theme

    def refresh_model_menu(self):
        """Recarrega o seletor inteligente de modelos agrupados por provedor em cascata e sincroniza cores com o Metis."""
        # 1. Sincroniza dinamicamente o tema ativo do Metis
        theme = self.reload_theme()
        menu_stylesheet = theme_manager.generate_menu_stylesheet(theme)

        active_prov, active_mod = model_manager.get_active_model()
        self.current_provider = active_prov
        self.current_model = active_mod

        # Determina ícone e rótulo para o botão Pill
        short_mod = active_mod.split('/')[-1] if active_mod else "Nenhum"
        prov_icon = model_manager.get_provider_icon(active_prov)
        self.model_btn.setText(f"{prov_icon} {active_prov.upper()} • {short_mod}  ▾")
        self.model_btn.setToolTip(
            f"Provedor ativo: {active_prov.upper()}\n"
            f"Modelo ativo: {active_mod}\n\n"
            f"Clique para abrir o menu inteligente organizado por provedor"
        )

        # Constrói o menu suspenso hierárquico com as cores do tema
        menu = self.model_btn.menu()
        if not menu:
            menu = QMenu(self)
            menu.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            menu.aboutToShow.connect(self.refresh_model_menu)
            self.model_btn.setMenu(menu)

        menu.blockSignals(True)
        menu.clear()
        menu.setStyleSheet(menu_stylesheet)

        grouped = model_manager.get_grouped_model_list()
        for group in grouped:
            p_name = group["provider"]
            p_key = group["key"]
            p_icon = group["icon"]
            models = group["models"]

            is_active_prov = (p_key.lower() == active_prov.lower())
            count_str = f"({len(models)})"
            
            # Título do submenu do provedor
            if is_active_prov:
                sub_title = f"{p_icon}  {p_name}  {count_str}  ●"
            else:
                sub_title = f"{p_icon}  {p_name}  {count_str}"

            sub_menu = menu.addMenu(sub_title)
            sub_menu.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            sub_menu.setStyleSheet(menu_stylesheet)

            if not models:
                empty_act = sub_menu.addAction("(Nenhum modelo cadastrado)")
                empty_act.setEnabled(False)
            else:
                for m in models:
                    is_active_mod = (is_active_prov and m == active_mod)
                    
                    if is_active_mod:
                        item_text = f"✓  {m}  (Ativo)"
                    else:
                        item_text = f"    {m}"

                    action = sub_menu.addAction(item_text)
                    action.setToolTip(f"Provedor: {p_name}\nID do modelo: {m}")
                    action.triggered.connect(
                        lambda checked, pk=p_key, mid=m: self.on_model_selected(pk, mid)
                    )

        menu.addSeparator()
        settings_act = menu.addAction("⚙️  Gerenciar Modelos e Provedores...")
        settings_act.triggered.connect(self.open_settings)
        menu.blockSignals(False)

    def refresh_model_combo(self):
        """Alias para manter total retrocompatibilidade com chamadas existentes."""
        self.refresh_model_menu()

    def on_model_selected(self, provider_key: str, model_id: str):
        """Manipula a seleção de um modelo a partir de qualquer submenu de provedor."""
        self.current_provider = provider_key
        self.current_model = model_id
        model_manager.set_active_model(provider_key, model_id)
        
        # Atualiza o botão e os checkmarks do menu
        self.refresh_model_menu()
        
        short_mod = model_id.split('/')[-1]
        prov_name = provider_key.upper()
        
        # Se havia um prompt com erro/timeout pendente, restaura no input
        if getattr(self, 'last_failed_prompt', None):
            self.search_input.setText(self.last_failed_prompt)
            self.search_input.selectAll()
            self.status_label.setText(f"⭐ Ativo: {prov_name} • {short_mod} • Pressione Enter para reenviar ao novo modelo")
        else:
            self.status_label.setText(f"✓ Modelo ativo: {prov_name} • {short_mod}")

    def on_model_changed(self, index: int = 0):
        """Método de retrocompatibilidade."""
        pass

    def on_submit_query(self):
        query = self.search_input.text().strip()
        if not query:
            query = config.QUICK_ACTIONS["resumo"]
        self.execute_analysis(query)

    def execute_analysis(self, prompt: str):
        detected_context, detected_paths = detect_and_attach_local_files(prompt, extra_cwd=self.active_window_cwd)
        if detected_context:
            self.text_context = detected_context
            
            if detected_paths:
                detected_path = detected_paths[0]
                self.target_path = str(detected_path)
                if detected_path.is_file():
                    self.set_mode_badge("file", f"📄 {detected_path.name}")
                    self.section_title.setText(f"📄 ARQUIVO: {detected_path.name.upper()}")
                    self.thumb_label.setText("📄")
                else:
                    self.set_mode_badge("folder", f"📁 {detected_path.name}")
                    self.section_title.setText(f"📁 PASTA: {detected_path.name.upper()}")
                    self.thumb_label.setText("📁")

        if not self.captured_image and not self.text_context:
            self.take_initial_screenshot()
            if not self.captured_image and not self.text_context:
                return

        # Para worker anterior com segurança se estiver rodando
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(300)

        self.pending_save_path = detect_save_target_path(prompt, extra_cwd=self.active_window_cwd)
        self.chat_history.append({"role": "user", "content": prompt})

        if len(self.chat_history) > 1:
            self.rendered_markdown_history += f"\n\n---\n\n### 🧑 **Você:**\n{prompt}\n\n### 🤖 **Metis:**\n"
        else:
            self.rendered_markdown_history = f"### 🤖 **Metis:**\n"

        self.current_stream_chunk = ""
        self.preview_container.hide()
        self.response_browser.show()
        self.response_browser.setMarkdown(self.rendered_markdown_history + "*⏳ Consultando o modelo de IA e processando...*")
        self.copy_btn.hide()
        self.copy_cmd_btn.hide()
        self.save_btn.hide()
        self.reset_chat_btn.show()

        self.animate_to_bottom_right()

        self.status_label.setText("🧠 Pensando... (Ctrl+C para parar)")
        self.search_input.setEnabled(False)

        self.worker = ChatWorker(
            messages=self.chat_history,
            image_bytes=self.captured_image,
            text_context=self.text_context,
            provider=self.current_provider,
            model=self.current_model
        )
        self.worker.chunk_received.connect(self.on_chunk_received)
        self.worker.finished_stream.connect(self.on_analysis_finished)
        self.worker.error_occurred.connect(self.on_analysis_error)
        self.worker.start()

    def on_chunk_received(self, chunk: str):
        self.current_stream_chunk += chunk
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _flush_markdown_render(self):
        """Renderiza o Markdown acumulado com posicionamento suave do cursor."""
        content = self.rendered_markdown_history + (self.current_stream_chunk if self.current_stream_chunk else "*⏳ Gerando resposta...*")
        self.response_browser.setMarkdown(content)
        cursor = self.response_browser.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.response_browser.setTextCursor(cursor)

    def on_analysis_finished(self, final_text: str):
        if self._render_timer.isActive():
            self._render_timer.stop()
        self.current_stream_chunk = ""
        self.last_failed_prompt = None
        self.chat_history.append({"role": "assistant", "content": final_text})
        self.rendered_markdown_history += final_text
        self._flush_markdown_render()

        model_display = self.current_model.split('/')[-1] if self.current_model else self.current_provider.upper()
        self.status_label.setText(f"✓ Concluído via {self.current_provider.upper()} ({model_display})")
        self.search_input.setEnabled(True)
        self.search_input.clear()
        self.search_input.setPlaceholderText("💬 Pergunte algo a mais sobre esta tela (ou Enter para enviar)...")
        self.search_input.setFocus()
        
        self.copy_btn.show()
        self.save_btn.show()

        if self.pending_save_path:
            try:
                self.pending_save_path.parent.mkdir(parents=True, exist_ok=True)
                self.pending_save_path.write_text(final_text, encoding="utf-8")
                self.status_label.setText(f"💾 Salvo em: {self.pending_save_path.name}")
            except Exception as e:
                self.status_label.setText(f"⚠️ Erro ao salvar: {str(e)}")

        commands = self.extract_commands_from_text(final_text)
        if commands:
            self.copy_cmd_btn.setText(f"▶ Copiar {len(commands)} Comando(s)" if len(commands) > 1 else "▶ Copiar Comando")
            self.copy_cmd_btn.show()
        else:
            self.copy_cmd_btn.hide()

    def on_analysis_error(self, error_msg: str):
        if self._render_timer.isActive():
            self._render_timer.stop()
        self.current_stream_chunk = ""

        # Recupera e remove a pergunta com falha do histórico para manter a integridade dos turnos
        if self.chat_history and self.chat_history[-1].get("role") == "user":
            self.last_failed_prompt = self.chat_history.pop()["content"]

        self.status_label.setText("⚠️ Falha/Timeout. Escolha outro modelo em 'Mais Ações' (Alt+M).")
        self.response_browser.append(f"\n\n> ⚠️ **Falha/Timeout:** {error_msg}\n\n*Dica: Clique em **⋯ Mais Ações** para alternar de modelo e tentar novamente.*")
        self.search_input.setEnabled(True)
        if getattr(self, 'last_failed_prompt', None):
            self.search_input.setText(self.last_failed_prompt)
            self.search_input.selectAll()
        self.search_input.setFocus()

    def extract_commands_from_text(self, text: str) -> List[str]:
        code_blocks = re.findall(r'```(?:bash|sh|shell|zsh)?\s*\n(.*?)\n```', text, re.DOTALL)
        commands = []
        for block in code_blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip() and not line.strip().startswith("#")]
            if lines:
                commands.extend(lines)
        return commands

    def _reset_copy_cmd_btn(self):
        self.copy_cmd_btn.setText("▶ Copiar Comandos")
        self.copy_cmd_btn.setStyleSheet("")

    def _reset_copy_btn(self):
        self.copy_btn.setText("📋 Copiar Tudo")
        self.copy_btn.setStyleSheet("")

    def _reset_save_btn(self):
        self.save_btn.setText("💾 Salvar")
        self.save_btn.setStyleSheet("")

    def copy_commands_only(self):
        latest_reply = next((m["content"] for m in reversed(self.chat_history) if m.get("role") == "assistant"), "")
        commands = self.extract_commands_from_text(latest_reply)
        if commands:
            cmd_text = "\n".join(commands)
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(cmd_text)
                self.copy_cmd_btn.setText("✓ Comandos Copiados!")
                self.copy_cmd_btn.setStyleSheet("background-color: #f59e0b; color: #0f172a; font-weight: bold;")
                self.status_label.setText("✓ Comandos copiados para a área de transferência!")
                QTimer.singleShot(1500, self._reset_copy_cmd_btn)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        latest_reply = next((m["content"] for m in reversed(self.chat_history) if m.get("role") == "assistant"), "")
        if clipboard and latest_reply:
            clipboard.setText(latest_reply)
            self.copy_btn.setText("✓ Copiado!")
            self.copy_btn.setStyleSheet("background-color: #f59e0b; color: #0f172a; font-weight: bold; border: none;")
            self.status_label.setText("✓ Resposta copiada para a área de transferência!")
            QTimer.singleShot(1500, self._reset_copy_btn)

    def save_to_file_dialog(self):
        latest_reply = next((m["content"] for m in reversed(self.chat_history) if m.get("role") == "assistant"), "")
        if not latest_reply:
            return
        base_dir = self.active_window_cwd or (Path.home() / "Downloads")
        default_name = str(base_dir / "metis_resposta.md")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Resposta do Metis", default_name, "Markdown (*.md);;Texto (*.txt);;Todos os arquivos (*)"
        )
        if file_path:
            try:
                Path(file_path).write_text(latest_reply, encoding="utf-8")
                self.save_btn.setText("✓ Salvo!")
                self.save_btn.setStyleSheet("background-color: #f59e0b; color: #0f172a; font-weight: bold;")
                self.status_label.setText(f"💾 Salvo com sucesso: {Path(file_path).name}")
                QTimer.singleShot(1500, self._reset_save_btn)
            except Exception as e:
                self.status_label.setText(f"⚠️ Erro ao salvar: {str(e)}")

    def show_help(self):
        help_markdown = """## 🏛️ Guia de Recursos do Metis Vision & HUD

### 🌟 Recursos Principais:
1. **« / » Barra Lateral Recolhível:** Clique no botão no topo da barra para recolher ou expandir. Sua preferência fica salva automaticamente!
2. **💬 Chat Contínuo & Multilinha:** Faça perguntas de acompanhamento na mesma tela. Use **`Shift + Enter`** para pular linhas.
3. **⚙️ Gerenciador de Modelos Integrado:** Clique em **`⋯ Mais Ações`** para alternar entre Provedores (*NVIDIA, Gemini, OpenRouter, Ollama, Groq*) e gerenciar modelos com um clique.
4. **▶ Copiar Comandos:** Se a IA sugerir comandos de terminal, copie-os limpos e prontos para executar.
5. **📁 Análise de Arquivos e Pastas:** Arraste pastas de projetos ou arquivos de código para a janela para análise instantânea.
6. **🟢 Indicadores de Modo:** Identifique o contexto ativo pela cor da bolinha no topo (🟢 Janela Ativa, 🔵 Recorte, 🟡 Tela Cheia, 🟣 Arquivo, 🌸 Pasta).

---

### ⌨️ Atalhos Globais no Hyprland:
* **`Super + Z`** ➔ Abrir Metis na Janela Ativa
* **`Super + Shift + Z`** ➔ Recortar Área com o Mouse
* **`Super + Ctrl + Z`** ➔ Captura de Tela Cheia

---

### 🔘 Ações Rápidas do Menu:
* **`Alt + R`** ➔ **⚡ Resumo:** Resumo visual estruturado da tela.
* **`Alt + E`** ➔ **🦉 Explicar Erro:** Diagnostica mensagens de erro e propõe correções.
* **`Alt + T`** ➔ **🏛️ Traduzir:** Traduz textos ou código da tela para o Português.
* **`Alt + O`** ➔ **📜 Extrair OCR:** Extrai texto e código da imagem com alta fidelidade.
* **`Alt + C`** ➔ **⛶ Recortar Área:** Seleciona um retângulo na tela com o mouse.
* **`Alt + M`** ➔ **⋯ Mais Ações:** Abre as configurações e gerenciador de modelos.

---

### 🕹️ Navegação pelo Teclado:
* **`↓` / `↑` (Setas)** ➔ Navega pelos botões do menu lateral com destaque visual verde.
* **`Enter`** ➔ Executa a ação do menu selecionada (ou envia sua pergunta digitada).
* **`Shift + Enter`** ➔ Pula linha no campo de perguntas.
* **`←` / `→` (Nas Configurações)** ➔ Alterna foco entre a lista de Provedores e Modelos.
* **`Ctrl + C`** ➔ Interrompe a resposta da IA em tempo real.
* **`Esc`** ➔ Fecha o Metis ou volta das configurações.
* **`🔄`** ➔ Reinicia o histórico da conversa e volta à tela inicial.
"""
        self.content_stack.setCurrentIndex(0)
        self.preview_container.hide()
        self.response_browser.clear()
        self.response_browser.setMarkdown(help_markdown)
        self.response_browser.show()
        self.reset_chat_btn.show()
        self.copy_btn.show()
        self.animate_to_bottom_right()
        self.status_label.setText("💡 Guia de ajuda exibido. Pressione 🔄 ou Esc para retornar.")

    def stop_generation(self):
        """Interrompe imediatamente a geração e pensamento da IA."""
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
            
            if self.current_stream_chunk:
                self.chat_history.append({"role": "assistant", "content": self.current_stream_chunk})
                self.rendered_markdown_history += self.current_stream_chunk
                
                commands = self.extract_commands_from_text(self.current_stream_chunk)
                if commands:
                    self.copy_cmd_btn.setText(f"▶ Copiar {len(commands)} Comando(s)" if len(commands) > 1 else "▶ Copiar Comando")
                    self.copy_cmd_btn.show()
                self.copy_btn.show()

            self.status_label.setText("⏹️ Geração interrompida (Ctrl+C).")
            self.search_input.setEnabled(True)
            self.search_input.clear()
            self.search_input.setPlaceholderText("💬 Pergunte algo a mais sobre esta tela (ou Enter para enviar)...")
            self.search_input.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # 1. Se estiver na tela de configurações / modelos (Página 1)
        if self.content_stack.currentIndex() == 1:
            if key == Qt.Key.Key_Left:
                self.settings_provider_list.setFocus()
                event.accept()
                return
            elif key == Qt.Key.Key_Right:
                self.settings_models_list.setFocus()
                event.accept()
                return
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.settings_models_list.hasFocus():
                    self.set_selected_as_active()
                    event.accept()
                    return
            elif key == Qt.Key.Key_Delete:
                self.remove_selected_model()
                event.accept()
                return
            elif key == Qt.Key.Key_F2:
                self.edit_selected_model()
                event.accept()
                return
            elif key == Qt.Key.Key_Escape:
                self.close_settings()
                event.accept()
                return

        # 2. Navegação por setas na barra lateral na tela principal
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            direction = 1 if key == Qt.Key.Key_Down else -1
            self.navigate_sidebar(direction)
            event.accept()
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.selected_sidebar_idx >= 0:
            if not self.search_input.text().strip():
                if self.execute_selected_sidebar_action():
                    event.accept()
                    return

        # 3. Interrupção por Ctrl+C
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_C:
            if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
                self.stop_generation()
                event.accept()
                return

        # 4. Fechar ou Interromper por Escape
        if key == Qt.Key.Key_Escape:
            if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
                self.stop_generation()
                event.accept()
                return
            if self.response_browser.isVisible() and not self.chat_history:
                self.reset_conversation()
                event.accept()
                return
            self.close()
        # 5. Atalhos Alt+[Tecla]
        elif event.modifiers() & Qt.KeyboardModifier.AltModifier:
            if key == Qt.Key.Key_R:
                self.trigger_action("resumo")
            elif key == Qt.Key.Key_E:
                self.trigger_action("explicar")
            elif key == Qt.Key.Key_T:
                self.trigger_action("traduzir")
            elif key == Qt.Key.Key_O:
                self.trigger_action("extrair")
            elif key == Qt.Key.Key_C:
                self.trigger_action("region_capture")
            elif key == Qt.Key.Key_M:
                self.open_settings()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)
        super().closeEvent(event)


def run_app(capture_mode: str = "fullscreen", target_path: Optional[str] = None):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Metis Vision")
    app.setDesktopFileName("metis-vision")

    # Ícone global da aplicação para o compositor Wayland / Hyprland
    assets_dir = Path(__file__).parent / "assets"
    app_icon = QIcon()
    for sz in [16, 24, 32, 48, 64, 128, 256, 512]:
        png_sz = assets_dir / f"icon_{sz}x{sz}.png"
        if png_sz.exists():
            app_icon.addFile(str(png_sz))
    if app_icon.isNull():
        fallback_png = assets_dir / "metis_app_icon.png"
        if fallback_png.exists():
            app_icon.addFile(str(fallback_png))
    app.setWindowIcon(app_icon)

    window = ScreenAIOverlay(capture_mode=capture_mode, target_path=target_path)
    window.show()
    window.activateWindow()
    window.raise_()
    return app.exec()


if __name__ == "__main__":
    run_app()
