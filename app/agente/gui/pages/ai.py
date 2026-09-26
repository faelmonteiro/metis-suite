"""Transversal: a consulta a LLM, a fila e o cancelamento.

Nao monta pagina. Atende o chat, mas vale a pena separada: e onde mora a
logica de streaming, fila e retry, que nao tem nada de visual e e o trecho
mais provavel de ganhar provider novo.

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
)

from PyQt6.QtCore import QTimer

from PyQt6.QtGui import QFont

import time, webbrowser

from agente import config
from agente.gui.text.commands import (
    copiar_para_area_de_transferencia,
    resolver_comando_instantaneo,
)

# Comandos slash que nao recebem argumento: o texto bate exatamente e o metodo
# indicado roda. A ordem do dicionario nao importa porque as chaves sao exatas
# e nenhuma e prefixo de outra.
_COMANDOS_DIRETOS = {
    "/api": "show_apis_dialog",
    "/apis": "show_apis_dialog",
    "/chaves": "show_apis_dialog",
    "/key": "show_apis_dialog",
    "/keys": "show_apis_dialog",
    "/opcoes": "show_agent_options_dialog",
    "/opcao": "show_agent_options_dialog",
    "/opção": "show_agent_options_dialog",
    "/opções": "show_agent_options_dialog",
    "/avancado": "show_agent_options_dialog",
    "/avançado": "show_agent_options_dialog",
    "/agent": "show_agent_options_dialog",
    "/restaurar": "show_restore_server_dialog",
    "/restore": "show_restore_server_dialog",
    "/reativar": "show_restore_server_dialog",
    "/ajuda": "show_help_dialog",
    "/help": "show_help_dialog",
    "/status": "show_status_dialog",
    "/oraculo": "open_oracles_page",
    "/oraculos": "open_oracles_page",
    "/provedor": "open_oracles_page",
    "/provedores": "open_oracles_page",
    "/tema": "open_appearance_page",
    "/temas": "open_appearance_page",
    "/iris": "open_appearance_page",
    "/manto": "open_appearance_page",
    "/aparencia": "open_appearance_page",
    "/theme": "open_appearance_page",
    "/themes": "open_appearance_page",
    "/estilo": "open_appearance_page",
    "/estilos": "open_appearance_page",
    "/retry": "retry_last_query",
    "/repetir": "retry_last_query",
}

from agente.gui.widgets.checklist import AgentChecklistWidget
from agente.gui.workers import (
    AIWorker,
    CommandWorker,
)
from agente.history import HistoryManager
from agente.providers_manager import (
    obter_modelos_provedor,
    obter_servidor_customizado,
)
from agente.services import (
    searxng_service,
    ollama_service,
)
from agente.utils import (
    sanitizar_nome_sessao,
    limitar_texto,
    logger,
)
from datetime import datetime
from pathlib import Path

# Texto que o balao recebe quando a geracao para. Fica em uma constante porque
# duas coisas dependem dele: o aviso exibido e a checagem de idempotencia — se
# o texto mudar em um lugar e nao no outro, dois cliques em Parar passam a
# gerar dois avisos.
MARCA_DE_INTERROPCAO = "[Geração interrompida pelo usuário]"
GLIFO_DE_PARADO = "⏹️"
# Mesma escala do cronometro vivo, trocando so a cor. A folha de estilo estava
# duplicada em dois metodos, entao mudar a escala num so nao mudaria no outro.
ESTILO_DO_ROTULO_PARADO = "color: #ef4444; background: transparent; font-size: 8pt;"


class AiMixin:
    """Consulta a LLM, fila e cancelamento.

    Monta a query, envia para o `AIWorker`, gerencia a fila, para a geracao e
    re-tenta. Tambem cobre a busca direta via SearXNG, que nao passa pela LLM.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    # Fonte unica dos sinais do worker. Conectar e desconectar leem os dois
    # esta tabela; quando as listas eram separadas, `search_started` entrou na
    # de conectar e nunca entrou na de desconectar.
    _SINAIS_DO_WORKER = (
        ("chunk_received", "_on_chunk"),
        ("search_started", "_on_search_started"),
        ("tool_started", "_on_tool_started"),
        ("tool_finished", "_on_tool_finished"),
        ("finished_response", "_on_finished"),
        ("error_occurred", "_on_error"),
    )

    def send_chat_message(self):
        msg = self.chat_input.text().strip()
        if not msg and not self.current_attachment_path:
            return
        self.chat_input.clear()
        self.process_text_command_or_query(msg)

    def process_text_command_or_query(self, text: str):
        """Despacha `text`: atalho de menu, comando slash, ou consulta a IA.

        Antes era uma cadeia de 20 `if` de 240 linhas. A ordem dos testes
        abaixo e a ORIGINAL, linha a linha — as tabelas so substituem blocos
        `in (...)` por lookup, o que e seguro porque as chaves sao exatas e
        nenhuma e prefixo de outra.
        """
        if self._atalho_do_dashboard(text):
            return

        if self._copiar_comando_extraido(text):
            return

        l_text = text.lower().strip()

        if l_text.startswith("/executar ") or l_text.startswith("/run "):
            self._cmd_executar(text)
            return

        if l_text in ("/executar", "/run"):
            self.chat_input.setText("/executar ")
            self.chat_input.setFocus()
            return

        if l_text.startswith("/web "):
            self._cmd_web(text)
            return

        if l_text in _COMANDOS_DIRETOS:
            getattr(self, _COMANDOS_DIRETOS[l_text])()
            return

        if l_text.startswith("/sessao") or l_text == "/sessoes":
            self._cmd_sessao(text)
            return

        if l_text.startswith(("/novo", "/new", "/nova")):
            self._cmd_novo(text)
            return

        if l_text.startswith("/exportar"):
            self.export_current_session()
            return

        if l_text in ("/limpar", "/clear"):
            self.history_manager.limpar()
            self.clear_chat_view()
            self.refresh_telemetry()
            return

        if l_text in ("/deletar_tudo", "/purificar"):
            self.handle_menu_action("5")
            return

        if l_text == "/deletar_sessao":
            self._cmd_deletar_sessao()
            return

        if l_text.startswith("/modelo"):
            self._cmd_modelo(text)
            return

        if l_text.startswith("/arquivo"):
            self._cmd_arquivo(text)
            return

        # 3. Consulta de IA Normal
        self.stack.setCurrentIndex(1)
        self.start_ai_query(text, forcar_web=self.chk_web.isChecked())

    def _atalho_do_dashboard(self, text: str) -> bool:
        """No painel inicial, 1..6 disparam os cartoes do menu."""
        if self.stack.currentIndex() != 0:
            return False
        if text not in ["1", "2", "3", "4", "5", "6", "01", "02", "03", "04", "05", "06"]:
            return False
        self.handle_menu_action(text)
        return True

    def _copiar_comando_extraido(self, text: str) -> bool:
        """No chat, um numero copia o comando da lista extraida na resposta.

        Numero fora da faixa e erro do usuario, nao comando: mostra aviso e
        nao consome a entrada. O feedback vai no placeholder do campo em vez
        de poluir a conversa com HTML, e volta sozinho em 3,5s.
        """
        if self.stack.currentIndex() != 1:
            return False

        l_t = text.lower().strip()
        if l_t.isdigit():
            cmd_index = int(l_t)
        elif l_t.startswith("c ") and l_t[2:].strip().isdigit():
            cmd_index = int(l_t[2:].strip())
        elif l_t.startswith("copiar ") and l_t[7:].strip().isdigit():
            cmd_index = int(l_t[7:].strip())
        elif l_t.startswith("/c ") and l_t[3:].strip().isdigit():
            cmd_index = int(l_t[3:].strip())
        else:
            return False

        comandos = getattr(self, "last_extracted_commands", None)
        if not comandos:
            return False

        orig_ph = self.chat_input.placeholderText()
        if 1 <= cmd_index <= len(comandos):
            tipo, conteudo, desc = comandos[cmd_index - 1]
            copiar_para_area_de_transferencia(conteudo)
            aviso = f"✔ Comando [{cmd_index:02d}] copiado! Cole com Ctrl+Shift+V no terminal."
        else:
            aviso = f"⚠️ Número inválido ({cmd_index}). Escolha entre 1 e {len(comandos)}."

        self.chat_input.setPlaceholderText(aviso)
        QTimer.singleShot(3500, lambda: self.chat_input.setPlaceholderText(orig_ph))
        return True

    def _cmd_executar(self, text: str):
        """`/executar <cmd>`: tenta o atalho instantaneo, senao delega a IA.

        O atalho direto roda em thread (`CommandWorker`) para nao travar a UI.
        Sem atalho, vira um prompt que autoriza explicitamente a execucao, para
        a IA usar `executar_comando`.
        """
        cmd_pedido = text.split(maxsplit=1)[1].strip()
        self.stack.setCurrentIndex(1)

        # Execução Instantânea (0.001s) para comandos ou ações comuns
        cmd_direto = resolver_comando_instantaneo(cmd_pedido)
        if cmd_direto:
            self.mover_para_canto_superior_direito()
            self.add_chat_bubble("user", f"/executar {cmd_pedido}")

            # Executa em thread separada para não congelar a UI
            self._cmd_worker = CommandWorker(cmd_direto)
            self._cmd_worker.finished.connect(self._on_command_finished)
            self._cmd_worker.error_occurred.connect(self._on_command_error)
            self._cmd_worker.start()
            return

        prompt_exec = (
            "INSTRUÇÃO DO USUÁRIO COM AUTORIZAÇÃO EXPRESSA: Execute imediatamente o comando "
            "no sistema operacional ou abra o programa solicitado usando a ferramenta 'executar_comando'. "
            "Se for abrir navegador, use xdg-open ou o navegador padrão (ex: xdg-open https://google.com).\n"
            f"Pedido: {cmd_pedido}"
        )
        self.start_ai_query(prompt_exec, forcar_web=False, display_text=f"/executar {cmd_pedido}")

    def _cmd_web(self, text: str):
        """`/web <termo>`: liga a checkbox de web e pergunta direto."""
        pergunta = text[5:].strip()
        self.chk_web.setChecked(True)
        self.stack.setCurrentIndex(1)
        self.start_ai_query(pergunta, forcar_web=True)

    def _cmd_sessao(self, text: str):
        """`/sessao <nome>` abre a sessao nomeada; sem argumento, abre a pagina."""
        partes = text.split(maxsplit=1)
        if len(partes) > 1 and partes[1].strip():
            nome_s = sanitizar_nome_sessao(partes[1].strip())
            self.history_manager = HistoryManager(nome_s)
            self.clear_chat_view()
            self.refresh_telemetry()
        else:
            self.open_sessions_page()

    def _cmd_novo(self, text: str):
        """`/novo [nome]`: sem argumento, gera `chat_<timestamp>`."""
        partes = text.split(maxsplit=1)
        if len(partes) > 1 and partes[1].strip():
            nome_s = sanitizar_nome_sessao(partes[1].strip())
        else:
            nome_s = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.history_manager = HistoryManager(nome_s)
        self.clear_chat_view()
        self.refresh_telemetry()

    def _cmd_deletar_sessao(self):
        """Apaga a sessao atual apos confirmar; ja cria outra em seguida."""
        res = QMessageBox.warning(
            self,
            "Deletar Sessão",
            f"Tem certeza que deseja apagar a sessão atual '{self.history_manager.sessao}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.history_manager.deletar_sessao()
            nome_s = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.history_manager = HistoryManager(nome_s)
            self.clear_chat_view()
            self.refresh_telemetry()
            QMessageBox.information(self, "Metis", "Sessão deletada com sucesso!")

    def _cmd_arquivo(self, text: str):
        """`/arquivo <caminho>` anexa; sem argumento, abre o seletor."""
        partes = text.split(maxsplit=1)
        if len(partes) > 1 and partes[1].strip():
            self.set_attachment(partes[1].strip())
        else:
            self.open_file_dialog()
        self.prompt_input.clear()
        self.chat_input.clear()

    def _cmd_modelo(self, text: str):
        """`/modelo <provedor> [modelo]`: troca o provider ativo e confirma.

        Sem argumento, so abre a pagina de oraculos.
        """
        partes = text.split(maxsplit=1)
        if not (len(partes) > 1 and partes[1].strip()):
            self.open_oracles_page()
            return

        arg = partes[1].strip()
        arg_tokens = arg.split(maxsplit=1)
        first_tok = arg_tokens[0].lower()
        second_tok = arg_tokens[1].strip() if len(arg_tokens) > 1 else None

        resolvido = self._resolver_provedor(first_tok, second_tok, arg)
        if resolvido is None:
            return

        msg_conf, ativar = resolvido
        ativar()
        if self.stack.currentIndex() == 1 and msg_conf:
            self.add_chat_bubble("user", text)
            self.add_chat_bubble("assistant", msg_conf)
            self.history_manager.adicionar_mensagem("user", text)
            self.history_manager.adicionar_mensagem("assistant", msg_conf)
            self.refresh_telemetry()

    def _resolver_provedor(self, first_tok: str, second_tok, arg: str):
        """`(mensagem, callable)` para trocar o provider. `None` = nao achou.

        `first_tok` escolhe o provider e `second_tok` o modelo, caindo no
        padrao de cada um. `arg` (o argumento inteiro) so entra nas duas
        ultimas etapas: servidor customizado e busca por nome de modelo. A
        ordem entre as duasUltimas importa e e a original.
        """
        conhecidos = (
            ("ollama", "activate_ollama", config.OLLAMA_MODEL,
             "🏛️ **Provedor alterado para Ollama Local!**\n\n> 💡 **Modelo Ativo:** `{mod}`"),
            ("gemini", "activate_gemini", config.GEMINI_MODEL,
             "✨ **Provedor alterado para Google Gemini!**\n\n> 💡 **Modelo Ativo:** `{mod}`"),
            ("groq", "activate_groq", config.GROQ_MODEL,
             "⚡ **Provedor alterado para Groq Cloud!**\n\n> 💡 **Modelo Ativo:** `{mod}`"),
            ("nvidia", "activate_nvidia", getattr(config, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
             "🟢 **Provedor alterado para NVIDIA NIM!**\n\n> 💡 **Modelo Ativo:** `{mod}`"),
            ("g4f", "activate_g4f", getattr(config, "G4F_MODEL", "gpt-4o-mini"),
             "🌐 **Provedor alterado para G4F Free!**\n\n> 💡 **Modelo Ativo:** `{mod}`"),
        )
        for chave, metodo, padrao, modelo_de in conhecidos:
            if first_tok == chave:
                mod = second_tok or padrao
                return modelo_de.format(mod=mod), lambda: getattr(self, metodo)(mod)

        # servidor customizado, pelo nome
        srv = obter_servidor_customizado(first_tok)
        if srv:
            mod = second_tok or srv.get("modelo_atual", "default")
            nome = srv.get("nome", "Custom")
            return (
                f"🌐 **Provedor alterado para {nome}!**\n\n> 💡 **Modelo Ativo:** `{mod}`",
                lambda: self.activate_custom_server(srv, mod),
            )

        # busca por nome de modelo direto, na ordem original
        if arg in ollama_service.listar_modelos():
            return (
                f"🏛️ **Provedor alterado para Ollama Local!**\n\n> 💡 **Modelo Ativo:** `{arg}`",
                lambda: self.activate_ollama(arg),
            )
        if arg in obter_modelos_provedor("Gemini") or "gemini" in arg.lower():
            return (
                f"✨ **Provedor alterado para Google Gemini!**\n\n> 💡 **Modelo Ativo:** `{arg}`",
                lambda: self.activate_gemini(arg),
            )
        if arg in obter_modelos_provedor("Groq"):
            return (
                f"⚡ **Provedor alterado para Groq Cloud!**\n\n> 💡 **Modelo Ativo:** `{arg}`",
                lambda: self.activate_groq(arg),
            )
        if arg in obter_modelos_provedor("NVIDIA") or "nvidia" in arg.lower():
            return (
                f"🟢 **Provedor alterado para NVIDIA NIM!**\n\n> 💡 **Modelo Ativo:** `{arg}`",
                lambda: self.activate_nvidia(arg),
            )
        if arg in obter_modelos_provedor("G4F"):
            return (
                f"🌐 **Provedor alterado para G4F Free!**\n\n> 💡 **Modelo Ativo:** `{arg}`",
                lambda: self.activate_g4f(arg),
            )

        self.open_oracles_page()
        return None

    # ------------------------------------------------------------------
    # Consulta: decisoes em `start_ai_query`, corpos dos sinais em `_on_*`.
    #
    # O que este bloco decide esta fixado pelos testes de
    # `tests/test_gui_start_ai_query.py`: enfileirar ou nao, o texto que o
    # usuario ve, o contexto que o worker recebe e a ligacao dos seis sinais.
    # Os corpos leem o estado em `self._current_*`, o mesmo mecanismo que o
    # metodo ja usava para 6 dos valores.
    # ------------------------------------------------------------------

    def start_ai_query(self, pergunta: str, forcar_web: bool = False, display_text: str = None, from_queue: bool = False):
        """Prepara a consulta e liga o worker; o trabalho em si vive em `AIWorker`."""
        if not pergunta and not self.current_attachment_path:
            return

        texto_usuario = self._texto_do_usuario(pergunta, display_text)
        if self._ia_ocupada() and not from_queue:
            # As 7 chaves que `_process_next_in_queue` le. Deixadas aqui, no
            # orquestrador, para o contrato ficar a vista e poder ser conferido
            # contra o consumidor.
            item = {
                "pergunta": pergunta,
                "forcar_web": forcar_web,
                "display_text": display_text,
                "attachment_path": self.current_attachment_path,
                "media_paths": list(self.current_media_paths),
                "attachment_context": self.current_attachment_text_context,
            }
            self._enfileirar(item, texto_usuario)
            return

        # Na fila o balao do usuario ja foi criado quando ele foi enfileirado
        if not from_queue:
            self.add_chat_bubble("user", texto_usuario)

        ai_bubble, lbl_text, ai_b_layout = self.add_chat_bubble(
            "assistant",
            "<span style='color: #94a3b8; font-style: italic;'>● Pensando...</span>")

        # Checklist visual das ferramentas, escondido ate a primeira comecar
        self._current_checklist = None
        if getattr(config, "AGENT_VISUAL_CHECKLIST", True):
            self._current_checklist = AgentChecklistWidget(ai_bubble)
            self._current_checklist.setVisible(False)
            ai_b_layout.insertWidget(1, self._current_checklist)
        self.btn_stop.setVisible(True)
        self.mover_para_canto_superior_direito()

        self.active_worker = self._criar_worker(pergunta, forcar_web)
        self.clear_attachment()

        self._current_start_time = time.monotonic()
        self._current_lbl_text = lbl_text
        self._current_ai_bubble = ai_bubble
        self._current_ai_layout = ai_b_layout
        self._current_full_text = [""]
        self._current_pending_text = [""]
        self._current_timer_live = self._criar_cronometro()
        self._current_render_timer = self._criar_buffer_de_render()

        self._ligar_sinais_do_worker()
        self.active_worker.start()

    def _texto_do_usuario(self, pergunta, display_text):
        """O que o balao do usuario mostra, que nao e o que o worker recebe.

        Reenvio da fila e comandos exibem um texto e consultam outro — e por isso
        que `display_text` existe separado de `pergunta`.
        """
        texto = display_text if display_text else pergunta
        if self.current_attachment_path:
            p_name = Path(self.current_attachment_path).name
            sufixo = texto if texto else "Analise este anexo."
            texto = f"📎 <b>[{p_name}]</b><br>{sufixo}"
        return texto

    def _ia_ocupada(self):
        """True quando a IA ainda esta gerando resposta para a pergunta anterior."""
        return bool(self.active_worker and self.active_worker.isRunning())

    def _enfileirar(self, item, texto_usuario):
        """Guarda a consulta para quando a atual terminar.

        Nao enfileira vinda da fila: o balao do usuario ja foi criado quando ele
        entrou, e reenfileirar aqui seria laco infinito.
        """
        u_bubble, _, _ = self.add_chat_bubble("user", texto_usuario, is_queued=True)
        item["user_bubble"] = u_bubble
        self.query_queue.append(item)
        self.clear_attachment()
        self.scroll_chat_to_bottom()

    def _criar_worker(self, pergunta, forcar_web):
        """O worker recebe a pergunta crua e o contexto; o texto da tela nao."""
        return AIWorker(
            pergunta=pergunta if pergunta else "Analise e descreva o anexo detalhadamente.",
            history_manager=self.history_manager,
            service=self.current_service,
            forcar_web=forcar_web,
            media_paths=list(self.current_media_paths),
            file_attachment_context=self.current_attachment_text_context
        )

    def _criar_cronometro(self):
        """Timer de 100ms que escreve o tempo decorrido no rotulo do balao."""
        timer = QTimer(self)
        timer.timeout.connect(self._atualizar_cronometro)
        timer.start(100)
        return timer

    def _criar_buffer_de_render(self):
        """Timer de 75ms que aplica o acumulado no balao (~13 FPS)."""
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(75)
        timer.timeout.connect(self._flush_render)
        return timer

    def _ligar_sinais_do_worker(self):
        for sinal, handler in self._SINAIS_DO_WORKER:
            getattr(self.active_worker, sinal).connect(getattr(self, handler))

    def _rotulo_do_cronometro(self):
        """O rotulo do cronometro do balao, ou None quando o balao nao tem um."""
        balao = self._current_ai_bubble
        if hasattr(balao, "_lbl_timer") and balao._lbl_timer:
            return balao._lbl_timer
        return None

    def _atualizar_cronometro(self):
        rotulo = self._rotulo_do_cronometro()
        if rotulo is None:
            return
        elapsed = time.monotonic() - self._current_start_time
        rotulo.setText(f"⏱️ {elapsed:.1f}s")
        rotulo.setStyleSheet("color: #fad094; background: transparent; font-size: 8pt;")

    def _fechar_cronometro(self, cor):
        """Congela o tempo no rotulo, na cor do desfecho."""
        rotulo = self._rotulo_do_cronometro()
        if rotulo is None:
            return
        elapsed = time.monotonic() - self._current_start_time
        rotulo.setText(f"⏱️ {elapsed:.2f}s")
        rotulo.setStyleSheet(f"color: {cor}; background: transparent; font-size: 8pt;")

    def _flush_render(self):
        if not self._current_pending_text[0]:
            return
        self._set_bubble_content(self._current_lbl_text, self._current_pending_text[0])
        self.scroll_chat_to_bottom()
        self._current_pending_text[0] = ""

    # Sinais do worker ----------------------------------------------------
    # Cada um engole a excecao para o log e devolve: um handler que levanta
    # derrubaria a thread do Qt sem isso. `_on_finished` e `_on_error`
    # avancam a fila mesmo no `except`, para que uma falha de escrita nao
    # trave as perguntas que estavam na espera.

    def _on_chunk(self, chunk):
        try:
            self._current_full_text[0] += chunk
            self._current_pending_text[0] = self._current_full_text[0]
            if not self._current_render_timer.isActive():
                self._current_render_timer.start()
        except Exception as e:
            logger.error(f"Erro em on_chunk: {e}")

    def _on_search_started(self, query):
        try:
            self._current_lbl_text.setText(
                "<span style='color: #67e8f9; font-style: italic;'>"
                "🌐 Buscando informações na web...</span>")
        except Exception as e:
            logger.error(f"Erro em on_search_started: {e}")

    def _on_tool_started(self, data):
        try:
            if self._current_checklist:
                self._current_checklist.setVisible(True)
                self._current_checklist.add_or_update_started(data)
                self.scroll_chat_to_bottom()
        except Exception as e:
            logger.error(f"Erro em on_tool_started: {e}")

    def _on_tool_finished(self, data):
        try:
            if self._current_checklist:
                self._current_checklist.setVisible(True)
                self._current_checklist.add_or_update_finished(data)
                self.scroll_chat_to_bottom()
        except Exception as e:
            logger.error(f"Erro em on_tool_finished: {e}")

    def _on_finished(self, final_resp):
        try:
            self._current_timer_live.stop()
            self._current_render_timer.stop()
            self._flush_render()
            self._fechar_cronometro("#94a3b8")
            rotulo = self._rotulo_do_cronometro()
            if rotulo is not None:
                total = time.monotonic() - self._current_start_time
                rotulo.setToolTip(f"Tempo total de resposta: {total:.2f}s")
            self._set_bubble_content(self._current_lbl_text, final_resp)
            self._render_command_chips_for_bubble(
                self._current_ai_bubble, self._current_ai_layout, final_resp)
            self.btn_stop.setVisible(False)
            self.refresh_telemetry()
            self.scroll_chat_to_bottom()
            self._process_next_in_queue()
        except Exception as e:
            logger.error(f"Erro em on_finished: {e}")
            self._process_next_in_queue()

    def _on_error(self, err):
        try:
            self._current_timer_live.stop()
            self._fechar_cronometro("#ef4444")
            self._current_lbl_text.setText(
                "<span style='color: #ef4444; font-weight: bold;'>"
                f"❌ Erro na consulta:</span> {err}")
            self.btn_stop.setVisible(False)
            self.refresh_telemetry()
            self._process_next_in_queue()
        except Exception as e:
            logger.error(f"Erro em on_error: {e}")
            self._process_next_in_queue()

    def _process_next_in_queue(self):
        if self.query_queue:
            next_item = self.query_queue.pop(0)
            u_bubble = next_item.get("user_bubble")
            if u_bubble and hasattr(u_bubble, "_queue_badge") and u_bubble._queue_badge:
                try:
                    u_bubble._queue_badge.deleteLater()
                    u_bubble._queue_badge = None
                except Exception as _silent_e:
                    logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
            self.current_attachment_path = next_item.get("attachment_path")
            self.current_media_paths = next_item.get("media_paths", [])
            self.current_attachment_text_context = next_item.get("attachment_context", "")
            QTimer.singleShot(150, lambda: self.start_ai_query(
                pergunta=next_item.get("pergunta", ""),
                forcar_web=next_item.get("forcar_web", False),
                display_text=next_item.get("display_text"),
                from_queue=True
            ))

    def stop_ai_generation(self):
        worker = self.active_worker
        self.active_worker = None

        if worker and worker.isRunning():
            self._desligar_sinais_do_worker(worker)
            worker.cancel()
            self.btn_stop.setVisible(False)

            self._parar_timers_de_render()
            self._marcar_balao_interrompido()
            self._congelar_cronometro_interrompido()
            self.scroll_chat_to_bottom()
            self._devolver_foco_ao_chat()

        if self.query_queue:
            self.query_queue.clear()

    def _desligar_sinais_do_worker(self, worker):
        """Desconecta exatamente o que `_ligar_sinais_do_worker` conectou.

        A lista vivia duplicada em `stop_ai_generation` e ja tinha divergido:
        seis sinais eram conectados e cinco desconectados, entao
        `search_started` ficava ligado para sempre depois de um cancelamento
        — o worker soltado continuaria chamando o handler do balao. Ler as
        duas pontas da mesma tabela deixa a divergencia impossivel.

        `disconnect()` sem argumento solta todos os slots do sinal, e nao so o
        nosso. E o comportamento do original, entao foi preservado.

        As exceções sao estreitas de proposito: `disconnect` levanta TypeError
        quando o sinal ja nao tem slot, e RuntimeError quando o objeto C++ foi
        destruido. Um nome de sinal escrito errado levanta AttributeError e
        precisa aparecer — o `except Exception` original engoleva exatamente a
        classe de erro que esconde um `KeyInpu` no lugar de `KeyInput`.
        """
        for sinal, _handler in self._SINAIS_DO_WORKER:
            try:
                getattr(worker, sinal).disconnect()
            except (TypeError, RuntimeError) as e:
                logger.debug("Sinal %s já desligado: %s", sinal, e, exc_info=True)

    def _parar_timers_de_render(self):
        """Congela os dois timers antes de mexer no balao.

        Sem isto, um `_flush_render` pendente reescreve o texto de
        interrupcao logo depois e o usuario ve o aviso sumir sozinho.
        """
        for nome in ("_current_timer_live", "_current_render_timer"):
            timer = getattr(self, nome, None)
            if timer is None:
                continue
            try:
                timer.stop()
            except RuntimeError as e:
                logger.debug("Timer %s já parado: %s", nome, e, exc_info=True)

    def _marcar_balao_interrompido(self):
        """Acrescenta o aviso de interrupcao ao que ja foi gerado.

        A operacao e idempotente porque o texto marcado volta para
        `_current_full_text`. Sem essa escrita de volta, a guarda
        `MARCA_DE_INTERROPCAO not in texto` lia sempre o texto original e
        nunca disparava: dois cliques em Parar nao duplicavam o aviso por
        sorte, e nao por desenho. `_set_bubble_content` so escreve no QLabel,
        entao o estado do mixin ficava mentindo sobre o que estava na tela.
        """
        balao = getattr(self, "_current_lbl_text", None)
        if balao is None:
            return
        acumulado = getattr(self, "_current_full_text", None)
        texto = acumulado[0] if acumulado else ""
        if not texto.strip():
            texto = MARCA_DE_INTERROPCAO
        elif MARCA_DE_INTERROPCAO not in texto:
            texto = f"{texto}\n\n{MARCA_DE_INTERROPCAO}"
        if acumulado:
            acumulado[0] = texto
        self._set_bubble_content(balao, texto)

    def _congelar_cronometro_interrompido(self):
        """Fixa o tempo no valor parado, em vermelho, e mantem a escala.

        Copia a regra do cronometro vivo em vez de repetir a folha de estilo
        na mao: a string ficava em dois lugares, e mudar a escala num so nao
        mudaria no outro.
        """
        rotulo = self._rotulo_do_cronometro()
        if rotulo is None:
            return
        if not getattr(self, "_current_start_time", None):
            return
        elapsed = time.monotonic() - self._current_start_time
        rotulo.setText(f"{GLIFO_DE_PARADO} {elapsed:.1f}s")
        rotulo.setStyleSheet(ESTILO_DO_ROTULO_PARADO)

    def _devolver_foco_ao_chat(self):
        campo = getattr(self, "chat_input", None)
        if campo is not None:
            campo.setEnabled(True)
            campo.setFocus()

    def retry_last_query(self):
        turnos = self.history_manager.listar_turnos()
        if turnos:
            ultima_pergunta = turnos[-1].get("user", "")
            self.history_manager.deletar_ultimos(1)
            if ultima_pergunta:
                # Remove os últimos 2 bubbles da interface
                count = self.chat_layout.count()
                if count >= 3:
                    item1 = self.chat_layout.takeAt(count - 2)
                    if item1.widget():
                        item1.widget().deleteLater()
                if self.chat_layout.count() >= 2:
                    item2 = self.chat_layout.takeAt(self.chat_layout.count() - 2)
                    if item2.widget():
                        item2.widget().deleteLater()

                self.start_ai_query(ultima_pergunta, forcar_web=self.chk_web.isChecked())

    def execute_direct_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        while self.search_results_layout.count() > 1:
            item = self.search_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lbl_loading = QLabel(f"🔍 Buscando '{query}' na web...")
        lbl_loading.setStyleSheet("color: #67e8f9; font-weight: bold;")
        self.search_results_layout.insertWidget(0, lbl_loading)

        QApplication.processEvents()

        try:
            resultados = searxng_service.buscar_searxng(query, max_results=8)
            lbl_loading.deleteLater()

            if not resultados:
                lbl_no = QLabel("Nenhum resultado encontrado.")
                lbl_no.setStyleSheet("color: #64748b;")
                self.search_results_layout.insertWidget(0, lbl_no)
                return

            for item in reversed(resultados):
                card = QFrame()
                card.setStyleSheet("""
                    background-color: #0c1320;
                    border: 1px solid #1c2e47;
                    border-radius: 8px;
                    padding: 10px;
                """)
                c_layout = QVBoxLayout(card)
                c_layout.setSpacing(4)

                lbl_t = QLabel(item.get("title", "Sem título"))
                lbl_t.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
                lbl_t.setStyleSheet("color: #67e8f9;")
                c_layout.addWidget(lbl_t)

                lbl_snip = QLabel(item.get("snippet", ""))
                lbl_snip.setWordWrap(True)
                lbl_snip.setStyleSheet("color: #cbd5e1; font-size: 11px;")
                c_layout.addWidget(lbl_snip)

                url = item.get("url", "")
                btn_url = QPushButton(f"🔗 Abrir: {limitar_texto(url, 60)}")
                btn_url.setProperty("class", "CommandChip")
                btn_url.clicked.connect(lambda _, u=url: webbrowser.open(u))
                c_layout.addWidget(btn_url)

                self.search_results_layout.insertWidget(0, card)

        except Exception as e:
            lbl_loading.setText(f"❌ Erro na busca: {e}")
