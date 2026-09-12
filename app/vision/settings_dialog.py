"""
Janela de Configurações e Gerenciamento de Modelos por Categoria (PyQt6).
Permite adicionar, editar, remover e selecionar modelos do Metis em tempo real.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QMessageBox,
    QFrame
)

import model_manager
import theme_manager


PROVIDER_ICONS = {
    "nvidia": "⚡ NVIDIA NIM",
    "gemini": "💎 Google Gemini",
    "openrouter": "🌐 OpenRouter",
    "ollama": "🦙 Ollama Local",
    "groq": "🚀 Groq Cloud",
}

class SettingsDialog(QDialog):
    models_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.setStyleSheet(theme_manager.generate_settings_stylesheet())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(720, 460)
        self.drag_position = QPoint()

        self.init_ui()
        self.load_categories()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        # Cabeçalho
        header = QHBoxLayout()
        header_text_box = QVBoxLayout()
        header_text_box.setSpacing(2)
        
        title = QLabel("🏛️ METIS • GERENCIADOR DE MODELOS")
        title.setObjectName("SettingsTitle")
        
        subtitle = QLabel("Alterne provedores, adicione novos modelos de visão ou defina a IA padrão.")
        subtitle.setObjectName("SettingsSubtitle")
        
        header_text_box.addWidget(title)
        header_text_box.addWidget(subtitle)
        header.addLayout(header_text_box)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(255, 255, 255, 0.05); 
                color: #94a3b8; 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 14px; 
                font-size: 13px; 
                font-weight: bold; 
            } 
            QPushButton:hover { 
                background: rgba(239, 68, 68, 0.2); 
                color: #f87171; 
                border-color: #ef4444; 
            }
        """)
        close_btn.clicked.connect(self.accept)

        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # Conteúdo em 2 Colunas: Categorias à esquerda, Modelos à direita
        body = QHBoxLayout()
        body.setSpacing(14)

        # Coluna 1: Categorias (Provedores)
        cat_box = QVBoxLayout()
        cat_box.setSpacing(6)
        cat_label = QLabel("Provedores de IA")
        cat_label.setObjectName("SectionHeader")
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(190)
        self.category_list.currentRowChanged.connect(self.on_category_selected)
        cat_box.addWidget(cat_label)
        cat_box.addWidget(self.category_list)
        body.addLayout(cat_box)

        # Coluna 2: Modelos da Categoria Selecionada
        model_box = QVBoxLayout()
        model_box.setSpacing(6)
        
        self.model_header_label = QLabel("Modelos Disponíveis")
        self.model_header_label.setObjectName("SectionHeader")
        
        self.models_list = QListWidget()
        self.models_list.itemDoubleClicked.connect(self.edit_selected_model)
        
        # Botões de Ação de Modelos
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        add_btn = QPushButton("➕ Adicionar")
        add_btn.setProperty("class", "SettingsBtn")
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.clicked.connect(self.add_model_dialog)

        edit_btn = QPushButton("✏️ Editar")
        edit_btn.setProperty("class", "SettingsBtn")
        edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        edit_btn.clicked.connect(self.edit_selected_model)

        remove_btn = QPushButton("🗑️ Remover")
        remove_btn.setProperty("class", "DangerSettingsBtn")
        remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        remove_btn.clicked.connect(self.remove_selected_model)

        set_active_btn = QPushButton("⭐ Definir como Ativo")
        set_active_btn.setProperty("class", "PrimarySettingsBtn")
        set_active_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        set_active_btn.clicked.connect(self.set_selected_as_active)

        actions_row.addWidget(add_btn)
        actions_row.addWidget(edit_btn)
        actions_row.addWidget(remove_btn)
        actions_row.addStretch()
        actions_row.addWidget(set_active_btn)

        model_box.addWidget(self.model_header_label)
        model_box.addWidget(self.models_list)
        model_box.addLayout(actions_row)
        body.addLayout(model_box)

        card_layout.addLayout(body)

        # Rodapé
        footer = QHBoxLayout()
        self.status_label = QLabel("💡 Dê um duplo clique para editar ou clique em 'Definir como Ativo'.")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        done_btn = QPushButton("✓ Concluído")
        done_btn.setProperty("class", "PrimarySettingsBtn")
        done_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        done_btn.clicked.connect(self.accept)

        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(done_btn)
        card_layout.addLayout(footer)

        main_layout.addWidget(card)

    def load_categories(self):
        self.category_list.clear()
        providers = model_manager.get_providers()
        active_prov, _ = model_manager.get_active_model()

        seen_cats = set()
        active_row = 0
        current_idx = 0
        for prov in providers:
            prov_key = prov.strip().lower()
            if prov_key in seen_cats:
                continue
            seen_cats.add(prov_key)
            display_name = PROVIDER_ICONS.get(prov_key, f"⚡ {prov.upper()}")
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, prov)
            self.category_list.addItem(item)
            if prov_key == active_prov.lower():
                active_row = current_idx
            current_idx += 1

        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(active_row)

    def on_category_selected(self, row: int):
        if row < 0:
            return
        item = self.category_list.item(row)
        provider = item.data(Qt.ItemDataRole.UserRole) or item.text()
        display_name = PROVIDER_ICONS.get(provider.lower(), provider.upper())
        self.model_header_label.setText(f"Modelos de {display_name}")
        self.load_models_for_category(provider)

    def load_models_for_category(self, provider: str):
        self.models_list.clear()
        models = model_manager.get_models_for_provider(provider)
        active_prov, active_mod = model_manager.get_active_model()

        for m in models:
            is_active = (provider.lower() == active_prov.lower() and m == active_mod)
            if is_active:
                display_text = f"⭐  {m}   (Ativo)"
            else:
                display_text = f"🤖  {m}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, m)
            self.models_list.addItem(item)

    def add_model_dialog(self):
        curr_row = self.category_list.currentRow()
        if curr_row < 0:
            return
        item = self.category_list.item(curr_row)
        provider = item.data(Qt.ItemDataRole.UserRole) or item.text()

        text, ok = QInputDialog.getText(
            self,
            "Adicionar Modelo",
            f"Digite o nome ou ID do modelo para {provider} (ex: meta/llama-3.2-11b-vision-instruct):"
        )
        if ok and text.strip():
            model_id = text.strip()
            if model_manager.add_model_to_provider(provider, model_id):
                self.load_models_for_category(provider)
                self.status_label.setText(f"✓ Modelo '{model_id}' adicionado a {provider}!")
                self.models_changed.emit()
            else:
                self.status_label.setText(f"⚠️ O modelo já existe na categoria {provider}.")

    def edit_selected_model(self):
        curr_cat_row = self.category_list.currentRow()
        curr_model_row = self.models_list.currentRow()
        if curr_cat_row < 0 or curr_model_row < 0:
            return

        cat_item = self.category_list.item(curr_cat_row)
        provider = cat_item.data(Qt.ItemDataRole.UserRole) or cat_item.text()
        old_model = self.models_list.item(curr_model_row).data(Qt.ItemDataRole.UserRole)

        text, ok = QInputDialog.getText(
            self,
            "Editar Modelo",
            f"Editar ID do modelo em {provider}:",
            text=old_model
        )
        if ok and text.strip() and text.strip() != old_model:
            new_model = text.strip()
            if model_manager.edit_model_in_provider(provider, old_model, new_model):
                self.load_models_for_category(provider)
                self.status_label.setText(f"✓ Modelo atualizado para '{new_model}'!")
                self.models_changed.emit()

    def remove_selected_model(self):
        curr_cat_row = self.category_list.currentRow()
        curr_model_row = self.models_list.currentRow()
        if curr_cat_row < 0 or curr_model_row < 0:
            return

        cat_item = self.category_list.item(curr_cat_row)
        provider = cat_item.data(Qt.ItemDataRole.UserRole) or cat_item.text()
        model_id = self.models_list.item(curr_model_row).data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Remover Modelo",
            f"Tem certeza que deseja remover o modelo '{model_id}' da categoria {provider}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if model_manager.remove_model_from_provider(provider, model_id):
                self.load_models_for_category(provider)
                self.status_label.setText(f"✓ Modelo '{model_id}' removido.")
                self.models_changed.emit()

    def set_selected_as_active(self):
        curr_cat_row = self.category_list.currentRow()
        curr_model_row = self.models_list.currentRow()
        if curr_cat_row < 0 or curr_model_row < 0:
            return

        cat_item = self.category_list.item(curr_cat_row)
        provider = cat_item.data(Qt.ItemDataRole.UserRole) or cat_item.text()
        model_id = self.models_list.item(curr_model_row).data(Qt.ItemDataRole.UserRole)

        model_manager.set_active_model(provider, model_id)
        self.load_models_for_category(provider)
        self.status_label.setText(f"⭐ '{model_id}' definido como o modelo padrão ativo!")
        self.models_changed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = SettingsDialog()
    dlg.show()
    sys.exit(app.exec())
