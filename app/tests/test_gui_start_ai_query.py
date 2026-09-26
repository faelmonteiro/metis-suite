"""`start_ai_query`: as decisoes que NAO aparecem na arvore de widgets.

O fingerprint de arvore cobre montagem. Aqui o risco e outro: o metodo decide
enfileirar ou nao, escolhe o texto que o usuario ve, monta o `AIWorker` e liga
seis sinais. Um desvio nessas decisoes nao quebra build, nao quebra a impressao
digital e nao quebra nenhuma assertiva de widget — a consulta simplesmente
responde a coisa errada, ou a fila trava silenciosamente.

Por isso os testes trocam `AIWorker` e `add_chat_bubble` por gravadores,
chamam o metodo e conferem as consequencias: o que foi enfileirado, o que foi
passado ao worker, e o que cada sinal faz no balao.

Escritos ANTES de qualquer refatoracao, contra o metodo como estava.
"""

import os
import time
import unittest
from unittest import mock

from PyQt6.QtWidgets import QWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_APP = None

# Os sinais que `start_ai_query` conecta no worker. A ordem nao importa; o
# conjunto importa — um sinal novo sem handler (ou handler sem sinal) e um
# Workflow silenciosamente quebrado.
SINAIS = (
    "chunk_received", "search_started", "tool_started",
    "tool_finished", "finished_response", "error_occurred",
)

# As chaves que o produtor (enfileirar) escreve e que `_process_next_in_queue`
# le. As duas pontas precisam concordar; o teste abaixo compara as duas listas
# contra a fonte, para pegar erro de digitacao em qualquer dos lados.
CHAVES_FILA = (
    "pergunta", "forcar_web", "display_text", "attachment_path",
    "media_paths", "attachment_context", "user_bubble",
)


def _janela():
    global _APP
    from PyQt6.QtWidgets import QApplication
    import agente.ui.gui_app  # noqa: F401
    from agente.ui.gui_app import MetisMainWindow

    # Referencia global: se a QApplication virar lixo no fim deste escopo, as
    # janelas seguintes vem com o C++ ja destruido e o teste morre com
    # "wrapped C/C++ object ... has been deleted".
    _APP = QApplication.instance() or QApplication([])
    return MetisMainWindow()


class _Balao:
    """O que `add_chat_bubble` devolveria: widget, layout e rotulo."""

    def __init__(self, tipo, texto, kw):
        from PyQt6.QtWidgets import QLabel, QVBoxLayout
        self.tipo, self.texto, self.kw = tipo, texto, kw
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.lbl = QLabel()
        # `start_ai_query` checa `hasattr(ai_bubble, "_lbl_timer")`. Por padrao
        # deixo de fora, para exercitar o desvio; os testes que precisam do
        # cronometro anexam um rotulo.
        self.rotulo_timer = None

    def com_cronometro(self):
        from PyQt6.QtWidgets import QLabel
        self.rotulo_timer = QLabel()
        self.widget._lbl_timer = self.rotulo_timer
        return self


class _ChecklistFalso(QWidget):
    """Widget real — `insertWidget` checa o tipo — com os metodos gravados.

    `setVisible` fica registrado em vez de virar `Mock`, para o comportamento
    real do QWidget continuar valendo.
    """

    def __init__(self, pai=None):
        super().__init__(pai)
        self.visibilidades = []
        self.add_or_update_started = mock.Mock()
        self.add_or_update_finished = mock.Mock()

    def setVisible(self, vis):
        self.visibilidades.append(bool(vis))
        super().setVisible(vis)


