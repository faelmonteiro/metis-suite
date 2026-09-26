"""Ponto de entrada da GUI PyQt6 do Metis.

Instancia unica via QLocalSocket, icone e loop de eventos. Vive separado de
`main_window.py` para que a janela possa ser importada sem arrastar o
`sys.excepthook` global nem a criacao do QApplication.
"""

from PyQt6.QtWidgets import QApplication

from PyQt6.QtGui import QIcon

import sys

from agente import config
from agente.gui.main_window import MetisMainWindow
from agente.utils import logger

def main():
    def global_excepthook(exc_type, exc_value, exc_traceback):
        import traceback
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"Exceção não tratada capturada pelo Metis: {err_msg}")
        print(f"\n[AVISO METIS] Exceção capturada: {err_msg}", file=sys.stderr)

    sys.excepthook = global_excepthook

    app = QApplication(sys.argv)
    app.setApplicationName("Metis Oracle System")
    app.setDesktopFileName("metis")

    # Verificação de instância única via QLocalSocket (impede janelas duplicadas ao teclar Super + R)
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket

    socket_name = "metis_oracle_single_instance"
    socket = QLocalSocket()
    socket.connectToServer(socket_name)
    if socket.waitForConnected(200):
        # Outra instância do Metis já está em execução: envia sinal para alternar/focar e encerra a nova
        socket.write(b"toggle\n")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        sys.exit(0)

    # Limpa eventual socket órfão de execução anterior
    QLocalServer.removeServer(socket_name)
    server = QLocalServer()
    if not server.listen(socket_name):
        logger.warning(f"Não foi possível registrar QLocalServer no socket {socket_name}")

    icon_path = config.PROJECT_ROOT / "assets" / "icons" / "icon_128x128.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MetisMainWindow()

    def on_new_connection():
        client = server.nextPendingConnection()
        if client:
            def handle_read():
                try:
                    bytes(client.readAll()).decode("utf-8").strip()
                except Exception:
                    pass
                client.disconnectFromServer()
                window.toggle_or_focus()

            client.readyRead.connect(handle_read)

    server.newConnection.connect(on_new_connection)
    app.aboutToQuit.connect(lambda: QLocalServer.removeServer(socket_name))

    window.show()
    sys.exit(app.exec())
if __name__ == "__main__":
    main()
