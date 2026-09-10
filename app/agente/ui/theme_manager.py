"""
Módulo de Gerenciamento de Temas, Aparência e Estilos do Metis.
Permite alternar paletas visuais completas, transparência/opacidade,
tamanho e família de fontes, efeitos de brilho (glow neon) e preferências visuais.
"""
from typing import Dict, List, Any
from agente.providers_manager import obter_preferencia, salvar_preferencia

# -----------------------------------------------------------------------------
# Definição dos 7 Temas Completos
# -----------------------------------------------------------------------------
THEMES: Dict[str, Dict[str, Any]] = {
    "metis_oracle": {
        "id": "metis_oracle",
        "name": "Metis Oracle",
        "icon": "🏛️",
        "category": "PADRÃO",
        "description": "Dourado âmbar com azul espacial profundo e sobriedade analítica.",
        "bg_main": "#080f1d",
        "bg_card": "#0e1a30",
        "bg_input": "#12223f",
        "border": "#1e3557",
        "border_glow": "#fad094",
        "fg_text": "#f8fafc",
        "fg_sub": "#94a3b8",
        "accent_gold": "#fad094",
        "accent_cyan": "#67e8f9",
        "user_bubble": "#193155",
        "ai_bubble": "#0e1a30",
        "primary_btn_bg": "#d97706",
        "primary_btn_hover": "#f59e0b",
        "primary_btn_fg": "#ffffff",
        "badge_bg": "#0e1c2e",
        "badge_border": "#1c2e47",
    },
    "olympus_greek": {
        "id": "olympus_greek",
        "name": "Olimpo Sagrado",
        "icon": "🏺",
        "category": "MITOLOGIA GREGA",
        "description": "Mármore e bronze de Delfos, ouro divino e a nobreza sábia de Atena.",
        "bg_main": "#17120a",
        "bg_card": "#231c11",
        "bg_input": "#302617",
        "border": "#5a4522",
        "border_glow": "#d4af37",
        "fg_text": "#fdfbf7",
        "fg_sub": "#d6d3d1",
        "accent_gold": "#d4af37",
        "accent_cyan": "#93c5fd",
        "user_bubble": "#3d301c",
        "ai_bubble": "#231c11",
        "primary_btn_bg": "#b48b18",
        "primary_btn_hover": "#d4af37",
        "primary_btn_fg": "#000000",
        "badge_bg": "#2b2111",
        "badge_border": "#5a4522",
    },
    "valhalla_nordic": {
        "id": "valhalla_nordic",
        "name": "Valhalla & Runas",
        "icon": "⚡",
        "category": "MITOLOGIA NÓRDICA",
        "description": "Fiordes glaciais, aço forjado e luzes místicas da Aurora Boreal.",
        "bg_main": "#061523",
        "bg_card": "#0a2238",
        "bg_input": "#0f2d4a",
        "border": "#184a75",
        "border_glow": "#38bdf8",
        "fg_text": "#f0fdf4",
        "fg_sub": "#a5f3fc",
        "accent_gold": "#34d399",
        "accent_cyan": "#38bdf8",
        "user_bubble": "#143e66",
        "ai_bubble": "#0a2238",
        "primary_btn_bg": "#0284c7",
        "primary_btn_hover": "#0ea5e9",
        "primary_btn_fg": "#ffffff",
        "badge_bg": "#0a2842",
        "badge_border": "#184a75",
    },
    "dracula_synth": {
        "id": "dracula_synth",
        "name": "Dracula Synth",
        "icon": "🧛",
        "category": "CYBERPUNK",
        "description": "Roxo cósmico, rosa neon vibrante e estética retrowave futurista.",
        "bg_main": "#170b29",
        "bg_card": "#23113d",
        "bg_input": "#311754",
        "border": "#5e248f",
        "border_glow": "#f472b6",
        "fg_text": "#fdf4ff",
        "fg_sub": "#f0abfc",
        "accent_gold": "#f472b6",
        "accent_cyan": "#c084fc",
        "user_bubble": "#441b75",
        "ai_bubble": "#23113d",
        "primary_btn_bg": "#9333ea",
        "primary_btn_hover": "#a855f7",
        "primary_btn_fg": "#ffffff",
        "badge_bg": "#331354",
        "badge_border": "#5e248f",
    },
    "nord_ocean": {
        "id": "nord_ocean",
        "name": "Nord Arctic",
        "icon": "❄️",
        "category": "MINIMALISTA",
        "description": "Azul glacial ártico, tons frios serenos e clareza polar cristalina.",
        "bg_main": "#0d1726",
        "bg_card": "#142238",
        "bg_input": "#1b2e4c",
        "border": "#2a4873",
        "border_glow": "#88c0d0",
        "fg_text": "#eceff4",
        "fg_sub": "#88c0d0",
        "accent_gold": "#ebcb8b",
        "accent_cyan": "#88c0d0",
        "user_bubble": "#263f66",
        "ai_bubble": "#142238",
        "primary_btn_bg": "#434c5e",
        "primary_btn_hover": "#5e81ac",
        "primary_btn_fg": "#eceff4",
        "badge_bg": "#182a44",
        "badge_border": "#2a4873",
    },
    "matrix_emerald": {
        "id": "matrix_emerald",
        "name": "Matrix Emerald",
        "icon": "🌲",
        "category": "HACKER",
        "description": "Preto e verde fosforoso com realces esmeralda luminosos de terminal.",
        "bg_main": "#031409",
        "bg_card": "#062210",
        "bg_input": "#0a3017",
        "border": "#155c2d",
        "border_glow": "#10b981",
        "fg_text": "#ecfdf5",
        "fg_sub": "#6ee7b7",
        "accent_gold": "#10b981",
        "accent_cyan": "#34d399",
        "user_bubble": "#0f421f",
        "ai_bubble": "#062210",
        "primary_btn_bg": "#059669",
        "primary_btn_hover": "#10b981",
        "primary_btn_fg": "#ffffff",
        "badge_bg": "#0a3618",
        "badge_border": "#155c2d",
    },
    "onyx_mono": {
        "id": "onyx_mono",
        "name": "Onyx Minimal",
        "icon": "🌑",
        "category": "MONOCROMÁTICO",
        "description": "Preto carvão e cinza titânio puro para foco extremo sem distrações.",
        "bg_main": "#121215",
        "bg_card": "#1a1a1f",
        "bg_input": "#24242b",
        "border": "#363642",
        "border_glow": "#e4e4e7",
        "fg_text": "#fafafa",
        "fg_sub": "#a1a1aa",
        "accent_gold": "#f4f4f5",
        "accent_cyan": "#a1a1aa",
        "user_bubble": "#2f2f38",
        "ai_bubble": "#1a1a1f",
        "primary_btn_bg": "#27272a",
        "primary_btn_hover": "#3f3f46",
        "primary_btn_fg": "#ffffff",
        "badge_bg": "#1e1e24",
        "badge_border": "#363642",
    }
}

