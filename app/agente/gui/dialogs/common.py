"""Utilitario compartilhado por todas as janelas modais.

Fica num modulo folha (so depende do Qt) para que os dialogs possam ser
importados sem puxar `agente.ui.gui_app` — que por sua vez reexporta os
dialogs. Sem esta separacao haveria import circular.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
)

from typing import Optional

def _constrain_dialog_to_parent(dialog: QDialog, pref_w: int, pref_h: int, parent: Optional[QWidget] = None):
    """Garante que qualquer janela modal respeite estritamente as bordas e dimensões da janela principal."""
    if parent is not None:
        try:
            p_w = max(380, parent.width() - 36)
            p_h = max(340, parent.height() - 36)
        except Exception:
            p_w, p_h = 720, 540
    else:
        p_w, p_h = 720, 540
    target_w = min(pref_w, p_w)
    target_h = min(pref_h, p_h)
    dialog.resize(target_w, target_h)
    dialog.setMaximumSize(p_w, p_h)
    dialog.setMinimumSize(min(360, target_w), min(280, target_h))
