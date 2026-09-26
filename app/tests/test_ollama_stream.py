import json
import unittest
from unittest.mock import MagicMock, patch

from agente.services.ollama_service import gerar_resposta_stream


def _fazer_client_com_resposta(linhas, status=200):
    """Mock de httpx.Client cujo stream devolve as linhas NDJSON fornecidas."""
    res = MagicMock()
    res.status_code = status
    res.iter_lines.return_value = list(linhas)

    client = MagicMock()
    ctx = client.stream.return_value
    ctx.__enter__.return_value = res
    ctx.__exit__.return_value = False
    return client


class TestOllamaStream(unittest.TestCase):

    def _coletar(self, linhas, iteration=1, **kwargs):
        mensagens = [{"role": "user", "content": "olá"}]
        with patch("agente.services.http_client.get_http_client",
                   return_value=_fazer_client_com_resposta(linhas)):
            return list(gerar_resposta_stream(mensagens, iteration=iteration, **kwargs))

    def test_processa_todas_as_linhas(self):
        linhas = [
            json.dumps({"message": {"role": "assistant", "content": "primeira"}}),
            json.dumps({"message": {"role": "assistant", "content": "segunda"}}),
            json.dumps({"message": {"role": "assistant", "content": "terceira"}}),
            json.dumps({"done": True}),
        ]
        resultado = self._coletar(linhas)
        self.assertEqual(resultado, ["primeira", "segunda", "terceira"])

    def test_stream_vazio_nao_crasha(self):
        resultado = self._coletar([])
        self.assertEqual(resultado, [])

    def test_linhas_vazias_e_corrompidas_sao_ignoradas(self):
        linhas = [
            "",
            "não-sou-json",
            json.dumps({"message": {"role": "assistant", "content": "ok"}}),
            "",
            "   ",
        ]
        resultado = self._coletar(linhas)
        self.assertEqual(resultado, ["ok"])

    def test_erro_do_modelo_vira_runtime_error(self):
        linhas = [json.dumps({"error": "model not found"})]
        with self.assertRaises(RuntimeError) as ctx:
            self._coletar(linhas)
        self.assertIn("model not found", str(ctx.exception))

    def test_detecta_tool_calls(self):
        linhas = [
            json.dumps({"message": {
                "role": "assistant",
                "tool_calls": [{
                    "function": {"name": "listar_diretorio", "arguments": {"caminho": "/tmp"}}
                }],
            }}),
            json.dumps({"done": True}),
        ]
        # Com iteration=5 (máximo), não re-executa a tool; apenas o aviso é emitido.
        resultado = self._coletar(linhas, iteration=5, max_iterations=5)
        self.assertTrue(any("ferramentas" in r for r in resultado))


if __name__ == "__main__":
    unittest.main()