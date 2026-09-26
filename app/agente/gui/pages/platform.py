"""Transversal: ciclo de vida da janela, tema, opacidade e eventos do Qt/Hyprland.

Nao monta pagina. Serve a todas elas, e e o unico que implementa os
overrides do Qt (`eventFilter`, `keyPressEvent`, `resizeEvent`, `closeEvent`,
`showEvent`) — por isso precisa ficar antes de `QMainWindow` nas bases.

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QFrame,
    QToolTip,
)

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QEvent,
)

from PyQt6.QtGui import (
    QFont,
    QColor,
    QPalette,
    QFontMetrics,
)

import json, os, shutil, subprocess

from agente import config
from agente.gui.theme_bridge import (
    get_current_theme_colors,
    get_window_opacity_setting,
    build_dynamic_qss,
)
from agente.history import HistoryManager
from agente.providers_manager import (
    obter_preferencia,
    salvar_preferencia,
)
from agente.utils import (
    hyprctl,
    mover_janela_canto_superior_direito,
    logger,
)
from datetime import datetime

class PlatformMixin:
    """Ciclo de vida da janela e integracao com a area de trabalho.

    Cria a janela, aplica tema e opacidade, centraliza/maximiza, e trata os
    eventos do Qt (resize, close, filtro de evento) e do Hyprland (posicao,
    alpha). Tambem implementa `toggle_or_focus`, o contrato usado pelo launcher
    de instancia unica.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("METIS • Oracle System")
        self.setMinimumSize(780, 480)

        saved_size = obter_preferencia("window_size")
        if saved_size and isinstance(saved_size, list) and len(saved_size) == 2:
            w = min(1000, max(780, int(saved_size[0])))
            h = min(680, max(480, int(saved_size[1])))
            self.resize(w, h)
        else:
            self.resize(860, 550)

        # Sessão & Histórico
        nome_sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.history_manager = HistoryManager(nome_sessao)
        self.current_service = self.carregar_servico_padrao()
        self.active_worker = None
        self.query_queue = []

        # Anexos pendentes
        self.current_attachment_path = None
        self.current_media_paths = []
        self.current_attachment_text_context = ""

        self.cards = []
        self.selected_card_index = 0

        self.oracle_buttons = []
        self.selected_oracle_index = 0
        self.last_extracted_commands = []

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.init_ui()
        self.apply_theme()
        self.refresh_telemetry()
        self.select_card(0)

        self.installEventFilter(self)
        self.prompt_input.installEventFilter(self)

        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.refresh_telemetry)
        self.telemetry_timer.start(6000)

        # Foco automático imediato no campo de texto ao iniciar
        QTimer.singleShot(50, self.prompt_input.setFocus)

    def sync_window_opacity(self, opacity_val: int):
        """Aplica a opacidade e translucidez em múltiplos níveis (Qt, X11 e compositor Hyprland/Wayland)."""
        alpha = max(0.4, min(1.0, opacity_val / 100.0))
        try:
            self.setWindowOpacity(alpha)
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

        # Sincronização nativa direta com o Hyprland
        if shutil.which("hyprctl"):
            try:
                pid = os.getpid()
                clients_res = subprocess.run(["hyprctl", "clients", "-j"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.3)
                if clients_res.returncode == 0 and clients_res.stdout.strip():
                    for cl in json.loads(clients_res.stdout):
                        if cl.get("pid") == pid or "METIS" in cl.get("title", ""):
                            addr = cl.get("address", "")
                            if addr:
                                hyprctl(f"setprop address:{addr} alpha {alpha:.2f} lock")
                                hyprctl(f"setprop address:{addr} activealpha {alpha:.2f} lock")
                                hyprctl(f"setprop address:{addr} inactivealpha {max(0.4, alpha - 0.08):.2f} lock")
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    def apply_theme(self):
        self.setStyleSheet(build_dynamic_qss())
        opacity = get_window_opacity_setting()
        self.sync_window_opacity(opacity)
        c = get_current_theme_colors()
        QToolTip.setFont(QFont("Sans Serif", 9, QFont.Weight.Medium))
        pal = QApplication.palette()
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(c.get("bg_card", "#080f1e")))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor(c.get("fg_text", "#ffffff")))
        QApplication.setPalette(pal)

        # Atualiza a caixinha de comandos slash em tempo real
        if hasattr(self, "prompt_input") and hasattr(self.prompt_input, "slash_popup") and self.prompt_input.slash_popup:
            self.prompt_input.slash_popup.update_theme_style()
        if hasattr(self, "chat_input") and hasattr(self.chat_input, "slash_popup") and self.chat_input.slash_popup:
            self.chat_input.slash_popup.update_theme_style()

        # Atualiza o subtítulo e título do cabeçalho
        if hasattr(self, "lbl_main_sub") and self.lbl_main_sub:
            self.lbl_main_sub.setStyleSheet("color: #75c45a; font-weight: bold; background: transparent; letter-spacing: 0.5px;")
        if hasattr(self, "lbl_main_title") and self.lbl_main_title:
            self.lbl_main_title.setStyleSheet(f"color: {c['accent_gold']}; font-weight: bold; background: transparent;")

    def showEvent(self, event):
        super().showEvent(event)
        self._on_page_changed(self.stack.currentIndex())
        self.apply_theme()
        QTimer.singleShot(60, self.centralizar_janela)
        QTimer.singleShot(220, self.centralizar_janela)

    def centralizar_janela(self):
        """Garante que a janela abra perfeitamente no centro da tela em modo flutuante."""
        try:
            w_target, h_target = 860, 550
            self.resize(w_target, h_target)
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = max(geo.left() + 20, geo.left() + (geo.width() - w_target) // 2)
                y = max(geo.top() + 20, geo.top() + (geo.height() - h_target) // 2)
                self.move(x, y)

            opacity = get_window_opacity_setting()
            self.sync_window_opacity(opacity)

            if getattr(config, "HYPRLAND_ENABLED", False) or shutil.which("hyprctl"):
                pid = os.getpid()
                clients_res = subprocess.run(["hyprctl", "clients", "-j"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.4)
                if clients_res.returncode == 0:
                    clients = json.loads(clients_res.stdout)
                    metis_win = next((c for c in clients if c.get("pid") == pid), None)
                    if metis_win:
                        addr = metis_win.get("address")
                        if addr:
                            hyprctl(f"dispatch moveoutofgroup address:{addr}")
                            hyprctl(f"dispatch setfloating address:{addr}")
                            hyprctl(f"dispatch resizewindowpixel exact {w_target} {h_target},address:{addr}")
                            hyprctl(f"dispatch centerwindow address:{addr}")
                            return

                hyprctl("dispatch setfloating")
                hyprctl(f"dispatch resizewindowpixel exact {w_target} {h_target}")
                hyprctl("dispatch centerwindow")
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    def toggle_or_focus(self):
        """Alterna a visibilidade ou foca a janela se uma segunda instância for chamada (ex: Super + R)."""
        is_active_hypr = False
        addr_metis = None

        if shutil.which("hyprctl"):
            try:
                active_res = subprocess.run(["hyprctl", "activewindow", "-j"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.3)
                if active_res.returncode == 0 and active_res.stdout.strip():
                    active_info = json.loads(active_res.stdout)
                    title = active_info.get("title", "")
                    if "METIS" in title or "Metis" in title:
                        is_active_hypr = True

                clients_res = subprocess.run(["hyprctl", "clients", "-j"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.3)
                if clients_res.returncode == 0 and clients_res.stdout.strip():
                    for c in json.loads(clients_res.stdout):
                        if "METIS" in c.get("title", "") or "Metis" in c.get("title", ""):
                            addr_metis = c.get("address", "")
                            break
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

        # Se já estiver visível e ativa (usuário apertou Super+R na janela atual), oculta a janela
        if (self.isVisible() and self.isActiveWindow()) or is_active_hypr:
            self.hide()
            return

        # Se estiver oculta ou em segundo plano, restaura e foca
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()

        if hasattr(self, "prompt_input"):
            self.prompt_input.setFocus()

        if addr_metis:
            hyprctl(f"dispatch focuswindow address:{addr_metis}")

    def _on_page_changed(self, index: int):
        """Garante que o campo de digitação receba foco automático ao trocar de página e fecha popups residuais."""
        if hasattr(self, "prompt_input") and self.prompt_input.slash_popup:
            self.prompt_input.slash_popup.hide()
        if hasattr(self, "chat_input") and self.chat_input.slash_popup:
            self.chat_input.slash_popup.hide()

        if index == 0:
            QTimer.singleShot(30, self.prompt_input.setFocus)
        elif index == 1:
            QTimer.singleShot(30, self.chat_input.setFocus)
        elif index == 2:
            QTimer.singleShot(30, self.search_input.setFocus)

    def _on_command_finished(self, comando: str, saida: str):
        """Callback quando comando /executar termina em background thread."""
        resposta_formatada = f"⚡ **Comando Executado:** `{comando}`\n\n> 💡 **Resultado:** {saida}"
        self.add_chat_bubble("assistant", resposta_formatada)
        self.history_manager.adicionar_mensagem("user", f"/executar {comando}")
        self.history_manager.adicionar_mensagem("assistant", resposta_formatada)
        self.refresh_telemetry()

    def _on_command_error(self, error: str):
        """Callback quando comando /executar falha."""
        resposta_erro = f"❌ **Erro ao executar comando:**\n```\n{error}\n```"
        self.add_chat_bubble("assistant", resposta_erro)
        self.history_manager.adicionar_mensagem("assistant", resposta_erro)
        self.refresh_telemetry()

    def mover_para_canto_superior_direito(self):
        """Move a janela flutuante perfeitamente para o canto superior direito da tela ao gerar resposta."""
        try:
            target_x, target_y = mover_janela_canto_superior_direito(self.width(), self.height())
            
            # Sincroniza posição nativa do widget Qt caso aplicável
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                if target_x is None or target_y is None:
                    target_x = max(geo.left() + 10, geo.left() + geo.width() - self.width() - 10)
                    target_y = max(geo.top() + 14, geo.top() + 14)
                self.move(target_x, target_y)
        except Exception as _silent_e:
            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            # 0. Interrupção instantânea da IA se ativa via ESC ou Ctrl+C
            if self.active_worker and self.active_worker.isRunning():
                if event.key() == Qt.Key.Key_Escape:
                    self.stop_ai_generation()
                    return True
                if event.key() == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    # Se houver texto selecionado no input, permite a cópia de texto normal
                    if hasattr(source, "textCursor") and source.textCursor().hasSelection():
                        pass
                    else:
                        self.stop_ai_generation()
                        return True

            # 1. Navegação no Dashboard Principal (Página 0)
            if self.stack.currentIndex() == 0:
                if event.key() == Qt.Key.Key_Down:
                    self.navigate_menu(1)
                    return True
                elif event.key() == Qt.Key.Key_Up:
                    self.navigate_menu(-1)
                    return True
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    txt = self.prompt_input.text().strip()
                    if not txt:
                        if 0 <= self.selected_card_index < len(self.cards):
                            self.handle_menu_action(self.cards[self.selected_card_index].code)
                            return True
                elif event.text() and source != self.prompt_input and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.prompt_input.setFocus()

            # 2. Navegação na Página de Oráculos & Modelos (Página 3)
            elif self.stack.currentIndex() == 3:
                if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Tab, Qt.Key.Key_J, Qt.Key.Key_L):
                    self.navigate_oracles(1)
                    return True
                elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Left, Qt.Key.Key_Backtab, Qt.Key.Key_K, Qt.Key.Key_H):
                    self.navigate_oracles(-1)
                    return True
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                    if 0 <= self.selected_oracle_index < len(self.oracle_buttons):
                        self.oracle_buttons[self.selected_oracle_index].click()
                        return True

        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        # 1. Ctrl + C global para interromper geração da IA
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if self.active_worker and self.active_worker.isRunning():
                self.stop_ai_generation()
                return

        # 2. Escape para interromper IA ou voltar ao Dashboard
        if event.key() == Qt.Key.Key_Escape:
            if self.active_worker and self.active_worker.isRunning():
                self.stop_ai_generation()
                return
            if self.stack.currentIndex() != 0:
                self.stack.setCurrentIndex(0)
            else:
                self.close()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "chat_scroll") and hasattr(self, "chat_layout"):
            max_limit = min(620, max(380, int(self.chat_scroll.viewport().width() * 0.72)))
            for i in range(self.chat_layout.count()):
                item = self.chat_layout.itemAt(i)
                if item and item.widget():
                    for user_b in item.widget().findChildren(QFrame):
                        if user_b.property("class") == "UserBubble":
                            lbl = user_b.findChild(QLabel)
                            if lbl and hasattr(lbl, "_raw_text"):
                                fm = QFontMetrics(lbl.font())
                                linhas = lbl._raw_text.split("\n")
                                max_linha_w = max(fm.horizontalAdvance(l) for l in linhas) if linhas else 100
                                if max_linha_w + 30 <= max_limit:
                                    user_b.setFixedWidth(max_linha_w + 30)
                                else:
                                    user_b.setMaximumWidth(max_limit)
                                    user_b.setMinimumWidth(360)

    def closeEvent(self, event):
        if not self.isMaximized() and not self.isFullScreen():
            w = min(1000, max(780, self.width()))
            h = min(680, max(480, self.height()))
            salvar_preferencia("window_size", [w, h])
        if hasattr(self, "chk_web"):
            salvar_preferencia("web_search_enabled", self.chk_web.isChecked())
        super().closeEvent(event)
