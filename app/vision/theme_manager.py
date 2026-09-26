"""
Theme Manager para Metis Vision (ScreenAI) - Importa definições do Metis principal.
Carrega e aplica dinamicamente o tema ativo, opacidade, cores, tipografia e bordas
escolhidos no Metis (7 temas: Metis Oracle, Olimpo Sagrado, Valhalla & Runas, Dracula Synth, Nord Arctic, Matrix Emerald, Onyx Minimal).
"""

import sys
from pathlib import Path

# Importa definições oficiais de temas do Metis
metis_root = Path(__file__).parent.parent
if str(metis_root) not in sys.path:
    sys.path.insert(0, str(metis_root))

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

# Importa build_dynamic_qss do gui_app se disponível
try:
    from agente.ui.gui_app import build_dynamic_qss
except ImportError:
    build_dynamic_qss = None

# Alias de compatibilidade para código legado do Vision
def get_theme_palette():
    """Alias de compatibilidade - retorna cores do tema atual."""
    return get_current_theme_colors()

def generate_main_stylesheet(theme_colors: dict = None):
    """Alias de compatibilidade - gera QSS do tema."""
    return build_theme_qss()

def generate_menu_stylesheet(theme_colors: dict = None):
    """Alias de compatibilidade - gera QSS do menu."""
    if build_dynamic_qss:
        return build_dynamic_qss()
    return build_theme_qss()

# Re-exporta tudo para compatibilidade
__all__ = [
    "THEMES",
    "FONT_SIZE_MAP",
    "FONT_FAMILY_MAP",
    "get_available_themes",
    "get_current_theme_id",
    "get_current_theme_colors",
    "get_theme_palette",  # alias compatibilidade
    "get_font_size_setting",
    "get_current_font_sizes",
    "get_font_family_setting",
    "get_window_opacity_setting",
    "get_neon_glow_setting",
    "get_copy_btn_setting",
    "set_theme_preference",
    "build_theme_qss",
    "generate_main_stylesheet",  # alias compatibilidade
    "generate_menu_stylesheet",  # alias compatibilidade
]