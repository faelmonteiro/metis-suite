"""`CommandWorker`: o atalho instantaneo do `/executar`.

Este worker roda `executar_comando` direto na thread, sem passar pela IA, e foi
o arquivo que ganhou `auto_approve_temporario` junto com o `AIWorker` quando o
estado do auto-approve deixou de ser forcado no `finally`. Ficou sem teste
nenhum: a correcao do `run()` foi verificada so pelo lado do `AIWorker`, e as
duas classes nao compartilham codigo — a do `CommandWorker` e uma `QThread` com
dois sinais, nao um pipeline.

O risco aqui e especifico do caminho feliz: `executar_comando` e
auto-aprovado por construcao, e se o auto-approve nao estiver ligado no
contexto, o comando e negado — o usuario digita `/executar` e recebe "permissao
negada" sem nenhuma explicacao do motivo. O inverso tambem importa: o
auto-approve tem que estar **desligado** ao final, senao a proxima consulta da
IA herda a permissao de um comando de terminal.
"""

import os
import threading
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_APP = None


def _app():
    global _APP
    from PyQt6.QtWidgets import QApplication

    _APP = QApplication.instance() or QApplication([])
    return _APP


class _Registro:
    """Assiste a sequencia de sinais do worker."""

    def __init__(self, worker):
        self.eventos = []
        for nome in ("finished", "error_occurred"):
            getattr(worker, nome).connect(self._grava(nome))

    def _grava(self, nome):
        def _(*args):
            self.eventos.append((nome, args))
        return _


