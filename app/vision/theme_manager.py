"""
Theme Manager para Metis Vision (ScreenAI) • Totalmente Sincronizado com o Metis.
Carrega e aplica dinamicamente o tema ativo, opacidade, cores, tipografia e bordas
escolhidos no Metis (7 temas: Metis Oracle, Olimpo Sagrado, Valhalla & Runas, Dracula Synth, Nord Arctic, Matrix Emerald, Onyx Minimal).
"""

import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Garante acesso à raiz do Metis para importar as definições oficiais
metis_root = Path(__file__).parent.parent
if str(metis_root) not in sys.path:
    sys.path.insert(0, str(metis_root))

try:
    from agente.ui.theme_manager import (
        THEMES,
        FONT_SIZE_MAP,
        FONT_FAMILY_MAP,
        get_available_themes,
        get_current_theme_id,
        get_current_theme_colors,
        get_font_size_setting,
        get_current_font_sizes,
        get_font_family_setting,
        get_window_opacity_setting,
        get_neon_glow_setting,
        get_copy_btn_setting,
        set_theme_preference,
        build_theme_qss,
    )
except Exception:
    THEMES = {
        "metis_oracle": {
            "name": "Metis Oracle",
            "bg_main": "#080f1d",
            "bg_card": "#0e1a30",
            "bg_input": "#12223f",
            "border": "#1e3557",
            "border_glow": "#fad094",
            "fg_text": "#f8fafc",
            "fg_sub": "#94a3b8",
            "accent_gold": "#fad094",
            "accent_cyan": "#67e8f9",
            "primary_btn_bg": "#d97706",
            "primary_btn_hover": "#f59e0b",
            "primary_btn_fg": "#ffffff",
        }
    }
    FONT_SIZE_MAP = {"medium": {"base": 12}}
    FONT_FAMILY_MAP = {"default": "system-ui, sans-serif"}
    get_available_themes = lambda: list(THEMES.values())
    get_current_theme_id = lambda: "metis_oracle"
    get_current_theme_colors = lambda: THEMES["metis_oracle"]
    get_font_size_setting = lambda: "medium"
    get_current_font_sizes = lambda: {"base": 12}
    get_font_family_setting = lambda: "default"
    get_window_opacity_setting = lambda: 98
    get_neon_glow_setting = lambda: True
    get_copy_btn_setting = lambda: True
    set_theme_preference = lambda *a, **kw: None
    build_theme_qss = lambda *a, **kw: ""


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converte hexadecimal '#RRGGBB' para tupla (r, g, b)."""
    hex_str = str(hex_str).lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join([c * 2 for c in hex_str])
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return r, g, b
    except Exception:
        return 14, 26, 48


def _hex_to_rgba(hex_str: str, alpha: float) -> str:
    """Converte hexadecimal para formato rgba(r, g, b, alpha)."""
    r, g, b = hex_to_rgb(hex_str)
    return f"rgba({r}, {g}, {b}, {max(0.0, min(1.0, alpha)):.2f})"


def get_theme_palette(theme_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retorna a paleta de cores completa sincronizada com o tema ativo do Metis,
    incluindo transparências, fontes e efeitos de borda.
    """
    t_id = theme_id or get_current_theme_id()
    c = THEMES.get(t_id, THEMES.get("metis_oracle", {}))

    op_val = get_window_opacity_setting()
    has_glow = get_neon_glow_setting()
    f_fam_key = get_font_family_setting()
    f_sz_key = get_font_size_setting()

    font_family = FONT_FAMILY_MAP.get(f_fam_key, "system-ui, -apple-system, sans-serif")
    f_sz = FONT_SIZE_MAP.get(f_sz_key, FONT_SIZE_MAP.get("medium", {"base": 12}))
    font_size_px = f_sz.get("base", 12)

    alpha_main = max(0.40, min(1.0, op_val / 100.0))
    alpha_card = max(0.45, min(1.0, alpha_main * 0.96))
    alpha_input = max(0.55, min(1.0, alpha_main * 0.98))

    border_color = c.get("border_glow", "#fad094") if has_glow else c.get("border", "#1e3557")
    if has_glow:
        card_border_style = f"1.5px solid {_hex_to_rgba(c.get('border_glow', '#fad094'), 0.75)}"
        search_border = f"1.2px solid {_hex_to_rgba(c.get('border_glow', '#fad094'), 0.50)}"
        search_border_focus = f"1.5px solid {c.get('accent_gold', '#fad094')}"
        gold_border_rgba = _hex_to_rgba(c.get("border_glow", "#fad094"), 0.75)
        gold_glow_rgba = _hex_to_rgba(c.get("border_glow", "#fad094"), 0.25)
    else:
        card_border_style = f"1px solid {_hex_to_rgba(c.get('border', '#1e3557'), 0.70)}"
        search_border = f"1px solid {_hex_to_rgba(c.get('border', '#1e3557'), 0.60)}"
        search_border_focus = f"1.2px solid {_hex_to_rgba(c.get('border', '#1e3557'), 0.95)}"
        gold_border_rgba = _hex_to_rgba(c.get("border", "#1e3557"), 0.70)
        gold_glow_rgba = "transparent"

    card_bg_rgba = _hex_to_rgba(c.get("bg_card", "#0e1a30"), alpha_card)
    main_bg_rgba = _hex_to_rgba(c.get("bg_main", "#080f1d"), alpha_main)
    input_bg_rgba = _hex_to_rgba(c.get("bg_input", "#12223f"), alpha_input)

    palette = {
        "is_dark": True,
        "theme_id": t_id,
        "theme_name": c.get("name", "Metis Theme"),
        "opacity": op_val,
        "has_glow": has_glow,
        "card_border_style": card_border_style,
        "search_border": search_border,
        "search_border_focus": search_border_focus,
        "font_family": font_family,
        "font_size_px": font_size_px,
        "card_bg_rgba": card_bg_rgba,
        "card_bg_hex": c.get("bg_card", "#0e1a30"),
        "main_bg_rgba": main_bg_rgba,
        "inner_box_bg": input_bg_rgba,
        "inner_box_hover": _hex_to_rgba(c.get("accent_gold", "#fad094"), 0.16),
        "border_col": _hex_to_rgba(c.get("border", "#1e3557"), 0.85),
        "border_subtle": _hex_to_rgba(c.get("border", "#1e3557"), 0.45),
        "gold_border": gold_border_rgba,
        "gold_glow": gold_glow_rgba,
        "text_primary": c.get("fg_text", "#f8fafc"),
        "text_muted": c.get("fg_sub", "#94a3b8"),
        "text_dim": _hex_to_rgba(c.get("fg_sub", "#94a3b8"), 0.70),
        "accent": c.get("accent_gold", "#fad094"),
        "accent_light": c.get("accent_cyan", "#67e8f9"),
        "accent_btn_bg": c.get("primary_btn_bg", "#d97706"),
        "accent_btn_fg": c.get("primary_btn_fg", "#ffffff"),
        "accent_btn_hover": c.get("primary_btn_hover", c.get("accent_gold", "#f59e0b")),
        "badge_bg": c.get("badge_bg", c.get("bg_input", "#12223f")),
        "badge_border": c.get("badge_border", c.get("border", "#1e3557")),
        "scroll_bg": _hex_to_rgba(c.get("bg_input", "#12223f"), 0.4),
        "scroll_handle": _hex_to_rgba(c.get("accent_gold", "#fad094"), 0.45),
        "bg_main": c.get("bg_main", "#080f1d"),
        "bg_card": c.get("bg_card", "#0e1a30"),
        "bg_input": c.get("bg_input", "#12223f"),
        "raw": c,
        **c,
    }
    return palette


