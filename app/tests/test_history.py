import unittest
import tempfile
import shutil
import json
from pathlib import Path

from agente import config
from agente.history import HistoryManager

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_historico_dir = config.HISTORICO_DIR
        config.HISTORICO_DIR = self.temp_dir

    def tearDown(self):
        config.HISTORICO_DIR = self.old_historico_dir
        shutil.rmtree(self.temp_dir)

    def test_criacao_sessao_e_salvamento(self):
        hm = HistoryManager("test_session")
        hm.adicionar_mensagem("user", "Hello world")
        hm.adicionar_mensagem("assistant", "Hi there")
        
        # Verify it's in memory
        self.assertEqual(len(hm.historico), 2)
        self.assertEqual(hm.historico[0]["content"], "Hello world")
        
        # Verify it was saved to disk
        expected_file = Path(self.temp_dir) / "test_session.json"
        self.assertTrue(expected_file.exists())
        
        with open(expected_file, "r") as f:
            dados = json.load(f)
            self.assertEqual(len(dados["historico"]), 2)
            self.assertEqual(dados["historico"][1]["role"], "assistant")

    def test_carregamento_sessao_existente(self):
        hm1 = HistoryManager("test_carregamento")
        hm1.adicionar_mensagem("user", "Primeira mensagem")
        hm1.adicionar_mensagem("assistant", "Resposta 1")
        
        # Simulate loading in a new instance
        hm2 = HistoryManager("test_carregamento")
        self.assertEqual(len(hm2.historico), 2)
        self.assertEqual(hm2.historico[0]["content"], "Primeira mensagem")
        self.assertEqual(hm2.contagem_conversas(), 1)

    def test_truncar_ate(self):
        hm = HistoryManager("test_truncar")
        hm.adicionar_mensagem("user", "Msg 1")
        hm.adicionar_mensagem("assistant", "Res 1")
        hm.adicionar_mensagem("user", "Msg 2")
        hm.adicionar_mensagem("assistant", "Res 2")
        
        self.assertEqual(hm.contagem_conversas(), 2)
        
        # Keep only the first turn (index 0)
        hm.truncar_ate(0)
        self.assertEqual(hm.contagem_conversas(), 1)
        self.assertEqual(len(hm.historico), 2)
        self.assertEqual(hm.historico[-1]["content"], "Res 1")

    def test_limitador_de_contexto(self):
        hm = HistoryManager("test_context")
        old_max = config.MAX_HISTORY_MESSAGES
        config.MAX_HISTORY_MESSAGES = 2  # Set to 2 messages (1 turn)
        
        hm.adicionar_mensagem("user", "U1")
        hm.adicionar_mensagem("assistant", "A1")
        hm.adicionar_mensagem("user", "U2")
        hm.adicionar_mensagem("assistant", "A2")
        hm.adicionar_mensagem("user", "U3")
        
        contexto = hm.obter_contexto()
        # Max is 2, but the first must be a user message.
        # Last two messages are "A2" and "U3".
        # Pop until first is user: "A2" is popped -> leaves ["U3"]
        self.assertEqual(len(contexto), 1)
        self.assertEqual(contexto[0]["content"], "U3")
        
        config.MAX_HISTORY_MESSAGES = old_max

    def test_deletar_e_listar_sessoes(self):
        hm1 = HistoryManager("sessao_a")
        hm1.adicionar_mensagem("user", "Oi")
        hm2 = HistoryManager("sessao_b")
        hm2.adicionar_mensagem("user", "Ola")

        sessoes = HistoryManager.listar_sessoes()
        self.assertIn("sessao_a", sessoes)
        self.assertIn("sessao_b", sessoes)

        # Deletar sessão A
        self.assertTrue(hm1.deletar_sessao())
        sessoes_apos = HistoryManager.listar_sessoes()
        self.assertNotIn("sessao_a", sessoes_apos)
        self.assertIn("sessao_b", sessoes_apos)

    def test_renomear_sessao(self):
        hm = HistoryManager("sessao_antiga")
        hm.adicionar_mensagem("user", "Teste")
        self.assertTrue(hm.renomear_sessao("sessao_nova"))
        self.assertEqual(hm.sessao, "sessao_nova")
        self.assertTrue(hm.file_path.exists())

    def test_nao_mutar_modelo_global_ao_carregar(self):
        config.OLLAMA_MODEL = "modelo_ativo_original"
        # Cria sessão com outro modelo salvo no JSON
        file_path = Path(self.temp_dir) / "sessao_com_outro_modelo.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"OLLAMA_MODEL": "outro_modelo_antigo", "historico": [{"role": "user", "content": "teste"}]}, f)

        # Instancia HistoryManager para a sessão
        hm = HistoryManager("sessao_com_outro_modelo")
        # Deve ler self.saved_model sem alterar config.OLLAMA_MODEL
        self.assertEqual(hm.saved_model, "outro_modelo_antigo")
        self.assertEqual(config.OLLAMA_MODEL, "modelo_ativo_original")

    def test_preservar_tool_calls_no_historico(self):
        file_path = Path(self.temp_dir) / "sessao_com_tools.json"
        msgs = [
            {"role": "user", "content": "qual a memoria?"},
            {"role": "functionCall", "functionCall": {"name": "executar_comando", "args": {"comando": "free -m"}}},
            {"role": "functionResponse", "name": "executar_comando", "content": "total 16G"},
            {"role": "assistant", "content": "Voce tem 16G de memoria."}
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"historico": msgs}, f)

        hm = HistoryManager("sessao_com_tools")
        self.assertEqual(len(hm.historico), 4)
        roles = [m["role"] for m in hm.historico]
        self.assertEqual(roles, ["user", "functionCall", "functionResponse", "assistant"])


if __name__ == "__main__":
    unittest.main()
