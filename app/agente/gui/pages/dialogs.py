"""Transversal: abrir os dialogos modais e reagir ao retorno deles.

Nao monta widget. Ficou separado porque e o unico dominio cuja superficie
inteira e "mostrar algo e tratar a resposta" — sem estado visual proprio.

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import QMessageBox

from agente.gui.dialogs.agent_options import ModernAgentOptionsDialog
from agente.gui.dialogs.apis import ModernApisDialog
from agente.gui.dialogs.info import (
    ModernHelpDialog,
    ModernStatusDialog,
)
from agente.utils import logger

class DialogsMixin:
    """Abertura dos dialogos modais e do que acontece depois deles.

    Cada metodo mostra um dialogo e trata o retorno. Ficou separado de `chat.py`
    porque e o unico dominio que nao monta widget: so instancia dialogo e reage
    ao resultado.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def show_apis_dialog(self):
        dlg = ModernApisDialog(self)
        dlg.keys_saved.connect(self.on_apis_updated)
        dlg.exec()

    def on_apis_updated(self):
        self.refresh_telemetry()
        self.rebuild_oracle_buttons()
        try:
            self.carregar_servico_padrao()
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
        QMessageBox.information(self, "Metis", "Chaves de API atualizadas e salvas com sucesso no .env!")

    def show_agent_options_dialog(self):
        dlg = ModernAgentOptionsDialog(self)
        dlg.options_saved.connect(self.on_agent_options_updated)
        dlg.exec()

    def on_agent_options_updated(self):
        self.refresh_telemetry()

    def show_help_dialog(self):
        dlg = ModernHelpDialog(self)
        dlg.exec()

    def show_status_dialog(self):
        dlg = ModernStatusDialog(self.history_manager, self.current_service, self)
        dlg.exec()

    def export_current_session(self):
        try:
            from agente.sessions.command_handlers import handle_exportar
            handle_exportar(self.history_manager)
            QMessageBox.information(self, "Exportar", "Sessão exportada com sucesso para a pasta 'exports' no projeto!")
        except Exception as e:
            QMessageBox.warning(self, "Exportar", f"Erro ao exportar: {e}")
