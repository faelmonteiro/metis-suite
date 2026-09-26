"""Comandos slash: cada um tem que cair no metodo certo.

O `test_impressao_digital_da_arvore` cobre a montagem visual. Aqui nao ha
widget nenhum involved — o risco e de rota: um `/sessao` que cai no handler de
`/novo` nao quebra build, nao quebra print digital e nao quebra nenhuma
assertiva pontual. So um teste que executa o despacho e ve quem foi chamado.

Cada caso substitui os handlers por gravadores, despacha e confere quem
disparou. Nao testa a implementacao de cada handler (isso e do handler), testa
a tabela de rotas.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


_APP = None


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


# Metodos que o despacho pode chamar, e o que cada um faz. Nenhum e lido de
# verdade aqui: sao substituidos por `mock.Mock()`.
HANDLERS = (
    "show_apis_dialog", "show_agent_options_dialog", "show_restore_server_dialog",
    "show_help_dialog", "show_status_dialog", "open_oracles_page",
    "open_appearance_page", "retry_last_query", "export_current_session",
    "handle_menu_action", "open_sessions_page", "open_file_dialog",
    "set_attachment", "clear_chat_view", "refresh_telemetry",
    "start_ai_query", "add_chat_bubble", "mover_para_canto_superior_direito",
    "activate_ollama", "activate_gemini", "activate_groq", "activate_nvidia",
    "activate_g4f", "activate_custom_server",
)


class TestComandosSlash(unittest.TestCase):
    """Roteamento de `process_text_command_or_query`."""

    def setUp(self):
        self.win = _janela()
        self.win.stack.setCurrentIndex(1)  # chat: desliga o atalho do dashboard
        self.gravados = []
        # Cada teste ganha uma janela nova, entao basta sobrescrever os
        # handlers direto: nao ha estado compartilhado a restaurar.
        for nome in HANDLERS:
            setattr(self.win, nome, mock.Mock(side_effect=self._registra(nome)))
        # /limpar passa pelo gerenciador, e nao por um handler da tabela
        hist = mock.Mock(sessao="atual")
        hist.limpar.side_effect = self._registra("history_limpar")
        self.win.history_manager = hist
        # HistoryManager escreveria arquivo de sessao de verdade
        self.patcher = mock.patch(
            "agente.gui.pages.ai.HistoryManager",
            side_effect=lambda nome: mock.Mock(sessao=nome),
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()

    def _registra(self, nome):
        def _(*args, **kwargs):
            self.gravados.append((nome, args, kwargs))
        return _

    def despacha(self, texto):
        self.gravados.clear()
        self.win.process_text_command_or_query(texto)
        return [n for n, _, _ in self.gravados]

    def _nao_eh(self, texto, *proibidos):
        """Falha se algum handler proibido for chamado."""
        chamados = self.despacha(texto)
        for p in proibidos:
            self.assertNotIn(p, chamados,
                             f"{texto!r} disparou {p} (chamou {chamados})")

    def _eh(self, texto, esperado):
        chamados = self.despacha(texto)
        self.assertEqual(chamados, list(esperado),
                         f"{texto!r} -> {chamados}, esperado {list(esperado)}")

    def _args(self, posicao=0):
        """Argumentos da n-esima chamada registrada."""
        return self.gravados[posicao][1]

    def _kwargs(self, posicao=0):
        """Keywords da n-esima chamada registrada."""
        return self.gravados[posicao][2]

    def test_comandos_de_um_passo(self):
        """A tabela _COMANDOS_DIRETOS roteia pelo nome do metodo."""
        esperado = {
            "/api": "show_apis_dialog",
            "/chaves": "show_apis_dialog",
            "/key": "show_apis_dialog",
            "/opcoes": "show_agent_options_dialog",
            "/opcao": "show_agent_options_dialog",
            "/opção": "show_agent_options_dialog",
            "/avancado": "show_agent_options_dialog",
            "/agent": "show_agent_options_dialog",
            "/restaurar": "show_restore_server_dialog",
            "/reativar": "show_restore_server_dialog",
            "/ajuda": "show_help_dialog",
            "/help": "show_help_dialog",
            "/status": "show_status_dialog",
            "/oraculo": "open_oracles_page",
            "/provedores": "open_oracles_page",
            "/tema": "open_appearance_page",
            "/manto": "open_appearance_page",
            "/estilos": "open_appearance_page",
            "/retry": "retry_last_query",
            "/repetir": "retry_last_query",
        }
        for comando, metodo in esperado.items():
            with self.subTest(comando=comando):
                self._eh(comando, [metodo])

    def test_comandos_de_um_passo_sao_case_insensitive(self):
        """O despacho normaliza com lower().strip() antes de comparar."""
        self._eh("  /AJUDA  ", ["show_help_dialog"])
        self._eh("/TEMA", ["open_appearance_page"])

    def test_limpar_usa_o_gerenciador_e_repinta(self):
        """`/limpar` e tres chamadas, nao um handler so."""
        self._eh("/limpar", ["history_limpar", "clear_chat_view", "refresh_telemetry"])

    def test_deletar_tudo_delega_ao_cartao_5(self):
        """/deletar_tudo reaproveita o fluxo do cartao PURIFICAR MEMORIA."""
        self._eh("/deletar_tudo", ["handle_menu_action"])
        self.assertEqual(self._args(), ("5",))

    def test_exportar_aceita_prefixo(self):
        """`/exportar` e startswith: `/exportar x` tambem exporta."""
        self._eh("/exportar", ["export_current_session"])
        self._eh("/exportar algo", ["export_current_session"])

    def test_sessao_sem_argumento_abre_a_pagina(self):
        self._eh("/sessao", ["open_sessions_page"])
        self._eh("/sessoes", ["open_sessions_page"])

    def test_sessao_com_argumento_troca_o_gerenciador(self):
        """Com nome, nao navega: abre a sessao e limpa a conversa."""
        self.gravados.clear()
        with mock.patch("agente.gui.pages.ai.HistoryManager") as hm:
            hm.side_effect = lambda nome: mock.Mock(sessao=nome)
            self.win.process_text_command_or_query("/sessao projeto-novo")
        hm.assert_called_once_with("projeto-novo")
        self.assertEqual(
            [n for n, _, _ in self.gravados],
            ["clear_chat_view", "refresh_telemetry"],
        )

    def test_novo_sem_argumento_gera_nome_com_timestamp(self):
        with mock.patch("agente.gui.pages.ai.HistoryManager") as hm:
            hm.side_effect = lambda nome: mock.Mock(sessao=nome)
            with mock.patch("agente.gui.pages.ai.sanitizar_nome_sessao",
                            side_effect=lambda s: s):
                self.win.process_text_command_or_query("/novo")
        (nome,), _ = hm.call_args
        self.assertTrue(nome.startswith("chat_"), f"nome inesperado: {nome}")

    def test_novo_com_argumento_sanitiza(self):
        with mock.patch("agente.gui.pages.ai.HistoryManager") as hm:
            hm.side_effect = lambda nome: mock.Mock(sessao=nome)
            with mock.patch("agente.gui.pages.ai.sanitizar_nome_sessao") as san:
                san.side_effect = lambda s: s.upper()
                self.win.process_text_command_or_query("/novo meu nome")
        san.assert_called_once_with("meu nome")
        hm.assert_called_once_with("MEU NOME")

    def test_web_liga_o_checkbox_e_consulta(self):
        self._eh("/web quem e metis", ["start_ai_query"])
        self.assertTrue(self.win.chk_web.isChecked())
        self.assertEqual(self._args(0), ("quem e metis",))
        self.assertTrue(self._kwargs(0).get("forcar_web"),
                        "/web tem que forcar a busca web")

    def test_arquivo_com_caminho_anexa_e_limpa_os_campos(self):
        """Com caminho: set_attachment. Sem caminho: abre o seletor."""
        self._eh("/arquivo /tmp/nota.txt", ["set_attachment"])
        self._eh("/arquivo", ["open_file_dialog"])

    def test_modelo_sem_argumento_so_abre_a_pagina(self):
        self._eh("/modelo", ["open_oracles_page"])

    def test_modelo_troca_o_provider_por_nome(self):
        """Troca o provider e confirma com dois baloes no chat."""
        for token, metodo in (
            ("ollama", "activate_ollama"),
            ("gemini", "activate_gemini"),
            ("groq", "activate_groq"),
            ("nvidia", "activate_nvidia"),
            ("g4f", "activate_g4f"),
        ):
            with self.subTest(provedor=token):
                self._eh(f"/modelo {token}", [metodo] + self._confirmacao())

    def _confirmacao(self):
        """O que `/modelo` faz depois de ativar, estando no chat."""
        return ["add_chat_bubble", "add_chat_bubble", "refresh_telemetry"]

    def test_modelo_usa_o_padrao_quando_falta_o_modelo(self):
        from agente import config

        self.win.stack.setCurrentIndex(1)
        self.gravados.clear()
        self.win.process_text_command_or_query("/modelo ollama")
        self.assertEqual(self._args(), (config.OLLAMA_MODEL,))

    def test_modelo_desconhecido_abre_oraculos(self):
        """Sem provider conhecido, nem modelo direto: volta pra pagina."""
        with mock.patch("agente.gui.pages.ai.ollama_service.listar_modelos",
                        return_value=[]), \
             mock.patch("agente.gui.pages.ai.obter_servidor_customizado",
                        return_value=None), \
             mock.patch("agente.gui.pages.ai.obter_modelos_provedor",
                        return_value=[]):
            self._eh("/modelo nada-disso", ["open_oracles_page"])

    def test_modelo_encontra_servidor_customizado(self):
        srv = {"nome": "MeuServer", "modelo_atual": "default"}
        with mock.patch("agente.gui.pages.ai.obter_servidor_customizado",
                        return_value=srv):
            self._eh("/modelo meuserver llama-3",
                     ["activate_custom_server"] + self._confirmacao())
        self.assertEqual(self._args(), (srv, "llama-3"))

    def test_texto_livre_vira_consulta(self):
        """Sem comando slash, e pergunta normal para a IA."""
        self._eh("qual a capital da Franca?", ["start_ai_query"])
        self.assertEqual(self._args(0)[0], "qual a capital da Franca?")

    def test_atalho_do_dashboard_somente_na_pagina_zero(self):
        """1..6 so acionam cartoes no painel inicial."""
        self.win.stack.setCurrentIndex(0)
        self._eh("3", ["handle_menu_action"])
        self.assertEqual(self._args(), ("3",))
        # no chat, "3" e pergunta, nao atalho
        self.win.stack.setCurrentIndex(1)
        self._eh("3", ["start_ai_query"])

    def test_numero_copia_comando_extraido(self):
        """No chat, 1..N copia o comando N da resposta anterior."""
        self.win.last_extracted_commands = [("shell", "ls -la", "lista arquivos")]
        with mock.patch("agente.gui.pages.ai.copiar_para_area_de_transferencia") as cp:
            self._eh("1", [])
        cp.assert_called_once_with("ls -la")
        self.assertIn("copiado", self.win.chat_input.placeholderText())

    def test_numero_fora_da_faixa_avisa_sem_engolir(self):
        """9 nao copia nada, mas avisa — e o aviso volta sozinho."""
        self.win.last_extracted_commands = [("shell", "ls", "x")]
        with mock.patch("agente.gui.pages.ai.copiar_para_area_de_transferencia") as cp:
            self.gravados.clear()
            self.win.process_text_command_or_query("9")
        cp.assert_not_called()
        self.assertIn("inválido", self.win.chat_input.placeholderText())

    def test_comandos_com_argumento_nao_cai_na_consulta(self):
        """Nenhum comando com argumento pode vazar para `start_ai_query`.

        `/web` e a excecao proposital: ele existe para consultar, entao vai
        para a IA de proposito (com `forcar_web=True`).
        """
        for texto in ("/sessao x", "/novo x", "/modelo ollama",
                      "/arquivo x", "/exportar x"):
            with self.subTest(texto=texto):
                self._nao_eh(texto, "start_ai_query")


if __name__ == "__main__":
    unittest.main()
