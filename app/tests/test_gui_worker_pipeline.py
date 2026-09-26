"""`AIWorker.run`: o pipeline que produz a resposta.

Duas classes de risco, e nenhuma delas aparece em fingerprint de arvore.

A primeira e a composicao do prompt. Sao quatro decisoes que se anulam e
dependem uma da outra — contexto do historico, system prompt, texto do anexo na
frente, e o bloco `<search_results>` com a regra de seguranca contra injecao de
prompt. Um erro ali nao quebra nada: a IA simplesmente responde a outra coisa,
ou obedece a uma instrucao que veio de dentro dos resultados de busca.

A segunda e a ordem dos sinais. `chunk_received` precisa chegar na ordem, o
`finished_response` tem de vir depois do ultimo chunk, e o `error_occurred` nao
pode vir com um `finished_response` junto. Um `emit` fora de ordem nao quebra
build e nao quebra nenhuma assertiva de widget.

Por isso os testes trocam o servico e o historico por dublês e rodam `run()` de
verdade, assistindo a sequencia de sinais.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_APP = None

# A ordem completa que `run()` produz no caminho feliz. Um sinal fora de lugar
# aqui e um bug de interface que o usuario ve na hora.
SINAIS_ESPERADOS = [
    "tool_started", "search_started", "search_done", "tool_finished",
    "chunk_received", "finished_response",
]


def _app():
    global _APP
    from PyQt6.QtWidgets import QApplication
    _APP = QApplication.instance() or QApplication([])
    return _APP


class _ServicoDuble:
    """Servico de oráculo que devolve chunks pré-definidos."""

    def __init__(self, chunks=("resposta",), erro=None, nome_provedor="groq"):
        self.chunks = list(chunks)
        self.erro = erro
        self.nome_provedor = nome_provedor
        self.recebeu = None

    def gerar_resposta_stream(self, mensagens):
        self.recebeu = mensagens
        if self.erro is not None:
            raise self.erro
        for c in self.chunks:
            yield c


class _HistoricoDuble:
    def __init__(self, contexto=None, erro=None):
        self.contexto = list(contexto or [])
        self.erro = erro
        self.salvou = []

    def obter_contexto(self):
        return [dict(m) for m in self.contexto]

    def adicionar_mensagem(self, papel, conteudo, media_paths=None):
        if self.erro is not None:
            raise self.erro
        self.salvou.append((papel, conteudo, media_paths))


def _worker(**kw):
    from agente.gui.workers import AIWorker
    from agente.prompts import build_system_prompt
    w = AIWorker(
        pergunta=kw.pop("pergunta", "pergunta"),
        history_manager=kw.pop("hm", _HistoricoDuble()),
        service=kw.pop("service", _ServicoDuble()),
        forcar_web=kw.pop("forcar_web", False),
        media_paths=kw.pop("media_paths", None),
        file_attachment_context=kw.pop("file_attachment_context", None),
    )
    return w


class _Registro:
    """Assiste a sequencia de sinais emitida pelo worker."""

    def __init__(self, worker):
        self.eventos = []
        for nome in ("chunk_received", "search_started", "search_done",
                     "tool_started", "tool_finished", "tool_executed",
                     "finished_response", "error_occurred"):
            sinal = getattr(worker, nome)
            sinal.connect(self._grava(nome))

    def _grava(self, nome):
        def _(*args):
            self.eventos.append((nome,) + args)
        return _

    def nomes(self):
        return [e[0] for e in self.eventos]

    def de(self, nome):
        return [e for e in self.eventos if e[0] == nome]


class TestPipelineDoWorker(unittest.TestCase):
    def setUp(self):
        _app()
        from agente.gui.workers import AIWorker
        self.AIWorker = AIWorker
        self.busca = mock.patch("agente.services.searxng_service.buscar_web",
                                return_value="conteudo da web")
        self.busca.start()
        self.addCleanup(self.busca.stop)
        self.registros = []
        # O listener de ferramentas e global; sem este patch, `run()` registra
        # um listener real que sobrevive ao teste.
        self.registro_listener = mock.patch(
            "agente.services.tool_executor.register_tool_listener")
        self.unregistro = mock.patch(
            "agente.services.tool_executor.unregister_tool_listener")
        self.registro_listener.start()
        self.unregistro.start()
        self.addCleanup(self.registro_listener.stop)
        self.addCleanup(self.unregistro.stop)
        self.prompt = mock.patch(
            "agente.gui.workers.build_system_prompt", return_value="")
        self.prompt_mock = self.prompt.start()
        self.addCleanup(self.prompt.stop)

    def roda(self, worker, com_web=False):
        """Roda `run()` de verdade e devolve o registro dos sinais."""
        reg = _Registro(worker)
        self.registros.append(reg)
        if com_web:
            worker.forcar_web = True
        worker.run()
        return reg

    # sinais ----------------------------------------------------------------

    def test_caminho_feliz_emite_nesta_ordem(self):
        w = _worker(service=_ServicoDuble(chunks=["a", "b"]))
        reg = self.roda(w)
        self.assertEqual(reg.nomes(), ["chunk_received"] * 2 + ["finished_response"])

    def test_stream_inteiro_e_repassado(self):
        w = _worker(service=_ServicoDuble(chunks=["a", "b", "c"]))
        reg = self.roda(w)
        self.assertEqual("".join(e[1] for e in reg.de("chunk_received")), "abc")

    def test_resposta_final_e_o_texto_completo(self):
        w = _worker(service=_ServicoDuble(chunks=["abc"]))
        reg = self.roda(w)
        self.assertEqual(reg.de("finished_response")[0][1], "abc")

    def test_chunk_vazio_ainda_fala_na_historico(self):
        """Servico que nao devolve nada nao pode deixar a conversa pela metade."""
        w = _worker(service=_ServicoDuble(chunks=[]))
        reg = self.roda(w)
        self.assertEqual(len(reg.de("finished_response")), 1)
        self.assertTrue(reg.de("finished_response")[0][1].strip())

    def test_historico_guarda_o_par(self):
        w = _worker(service=_ServicoDuble(chunks=["resposta"]))
        self.roda(w)
        self.assertEqual([p for p, _, _ in w.hm.salvou], ["user", "assistant"])

    def test_erro_vira_error_occurred_sem_finished(self):
        w = _worker(service=_ServicoDuble(erro=RuntimeError("sem credito")))
        reg = self.roda(w)
        self.assertEqual(reg.nomes(), ["error_occurred"])
        self.assertIn("sem credito", reg.de("error_occurred")[0][1])

    def test_erro_tambem_e_guardado_na_historico(self):
        w = _worker(service=_ServicoDuble(erro=RuntimeError("sem credito")))
        self.roda(w)
        self.assertIn("sem credito", w.hm.salvou[1][1])

    def test_erro_na_historico_nao_esconde_o_erro_original(self):
        """Se o historico falhar ao gravar, o erro do oráculo ainda chega."""
        w = _worker(service=_ServicoDuble(erro=RuntimeError("sem credito")),
                    hm=_HistoricoDuble(erro=OSError("disco cheio")))
        reg = self.roda(w)
        self.assertEqual(reg.nomes(), ["error_occurred"])
        self.assertIn("sem credito", reg.de("error_occurred")[0][1])

    def test_cancelar_no_meio_do_stream(self):
        """Cancelar durante o stream marca a resposta como interrompida."""
        w = _worker(service=_ServicoDuble(chunks=["a", "b", "c"]))
        reg = _Registro(w)
        w.chunk_received.connect(lambda *_: w.cancel())
        w.run()
        self.assertIn("[Geração interrompida", reg.de("finished_response")[0][1])

    def test_cancelado_nao_tenta_buscar_nem_consultar(self):
        w = _worker(forcar_web=True)
        w.cancel()
        reg = self.roda(w)
        self.assertNotIn("search_started", reg.nomes())
        self.assertIsNone(w.service.recebeu)

    def test_cancelado_sem_gerar_nada_nao_salva_nada(self):
        """Cancela no meio do stream sem devolver chunk algum.

        E o unico caminho que chega ao ramo "cancelado" com resposta vazia: sem
        texto, nao ha nada para salvar, mas o `finished_response` ainda sai —
        senao a GUI ficaria esperando para sempre.
        """
        alvo = {}

        class _CancelaSemGerar(_ServicoDuble):
            def gerar_resposta_stream(self, mensagens):
                self.recebeu = mensagens
                alvo["worker"].cancel()
                return
                yield  # deixa o metodo ser gerador

        w = _worker(service=_CancelaSemGerar(chunks=[]))
        alvo["worker"] = w
        reg = self.roda(w)
        self.assertEqual(reg.nomes(), ["finished_response"])
        self.assertEqual(reg.de("finished_response")[0][1], "")
        self.assertEqual(w.hm.salvou, [])

    def test_marca_de_interrupcao_e_idempotente(self):
        """Nenhum fluxo do pipeline chama duas vezes, mas o contrato vale.

        Se um dia alcancar, o usuario ve "[Geração interrompida pelo usuario]"
        repetido duas vezes no fim da resposta, e parece bug de loop.
        """
        w = _worker()
        w._current_checklist = None
        reg = _Registro(w)
        primeira = w._marcar_interrompida("resposta")
        segunda = w._marcar_interrompida(primeira)
        self.assertEqual(primeira.count("[Geração interrompida"), 1)
        self.assertEqual(segunda, primeira)
        self.assertEqual(
            len([e for e in reg.eventos if e[0] == "chunk_received"]), 1)

    def test_cancelado_grava_a_midia(self):
        """Cancelado com anexo tem que gravar a midia, como os outros caminhos.

        Este foi o unico dos tres saidas do pipeline que nao gravava
        `media_paths` na mensagem do usuario. O de erro tambem nao devolve
        resposta util e gravava com. `media_paths` registra "esta mensagem
        tinha estes anexos": sem ele, o historico guarda uma pergunta sobre
        imagem que nao tem imagem, e os servicos (base.py, gemini, ollama) nao
        acham o que reenviar ao remontar a requisicao.
        """
        w = _worker(service=_ServicoDuble(chunks=["a"]), media_paths=["/tmp/a.png"])
        reg = _Registro(w)
        w.chunk_received.connect(lambda *_: w.cancel())
        w.run()
        self.assertEqual(w.hm.salvou[0][2], ["/tmp/a.png"])

    def test_cancelado_e_erro_gravam_a_midia_igual(self):
        """Trava a decisao: os tres caminhos que salvam, salvam igual.

        Sem isto, reintroduzir a assimetria passa: so o caminho de cancelamento
        seria testado, e ele e o unico que nao tem teste de erro equivalente.
        """
        def midia_de(worker):
            return worker.hm.salvou[0][2]

        w_norm = _worker(media_paths=["/tmp/a.png"])
        self.roda(w_norm)

        w_can = _worker(service=_ServicoDuble(chunks=["a"]), media_paths=["/tmp/a.png"])
        _Registro(w_can)
        w_can.chunk_received.connect(lambda *_: w_can.cancel())
        w_can.run()

        w_err = _worker(
            service=_ServicoDuble(erro=RuntimeError("boom")),
            media_paths=["/tmp/a.png"],
        )
        _Registro(w_err)
        w_err.run()

        self.assertEqual(midia_de(w_norm), ["/tmp/a.png"])
        self.assertEqual(midia_de(w_can), midia_de(w_norm))
        self.assertEqual(midia_de(w_err), midia_de(w_norm))

    def test_normal_grava_a_midia(self):
        w = _worker(media_paths=["/tmp/a.png"])
        self.roda(w)
        self.assertEqual(w.hm.salvou[0][2], ["/tmp/a.png"])

    def test_cancelado_ainda_salva_o_que_gerou(self):
        w = _worker(service=_ServicoDuble(chunks=["a", "b"]))
        reg = _Registro(w)
        w.chunk_received.connect(lambda *_: w.cancel())
        w.run()
        papeis = [p for p, _, _ in w.hm.salvou]
        self.assertEqual(papeis, ["user", "assistant"])

    # montagem do prompt ----------------------------------------------------

    def _prompt_da_ultima(self, w):
        return w.service.recebeu[-1]["content"]

    def test_pergunta_vai_como_mensagem_do_usuario(self):
        w = _worker(pergunta="qual a temperatura?")
        self.roda(w)
        self.assertEqual(self._prompt_da_ultima(w), "qual a temperatura?")

    def test_contexto_do_historico_e_mantido(self):
        w = _worker(hm=_HistoricoDuble(contexto=[
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "olá"},
        ]))
        self.roda(w)
        papeis = [m["role"] for m in w.service.recebeu]
        self.assertEqual(papeis, ["user", "assistant", "user"])

    def test_system_prompt_vai_primeiro(self):
        """Primeiro de tudo, mesmo com historico cheio.

        Com historico vazio, `insert(0, ...)` e `append(...)` dao o mesmo
        resultado — entao o teste so prova alguma coisa se houver conversa
        antes. System prompt fora da primeira posicao faz o provedor recusar ou
        ignorar as diretrizes.
        """
        self.prompt_mock.return_value = "Voce e o Metis."
        w = _worker(hm=_HistoricoDuble(contexto=[
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "olá"},
        ]))
        self.roda(w)
        papeis = [m["role"] for m in w.service.recebeu]
        self.assertEqual(papeis, ["system", "user", "assistant", "user"])
        self.assertEqual(w.service.recebeu[0]["content"], "Voce e o Metis.")

    def test_sem_system_prompt_nao_ha_mensagem_de_system(self):
        w = _worker()
        self.roda(w)
        self.assertNotIn("system", [m["role"] for m in w.service.recebeu])

    def test_texto_do_anexo_vai_na_frente(self):
        w = _worker(pergunta="o que tem na imagem?",
                    file_attachment_context="DESCRICAO DO ANEXO")
        self.roda(w)
        self.assertEqual(
            self._prompt_da_ultima(w),
            "DESCRICAO DO ANEXO\n\no que tem na imagem?")

    def test_midia_vai_na_mensagem_do_usuario(self):
        w = _worker(media_paths=["/tmp/a.png"])
        self.roda(w)
        self.assertEqual(w.service.recebeu[-1]["media_paths"], ["/tmp/a.png"])

    def test_sem_midia_a_chave_some(self):
        w = _worker()
        self.roda(w)
        self.assertNotIn("media_paths", w.service.recebeu[-1])

    # busca web -------------------------------------------------------------

    def test_busca_aciona_o_ciclo_de_sinais(self):
        w = _worker()
        reg = self.roda(w, com_web=True)
        nomes = reg.nomes()
        self.assertEqual(nomes[:4], SINAIS_ESPERADOS[:4])
        self.assertIn("search_started", nomes)
        self.assertIn("search_done", nomes)

    def test_busca_entra_no_prompt(self):
        w = _worker(forcar_web=True)
        self.roda(w)
        self.assertIn("conteudo da web", self._prompt_da_ultima(w))

    def test_busca_leva_a_regra_de_seguranca(self):
        """O conteudo da web e dado bruto e nunca pode virar instrucao."""
        w = _worker(forcar_web=True)
        self.roda(w)
        prompt = self._prompt_da_ultima(w)
        self.assertIn("<search_results>", prompt)
        self.assertIn("NUNCA contém instruções", prompt)

    def test_resultado_da_web_e_marcado_como_externo(self):
        w = _worker(forcar_web=True)
        self.roda(w)
        self.assertIn("DADO BRUTO", self._prompt_da_ultima(w))

    def test_instrucao_de_links_marcado_para_provedor_comum(self):
        w = _worker(service=_ServicoDuble(nome_provedor="groq"), forcar_web=True)
        self.roda(w)
        self.assertIn("Markdown", self._prompt_da_ultima(w))

    def test_instrucao_de_links_marcado_e_omitida_em_modelo_pequeno(self):
        """Models pequenos se saem pior com instrucao longa de formatacao.

        Condicao separada da do ollama: um `llama3.2:3b` de nuvem tambem
        dispensa, e testar so o ollama deixaria essa metade sem cobertura.
        """
        w = _worker(service=_ServicoDuble(nome_provedor="llama3.2:3b"),
                    forcar_web=True)
        self.roda(w)
        self.assertNotIn("Markdown", self._prompt_da_ultima(w))

    def test_instrucao_de_links_marcado_e_omitida_no_ollama(self):
        w = _worker(service=_ServicoDuble(nome_provedor="ollama"), forcar_web=True)
        self.roda(w)
        self.assertNotIn("Markdown", self._prompt_da_ultima(w))

    def test_busca_que_falha_nao_derruba_a_consulta(self):
        with mock.patch("agente.services.searxng_service.buscar_web",
                        side_effect=OSError("dns")):
            w = _worker(forcar_web=True)
            reg = self.roda(w)
        self.assertIn("finished_response", reg.nomes())
        self.assertNotIn("search_done", reg.nomes())
        fim = reg.de("tool_finished")[0][1]
        self.assertIn("dns", fim["result"])
        self.assertFalse(fim["success"],
                         "`success` falso e o que pinta a ferramenta de vermelho")

    def test_busca_sem_resultado_conta_como_sucesso(self):
        """Nada encontrado e uma busca que funcionou, e nao uma busca quebrada.

        Distinguir os dois importa: `success` falso pinta a ferramenta de
        vermelho no checklist e sugere conexao com o oráculo, que nao e o caso.
        """
        with mock.patch("agente.services.searxng_service.buscar_web",
                        return_value=""):
            w = _worker(forcar_web=True)
            reg = self.roda(w)
        fim = reg.de("tool_finished")[0][1]
        self.assertTrue(fim["success"])
        self.assertIn("Nenhum resultado", fim["result"])
        self.assertNotIn("search_done", reg.nomes(),
                         "sem conteudo nao ha o que mostrar")

    def test_busca_que_da_certo_marca_o_sucesso(self):
        w = _worker(forcar_web=True)
        reg = self.roda(w)
        self.assertTrue(reg.de("tool_finished")[0][1]["success"])

    # auto-approve: o `finally` nao pode destruir estado de quem chamou ----

    def test_run_nao_apaga_o_auto_approve_de_quem_chamou(self):
        """Regressao: o `finally` usava forcar `False` em vez de restaurar.

        Como o valor e thread-local, forcar `False` deixa um atributo definido
        na thread, e definido tem prioridade sobre o fallback global — o
        `/automode` do CLI morria para sempre ali, sem erro nenhum, e as
        ferramentas de escrita passavam a ser negadas em silencio.
        """
        from agente.services import tools_defs
        contexto = tools_defs._auto_approve_context
        if hasattr(contexto, "ativo"):
            del contexto.ativo
        tools_defs.definir_auto_approve(True)
        try:
            w = _worker()
            self.roda(w)
            self.assertTrue(tools_defs.auto_approve_habilitado(),
                            "durante o run o auto-approve tem que estar ligado")
            self.assertTrue(tools_defs.auto_approve_habilitado(),
                            "depois do run o estado anterior nao foi restaurado")
        finally:
            if hasattr(contexto, "ativo"):
                del contexto.ativo

    def test_run_deixa_o_fallback_global_intacto(self):
        from agente.services import tools_defs
        tools_defs.AUTO_APPROVE_MODE = True
        try:
            self.assertTrue(tools_defs.auto_approve_habilitado())
            self.roda(_worker())
            self.assertTrue(
                tools_defs.auto_approve_habilitado(),
                "o fallback global ficou sombreado pelo run()")
        finally:
            if "AUTO_APPROVE_MODE" in vars(tools_defs):
                del tools_defs.AUTO_APPROVE_MODE

    def test_run_nao_deixa_rastro_na_thread(self):
        """A thread tem que voltar a nao ter valor proprio."""
        from agente.services import tools_defs
        contexto = tools_defs._auto_approve_context
        if hasattr(contexto, "ativo"):
            del contexto.ativo
        self.roda(_worker())
        self.assertFalse(hasattr(contexto, "ativo"),
                         "o run() deixou `ativo` definido sem precisar")

    def test_cancela_antes_de_buscar_pula_a_busca(self):
        w = _worker(forcar_web=True)
        w.cancel()
        reg = self.roda(w)
        self.assertNotIn("search_started", reg.nomes())


if __name__ == "__main__":
    unittest.main()
