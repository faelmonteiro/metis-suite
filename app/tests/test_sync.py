import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agente import config
from agente.providers_manager import (
    _atualizar_conteudo_env,
    sincronizar_config,
    salvar_servidor_customizado,
    obter_servidores_customizados
)


class TestConfigSync(unittest.TestCase):
    def test_atualizar_conteudo_env_preserva_comentarios_e_export(self):
        original = (
            '# Comentario inicial\n'
            'export GEMINI_API_KEY="" # Chave gemini\n'
            'GROQ_API_KEY="gsk_123"\n'
            'OLLAMA_HOST=http://localhost:11434\n'
        )
        # Atualizar chave com export
        atualizado = _atualizar_conteudo_env(original, "GEMINI_API_KEY", "AIzaSy_test_123")
        self.assertIn('export GEMINI_API_KEY="AIzaSy_test_123" # Chave gemini', atualizado)
        self.assertIn('# Comentario inicial', atualizado)
        self.assertIn('GROQ_API_KEY="gsk_123"', atualizado)

        # Atualizar chave existente sem export
        atualizado2 = _atualizar_conteudo_env(original, "GROQ_API_KEY", "gsk_nova_chave")
        self.assertIn('GROQ_API_KEY="gsk_nova_chave"', atualizado2)

        # Adicionar nova chave inexistente
        atualizado3 = _atualizar_conteudo_env(original, "NOVA_VARIAVEL", "valor_novo")
        self.assertIn('NOVA_VARIAVEL="valor_novo"', atualizado3)

    def test_sincronizar_config_atualiza_memoria_e_disco(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_env = Path(tmpdir) / ".env"
            temp_env.write_text('GEMINI_API_KEY=""\nDEFAULT_PROVIDER="ollama"\n')

            with patch("agente.providers_manager.get_target_env_files", return_value=[temp_env]):
                sincronizar_config("GEMINI_API_KEY", "AIzaSy_sync_test")

                # Verifica os.environ
                self.assertEqual(os.environ.get("GEMINI_API_KEY"), "AIzaSy_sync_test")
                # Verifica módulo config
                self.assertEqual(config.GEMINI_API_KEY, "AIzaSy_sync_test")
                # Verifica arquivo em disco
                conteudo = temp_env.read_text()
                self.assertIn('GEMINI_API_KEY="AIzaSy_sync_test"', conteudo)

    def test_salvar_servidor_customizado_sem_colisao_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_cfg = Path(tmpdir) / "config_models.json"
            temp_env = Path(tmpdir) / ".env"
            temp_env.write_text("")

            with patch("agente.providers_manager.get_config_file_path", return_value=temp_cfg), \
                 patch("agente.providers_manager.get_target_env_files", return_value=[temp_env]):
                
                # Criar 2 servidores com nomes genéricos vazios/símbolos
                s1 = salvar_servidor_customizado("---", "https://api1.com", "key1")
                s2 = salvar_servidor_customizado("---", "https://api2.com", "key2")

                self.assertNotEqual(s1["id"], s2["id"])
                servidores = obter_servidores_customizados()
                ids = [s["id"] for s in servidores]
                self.assertEqual(len(ids), len(set(ids)))

    def test_tool_call_id_uniqueness(self):
        from agente.services.base import process_tool_calls_map
        import unittest.mock as mock

        tc_map1 = {0: {"name": "executar_comando", "args_str": "{}", "id": ""}}
        tc_map2 = {0: {"name": "executar_comando", "args_str": "{}", "id": ""}}
        msgs1 = []
        msgs2 = []

        with mock.patch("agente.services.tool_executor.executar_tool", return_value="result"):
            process_tool_calls_map(tc_map1, msgs1, iteration=1)
            process_tool_calls_map(tc_map2, msgs2, iteration=1)

        id1 = msgs1[0]["functionCall"]["id"]
        id2 = msgs2[0]["functionCall"]["id"]
        self.assertNotEqual(id1, id2)
        self.assertEqual(msgs1[1]["id"], id1)
        self.assertEqual(msgs2[1]["id"], id2)

    def test_restaurar_servico_sessao(self):
        from agente.services.base import BaseService
        from agente.sessions.command_handlers import restaurar_servico_sessao
        from agente.history import HistoryManager
        import unittest.mock as mock

        class DummyService(BaseService):
            def __init__(self):
                self.model = "fallback-model"
            @property
            def nome_provedor(self) -> str:
                return "Dummy"
            def gerar_resposta_stream(self, historico):
                yield "ok"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("agente.config.HISTORICO_DIR", tmpdir):
                hm = HistoryManager(sessao="test_session")
                hm.saved_provider = "groq"
                hm.saved_model = "llama-3.3-70b-versatile"
                hm.salvar()

                # Recarrega do disco
                hm_reloaded = HistoryManager(sessao="test_session")
                self.assertEqual(hm_reloaded.saved_provider, "groq")
                self.assertEqual(hm_reloaded.saved_model, "llama-3.3-70b-versatile")

                current_srv = DummyService()
                restaurado = restaurar_servico_sessao(hm_reloaded, current_srv)
                self.assertEqual(restaurado.model, "llama-3.3-70b-versatile")
                self.assertIn("groq", restaurado.nome_provedor.lower())


if __name__ == "__main__":
    unittest.main()
