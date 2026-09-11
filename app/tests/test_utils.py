import unittest
from agente.ui.clipboard import extrair_blocos

class TestUtils(unittest.TestCase):
    def test_extrair_bloco_shell_com_tag(self):
        resposta = "Aqui está o comando:\n```bash\nls -l\npwd\n```\nExecute-o."
        blocos_shell, blocos_codigo = extrair_blocos(resposta)
        
        self.assertEqual(len(blocos_shell), 1)
        self.assertEqual(len(blocos_codigo), 0)
        self.assertEqual(blocos_shell[0], "ls -l\npwd")

    def test_extrair_bloco_shell_sem_tag(self):
        resposta = "Comando sem tag de linguagem:\n```\necho 'hello'\n```"
        blocos_shell, blocos_codigo = extrair_blocos(resposta)
        
        self.assertEqual(len(blocos_shell), 1)
        self.assertEqual(len(blocos_codigo), 0)
        self.assertEqual(blocos_shell[0], "echo 'hello'")

    def test_extrair_bloco_python(self):
        resposta = "Código Python:\n```python\nprint('hello')\n```"
        blocos_shell, blocos_codigo = extrair_blocos(resposta)
        
        self.assertEqual(len(blocos_shell), 0)
        self.assertEqual(len(blocos_codigo), 1)
        self.assertEqual(blocos_codigo[0], ("python", "print('hello')"))

    def test_extrair_multiplos_blocos(self):
        resposta = (
            "Script Python:\n"
            "```python\ndef test(): pass\n```\n"
            "Comando para rodar:\n"
            "```sh\npython test.py\n```"
        )
        blocos_shell, blocos_codigo = extrair_blocos(resposta)
        
        self.assertEqual(len(blocos_shell), 1)
        self.assertEqual(len(blocos_codigo), 1)
        self.assertEqual(blocos_shell[0], "python test.py")
        self.assertEqual(blocos_codigo[0], ("python", "def test(): pass"))

    def test_ignorar_texto_sem_blocos(self):
        resposta = "Apenas texto normal sem crases."
        blocos_shell, blocos_codigo = extrair_blocos(resposta)
        
        self.assertEqual(len(blocos_shell), 0)
        self.assertEqual(len(blocos_codigo), 0)

    def test_g4f_models_management(self):
        from agente.providers_manager import (
            obter_modelos_provedor,
            adicionar_modelo_provedor,
            remover_modelo_provedor,
        )
        modelos = obter_modelos_provedor("G4F")
        self.assertIsInstance(modelos, list)

        # Adicionar modelo customizado
        adicionar_modelo_provedor("G4F", "test-g4f-custom-model")
        modelos_apos_add = obter_modelos_provedor("G4F")
        self.assertIn("test-g4f-custom-model", modelos_apos_add)

        # Remover modelo
        self.assertTrue(remover_modelo_provedor("G4F", "test-g4f-custom-model"))
        modelos_apos_rem = obter_modelos_provedor("G4F")
        self.assertNotIn("test-g4f-custom-model", modelos_apos_rem)

    def test_normalizar_prompt_enviado(self):
        from agente.utils import normalizar_prompt_enviado
        # Parágrafo contínuo quebrado visualmente na tela
        texto_wrap = "Como funciona o sistema de roteamento\ndo OpenRouter quando usamos\no endpoint gratuito?"
        self.assertEqual(
            normalizar_prompt_enviado(texto_wrap),
            "Como funciona o sistema de roteamento do OpenRouter quando usamos o endpoint gratuito?"
        )

        # Bloco de código com quebras intencionais deve ser preservado
        texto_code = "Veja o código:\n```python\ndef foo():\n    return True\n```"
        self.assertEqual(normalizar_prompt_enviado(texto_code), texto_code)

        # Lista com itens deve ser preservada
        texto_lista = "Pontos:\n- Item 1\n- Item 2"
        self.assertEqual(normalizar_prompt_enviado(texto_lista), texto_lista)

    def test_parse_indices_multiplos(self):
        from agente.menu_config import parse_indices_multiplos
        self.assertEqual(parse_indices_multiplos("1", 5), [0])
        self.assertEqual(parse_indices_multiplos("1 2 3", 5), [0, 1, 2])
        self.assertEqual(parse_indices_multiplos("1, 3, 5", 5), [0, 2, 4])
        self.assertEqual(parse_indices_multiplos("1-3 5", 5), [0, 1, 2, 4])
        self.assertEqual(parse_indices_multiplos("99 abc", 5), [])

    def test_custom_servers_openrouter(self):
        from agente.providers_manager import (
            obter_servidores_customizados,
            obter_servidor_customizado,
            adicionar_modelo_provedor,
            remover_modelo_provedor,
        )
        servidores = obter_servidores_customizados()
        ids = [s.get("id") for s in servidores]
        self.assertIn("openrouter", ids)

        openrouter_srv = obter_servidor_customizado("openrouter")
        self.assertIsNotNone(openrouter_srv)
        self.assertEqual(openrouter_srv.get("nome"), "OpenRouter")
        self.assertIsInstance(openrouter_srv.get("modelos", []), list)

        # Testa adição e remoção de modelo em servidor customizado
        adicionar_modelo_provedor("openrouter", "test/custom-openrouter-model")
        openrouter_apos_add = obter_servidor_customizado("openrouter")
        self.assertIn("test/custom-openrouter-model", openrouter_apos_add.get("modelos", []))

        self.assertTrue(remover_modelo_provedor("openrouter", "test/custom-openrouter-model"))
        openrouter_apos_rem = obter_servidor_customizado("openrouter")
        self.assertNotIn("test/custom-openrouter-model", openrouter_apos_rem.get("modelos", []))


    def test_http_client_singleton(self):
        from agente.services.http_client import get_http_client, close_http_client
        c1 = get_http_client()
        c2 = get_http_client()
        self.assertIs(c1, c2)
        self.assertFalse(c1.is_closed)
        close_http_client()
        self.assertTrue(c1.is_closed)


    def test_prompt_links_server_vs_local(self):
        from agente.prompts import build_system_prompt
        # Provedor local / Ollama: permanece enxuto e sem alterações
        prompt_ollama = build_system_prompt("Ollama")
        self.assertEqual(prompt_ollama, "Você é o assistente Metis. Responda sempre em português brasileiro de forma concisa e direta.")
        self.assertNotIn("Links e Sites Clicáveis", prompt_ollama)

        prompt_small = build_system_prompt("llama3.2:3b")
        self.assertEqual(prompt_small, "Você é o assistente Metis. Responda sempre em português brasileiro de forma concisa e direta.")
        self.assertNotIn("Links e Sites Clicáveis", prompt_small)

        # Provedores em nuvem / servidor: inclui diretriz de links clicáveis
        prompt_gemini = build_system_prompt("Gemini")
        self.assertIn("Links e Sites Clicáveis", prompt_gemini)
        self.assertIn("[Nome do Site ou Título](https://link-completo)", prompt_gemini)

        prompt_groq = build_system_prompt("Groq")
        self.assertIn("Links e Sites Clicáveis", prompt_groq)

        prompt_compact = build_system_prompt("Groq", compacto=True)
        self.assertIn("DIRETRIZES DE RESPOSTA E DESIGN", prompt_compact)

    def test_format_markdown_links_to_html(self):
        from agente.ui.gui_app import format_markdown_to_html
        texto = "Consulte o [Google](https://google.com) ou a [Wikipedia](https://wikipedia.org) para mais detalhes."
        html_out = format_markdown_to_html(texto)
        self.assertIn('<a href="https://google.com"', html_out)
        self.assertIn('>Google</a>', html_out)
        self.assertIn('<a href="https://wikipedia.org"', html_out)
        self.assertIn('>Wikipedia</a>', html_out)


    def test_comando_novo_chat(self):
        from agente.sessions.command_handlers import handle_novo_chat
        # Sem argumentos gera sessão com prefixo chat_
        hm1 = handle_novo_chat("/novo")
        self.assertTrue(hm1.sessao.startswith("chat_"))
        self.assertEqual(hm1.contagem_conversas(), 0)

        # Com nome explícito
        hm2 = handle_novo_chat("/novo novo_topico")
        self.assertEqual(hm2.sessao, "novo_topico")
        self.assertEqual(hm2.contagem_conversas(), 0)


    def test_single_instance_toggle_method(self):
        from agente.ui.gui_app import MetisMainWindow
        self.assertTrue(hasattr(MetisMainWindow, "toggle_or_focus"))
        self.assertTrue(callable(getattr(MetisMainWindow, "toggle_or_focus")))

    def test_service_model_constructors(self):
        from agente.services.gemini_service import GeminiService
        from agente.services.groq_service import GroqService
        from agente.services.ollama_service import OllamaService
        from agente.services.nvidia_service import NvidiaService
        from agente.services.g4f_service import G4FService

        gem = GeminiService(model="gemini-1.5-pro")
        self.assertEqual(gem.model, "gemini-1.5-pro")
        self.assertIn("gemini-1.5-pro", gem.nome_provedor)

        grq = GroqService(model="llama-3.1-8b-instant")
        self.assertEqual(grq.model, "llama-3.1-8b-instant")
        self.assertIn("llama-3.1-8b-instant", grq.nome_provedor)

        oll = OllamaService(model="llama3.2:3b")
        self.assertEqual(oll.model, "llama3.2:3b")
        self.assertIn("llama3.2:3b", oll.nome_provedor)

        nvd = NvidiaService(model="meta/llama-3.3-70b-instruct")
        self.assertEqual(nvd.model, "meta/llama-3.3-70b-instruct")
        self.assertIn("meta/llama-3.3-70b-instruct", nvd.nome_provedor)

        g4 = G4FService(model="claude-3.5-sonnet")
        self.assertEqual(g4.model, "claude-3.5-sonnet")
        self.assertIn("claude-3.5-sonnet", g4.nome_provedor)

    def test_handle_modelo_command(self):
        from agente.sessions.command_handlers import handle_modelo
        from agente.services.ollama_service import OllamaService
        from agente.services.gemini_service import GeminiService
        from agente.services.groq_service import GroqService

        srv = OllamaService()

        # Altera para Gemini com modelo específico
        srv_gem = handle_modelo(srv, "/modelo gemini gemini-1.5-pro")
        self.assertIsInstance(srv_gem, GeminiService)
        self.assertEqual(srv_gem.model, "gemini-1.5-pro")

        # Altera para Groq com modelo específico
        srv_grq = handle_modelo(srv_gem, "/modelo groq llama-3.1-8b-instant")
        self.assertIsInstance(srv_grq, GroqService)
        self.assertEqual(srv_grq.model, "llama-3.1-8b-instant")

        # Altera diretamente digitando o nome do modelo
        srv_oll = handle_modelo(srv_grq, "/modelo gemini-2.0-flash")
        self.assertIsInstance(srv_oll, GeminiService)
        self.assertEqual(srv_oll.model, "gemini-2.0-flash")

    def test_theme_manager(self):
        from agente.ui.theme_manager import (
            get_available_themes,
            get_current_theme_id,
            set_theme_preference,
            build_theme_qss,
            THEMES
        )
        themes = get_available_themes()
        self.assertEqual(len(themes), 7)
        theme_ids = [t["id"] for t in themes]
        self.assertIn("metis_oracle", theme_ids)
        self.assertIn("olympus_greek", theme_ids)
        self.assertIn("valhalla_nordic", theme_ids)
        self.assertIn("dracula_synth", theme_ids)
        self.assertIn("nord_ocean", theme_ids)
        self.assertIn("matrix_emerald", theme_ids)
        self.assertIn("onyx_mono", theme_ids)

        set_theme_preference("theme_id", "olympus_greek")
        self.assertEqual(get_current_theme_id(), "olympus_greek")

        qss = build_theme_qss(theme_id="olympus_greek")
        self.assertIn("QMainWindow", qss)
        self.assertIn(THEMES["olympus_greek"]["accent_gold"], qss)

        # Restaura para metis_oracle
        set_theme_preference("theme_id", "metis_oracle")


if __name__ == "__main__":
    unittest.main()



