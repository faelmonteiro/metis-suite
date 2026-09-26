"""Pagina 5, temas, fontes, opacidade e brilho.

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
    QCheckBox,
    QComboBox,
    QSlider,
)

from PyQt6.QtCore import Qt

from PyQt6.QtGui import QFont

from agente.gui.theme_bridge import (
    FONT_SIZE_MAP,
    get_available_themes,
    get_current_theme_id,
    get_font_size_setting,
    get_font_family_setting,
    get_window_opacity_setting,
    get_neon_glow_setting,
    get_copy_btn_setting,
    set_theme_preference,
    build_dynamic_qss,
)

class AppearanceMixin:
    """Temas, fontes, opacidade e brilho.

    Grade de temas, slider de opacidade, tamanho e familia de fonte, e o reset
    para os padroes. Aplica o QSS via `build_dynamic_qss` do theme_bridge.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def setup_appearance_ui(self, parent: QWidget):
        """Monta a pagina. So orquestra; cada painel tem seu builder.

        A ordem das chamadas NAO e cosmetics: `tests/gui_impressao_digital.txt`
        fixa a ordem de criacao dos objetos, e quem define a geometria final e
        a ordem de insercao no layout, nao a ordem do codigo.
        """
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addLayout(self._build_appearance_header())

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        layout.addWidget(div)

        # Split: Esquerda (Temas) | Direita (Ajustes Finos)
        split_layout = QHBoxLayout()
        split_layout.setSpacing(12)
        split_layout.addLayout(self._build_theme_list_panel(), 56)
        split_layout.addLayout(self._build_appearance_right(), 44)
        layout.addLayout(split_layout, 1)

    def _build_appearance_header(self):
        """Voltar, titulo e atalho para o chat."""
        header = QHBoxLayout()
        header.setSpacing(10)

        btn_back = QPushButton("← Voltar")
        btn_back.setProperty("class", "SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(btn_back)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_t = QLabel("🎨 MANTO DE ÍRIS • TEMAS & ESTILOS")
        lbl_t.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: #fad094;")
        t_box.addWidget(lbl_t)

        lbl_s = QLabel("Paletas visuais do Olimpo, translucidez, tipografia e iluminação (/tema)")
        lbl_s.setFont(QFont("Sans Serif", 8))
        lbl_s.setStyleSheet("color: #94a3b8;")
        t_box.addWidget(lbl_s)
        header.addLayout(t_box)

        header.addStretch()

        btn_go_chat = QPushButton("💬 Chat ↵")
        btn_go_chat.setProperty("class", "PrimaryBtn")
        btn_go_chat.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        header.addWidget(btn_go_chat)

        return header

    def _build_theme_list_panel(self):
        """A coluna esquerda: um QScrollArea cujo container recebe os cards.

        Os tres atributos ficam expostos porque `render_appearance_themes`
        reconstroi essa lista em tempo de execucao.
        """
        left_box = QVBoxLayout()
        left_box.setSpacing(6)

        lbl_head_themes = QLabel("🎨 PALETAS VISUAIS & MITOLÓGICAS (7 TEMAS)")
        lbl_head_themes.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_head_themes.setStyleSheet("color: #f0a85d; background: transparent;")
        left_box.addWidget(lbl_head_themes)

        self.themes_scroll = QScrollArea()
        self.themes_scroll.setWidgetResizable(True)
        self.themes_container = QWidget()
        self.themes_layout = QVBoxLayout(self.themes_container)
        self.themes_layout.setContentsMargins(0, 0, 0, 0)
        self.themes_layout.setSpacing(8)
        self.themes_scroll.setWidget(self.themes_container)
        left_box.addWidget(self.themes_scroll, 1)

        return left_box

    def _build_appearance_right(self):
        """A coluna direita: tres cards, o botao de reset e o espacador."""
        right_box = QVBoxLayout()
        right_box.setSpacing(8)

        right_box.addWidget(self._build_opacity_card())
        right_box.addWidget(self._build_typography_card())
        right_box.addWidget(self._build_chat_features_card())

        btn_reset = QPushButton("🔄 Restaurar Padrões Originais")
        btn_reset.setProperty("class", "SecondaryBtn")
        btn_reset.clicked.connect(self.reset_appearance_defaults)
        right_box.addWidget(btn_reset)

        right_box.addStretch()
        return right_box

    def _build_opacity_card(self):
        """Efeitos de janela: opacidade, slider e borda com brilho."""
        card_window = QFrame()
        card_window.setProperty("class", "ThemeCard")
        l_win = QVBoxLayout(card_window)
        l_win.setContentsMargins(12, 10, 12, 10)
        l_win.setSpacing(6)

        lbl_win_t = QLabel("🪟 EFEITOS DE JANELA & OPACIDADE")
        lbl_win_t.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_win_t.setStyleSheet("color: #f0a85d; background: transparent;")
        l_win.addWidget(lbl_win_t)

        row_op = QHBoxLayout()
        lbl_op_title = QLabel("Transparência:")
        lbl_op_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_op_title.setStyleSheet("color: #cbd5e1; background: transparent;")
        row_op.addWidget(lbl_op_title)

        curr_opacity = get_window_opacity_setting()
        self.lbl_opacity_val = QLabel(f"{curr_opacity}%")
        self.lbl_opacity_val.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        self.lbl_opacity_val.setStyleSheet("color: #67e8f9; background: transparent;")
        row_op.addWidget(self.lbl_opacity_val)
        row_op.addStretch()
        l_win.addLayout(row_op)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(50, 100)
        self.slider_opacity.setValue(curr_opacity)
        self.slider_opacity.valueChanged.connect(self.on_opacity_slider_changed)
        l_win.addWidget(self.slider_opacity)

        self.chk_glow = QCheckBox("✨ Borda com Brilho Neon (Glow Color)")
        self.chk_glow.setChecked(get_neon_glow_setting())
        self.chk_glow.toggled.connect(self.on_glow_toggled)
        l_win.addWidget(self.chk_glow)

        return card_window

    def _build_typography_card(self):
        """Tamanho do texto (chips) e familia da fonte (combo)."""
        card_font = QFrame()
        card_font.setProperty("class", "ThemeCard")
        l_f = QVBoxLayout(card_font)
        l_f.setContentsMargins(12, 10, 12, 10)
        l_f.setSpacing(6)

        lbl_font_t = QLabel("🔤 TIPOGRAFIA & FONTES")
        lbl_font_t.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_font_t.setStyleSheet("color: #f0a85d; background: transparent;")
        l_f.addWidget(lbl_font_t)

        lbl_sz = QLabel("Tamanho do Texto:")
        lbl_sz.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_sz.setStyleSheet("color: #cbd5e1; background: transparent;")
        l_f.addWidget(lbl_sz)

        row_f_sz = QHBoxLayout()
        row_f_sz.setSpacing(6)
        curr_sz = get_font_size_setting()

        self.font_size_btns = {}
        for k, info in FONT_SIZE_MAP.items():
            btn_sz = QPushButton(info["label"].split()[0])
            btn_sz.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_sz.setProperty("class", "ActionChip" if k == curr_sz else "SecondaryBtn")
            # `key=k` fecha o valor agora: sem isso os 5 botoes repassam o k do
            # ultimo do laco.
            btn_sz.clicked.connect(lambda _, key=k: self.on_font_size_selected(key))
            row_f_sz.addWidget(btn_sz)
            self.font_size_btns[k] = btn_sz

        l_f.addLayout(row_f_sz)

        lbl_fam = QLabel("Família de Fonte:")
        lbl_fam.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_fam.setStyleSheet("color: #cbd5e1; background: transparent;")
        l_f.addWidget(lbl_fam)

        self.combo_font_fam = QComboBox()
        self.combo_font_fam.addItem("Padrão do Sistema (Sans-Serif)", "default")
        self.combo_font_fam.addItem("JetBrains Mono (Programador)", "jetbrains")
        self.combo_font_fam.addItem("Fira Code (Ligaduras)", "fira")
        self.combo_font_fam.addItem("Inter (Moderna UI)", "inter")
        self.combo_font_fam.addItem("Roboto (Clean)", "roboto")

        curr_fam = get_font_family_setting()
        for idx in range(self.combo_font_fam.count()):
            if self.combo_font_fam.itemData(idx) == curr_fam:
                self.combo_font_fam.setCurrentIndex(idx)
                break

        self.combo_font_fam.currentIndexChanged.connect(self.on_font_family_selected)
        l_f.addWidget(self.combo_font_fam)

        return card_font

    def _build_chat_features_card(self):
        """Uma opcao: o botao 'Copiar' nos blocos de codigo."""
        card_features = QFrame()
        card_features.setProperty("class", "ThemeCard")
        l_feat = QVBoxLayout(card_features)
        l_feat.setContentsMargins(12, 10, 12, 10)
        l_feat.setSpacing(6)

        lbl_feat_t = QLabel("⚡ RECURSOS DO CHAT")
        lbl_feat_t.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_feat_t.setStyleSheet("color: #f0a85d; background: transparent;")
        l_feat.addWidget(lbl_feat_t)

        self.chk_copy_code = QCheckBox("📋 Botão 'Copiar' em blocos de código")
        self.chk_copy_code.setChecked(get_copy_btn_setting())
        self.chk_copy_code.toggled.connect(lambda chk: set_theme_preference("copy_btn_enabled", chk))
        l_feat.addWidget(self.chk_copy_code)

        return card_features

    def open_appearance_page(self):
        self.render_appearance_themes()
        self.refresh_telemetry()
        self.stack.setCurrentIndex(5)

    def render_appearance_themes(self):
        while self.themes_layout.count() > 0:
            item = self.themes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        curr_theme = get_current_theme_id()
        themes = get_available_themes()

        for t in themes:
            is_active = (t["id"] == curr_theme)
            card = QFrame()
            card.setProperty("class", "ThemeCardActive" if is_active else "ThemeCard")
            l_t = QVBoxLayout(card)
            l_t.setContentsMargins(12, 9, 12, 9)
            l_t.setSpacing(5)

            head_row = QHBoxLayout()
            head_row.setSpacing(8)

            lbl_name = QLabel(f"{t['icon']}  <b>{t['name']}</b>")
            lbl_name.setFont(QFont("Sans Serif", 10))
            lbl_name.setStyleSheet(f"color: {t['accent_gold']}; background: transparent;")
            head_row.addWidget(lbl_name)

            lbl_cat = QLabel(t["category"])
            lbl_cat.setProperty("class", "ProviderTag")
            head_row.addWidget(lbl_cat)

            head_row.addStretch()

            if is_active:
                lbl_badge = QLabel("✓ Ativo")
                lbl_badge.setProperty("class", "StatusPillActive")
                head_row.addWidget(lbl_badge)
            else:
                btn_apply = QPushButton("Aplicar")
                btn_apply.setProperty("class", "ActionChip")
                btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_apply.clicked.connect(lambda _, tid=t["id"]: self.select_theme(tid))
                head_row.addWidget(btn_apply)

            l_t.addLayout(head_row)

            lbl_desc = QLabel(t["description"])
            lbl_desc.setFont(QFont("Sans Serif", 8))
            lbl_desc.setStyleSheet(f"color: {t['fg_sub']}; background: transparent;")
            lbl_desc.setWordWrap(True)
            l_t.addWidget(lbl_desc)

            row_swatches = QHBoxLayout()
            row_swatches.setSpacing(5)

            for col_name, col_val in [
                ("Fundo", t["bg_main"]),
                ("Cartões", t["bg_card"]),
                ("Realce Ouro", t["accent_gold"]),
                ("Destaque Ciano", t["accent_cyan"]),
                ("Texto", t["fg_text"])
            ]:
                swatch = QFrame()
                swatch.setFixedSize(14, 14)
                swatch.setStyleSheet(f"background-color: {col_val}; border: 1px solid rgba(255,255,255,0.4); border-radius: 7px;")
                swatch.setToolTip(f"{col_name}: {col_val}")
                row_swatches.addWidget(swatch)

            row_swatches.addStretch()
            l_t.addLayout(row_swatches)

            self.themes_layout.addWidget(card)

        self.themes_layout.addStretch()

    def select_theme(self, theme_id: str):
        set_theme_preference("theme_id", theme_id)
        self.apply_theme()
        self.render_appearance_themes()
        self.refresh_telemetry()
        if hasattr(self, "rebuild_oracle_buttons"):
            self.rebuild_oracle_buttons()
        if hasattr(self, "cards"):
            for card in self.cards:
                card.update_style()

    def on_opacity_slider_changed(self, val: int):
        self.lbl_opacity_val.setText(f"{val}%")
        set_theme_preference("window_opacity", val)
        self.setStyleSheet(build_dynamic_qss(opacity=val))
        self.sync_window_opacity(val)

    def on_glow_toggled(self, checked: bool):
        set_theme_preference("neon_glow", checked)
        self.apply_theme()

    def on_font_size_selected(self, sz_key: str):
        set_theme_preference("font_size", sz_key)
        self.apply_theme()
        if hasattr(self, "font_size_btns"):
            for k, btn in self.font_size_btns.items():
                btn.setProperty("class", "ActionChip" if k == sz_key else "SecondaryBtn")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        self.render_appearance_themes()

    def on_font_family_selected(self, index: int):
        fam_key = self.combo_font_fam.itemData(index)
        if fam_key:
            set_theme_preference("font_family", fam_key)
            self.apply_theme()

    def reset_appearance_defaults(self):
        set_theme_preference("theme_id", "metis_oracle")
        set_theme_preference("window_opacity", 98)
        set_theme_preference("font_size", "medium")
        set_theme_preference("font_family", "default")
        set_theme_preference("neon_glow", True)
        set_theme_preference("copy_btn_enabled", True)
        if hasattr(self, "slider_opacity"):
            self.slider_opacity.setValue(98)
        if hasattr(self, "chk_glow"):
            self.chk_glow.setChecked(True)
        if hasattr(self, "chk_copy_code"):
            self.chk_copy_code.setChecked(True)
        if hasattr(self, "combo_font_fam"):
            self.combo_font_fam.setCurrentIndex(0)
        self.apply_theme()
        self.render_appearance_themes()
        self.refresh_telemetry()
        QMessageBox.information(self, "Metis", "Aparência e temas restaurados para os padrões originais!")