class _WorkerFalso:
    """`AIWorker` sem thread: guarda como foi construido e quem foi ligado."""

    def __init__(self, rodando=False):
        self.rodando = rodando
        self.conectados = {}
        self.iniciado = False
        self.kwargs = {}
        for nome in SINAIS:
            setattr(self, nome, self._sinal(nome))

    def _sinal(self, nome):
        s = mock.Mock(name=nome)

        def connect(cb, *args, **kwargs):
            self.conectados[nome] = cb
        s.connect.side_effect = connect
        return s

    def isRunning(self):
        return self.rodando

    def start(self):
        self.iniciado = True

    def handler(self, nome):
        h = self.conectados.get(nome)
        if h is None:
            raise AssertionError(
                f"sinal {nome!r} nao foi conectado; conectados: "
                f"{sorted(self.conectados)}")
        return h


class TestStartAIQuery(unittest.TestCase):
    def setUp(self):
        self.win = _janela()
        self.baloes = []
        self.workers = []
        # Ligado antes de chamar `start_ai_query`: os handlers fecham sobre o
        # balao devolvido na primeira chamada, entao um `_lbl_timer` anexado
        # depois nao alcanca o closure.
        self.com_cronometro = False
        self.checklists = []
        self.escritas = []
        win = self.win

        def add_chat_bubble(tipo, texto, **kw):
            b = _Balao(tipo, texto, kw)
            if self.com_cronometro:
                b.com_cronometro()
            self.baloes.append(b)
            return b.widget, b.lbl, b.layout
        win.add_chat_bubble = add_chat_bubble

        win.mover_para_canto_superior_direito = mock.Mock()
        win.scroll_chat_to_bottom = mock.Mock()
        win.refresh_telemetry = mock.Mock()
        win._process_next_in_queue = mock.Mock()
        win._render_command_chips_for_bubble = mock.Mock()
        win.clear_attachment = mock.Mock()
        win._set_bubble_content = lambda lbl, txt: self.escritas.append(txt)

        def _worker(**kw):
            w = _WorkerFalso()
            w.kwargs = kw
            self.workers.append(w)
            return w
        def _checklist(pai):
            c = _ChecklistFalso(pai)
            self.checklists.append(c)
            return c

        for alvo, factory in (("AIWorker", _worker),
                              ("AgentChecklistWidget", _checklist)):
            p = mock.patch(f"agente.gui.pages.ai.{alvo}", side_effect=factory)
            p.start()
            self.addCleanup(p.stop)

        p = mock.patch.object(
            __import__("agente.config", fromlist=["config"]),
            "AGENT_VISUAL_CHECKLIST", True)
        p.start()
        self.addCleanup(p.stop)

        win.current_attachment_path = None
        win.current_media_paths = []
        win.current_attachment_text_context = ""
        win.query_queue = []
        win.active_worker = None

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()

    # atalhos ---------------------------------------------------------------

    @property
    def worker(self):
        return self.workers[-1]

    @property
    def balao(self):
        """O ultimo balao criado (o de assistant, na maioria dos casos)."""
        return self.baloes[-1]

    def tipos(self):
        return [b.tipo for b in self.baloes]

    def chama(self, *args, **kw):
        self.win.start_ai_query(*args, **kw)

    # guardas ----------------------------------------------------------------

    def test_nada_acontece_sem_pergunta_e_sem_anexo(self):
        self.chama("")
        self.assertEqual(self.baloes, [])
        self.assertEqual(self.workers, [])

    def test_anexo_so_e_aceito(self):
        self.win.current_attachment_path = "/tmp/retrato.png"
        self.chama("")
        self.assertEqual(len(self.workers), 1)
        self.assertTrue(self.worker.kwargs["pergunta"])

    def test_worker_ocupado_enfileira_sem_rodar(self):
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("primeira")
        self.assertEqual(self.workers, [],
                         "enfileirar nao pode construir worker novo")
        self.assertEqual(len(self.win.query_queue), 1)
        self.assertEqual(self.tipos(), ["user"])
        self.assertIsNot(self.win.active_worker, None)
        self.assertFalse(self.win.active_worker.iniciado)

    def test_da_fila_nao_enfileira_de_novo(self):
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("segunda", from_queue=True)
        self.assertEqual(self.win.query_queue, [],
                         "veio da fila: reenfileirar seria laco infinito")

    def test_fora_da_fila_cria_balao_de_usuario(self):
        self.chama("ola")
        self.assertEqual(self.tipos(), ["user", "assistant"])

    def test_da_fila_nao_cria_balao_de_usuario(self):
        """Na fila o balao do usuario ja foi criado quando ele foi enfileirado."""
        self.chama("ola", from_queue=True)
        self.assertEqual(self.tipos(), ["assistant"])

    def test_copia_o_texto_para_o_worker(self):
        self.chama("pergunta real", display_text="texto na tela")
        self.assertEqual(self.worker.kwargs["pergunta"], "pergunta real")

    def test_display_text_e_o_que_o_usuario_ve(self):
        """`display_text` muda a tela, nao a consulta.

        Sao coisas diferentes de proposito: reenviar uma pergunta da fila, ou
        um comando, mostra um texto e consulta outro. Se o balão mostrar a
        pergunta bruta, o usuario le uma coisa e a IA responde outra.
        """
        self.chama("pergunta real", display_text="texto na tela")
        self.assertEqual(self.baloes[0].texto, "texto na tela")

    def test_anexo_muda_o_texto_da_tela_e_a_pergunta(self):
        self.win.current_attachment_path = "/tmp/retrato.png"
        self.chama("")
        self.assertIn("retrato.png", self.baloes[0].texto)
        self.assertNotEqual(self.worker.kwargs["pergunta"], "")

    def test_anexo_so_convida_a_analisar(self):
        """Sem pergunta, o balao convida a analisar — em vez de mostrar vazio."""
        self.win.current_attachment_path = "/tmp/retrato.png"
        self.chama("")
        self.assertIn("Analise este anexo", self.baloes[0].texto)

    # contrato da fila -------------------------------------------------------

    def test_item_da_filha_tem_exatamente_as_chaves_lidas_dentro(self):
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("primeira")
        self.assertEqual(set(self.win.query_queue[0]), set(CHAVES_FILA))

    def test_filho_tem_exatamente_as_chaves_lidas_dentro(self):
        """Ponta a ponta: o produtor e o consumidor da fila concordam."""
        import ast
        import pathlib
        import agente.gui.pages.ai as mod
        arq = pathlib.Path(mod.__file__)
        arvore = ast.parse(arq.read_text())
        cls = next(n for n in arvore.body
                   if isinstance(n, ast.ClassDef) and n.name == "AiMixin")
        cons = next(m for m in cls.body if isinstance(m, ast.FunctionDef)
                    and m.name == "_process_next_in_queue")
        lidas = {
            n.args[0].value
            for n in ast.walk(cons)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
            and n.args and isinstance(n.args[0], ast.Constant)
        }
        lidas.discard("user_bubble")
        self.assertEqual(lidas, {c for c in CHAVES_FILA if c != "user_bubble"})

    def test_fila_guarda_o_contexto_do_anexo(self):
        self.win.current_attachment_path = "/tmp/a.png"
        self.win.current_media_paths = ["/tmp/a.png", "/tmp/b.png"]
        self.win.current_attachment_text_context = "texto extraido"
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("primeira")
        item = self.win.query_queue[0]
        self.assertEqual(item["attachment_path"], "/tmp/a.png")
        self.assertEqual(item["media_paths"], ["/tmp/a.png", "/tmp/b.png"])
        self.assertEqual(item["attachment_context"], "texto extraido")

    def test_fila_toma_copia_das_midias(self):
        self.win.current_media_paths = ["/tmp/a.png"]
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("primeira")
        self.win.current_media_paths.append("/tmp/c.png")
        self.assertEqual(self.win.query_queue[0]["media_paths"], ["/tmp/a.png"],
                         "a fila guardou a lista viva, e nao uma copia")

    def test_enfileirar_marca_o_balao(self):
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("primeira")
        self.assertTrue(self.baloes[0].kw.get("is_queued"))

    # montagem --------------------------------------------------------------

    def test_worker_recebe_o_contexto(self):
        self.win.current_attachment_text_context = "texto extraido"
        self.win.current_media_paths = ["/tmp/a.png"]
        self.chama("ola", forcar_web=True)
        kw = self.worker.kwargs
        self.assertEqual(kw["forcar_web"], True)
        self.assertEqual(kw["file_attachment_context"], "texto extraido")
        self.assertEqual(kw["media_paths"], ["/tmp/a.png"])

    def test_worker_e_iniciado(self):
        self.chama("ola")
        self.assertTrue(self.worker.iniciado)

    def test_limpa_o_anexo_ao_enviar(self):
        self.win.current_attachment_path = "/tmp/a.png"
        self.chama("ola")
        self.win.clear_attachment.assert_called_once()

    def test_limpa_o_anexo_tambem_quando_enfileira(self):
        self.win.current_attachment_path = "/tmp/a.png"
        self.win.active_worker = _WorkerFalso(rodando=True)
        self.chama("primeira")
        self.win.clear_attachment.assert_called_once()

    def test_checklist_segue_a_config(self):
        with mock.patch("agente.config.AGENT_VISUAL_CHECKLIST", False):
            self.chama("ola")
        self.assertEqual(self.checklists, [])

    def test_checklist_entra_visivel_so_quando_a_ferramenta_comeca(self):
        self.chama("ola")
        self.assertEqual(len(self.checklists), 1)
        self.assertEqual(self.checklists[0].visibilidades, [False])

    def test_botao_parar_aparece(self):
        self.chama("ola")
        self.assertFalse(self.win.btn_stop.isHidden())

    def test_os_seis_sinais_sao_ligados(self):
        self.chama("ola")
        self.assertEqual(set(self.worker.conectados), set(SINAIS))

    # sinais ----------------------------------------------------------------

    def _com_worker_rodando(self):
        self.chama("ola")
        return self.worker

    def test_chunk_acumula(self):
        w = self._com_worker_rodando()
        w.handler("chunk_received")("parcial")
        w.handler("chunk_received")(" final")
        self.win._current_render_timer.timeout.emit()
        self.assertEqual(self.escritas, ["parcial final"])

    def test_chunk_repete_o_texto_inteiro(self):
        """Cada chunk recomeca do acumulado, e nao do chunk anterior."""
        w = self._com_worker_rodando()
        h = w.handler("chunk_received")
        h("a")
        h("b")
        self.win._current_render_timer.timeout.emit()
        self.assertEqual(self.escritas, ["ab"])

    def test_flush_nao_reescreve_o_que_ja_saiu(self):
        """O buffer esvazia depois de escrever.

        Sem isso, cada tique seguinte reescreve o mesmo texto no balao — na tela
        nao muda nada, mas a cada 75ms o balão inteiro e reprocessado.
        """
        w = self._com_worker_rodando()
        w.handler("chunk_received")("parcial")
        self.win._current_render_timer.timeout.emit()
        self.win._current_render_timer.timeout.emit()
        self.assertEqual(self.escritas, ["parcial"])

    def test_render_e_um_timer_unico_de_75ms(self):
        w = self._com_worker_rodando()
        timer = self.win._current_render_timer
        self.assertEqual(timer.interval(), 75)
        self.assertTrue(timer.isSingleShot(),
                        "sem singleShot o buffer reescreve a 13 FPS para sempre")

    def test_cronometro_bate_a_cada_100ms(self):
        self.com_cronometro = True
        self.chama("ola")
        self.assertEqual(self.win._current_timer_live.interval(), 100)
        self.assertFalse(self.win._current_timer_live.isSingleShot())

    def test_cronometro_rodando_mostra_um_digito(self):
        w, b = self._com_cronometro()
        self.win._current_timer_live.timeout.emit()
        self.assertRegex(b.rotulo_timer.text(), r"^\u23f1\ufe0f \d+\.\d s?$|\d\.\ds$",
                         f"formato inesperado: {b.rotulo_timer.text()!r}")

    def test_busca_web_marca_o_rotulo(self):
        w = self._com_worker_rodando()
        w.handler("search_started")("clima")
        self.assertIn("Buscando", self.balao.lbl.text())

    def test_ferramenta_revela_o_checklist(self):
        w = self._com_worker_rodando()
        w.handler("tool_started")({"nome": "busca"})
        self.assertIn(True, self.checklists[0].visibilidades)
        self.checklists[0].add_or_update_started.assert_called_once()

    def test_ferramenta_fim_revela_o_checklist(self):
        w = self._com_worker_rodando()
        w.handler("tool_finished")({"nome": "busca"})
        self.checklists[0].add_or_update_finished.assert_called_once()

    def test_resposta_final_escreve_e_avanca_a_fila(self):
        w = self._com_worker_rodando()
        w.handler("finished_response")("RESPOSTA")
        self.assertEqual(self.escritas, ["RESPOSTA"])
        self.win._process_next_in_queue.assert_called_once()

    def test_resposta_final_ganha_do_chunk_pendente(self):
        """O texto final tem que ganhar do que ainda estava no buffer."""
        w = self._com_worker_rodando()
        w.handler("chunk_received")("parcial")
        w.handler("finished_response")("RESPOSTA COMPLETA")
        self.assertEqual(self.escritas[-1], "RESPOSTA COMPLETA")

    def _com_cronometro(self):
        self.com_cronometro = True
        self.chama("ola")
        return self.worker, self.baloes[-1]

    def test_cronometro_corre_enquanto_gera(self):
        w, b = self._com_cronometro()
        self.assertTrue(self.win._current_timer_live.isActive())
        self.win._current_timer_live.timeout.emit()
        self.assertIn("s", b.rotulo_timer.text())
        self.assertTrue(self.win._current_timer_live.isActive(),
                        "o cronometro roda ate a resposta terminar")

    def test_resposta_final_para_o_cronometro(self):
        w, b = self._com_cronometro()
        w.handler("finished_response")("RESPOSTA")
        self.assertFalse(self.win._current_timer_live.isActive())
        self.assertIn("Tempo total", b.rotulo_timer.toolTip())

    def test_erro_para_o_cronometro_e_pinta_de_vermelho(self):
        w, b = self._com_cronometro()
        w.handler("error_occurred")("falhou")
        self.assertFalse(self.win._current_timer_live.isActive())
        self.assertIn("#ef4444", b.rotulo_timer.styleSheet())

    def test_erro_marca_o_balao(self):
        w = self._com_worker_rodando()
        w.handler("error_occurred")("sem credito")
        self.assertIn("sem credito", self.balao.lbl.text())
        self.assertIn("Erro", self.balao.lbl.text())

    def test_erro_avanca_a_fila(self):
        w = self._com_worker_rodando()
        w.handler("error_occurred")("sem credito")
        self.win._process_next_in_queue.assert_called_once()

    def test_balao_sem_cronometro_nao_quebra(self):
        """`_lbl_timer` nem sempre existe; o desvio precisa ser silencioso."""
        w = self._com_worker_rodando()
        w.handler("finished_response")("RESPOSTA")
        w.handler("error_occurred")("falhou")
        self.assertEqual(self.escritas, ["RESPOSTA"])

    def test_resposta_final_quebrada_ainda_avanca_a_fila(self):
        """Rede de seguranca: se um passo estourar, a fila nao pode travar."""
        w = self._com_worker_rodando()
        self.win._set_bubble_content = mock.Mock(
            side_effect=RuntimeError("boom"))
        w.handler("finished_response")("RESPOSTA")
        self.win._process_next_in_queue.assert_called_once()

    def test_erro_quebrado_ainda_avanca_a_fila(self):
        w = self._com_worker_rodando()
        self.win._set_bubble_content = mock.Mock(
            side_effect=RuntimeError("boom"))
        w.handler("error_occurred")("falhou")
        self.win._process_next_in_queue.assert_called_once()

    def test_resposta_final_esconde_o_botao_parar(self):
        w = self._com_worker_rodando()
        w.handler("finished_response")("RESPOSTA")
        self.assertTrue(self.win.btn_stop.isHidden())

    def test_erro_esconde_o_botao_parar(self):
        w = self._com_worker_rodando()
        w.handler("error_occurred")("falhou")
        self.assertTrue(self.win.btn_stop.isHidden())