# -----------------------------------------------------------------------------
# Escalas de Fontes
# -----------------------------------------------------------------------------
FONT_SIZE_MAP = {
    "small": {
        "label": "Pequeno (10px)",
        "base": 10,
        "chat_bubble": 10,
        "title": 11,
        "heading": 12,
        "card_title": 10,
        "card_sub": 8,
        "icon": 14,
    },
    "medium": {
        "label": "Padrão (11px)",
        "base": 11,
        "chat_bubble": 11,
        "title": 12,
        "heading": 13,
        "card_title": 11,
        "card_sub": 9,
        "icon": 16,
    },
    "large": {
        "label": "Grande (13px)",
        "base": 13,
        "chat_bubble": 13,
        "title": 14,
        "heading": 15,
        "card_title": 12,
        "card_sub": 10,
        "icon": 18,
    }
}

FONT_FAMILY_MAP = {
    "default": "sans-serif",
    "jetbrains": "'JetBrains Mono', monospace",
    "fira": "'Fira Code', monospace",
    "inter": "'Inter', sans-serif",
    "roboto": "'Roboto', sans-serif"
}


def get_available_themes() -> List[dict]:
    """Retorna a lista de todos os temas disponíveis."""
    return list(THEMES.values())


def get_current_theme_id() -> str:
    """Retorna o ID do tema atualmente selecionado nas preferências."""
    t_id = obter_preferencia("theme_id", "metis_oracle")
    if t_id not in THEMES:
        t_id = "metis_oracle"
    return t_id


