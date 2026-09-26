"""Ponte entre o tema do Metis e a GUI PyQt6.

`build_theme_qss` vive em `agente/ui/theme_manager.py` (que serve tanto a
TUI quanto a GUI). Este modulo expoe o nome que a GUI usa e avalia o QSS
global uma unica vez, no import.

Cuidado ao mover este arquivo: `agente/ui/gui_app.py` reexporta
`build_dynamic_qss` porque `vision/theme_manager.py` importa esse nome de la
(dentro de um `try/except ImportError` — se sumir, o Vision perde o QSS do
menu em silencio). `QSS_STYLE` tambem e avaliado no import: se
`build_dynamic_qss` levantar, "import agente.ui.gui_app" quebra para todos.
"""

from agente.ui.theme_manager import (
    FONT_SIZE_MAP,
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

__all__ = [
    "build_theme_qss", "build_dynamic_qss", "get_system_theme_colors",
    "get_current_theme_colors", "get_current_font_sizes", "get_current_theme_id",
    "get_available_themes", "get_font_family_setting", "get_font_size_setting",
    "get_window_opacity_setting", "get_copy_btn_setting", "get_neon_glow_setting",
    "set_theme_preference", "FONT_SIZE_MAP", "QSS_STYLE",
]


def build_dynamic_qss(*args, **kwargs) -> str:
    """Gera o estilo QSS da interface dinamicamente conforme o tema ativo e configurações."""
    return build_theme_qss(*args, **kwargs)


# Reexporta tambem os getters de tema e preferencias: assim os mixins de
# `agente/gui/pages/` nunca importam de `agente/ui/`, e esta ponte e a unica
# fronteira entre a GUI PyQt6 e o tema compartilhado com a TUI.
def get_system_theme_colors() -> dict:
    """Paleta de cores do tema ativo. Nome publico usado pela janela e por
    `agente/main.py`; mantido como funcao para nao mudar a assinatura."""
    return get_current_theme_colors()


QSS_STYLE = build_dynamic_qss()