class TestStopAiGeneration(unittest.TestCase):
    """`stop_ai_generation` era 75 linhas com dois padroes repetidos.

    O que se verifica aqui e o contrato, nao a forma: depois de parar, nenhum
    sinal do worker pode continuar conectado, os dois timers param, o balao
    ganha o aviso uma vez so, e a fila e limpa.
    """

    def setUp(self):
        self.win = _janela()
        win = self.win
        self.escritas = []
        win.btn_stop = mock.Mock()
        win.scroll_chat_to_bottom = mock.Mock()
        win.refresh_telemetry = mock.Mock()
        win.chat_input = mock.Mock()
        win.query_queue = [{"pergunta": "nao vai rodar"}]
        win._current_lbl_text = mock.Mock()
        win._current_full_text = ["resposta parcial"]
        win._current_ai_bubble = mock.Mock()
        win._current_ai_bubble._lbl_timer = mock.Mock()
        win._current_start_time = time.monotonic() - 3.0
        win._current_timer_live = mock.Mock()
        win._current_render_timer = mock.Mock()
        win._current_pending_text = [""]
        win._set_bubble_content = lambda lbl, txt: self.escritas.append(txt)

    def _worker_parado(self):
        """Um `AIWorker` de verdade, com sinais de verdade, sem thread.

        `isRunning` e forcado para True porque o corpo do `stop` so age sobre
        worker em andamento; sem isso o metodo inteiro seria pulado e o teste
        passaria sem exercitar nada.
        """
        from agente.gui.workers import AIWorker

        w = AIWorker(pergunta="p", history_manager=mock.Mock(), service=mock.Mock())
        w.isRunning = lambda: True
        return w

    def test_todos_os_sinais_desconectam(self):
        """O bug: a lista de desconexao tinha um item a menos que a de conexao.

        Seis sinais eram conectados e cinco desconectados, entao
        `search_started` sobrevivia ao cancelamento. Este teste falha se a
        tabela perder um item, porque passa a comparar as duas pontas.
        """
        win = self.win
        worker = self._worker_parado()
        win.active_worker = worker
        win._ligar_sinais_do_worker()
        for sinal, _handler in win._SINAIS_DO_WORKER:
            self.assertGreater(worker.receivers(getattr(worker, sinal)), 0,
                               f"pre-condicao: {sinal} deveria estar conectado")

        win.stop_ai_generation()

        for sinal, _handler in win._SINAIS_DO_WORKER:
            self.assertEqual(
                worker.receivers(getattr(worker, sinal)), 0,
                f"{sinal} continua conectado depois de parar",
            )

    def test_worker_ouvinte_ainda_esta_ligado(self):
        """Confere que a tabela grew como a que os handlers esperam.

        Se `_ligar_sinais_do_worker` passar a usar a tabela e a tabela ficar
        errada, os sinais passam a nao conectar e este teste acusa.
        """
        win = self.win
        worker = self._worker_parado()
        win.active_worker = worker
        win._ligar_sinais_do_worker()
        ligados = [s for s, _h in win._SINAIS_DO_WORKER
                   if worker.receivers(getattr(worker, sinal := s)) > 0]
        self.assertEqual(ligados, [s for s, _ in win._SINAIS_DO_WORKER])

    def test_os_dois_timers_param(self):
        win = self.win
        win.active_worker = self._worker_parado()
        win.stop_ai_generation()
        win._current_timer_live.stop.assert_called_once()
        win._current_render_timer.stop.assert_called_once()

    def test_timer_inexistente_nao_levanta(self):
        """Chamar Parar antes da primeira consulta nao pode estourar.

        Os atributos `_current_*` so existem depois que uma consulta comeca.
        """
        win = self.win
        for nome in ("_current_timer_live", "_current_render_timer",
                     "_current_lbl_text", "_current_full_text", "chat_input"):
            if hasattr(win, nome):
                delattr(win, nome)
        win.active_worker = self._worker_parado()
        win.stop_ai_generation()  # nao deve levantar
        self.assertTrue(win.query_queue == [])

    def test_o_aviso_entra_uma_vez_so(self):
        """Dois cliques em Parar nao podem gerar dois avisos."""
        win = self.win
        for _ in range(2):
            win.active_worker = self._worker_parado()
            win.stop_ai_generation()
        with_aviso = [t for t in self.escritas if "interrompida" in t]
        self.assertTrue(with_aviso, "o aviso de interrupção não apareceu")
        for texto in with_aviso:
            self.assertEqual(texto.count("interrompida pelo usuário"), 1,
                             f"aviso duplicado: {texto!r}")

    def test_o_estado_do_mixin_reflete_a_tela(self):
        """`_current_full_text` tem que ficar igual ao que o balao mostra.

        E o que torna a guarda de idempotencia real. Sem essa escrita de
        volta, a guarda lia sempre o texto original e nunca disparava: o
        aviso unico saia por sorte, nao por desenho, e qualquer refactor que
        religasse um sinal passaria a duplicar o aviso sem nenhum teste
        reclamar.
        """
        win = self.win
        win.active_worker = self._worker_parado()
        win.stop_ai_generation()
        self.assertIn(
            "[Geração interrompida pelo usuário]", win._current_full_text[0],
            "o texto acumulado do mixin não recebeu o aviso que foi desenhado",
        )

    def test_resposta_vazia_vira_so_o_aviso(self):
        win = self.win
        win._current_full_text = ["   "]
        win.active_worker = self._worker_parado()
        win.stop_ai_generation()
        self.assertEqual(self.escritas, ["[Geração interrompida pelo usuário]"])

    def test_o_cronometro_para_em_vermelho(self):
        win = self.win
        win.active_worker = self._worker_parado()
        win.stop_ai_generation()
        texto, estilo = win._current_ai_bubble._lbl_timer.setText.call_args[0][0], \
            win._current_ai_bubble._lbl_timer.setStyleSheet.call_args[0][0]
        self.assertTrue(texto.startswith("⏹️"), texto)
        self.assertIn("#ef4444", estilo)

    def test_a_fila_e_limpa(self):
        win = self.win
        win.active_worker = self._worker_parado()
        win.stop_ai_generation()
        self.assertEqual(win.query_queue, [])

    def test_worker_cancela_e_sai_da_variavel(self):
        win = self.win
        worker = self._worker_parado()
        worker.cancel = mock.Mock()
        win.active_worker = worker
        win.stop_ai_generation()
        worker.cancel.assert_called_once()
        self.assertIsNone(win.active_worker)

    def test_sem_worker_nao_faz_nada(self):
        win = self.win
        win.active_worker = None
        win.stop_ai_generation()  # nao deve levantar
        win._current_render_timer.stop.assert_not_called()

    def test_o_worker_parado_avisa_que_cancelou(self):
        """`cancel()` precisa chegar ao worker: e ele que aborta o stream."""
        win = self.win
        worker = self._worker_parado()
        worker.cancel = mock.Mock()
        win.active_worker = worker
        win.stop_ai_generation()
        self.assertTrue(worker.cancel.called)


if __name__ == "__main__":
    unittest.main()
