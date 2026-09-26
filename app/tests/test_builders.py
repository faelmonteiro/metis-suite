import unittest

from agente.services.base import format_openai_messages, iter_sse_json, parse_openai_sse_stream


class TestFormatOpenaiMessages(unittest.TestCase):

    def test_mescla_functioncalls_consecutivos(self):
        mensagens = [
            {"role": "user", "content": "liste os arquivos"},
            {"role": "functionCall", "functionCall": {"name": "listar_diretorio", "args": {"caminho": "/tmp"}}},
            {"role": "functionCall", "functionCall": {"name": "ler_arquivo", "args": {"caminho": "/tmp/a.txt"}}},
            {"role": "functionResponse", "name": "listar_diretorio", "id": "call_1", "content": "a.txt"},
            {"role": "functionResponse", "name": "ler_arquivo", "id": "call_2", "content": "conteudo"},
            {"role": "user", "content": "obrigado"},
        ]
        saida = format_openai_messages(mensagens)

        # Dois functionCall consecutivos viram UM assistant.tool_calls com 2 entries
        assistant_tc = [m for m in saida if m.get("role") == "assistant" and m.get("tool_calls")]
        self.assertEqual(len(assistant_tc), 1)
        self.assertEqual(len(assistant_tc[0]["tool_calls"]), 2)
        self.assertEqual(assistant_tc[0]["tool_calls"][0]["function"]["name"], "listar_diretorio")
        self.assertEqual(assistant_tc[0]["tool_calls"][1]["function"]["name"], "ler_arquivo")
        # Args dict viram JSON string (formato OpenAI)
        self.assertEqual(
            assistant_tc[0]["tool_calls"][0]["function"]["arguments"],
            '{"caminho": "/tmp"}',
        )
        # functionResponse viram role=tool
        tools = [m for m in saida if m.get("role") == "tool"]
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0]["tool_call_id"], "call_1")

    def test_descartar_tools_remove_function_call_e_response(self):
        mensagens = [
            {"role": "user", "content": "ola"},
            {"role": "functionCall", "functionCall": {"name": "x", "args": {}}},
            {"role": "functionResponse", "name": "x", "id": "c", "content": "r"},
        ]
        saida = format_openai_messages(mensagens, descartar_tools=True)
        roles = [m["role"] for m in saida]
        self.assertEqual(roles, ["user"])
        self.assertNotIn("tool_calls", saida[0])

    def test_texto_puro_quando_sem_midia(self):
        saida = format_openai_messages([{"role": "user", "content": "olá"}])
        self.assertEqual(saida, [{"role": "user", "content": "olá"}])


class TestIterSseJson(unittest.TestCase):

    def test_parseia_apenas_linhas_data_e_para_no_done(self):
        linhas = [
            "data: {\"choices\":[{\"delta\":{\"content\":\"ola\"}}]}",
            "evento: x",
            "data: {\"choices\":[{\"delta\":{\"content\":\" mundo\"}}]}",
            "data: [DONE]",
            "data: {\"choices\":[]}",  # jamais lido
        ]
        dados = list(iter_sse_json(linhas))
        self.assertEqual(len(dados), 2)
        self.assertEqual(dados[0]["choices"][0]["delta"]["content"], "ola")

    def test_linha_invalida_e_ignorada(self):
        linhas = ["data: nao-json", "data: {\"choices\":[{\"delta\":{\"content\":\"x\"}}]}"]
        self.assertEqual(len(list(iter_sse_json(linhas))), 1)

    def test_parse_openai_sse_equivale(self):
        linhas = ['data: {"choices":[{"delta":{"content":"oi"}}]}', "data: [DONE]"]
        map_tools = {}
        self.assertEqual(list(parse_openai_sse_stream(linhas, map_tools)), ["oi"])


if __name__ == "__main__":
    unittest.main()