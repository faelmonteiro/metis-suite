"""Constantes da GUI do Metis.

Ficam num modulo folha (sem imports de PyQt nem de `agente.ui.gui_app`) para
que os mixins de `agente/gui/pages/` possam usar sem criar import circular.
"""

from datetime import datetime

# Momento em que o processo carregou a GUI. Exibido no painel ("DESPERTO EM").
_INICIO_APP = datetime.now().strftime("%d/%m/%Y %H:%M")