def generate_main_stylesheet(theme: Optional[Dict[str, Any]] = None) -> str:
    """Gera o CSS do HUD principal em ui.py totalmente sincronizado com o tema do Metis."""
    t = theme or get_theme_palette()

    return f"""
QToolTip {{
    background-color: {t["card_bg_hex"]};
    color: {t["accent"]};
    border: 1px solid {t["accent"]};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 600;
    font-family: {t["font_family"]};
}}

QWidget#MainCard, QFrame#MainCard {{
    background-color: {t["card_bg_rgba"]};
    border: {t["card_border_style"]};
    border-radius: 16px;
    font-family: {t["font_family"]};
}}

/* Cabeçalho */
QLabel#HeaderTitle {{
    color: {t["accent"]};
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.3px;
    font-family: {t["font_family"]};
}}

QLabel#ThumbnailLabel {{
    border: 1px solid {t["border_subtle"]};
    border-radius: 8px;
    background-color: {t["inner_box_bg"]};
}}

QLabel#ModeBadge {{
    background-color: {t["badge_bg"]};
    color: {t["accent_light"]};
    border: 1px solid {t["gold_border"]};
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: {t["font_family"]};
}}

QPushButton#ModelSelector, QComboBox#ModelSelector {{
    background-color: {t["inner_box_bg"]};
    color: {t["text_primary"]};
    border: 1px solid {t["gold_border"]};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
    min-width: 140px;
    text-align: left;
    font-family: {t["font_family"]};
}}

QPushButton#ModelSelector:hover, QComboBox#ModelSelector:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent"]};
}}

QPushButton#ModelSelector::menu-indicator {{
    image: none;
    width: 0px;
}}

QComboBox#ModelSelector::drop-down {{
    border: none;
    width: 14px;
}}

QComboBox#ModelSelector QAbstractItemView {{
    background-color: {t["card_bg_hex"]};
    color: {t["text_primary"]};
    border: 1px solid {t["accent"]};
    selection-background-color: {t["accent"]};
    selection-color: #000000;
    border-radius: 8px;
    padding: 6px;
    font-family: {t["font_family"]};
}}

/* Menus e Submenus Hierárquicos de Provedores e Modelos */
QMenu {{
    background-color: {t["card_bg_hex"]};
    color: {t["text_primary"]};
    border: 1px solid {t["gold_border"]};
    border-radius: 10px;
    padding: 5px;
    font-family: {t["font_family"]};
    font-size: 11.5px;
}}

QMenu::item {{
    background: transparent;
    padding: 6px 18px 6px 12px;
    border-radius: 6px;
    color: {t["text_primary"]};
    font-size: 11px;
}}

QMenu::item:selected {{
    background-color: {t["inner_box_hover"]};
    color: {t["accent"]};
}}

QMenu::item:disabled {{
    color: {t["text_muted"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {t["border_subtle"]};
    margin: 4px 6px;
}}

/* Botões Circulares do Cabeçalho */
QPushButton.CircleIconBtn {{
    background-color: {t["inner_box_bg"]};
    color: {t["text_muted"]};
    border: 1px solid {t["border_subtle"]};
    border-radius: 14px;
    font-size: 13px;
    font-weight: bold;
    font-family: {t["font_family"]};
}}
QPushButton.CircleIconBtn:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent"]};
    color: {t["accent"]};
}}

/* Barra Lateral (Sidebar) */
QFrame#SidebarContainer {{
    background-color: {t["inner_box_bg"]};
    border: 1px solid {t["border_subtle"]};
    border-radius: 12px;
}}

QPushButton#SidebarToggleBtn {{
    background-color: {t["inner_box_bg"]};
    border: 1px solid {t["gold_border"]};
    color: {t["accent"]};
    border-radius: 6px;
    font-size: 11px;
    font-weight: 800;
    font-family: {t["font_family"]};
}}
QPushButton#SidebarToggleBtn:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent"]};
    color: {t["accent_light"]};
}}

/* Itens da Barra Lateral */
QFrame.SidebarItem {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
}}
QFrame.SidebarItem:hover, QFrame.SidebarItem[selected="true"] {{
    background-color: {t["inner_box_hover"]};
    border: 1px solid {t["accent"]};
}}

QLabel#SidebarIcon {{
    font-size: 15px;
    color: {t["accent"]};
    background: transparent;
}}

QLabel#SidebarLabel {{
    font-size: 12.5px;
    font-weight: 700;
    color: {t["text_primary"]};
    background: transparent;
    padding: 0px;
    margin: 0px;
    font-family: {t["font_family"]};
}}
QFrame.SidebarItem:hover QLabel#SidebarLabel, QFrame.SidebarItem[selected="true"] QLabel#SidebarLabel {{
    color: {t["accent"]};
}}

/* Título de Seção Principal */
QLabel#SectionTitleLabel {{
    color: {t["accent"]};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.8px;
    background: transparent;
    font-family: {t["font_family"]};
}}

/* Container de Preview Visual da Tela (Sem Moldura) */
QFrame#PreviewContainer {{
    background-color: transparent;
    border: none;
}}

/* Caixa de Busca / Pergunta */
QFrame#SearchContainer {{
    background-color: {t["inner_box_bg"]};
    border: {t["search_border"]};
    border-radius: 12px;
}}
QFrame#SearchContainer:focus-within {{
    border: {t["search_border_focus"]};
    background-color: {t["inner_box_hover"]};
}}

QPlainTextEdit#SearchInput, QTextEdit#SearchInput, QLineEdit#SearchInput {{
    background: transparent;
    border: none;
    font-size: {t["font_size_px"]}px;
    line-height: 1.35;
    color: {t["text_primary"]};
    padding: 4px 6px;
    font-family: {t["font_family"]};
}}

QLabel#EnterBadge {{
    color: {t["text_dim"]};
    font-size: 10px;
    font-weight: bold;
    background: transparent;
    font-family: {t["font_family"]};
}}

/* Área de Respostas / Chat */
QTextBrowser#ResponseBrowser {{
    background-color: {t["inner_box_bg"]};
    border: 1px solid {t["border_col"]};
    border-radius: 12px;
    padding: 12px;
    font-size: {t["font_size_px"]}px;
    line-height: 1.5;
    color: {t["text_primary"]};
    font-family: {t["font_family"]};
}}

/* Botões de Ação do Rodapé e Telas Integradas */
QPushButton#PrimaryBtn, QPushButton.PrimarySettingsBtn {{
    background-color: {t["accent_btn_bg"]};
    color: {t["accent_btn_fg"]};
    border: 1px solid {t["accent"]};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 11.5px;
    font-weight: 800;
    font-family: {t["font_family"]};
}}
QPushButton#PrimaryBtn:hover, QPushButton.PrimarySettingsBtn:hover {{
    background-color: {t["accent_btn_hover"]};
    border-color: {t["accent_light"]};
}}

QPushButton#SecondaryBtn, QPushButton.SettingsBtn {{
    background-color: {t["inner_box_bg"]};
    color: {t["text_primary"]};
    border: 1px solid {t["border_col"]};
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 11.5px;
    font-weight: 600;
    font-family: {t["font_family"]};
}}
QPushButton#SecondaryBtn:hover, QPushButton.SettingsBtn:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent"]};
    color: {t["accent"]};
}}

QPushButton#CmdBtn {{
    background-color: {t["accent_btn_bg"]};
    color: {t["accent_btn_fg"]};
    border: 1px solid {t["accent"]};
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 11.5px;
    font-weight: bold;
    font-family: {t["font_family"]};
}}
QPushButton#CmdBtn:hover {{
    background-color: {t["accent_btn_hover"]};
    border-color: {t["accent_light"]};
}}

/* Barra de Cabeçalho das Configurações */
QFrame#SettingsHeaderBar {{
    background-color: {t["inner_box_bg"]};
    border: 1px solid {t["border_col"]};
    border-radius: 10px;
    padding: 2px 6px;
}}

QPushButton#SettingsBackBtn {{
    background-color: {t["inner_box_hover"]};
    color: {t["accent"]};
    border: 1.2px solid {t["gold_border"]};
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 700;
    font-family: {t["font_family"]};
}}
QPushButton#SettingsBackBtn:hover {{
    background-color: {t["inner_box_bg"]};
    border-color: {t["accent"]};
    color: {t["accent_light"]};
}}

QPushButton#SettingsAddBtn {{
    background-color: {t["inner_box_bg"]};
    color: {t["accent_light"]};
    border: 1.2px solid {t["gold_border"]};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 11.5px;
    font-weight: 700;
    font-family: {t["font_family"]};
}}
QPushButton#SettingsAddBtn:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent"]};
    color: #ffffff;
}}

QPushButton#SettingsEditBtn {{
    background-color: {t["inner_box_bg"]};
    color: {t["accent"]};
    border: 1.2px solid {t["gold_border"]};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 11.5px;
    font-weight: 700;
    font-family: {t["font_family"]};
}}
QPushButton#SettingsEditBtn:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent_light"]};
    color: #ffffff;
}}

QPushButton#SettingsDeleteBtn, QPushButton.DangerSettingsBtn {{
    background-color: rgba(239, 68, 68, 0.12);
    color: #fca5a5;
    border: 1.2px solid rgba(239, 68, 68, 0.35);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 11.5px;
    font-weight: 700;
    font-family: {t["font_family"]};
}}
QPushButton#SettingsDeleteBtn:hover, QPushButton.DangerSettingsBtn:hover {{
    background-color: #ef4444;
    border-color: #f87171;
    color: #ffffff;
}}

QPushButton#SettingsActiveBtn {{
    background-color: {t["accent_btn_bg"]};
    color: {t["accent_btn_fg"]};
    border: 1px solid {t["accent"]};
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 11.5px;
    font-weight: 800;
    font-family: {t["font_family"]};
}}
QPushButton#SettingsActiveBtn:hover {{
    background-color: {t["accent_btn_hover"]};
    border-color: {t["accent_light"]};
}}

/* Listas Integradas (Provedores e Modelos em Configurações) */
QListWidget {{
    background-color: {t["inner_box_bg"]};
    border: 1.2px solid {t["border_col"]};
    border-radius: 10px;
    padding: 6px;
    color: {t["text_primary"]};
    font-size: 12px;
    outline: none;
    font-family: {t["font_family"]};
}}

QListWidget::item {{
    padding: 7px 10px;
    border-radius: 6px;
    margin-bottom: 3px;
    border: 1px solid transparent;
    font-family: {t["font_family"]};
}}

QListWidget::item:hover {{
    background-color: {t["inner_box_hover"]};
    color: {t["accent"]};
    border: 1px solid {t["gold_border"]};
}}

QListWidget::item:selected {{
    background-color: {t["accent"]};
    color: #000000;
    font-weight: 800;
}}

/* Rodapé Status */
QLabel#FooterStatus {{
    color: {t["text_muted"]};
    font-size: 11.5px;
    font-weight: 500;
    font-family: {t["font_family"]};
}}

/* Barras de Rolagem Verticais e Horizontais */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 2px 0px 2px 0px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {t["scroll_handle"]};
    min-height: 22px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t["accent"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: transparent;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 6px;
    margin: 0px 2px 2px 2px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {t["scroll_handle"]};
    min-width: 22px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t["accent"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: transparent;
    border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
QScrollBar::corner {{
    background: transparent;
}}

/* Diálogos e Modais Modernos */
QFrame#ModernModalCard {{
    background-color: {t["card_bg_rgba"]};
    border: {t["card_border_style"]};
    border-radius: 14px;
}}
"""