def get_current_theme_colors() -> dict:
    """Retorna o dicionário de cores do tema ativo."""
    t_id = get_current_theme_id()
    return THEMES.get(t_id, THEMES["metis_oracle"])


def get_font_size_setting() -> str:
    """Retorna a configuração de tamanho de fonte ('small', 'medium', 'large')."""
    return obter_preferencia("font_size", "medium")


def get_current_font_sizes() -> dict:
    """Retorna os tamanhos de fonte calibrados para o nível ativo ('small', 'medium', 'large')."""
    sz_key = get_font_size_setting()
    return FONT_SIZE_MAP.get(sz_key, FONT_SIZE_MAP["medium"])


def get_font_family_setting() -> str:
    """Retorna a família tipográfica selecionada."""
    return obter_preferencia("font_family", "default")


def get_window_opacity_setting() -> int:
    """Retorna a opacidade da janela (70 a 100)."""
    return int(obter_preferencia("window_opacity", 98))


def get_neon_glow_setting() -> bool:
    """Retorna se o efeito de brilho/glow na borda está ativado."""
    return bool(obter_preferencia("neon_glow", True))


def get_copy_btn_setting() -> bool:
    """Retorna se o botão de cópia de código está ativado."""
    return bool(obter_preferencia("copy_btn_enabled", True))


def set_theme_preference(key: str, value: Any) -> None:
    """Salva uma preferência visual de tema."""
    salvar_preferencia(key, value)


def _hex_to_rgba(hex_str: str, alpha: float) -> str:
    """Converte hexadecimal (#070b12) para formato rgba(r, g, b, alpha)."""
    try:
        hex_clean = str(hex_str).strip().lstrip("#")
        if len(hex_clean) == 3:
            hex_clean = "".join(ch * 2 for ch in hex_clean)
        if len(hex_clean) == 6:
            r = int(hex_clean[0:2], 16)
            g = int(hex_clean[2:4], 16)
            b = int(hex_clean[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha:.2f})"
    except Exception:
        pass
    return str(hex_str)


