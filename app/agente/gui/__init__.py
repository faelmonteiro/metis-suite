"""Interface grafica PyQt6 do Metis (janela principal, paginas, widgets e dialogs).

O pacote `agente/ui/` e a interface de TERMINAL (TUI: cores ANSI, painel,
completer). A GUI vive aqui, sob `agente/gui/`.

`agente/ui/gui_app.py` permanece como camada de compatibilidade e reexporta
todos os nomes publicos a partir daqui.
"""
import os

# Fica aqui, e nao no shim, porque este `__init__` roda antes do corpo de
# qualquer submodule de `agente/gui/`. Assim tanto `import
# agente.ui.gui_app` quanto `import agente.gui.main_window` pegam a config, e o
# Qt ja a ve no primeiro import de PyQt6. No shim original ela vivia no topo
# de `gui_app.py`; manter so ali quebrava qualquer import direto.
os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")