class TestCommandWorker(unittest.TestCase):
    def setUp(self):
        _app()
        from agente.services import tools_defs

        self.tools_defs = tools_defs
        # Estado global limpo: `/automode` no CLI mexe no fallback, e um teste
        # anterior que tenha ligado o modo deixaria o worker seguinte
        # comecando autorizado.
        self._fallback_anterior = vars(tools_defs).get("AUTO_APPROVE_MODE", None)
        vars(tools_defs)["AUTO_APPROVE_MODE"] = False
        self.addCleanup(self._restaura_fallback)

    def _restaura_fallback(self):
        if self._fallback_anterior is None:
            vars(self.tools_defs).pop("AUTO_APPROVE_MODE", None)
        else:
            vars(self.tools_defs)["AUTO_APPROVE_MODE"] = self._fallback_anterior

    def _worker(self, comando="ls -la"):
        from agente.gui.workers import CommandWorker

        return CommandWorker(comando)

    def _roda(self, worker, retorno="saida ok", erro=None):
        """Roda `run()` de verdade e devolve o registro dos sinais."""
        reg = _Registro(worker)
        self.addCleanup(worker.deleteLater)
        with mock.patch.object(
            self.tools_defs, "executar_comando",
            side_effect=erro if erro is not None else None,
            return_value=None if erro is not None else retorno,
        ) as chama:
            worker.run()
        return reg, chama

    # --- caminho feliz ------------------------------------------------------

    def test_executa_o_comando_e_emite_a_saida(self):
        worker = self._worker("ls -la")
        reg, chama = self._roda(worker, retorno="arquivo-a\narquivo-b")
        chama.assert_called_once_with("ls -la")
        self.assertEqual(reg.eventos, [("finished", ("ls -la", "arquivo-a\narquivo-b"))])

    def test_o_atalho_roda_com_auto_approve_ligado(self):
        """O comando precisa sair autorizado, senao e negado em silencio."""
        worker = self._worker("rm -rf /tmp/x")
        visto = {}

        def registra(cmd):
            visto["auto_approve"] = self.tools_defs.auto_approve_habilitado()
            return "ok"

        reg = _Registro(worker)
        self.addCleanup(worker.deleteLater)
        with mock.patch.object(self.tools_defs, "executar_comando", side_effect=registra):
            worker.run()
        self.assertTrue(visto.get("auto_approve"),
                        "executar_comando rodou sem auto-approve: seria negado")

    def test_o_atalho_usa_a_thread_do_worker(self):
        """O contexto e thread-local, entao o valor tem que estar na thread certa.

        Se `auto_approve_temporario` fosse aplicado na thread errada, o comando
        veria o fallback global — `False` — e seria negado.
        """
        worker = self._worker()
        visto = {}

        def registra(cmd):
            visto["thread"] = threading.current_thread().name
            return "ok"

        reg = _Registro(worker)
        self.addCleanup(worker.deleteLater)
        with mock.patch.object(self.tools_defs, "executar_comando", side_effect=registra):
            worker.run()
        self.assertEqual(visto.get("thread"), threading.current_thread().name)

    # --- auto-approve nao vaza ---------------------------------------------

    def test_o_auto_approve_desliga_depois(self):
        """O estado anterior da thread tem que voltar, nao ser forcado a False.

        E o bug que o contexto corrigeu no `AIWorker`, replicado aqui: quem
        forca `False` no fim deixa o atributo definido e ele sombrea o
        fallback global para sempre naquela thread.
        """
        worker = self._worker()
        self.tools_defs.definir_auto_approve(True)
        self.addCleanup(self._limpa_contexto)
        reg = _Registro(worker)
        self.addCleanup(worker.deleteLater)
        with mock.patch.object(self.tools_defs, "executar_comando", return_value="ok"):
            worker.run()
        # A thread do teste e a que roda o `run()` aqui, entao o contexto e o
        # mesmo que foi setado acima.
        self.assertTrue(
            self.tools_defs.auto_approve_habilitado(),
            "o auto-approve True de antes do comando nao foi restaurado",
        )

    def test_o_contexto_nao_sobra_definido(self):
        """Depois do comando, a thread nao pode ficar com atributo definido.

        E o que mantinha o `/automode` do CLI morto: o atributo existe, vale
        mais que o fallback, e nunca mais some.
        """
        from agente.services import tools_defs as td

        contexto = td._auto_approve_context
        if hasattr(contexto, "ativo"):
            del contexto.ativo
        self.addCleanup(self._limpa_contexto)

        worker = self._worker()
        reg = _Registro(worker)
        self.addCleanup(worker.deleteLater)
        with mock.patch.object(td, "executar_comando", return_value="ok"):
            worker.run()
        self.assertFalse(
            hasattr(contexto, "ativo"),
            "o contexto da thread ficou com `ativo` definido apos o comando",
        )
        self.assertFalse(td.auto_approve_habilitado(),
                         "o auto-approve ficou ligado depois do comando")

    def _limpa_contexto(self):
        contexto = self.tools_defs._auto_approve_context
        if hasattr(contexto, "ativo"):
            del contexto.ativo

    # --- caminho de erro ----------------------------------------------------

    def test_erro_emite_error_e_nao_finished(self):
        worker = self._worker("comando-quebrado")
        reg, _ = self._roda(worker, erro=RuntimeError("permissao negada"))
        self.assertEqual(len(reg.eventos), 1)
        nome, args = reg.eventos[0]
        self.assertEqual(nome, "error_occurred")
        self.assertIn("permissao negada", args[0])

    def test_erro_tambem_restaura_o_auto_approve(self):
        """O `finally` do contexto tem que rodar no erro tambem.

        Sem o `finally`, uma excecao deixaria o auto-approve ligado na thread e
        a proxima consulta da IA rodaria autorizada.
        """
        worker = self._worker("comando-quebrado")
        self.tools_defs.definir_auto_approve(True)
        self.addCleanup(self._limpa_contexto)
        reg = _Registro(worker)
        self.addCleanup(worker.deleteLater)
        with mock.patch.object(self.tools_defs, "executar_comando",
                               side_effect=RuntimeError("boom")):
            worker.run()
        self.assertTrue(self.tools_defs.auto_approve_habilitado(),
                        "o auto-approve True de antes nao voltou apos o erro")

    def test_saida_vazia_ainda_emite_finished(self):
        """Comando que nao imprime nada nao pode virar erro na GUI."""
        worker = self._worker("true")
        reg, _ = self._roda(worker, retorno="")
        self.assertEqual(reg.eventos, [("finished", ("true", ""))])


if __name__ == "__main__":
    unittest.main()