def build_theme_qss(
    theme_id: str = None,
    font_size: str = None,
    font_family: str = None,
    neon_glow: bool = None,
    opacity: int = None
) -> str:
    """
    Gera dinamicamente a folha de estilos QSS para toda a aplicação Metis,
    aplicando as cores do tema, translucidez/opacidade em RGBA, tamanhos de fonte, efeitos de borda e inputs.
    """
    t_id = theme_id or get_current_theme_id()
    c = THEMES.get(t_id, THEMES["metis_oracle"])

    f_sz_key = font_size or get_font_size_setting()
    f_sz = FONT_SIZE_MAP.get(f_sz_key, FONT_SIZE_MAP["medium"])

    f_fam_key = font_family or get_font_family_setting()
    font_stack = FONT_FAMILY_MAP.get(f_fam_key, "sans-serif")

    has_glow = get_neon_glow_setting() if neon_glow is None else neon_glow
    border_color = c["border_glow"] if has_glow else c["border"]
    central_border = f"1.5px solid {border_color}" if has_glow else f"1px solid {c['border']}"

    op_val = get_window_opacity_setting() if opacity is None else opacity
    alpha_main = max(0.40, min(1.0, op_val / 100.0))
    alpha_card = max(0.45, min(1.0, alpha_main * 0.96))
    alpha_input = max(0.55, min(1.0, alpha_main * 0.98))
    alpha_user_bubble = max(0.35, min(1.0, alpha_main * 0.90))
    alpha_ai_bubble = max(0.25, min(1.0, alpha_main * 0.80))
    alpha_border = max(0.08, min(0.35, alpha_main * 0.25))

    bg_main_css = _hex_to_rgba(c["bg_main"], alpha_main)
    bg_card_css = _hex_to_rgba(c["bg_card"], alpha_card)
    bg_input_css = _hex_to_rgba(c["bg_input"], alpha_input)
    user_bubble_css = _hex_to_rgba(c["user_bubble"], alpha_user_bubble)
    ai_bubble_css = _hex_to_rgba(c["ai_bubble"], alpha_ai_bubble)

    return f"""
QMainWindow {{
    background: transparent;
    font-family: {font_stack};
}}

QDialog {{
    background-color: {bg_main_css};
    font-family: {font_stack};
}}

QWidget#CentralWidget {{
    background-color: {bg_main_css};
    border: {central_border};
    border-radius: 14px;
}}

QLabel {{
    color: {c['fg_text']};
    font-family: {font_stack};
}}

/* Tooltips */
QToolTip {{
    background-color: {bg_card_css};
    color: {c['fg_text']};
    border: 1px solid {c['accent_gold']};
    border-radius: 4px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 500;
    font-family: {font_stack};
}}

/* Checkboxes */
QCheckBox {{
    color: {c['fg_text']};
    font-size: {f_sz['base']}px;
    spacing: 7px;
    background: transparent;
    font-family: {font_stack};
}}

QCheckBox:hover {{
    color: {c['accent_gold']};
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1.5px solid {c['border']};
    border-radius: 4px;
    background-color: {bg_input_css};
}}

QCheckBox::indicator:hover {{
    border: 1.5px solid {c['accent_gold']};
}}

QCheckBox::indicator:checked {{
    background-color: {c['accent_gold']};
    border: 1.5px solid {c['accent_gold']};
}}

/* Sliders de Transparência / Configurações */
QSlider::groove:horizontal {{
    height: 6px;
    background: {bg_input_css};
    border: 1px solid {c['border']};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {c['accent_gold']};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 1.5px solid {c['accent_gold']};
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {c['accent_cyan']};
    border: 1.5px solid #ffffff;
}}

/* Cards de Provedores, Turnos, Temas e Informações */
QFrame.ProviderCard, QFrame.TurnCard, QFrame.ApiCard, QFrame.HelpCard, QFrame.ThemeCard {{
    background-color: {bg_card_css};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}

QFrame.ProviderCard:hover, QFrame.ApiCard:hover, QFrame.ThemeCard:hover {{
    border: 1px solid {c['accent_gold']};
}}

QFrame.ThemeCardActive {{
    background-color: {bg_input_css};
    border: 2px solid {c['accent_gold']};
    border-radius: 12px;
}}

/* Sidebar de Provedores e Configurações */
QFrame#ProviderSidebar, QFrame#ThemeSidebar {{
    background-color: {bg_card_css};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}

QPushButton.ProviderSidebarBtn {{
    background-color: {bg_input_css};
    color: {c['fg_text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 11px;
    font-weight: bold;
    text-align: left;
    font-family: {font_stack};
}}

QPushButton.ProviderSidebarBtn:hover {{
    background-color: {bg_card_css};
    color: {c['accent_gold']};
    border: 1px solid {c['accent_gold']};
}}

QPushButton.ProviderSidebarBtnActive {{
    background-color: {bg_card_css};
    color: {c['accent_gold']};
    border: 1.5px solid {c['accent_gold']};
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 11px;
    font-weight: bold;
    text-align: left;
    font-family: {font_stack};
}}

/* Status Pills & Tags */
QLabel.ProviderTag {{
    background-color: {bg_input_css};
    color: {c['accent_cyan']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

QLabel.StatusPillActive {{
    background-color: #052e16;
    color: #4ade80;
    border: 1px solid #14532d;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

QLabel.StatusPillInactive {{
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

QLabel.StatusPillWarning {{
    background-color: #451a03;
    color: #fb923c;
    border: 1px solid #7c2d12;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

/* Botões do Sistema */
QPushButton.PrimaryBtn {{
    background-color: {c['primary_btn_bg']};
    color: {c['primary_btn_fg']};
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: {f_sz['base']}px;
    font-weight: bold;
    font-family: {font_stack};
}}

QPushButton.PrimaryBtn:hover {{
    background-color: {c['primary_btn_hover']};
}}

QPushButton.SecondaryBtn {{
    background-color: {bg_input_css};
    color: {c['fg_text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: {f_sz['base']}px;
    font-weight: 500;
    font-family: {font_stack};
}}

QPushButton.SecondaryBtn:hover {{
    background-color: {bg_card_css};
    border: 1px solid {c['accent_gold']};
    color: {c['accent_gold']};
}}

QPushButton.DangerBtn {{
    background-color: #450a0a;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: bold;
    font-family: {font_stack};
}}

QPushButton.DangerBtn:hover {{
    background-color: #7f1d1d;
    color: #ffffff;
    border: 1px solid #dc2626;
}}

QPushButton.ActionChip {{
    background-color: {bg_input_css};
    color: {c['accent_cyan']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: bold;
    font-family: {font_stack};
}}

QPushButton.ActionChip:hover {{
    background-color: {bg_card_css};
    border: 1px solid {c['accent_cyan']};
    color: #ffffff;
}}

QPushButton.ModelBtn {{
    background-color: {bg_input_css};
    color: {c['fg_text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: {f_sz['base']}px;
    font-weight: 500;
    text-align: left;
    font-family: {font_stack};
}}

QPushButton.ModelBtn:hover {{
    background-color: {bg_card_css};
    border: 1.5px solid {c['accent_gold']};
    color: {c['accent_gold']};
}}

QPushButton.ModelBtnActive {{
    background-color: {user_bubble_css};
    color: {c['accent_gold']};
    border: 2px solid {c['accent_gold']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: {f_sz['base']}px;
    font-weight: bold;
    text-align: left;
    font-family: {font_stack};
}}

/* Badge do Oráculo Ativo */
QLabel#OracleActiveBadge, QLabel.OracleActiveBadge {{
    background-color: {c['badge_bg']};
    color: {c['accent_cyan']};
    border: 1.5px solid {c['badge_border']};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: {f_sz['base']}px;
    font-weight: bold;
    font-family: {font_stack};
}}

/* Inputs de Texto */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {bg_input_css};
    color: {c['fg_text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: {max(5, f_sz['base'] - 6)}px 10px;
    font-size: {f_sz['base']}px;
    min-height: {f_sz['base'] + 10}px;
    font-family: {font_stack};
    selection-background-color: {c['accent_gold']};
    selection-color: #000000;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {c['accent_gold']};
    background-color: {bg_input_css};
}}

/* Barra de Digitação Principal / Prompt Input (Levemente aumentada para digitação confortável) */
QTextEdit#PromptInput, QPlainTextEdit#PromptInput, QLineEdit#PromptInput {{
    font-size: {f_sz['base'] + 1.5}px;
    padding: 6px 10px;
    line-height: 1.35;
}}

/* ComboBox */
QComboBox {{
    background-color: {bg_input_css};
    color: {c['fg_text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: {max(4, f_sz['base'] - 7)}px 10px;
    font-size: {f_sz['base']}px;
    min-height: {f_sz['base'] + 10}px;
    font-family: {font_stack};
}}

QComboBox:hover, QComboBox:focus {{
    border: 1.5px solid {c['accent_gold']};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {bg_card_css};
    color: {c['fg_text']};
    border: 1px solid {c['border']};
    selection-background-color: {c['accent_gold']};
    selection-color: #000000;
}}

/* ScrollBars Customizadas e Elegantes */
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {c['border']};
    min-height: 25px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c['accent_gold']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {c['border']};
    min-width: 25px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {c['accent_gold']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Informações e Detalhes do Dashboard */
QFrame#InfoPanel {{
    background-color: {bg_card_css};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}

QFrame#CommandBar {{
    background-color: {bg_card_css};
    border: 1px solid {c['border']};
    border-radius: 8px;
}}

QPushButton.CommandChip {{
    background-color: {bg_input_css};
    color: {c['accent_cyan']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 500;
}}

QPushButton.CommandChip:hover {{
    background-color: {bg_card_css};
    border: 1px solid {c['accent_cyan']};
    color: #ffffff;
}}

/* Scroll do Chat & Container de Mensagens (100% Translúcidos) */
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget, QWidget#ChatContainer {{
    background: transparent;
    background-color: transparent;
    border: none;
}}

/* Balões de Chat (Pergunta Translúcida com Borda Sutil e Resposta Flutuante) */
QFrame.UserBubble {{
    background-color: {user_bubble_css};
    border: 1px solid rgba(255, 255, 255, {alpha_border:.2f});
    border-radius: 12px;
    padding: 6px 12px;
    margin: 0px;
}}

QFrame.AIBubble {{
    background-color: {ai_bubble_css};
    border: 1px solid rgba(255, 255, 255, {max(0.04, alpha_border * 0.5):.2f});
    border-radius: 10px;
    padding: 6px 10px;
    margin: 0px;
}}

/* Blocos de Comando e Código no Chat */
QFrame.CommandBox {{
    background-color: {bg_card_css};
    border: 1px solid rgba(250, 208, 148, {min(0.8, alpha_border * 2.0):.2f});
    border-radius: 8px;
    padding: 6px 10px;
    margin-top: 4px;
}}

/* Botões de Ação por Ícone Translúcidos */
QPushButton.IconActionBtn {{
    background-color: transparent;
    color: {c['fg_sub']};
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 13px;
    min-width: 20px;
    min-height: 20px;
}}

QPushButton.IconActionBtn:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    color: {c['accent_gold']};
}}

/* Barra de Anexo Visual */
QFrame#AttachmentChip {{
    background-color: {bg_input_css};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 3px 8px;
}}

/* Menus Suspensos / Opções (QMenu) Perfeitamente Integrados com o Tema */
QMenu {{
    background-color: {bg_card_css};
    color: {c['fg_text']};
    border: 1px solid {c['accent_gold']};
    border-radius: 8px;
    padding: 4px;
    font-size: {f_sz['base']}px;
    font-family: {font_stack};
}}

QMenu::item {{
    background-color: transparent;
    color: {c['fg_text']};
    padding: 6px 14px 6px 10px;
    border-radius: 6px;
    font-size: {f_sz['base']}px;
    font-weight: 500;
    font-family: {font_stack};
    margin: 1px 2px;
}}

QMenu::item:selected {{
    background-color: {c['accent_gold']};
    color: #000000;
    font-weight: bold;
}}

QMenu::item:disabled {{
    color: {c['fg_sub']};
    background-color: transparent;
}}

QMenu::separator {{
    height: 1px;
    background-color: {c['border']};
    margin: 4px 6px;
}}

/* Popup de Comandos Slash (/) Estilo CLI Dinâmico e Integrado ao Tema */
QFrame#SlashCommandPopup {{
    background-color: {bg_card_css};
    border: 1.5px solid {c['accent_gold']};
    border-radius: 8px;
}}

QListWidget#SlashCommandList {{
    background: transparent;
    border: none;
    outline: none;
    font-family: {font_stack};
    font-size: {f_sz['base']}px;
}}

QListWidget#SlashCommandList::item {{
    padding: 3px 8px;
    border-radius: 4px;
    color: {c['fg_text']};
    font-family: {font_stack};
    font-size: {f_sz['base']}px;
    min-height: 18px;
    margin: 1px 2px;
}}

QListWidget#SlashCommandList::item:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    color: {c['accent_gold']};
}}

QListWidget#SlashCommandList::item:selected,
QListWidget#SlashCommandList::item:selected:!active,
QListWidget#SlashCommandList::item:selected:active {{
    background-color: {c['accent_gold']};
    color: #000000;
    font-weight: bold;
}}
"""