def generate_menu_stylesheet(theme: Optional[Dict[str, Any]] = None) -> str:
    """Gera o CSS específico para menus e submenus suspensos sincronizados com o tema."""
    t = theme or get_theme_palette()
    return f"""
QMenu {{
    background-color: {t["card_bg_hex"]};
    color: {t["text_primary"]};
    border: 1px solid {t["gold_border"]};
    border-radius: 10px;
    padding: 5px;
    font-family: {t["font_family"]};
    font-size: 11.5px;
}}

QMenu::item {{
    background: transparent;
    padding: 6px 18px 6px 12px;
    border-radius: 6px;
    color: {t["text_primary"]};
    font-size: 11px;
}}

QMenu::item:selected {{
    background-color: {t["inner_box_hover"]};
    color: {t["accent"]};
}}

QMenu::item:disabled {{
    color: {t["text_muted"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {t["border_subtle"]};
    margin: 4px 6px;
}}
"""


def generate_settings_stylesheet(theme: Optional[Dict[str, Any]] = None) -> str:
    """Gera o CSS do diálogo de configurações sincronizado com o tema."""
    t = theme or get_theme_palette()

    return f"""
QDialog#SettingsDialog {{
    background-color: {t["card_bg_rgba"]};
    border: {t["card_border_style"]};
    border-radius: 14px;
    font-family: {t["font_family"]};
}}

QFrame#SettingsCard {{
    background-color: transparent;
    border: none;
}}

QListWidget {{
    background-color: {t["inner_box_bg"]};
    border: 1.2px solid {t["border_col"]};
    border-radius: 10px;
    padding: 6px;
    color: {t["text_primary"]};
    font-size: 12px;
    outline: none;
    font-family: {t["font_family"]};
}}

QListWidget::item {{
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 3px;
    border: 1px solid transparent;
}}

QListWidget::item:hover {{
    background-color: {t["inner_box_hover"]};
    color: {t["accent"]};
    border: 1px solid {t["gold_border"]};
}}

QListWidget::item:selected {{
    background-color: {t["accent"]};
    color: #000000;
    font-weight: 800;
}}

QPushButton.SettingsBtn {{
    background-color: {t["inner_box_bg"]};
    color: {t["text_primary"]};
    border: 1px solid {t["border_subtle"]};
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
    font-family: {t["font_family"]};
}}

QPushButton.SettingsBtn:hover {{
    background-color: {t["inner_box_hover"]};
    border-color: {t["accent"]};
    color: {t["accent"]};
}}

QPushButton.PrimarySettingsBtn {{
    background-color: {t["accent_btn_bg"]};
    color: {t["accent_btn_fg"]};
    border: none;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 800;
    font-family: {t["font_family"]};
}}

QPushButton.PrimarySettingsBtn:hover {{
    background-color: {t["accent_btn_hover"]};
    color: #ffffff;
}}

QPushButton.DangerSettingsBtn {{
    background-color: rgba(239, 68, 68, 0.12);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
    font-family: {t["font_family"]};
}}

QPushButton.DangerSettingsBtn:hover {{
    background-color: #ef4444;
    color: #ffffff;
    border-color: #ef4444;
}}

QLabel#SettingsTitle {{
    color: {t["accent"]};
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.5px;
    font-family: {t["font_family"]};
}}

QLabel#SettingsSubtitle {{
    color: {t["text_muted"]};
    font-size: 11.5px;
    font-family: {t["font_family"]};
}}

QLabel#SectionHeader {{
    color: {t["accent"]};
    font-size: 11.5px;
    font-weight: 800;
    letter-spacing: 0.5px;
    font-family: {t["font_family"]};
}}
"""


# Re-exporta tudo para compatibilidade completa
__all__ = [
    "THEMES",
    "FONT_SIZE_MAP",
    "FONT_FAMILY_MAP",
    "get_available_themes",
    "get_current_theme_id",
    "get_current_theme_colors",
    "get_theme_palette",
    "get_font_size_setting",
    "get_current_font_sizes",
    "get_font_family_setting",
    "get_window_opacity_setting",
    "get_neon_glow_setting",
    "get_copy_btn_setting",
    "set_theme_preference",
    "build_theme_qss",
    "generate_main_stylesheet",
    "generate_menu_stylesheet",
    "generate_settings_stylesheet",
]