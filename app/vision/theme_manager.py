"""
Theme Manager para Metis Vision (ScreenAI) • Totalmente Sincronizado com o Metis Oracle.
Carrega e aplica dinamicamente o tema ativo, opacidade, cores, tipografia e bordas
escolhidos no Metis (7 temas: Metis Oracle, Olimpo Sagrado, Valhalla & Runas, Dracula Synth, Nord Arctic, Matrix Emerald, Onyx Minimal).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Tenta importar as definições oficiais de temas do Metis
try:
    metis_root = Path(__file__).parent.parent
    if str(metis_root) not in sys.path:
        sys.path.insert(0, str(metis_root))
    from agente.ui.theme_manager import THEMES as METIS_THEMES
except Exception:
    METIS_THEMES = {
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
        },
        "olympus_greek": {
            "name": "Olimpo Sagrado",
            "bg_main": "#17120a",
            "bg_card": "#231c11",
            "bg_input": "#302617",
            "border": "#5a4522",
            "border_glow": "#d4af37",
            "fg_text": "#fdfbf7",
            "fg_sub": "#d6d3d1",
            "accent_gold": "#d4af37",
            "accent_cyan": "#93c5fd",
            "primary_btn_bg": "#b48b18",
            "primary_btn_hover": "#d4af37",
            "primary_btn_fg": "#000000",
        },
        "valhalla_nordic": {
            "name": "Valhalla & Runas",
            "bg_main": "#061523",
            "bg_card": "#0a2238",
            "bg_input": "#0f2d4a",
            "border": "#184a75",
            "border_glow": "#38bdf8",
            "fg_text": "#f0fdf4",
            "fg_sub": "#a5f3fc",
            "accent_gold": "#34d399",
            "accent_cyan": "#38bdf8",
            "primary_btn_bg": "#0284c7",
            "primary_btn_hover": "#0ea5e9",
            "primary_btn_fg": "#ffffff",
        },
        "dracula_synth": {
            "name": "Dracula Synth",
            "bg_main": "#170b29",
            "bg_card": "#23113d",
            "bg_input": "#311754",
            "border": "#5e248f",
            "border_glow": "#f472b6",
            "fg_text": "#fdf4ff",
            "fg_sub": "#f0abfc",
            "accent_gold": "#f472b6",
            "accent_cyan": "#c084fc",
            "primary_btn_bg": "#9333ea",
            "primary_btn_hover": "#a855f7",
            "primary_btn_fg": "#ffffff",
        },
        "nord_ocean": {
            "name": "Nord Arctic",
            "bg_main": "#0d1726",
            "bg_card": "#142238",
            "bg_input": "#1b2e4c",
            "border": "#2a4873",
            "border_glow": "#88c0d0",
            "fg_text": "#eceff4",
            "fg_sub": "#88c0d0",
            "accent_gold": "#ebcb8b",
            "accent_cyan": "#88c0d0",
            "primary_btn_bg": "#434c5e",
            "primary_btn_hover": "#5e81ac",
            "primary_btn_fg": "#eceff4",
        },
        "matrix_emerald": {
            "name": "Matrix Emerald",
            "bg_main": "#031409",
            "bg_card": "#062210",
            "bg_input": "#0a3017",
            "border": "#155c2d",
            "border_glow": "#10b981",
            "fg_text": "#ecfdf5",
            "fg_sub": "#6ee7b7",
            "accent_gold": "#10b981",
            "accent_cyan": "#34d399",
            "primary_btn_bg": "#059669",
            "primary_btn_hover": "#10b981",
            "primary_btn_fg": "#ffffff",
        },
        "onyx_mono": {
            "name": "Onyx Minimal",
            "bg_main": "#121215",
            "bg_card": "#1a1a1f",
            "bg_input": "#24242b",
            "border": "#363642",
            "border_glow": "#e4e4e7",
            "fg_text": "#fafafa",
            "fg_sub": "#a1a1aa",
            "accent_gold": "#f4f4f5",
            "accent_cyan": "#a1a1aa",
            "primary_btn_bg": "#27272a",
            "primary_btn_hover": "#3f3f46",
            "primary_btn_fg": "#ffffff",
        },
    }


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converte string hexadecimal (#RRGGBB ou RRGGBB) para tupla (r, g, b)."""
    hex_str = str(hex_str).strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    if len(hex_str) != 6:
        return (14, 15, 20)
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b)
    except ValueError:
        return (14, 15, 20)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converte tupla (r, g, b) para hexadecimal (#RRGGBB)."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgba(hex_str: str, alpha: float) -> str:
    """Converte hexadecimal para formato rgba(r, g, b, alpha)."""
    r, g, b = hex_to_rgb(hex_str)
    return f"rgba({r}, {g}, {b}, {max(0.0, min(1.0, alpha)):.2f})"


def get_metis_saved_preferences() -> Dict[str, Any]:
    """Lê as preferências salvas no config_models.json canônico do Metis (~/.config/metis)."""
    cfg_file = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis")) / "config_models.json"
    candidates = [cfg_file]
    if not cfg_file.exists():
        candidates.extend([
            Path.home() / ".local/share/metis/app/config_models.json",
            Path(__file__).resolve().parent.parent / "config_models.json",
            Path.home() / "Metis" / "config_models.json",
        ])
    for p in candidates:
        if p.exists() and p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "preferences" in data:
                    return data["preferences"]
            except Exception:
                pass
    return {}


def get_theme_palette() -> Dict[str, Any]:
    """
    Retorna a paleta de cores completa sincronizada com o tema do Metis ativo.
    """
    prefs = get_metis_saved_preferences()
    theme_id = prefs.get("theme_id", "metis_oracle")
    op_val = int(prefs.get("window_opacity", 98))
    has_glow = bool(prefs.get("neon_glow", True))
    font_family_key = prefs.get("font_family", "default")
    font_size_key = prefs.get("font_size", "medium")

    # Mapeamento de fontes
    font_stacks = {
        "default": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        "jetbrains": "'JetBrains Mono', 'Fira Code', monospace",
        "fira": "'Fira Code', 'JetBrains Mono', monospace",
        "inter": "'Inter', 'Segoe UI', sans-serif",
        "roboto": "'Roboto', 'Segoe UI', sans-serif",
    }
    font_family = font_stacks.get(font_family_key, "system-ui, sans-serif")

    # Mapeamento de tamanhos de fonte
    font_sizes = {
        "small": 11,
        "medium": 12,
        "large": 13.5
    }
    font_size_px = font_sizes.get(font_size_key, 12)

    c = METIS_THEMES.get(theme_id, METIS_THEMES["metis_oracle"])

    alpha_main = max(0.40, min(1.0, op_val / 100.0))
    alpha_card = max(0.45, min(1.0, alpha_main * 0.96))
    alpha_input = max(0.55, min(1.0, alpha_main * 0.98))

    if has_glow:
        border_color = c["border_glow"]
        gold_border_rgba = _hex_to_rgba(c["border_glow"], 0.75)
        gold_glow_rgba = _hex_to_rgba(c["border_glow"], 0.25)
        card_border_style = f"1.5px solid {_hex_to_rgba(c['border_glow'], 0.75)}"
        search_border = f"1.2px solid {_hex_to_rgba(c['border_glow'], 0.50)}"
        search_border_focus = f"1.5px solid {c['accent_gold']}"
    else:
        border_color = c["border"]
        gold_border_rgba = _hex_to_rgba(c["border"], 0.70)
        gold_glow_rgba = "transparent"
        card_border_style = f"1px solid {_hex_to_rgba(c['border'], 0.70)}"
        search_border = f"1px solid {_hex_to_rgba(c['border'], 0.60)}"
        search_border_focus = f"1.2px solid {_hex_to_rgba(c['border'], 0.95)}"

    card_bg_rgba = _hex_to_rgba(c["bg_card"], alpha_card)

    return {
        "is_dark": True,
        "theme_id": theme_id,
        "theme_name": c.get("name", "Metis Theme"),
        "opacity": op_val,
        "has_glow": has_glow,
        "card_border_style": card_border_style,
        "search_border": search_border,
        "search_border_focus": search_border_focus,
        "font_family": font_family,
        "font_size_px": font_size_px,
        "card_bg_rgba": card_bg_rgba,
        "card_bg_hex": c["bg_card"],
        "inner_box_bg": _hex_to_rgba(c["bg_input"], alpha_input),
        "inner_box_hover": _hex_to_rgba(c["accent_gold"], 0.16),
        "border_col": _hex_to_rgba(c["border"], 0.85),
        "border_subtle": _hex_to_rgba(c["border"], 0.45),
        "gold_border": gold_border_rgba,
        "gold_glow": gold_glow_rgba,
        "text_primary": c["fg_text"],
        "text_muted": c["fg_sub"],
        "text_dim": _hex_to_rgba(c["fg_sub"], 0.70),
        "accent": c["accent_gold"],
        "accent_light": c["accent_cyan"],
        "accent_btn_bg": c["primary_btn_bg"],
        "accent_btn_fg": c["primary_btn_fg"],
        "accent_btn_hover": c.get("primary_btn_hover", c["accent_gold"]),
        "badge_bg": c.get("badge_bg", c["bg_input"]),
        "badge_border": c.get("badge_border", c["border"]),
        "scroll_bg": _hex_to_rgba(c["bg_input"], 0.4),
        "scroll_handle": _hex_to_rgba(c["accent_gold"], 0.45),
        "bg_main": c["bg_main"],
        "bg_card": c["bg_card"],
        "bg_input": c["bg_input"],
        "raw": c
    }


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

QWidget#MainCard {{
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

/* Caixa de Busca */
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

/* Barras de Rolagem Verticais e Horizontais Modernas */
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
    text-transform: uppercase;
    font-family: {t["font_family"]};
}}
"""


def get_action_tiles_data(theme: Optional[Dict[str, Any]] = None) -> list:
    """Retorna a lista de ações rápidas com ícones clássicos."""
    return [
        ("Resumo", "Alt+R", "⚡", "resumo"),
        ("Explicar Erro", "Alt+E", "🦉", "explicar"),
        ("Traduzir", "Alt+T", "🏛️", "traduzir"),
        ("Extrair OCR", "Alt+O", "📜", "extrair"),
        ("Recortar Área", "Alt+C", "⛶", "region_capture"),
        ("Mais Ações", "Alt+M", "⋯", "settings"),
    ]


def generate_menu_stylesheet(theme: Optional[Dict[str, Any]] = None) -> str:
    """
    Gera o CSS específico para menus e submenus suspensos, garantindo sincronização
    visual perfeita com o tema ativo do Metis.
    """
    t = theme or get_theme_palette()
    return f"""
QMenu {{
    background-color: {t["card_bg_hex"]};
    color: {t["text_primary"]};
    border: 1.5px solid {t["gold_border"]};
    border-radius: 12px;
    padding: 6px;
    font-family: {t["font_family"]};
    font-size: 11.5px;
}}

QMenu::item {{
    background-color: transparent;
    padding: 6px 20px 6px 14px;
    border-radius: 6px;
    color: {t["text_primary"]};
    font-size: 11.5px;
    font-weight: 500;
}}

QMenu::item:selected {{
    background-color: {t["inner_box_hover"]};
    color: {t["accent"]};
    font-weight: 600;
}}

QMenu::item:disabled {{
    color: {t["text_muted"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {t["border_subtle"]};
    margin: 5px 8px;
}}

QMenu::indicator {{
    width: 14px;
    height: 14px;
    left: 4px;
}}
"""

