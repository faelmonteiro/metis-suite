import unittest
from unittest.mock import MagicMock, patch

from agente.services.base import RetriableAPIError
import agente.services.custom_openai_service as custom_openai_service
import agente.services.groq_service as groq_service


def _mock_response(status, lines=(), body=None):
    res = MagicMock()
    res.status_code = status
    res.iter_lines.return_value = list(lines)
    res.read.return_value = body or b'{"error":{"message":"simulado"}}'
    return res


class _StubClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def stream(self, *args, **kwargs):
        class _Ctx:
            def __init__(self, res):
                self._res = res

            def __enter__(self):
                return self._res

            def __exit__(self, *exc):
                return False

        return _Ctx(self._responses.pop(0))


class TestGroqRetry(unittest.TestCase):

    def setUp(self):
        env_p = patch("agente.config.GROQ_API_KEY", "groq-chave-de-teste")
        env_p.start()
        self.addCleanup(env_p.stop)

    def test_401_falha_imediato_sem_retry(self):
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(401)])):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(groq_service.gerar_resposta_stream(
                        [{"role": "user", "content": "oi"}], model="teste"))
        sleep.assert_not_called()
        self.assertIn("Groq API (401)", str(ctx.exception))
        self.assertIn("simulado", str(ctx.exception))

    def test_429_e_500_sao_retriaveis_mas_falham_ao_final(self):
        for status in (429, 500):
            with patch("agente.services.http_client.get_http_client",
                       return_value=_StubClient([_mock_response(status)] * 5)):
                with patch("time.sleep") as sleep:
                    gen = groq_service.gerar_resposta_stream(
                        [{"role": "user", "content": "oi"}], model="teste")
                    with self.assertRaises(RuntimeError) as ctx:
                        list(gen)
                self.assertEqual(sleep.call_count, 4)
                self.assertIn(f"Groq API ({status})", str(ctx.exception))

    def test_400_nao_retriavel_nao_durme(self):
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(400)])):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(groq_service.gerar_resposta_stream(
                        [{"role": "user", "content": "oi"}], model="teste"))
        self.assertEqual(sleep.call_count, 0)
        self.assertIn("Groq API (400)", str(ctx.exception))


class TestCustomOpenAIRetry(unittest.TestCase):

    def _service(self):
        return custom_openai_service.CustomOpenAIService({
            "nome": "TesteAPI",
            "base_url": "https://example.com/v1",
        })

    def test_401_falha_imediato(self):
        srv = self._service()
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(401)])):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(srv.gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        sleep.assert_not_called()
        self.assertIn("TesteAPI API (401)", str(ctx.exception))

    def test_429_tentado_3x_e_falha_com_mensagem_clara(self):
        srv = self._service()
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(429)] * 3)):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(srv.gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(sleep.call_count, 2)
        self.assertIn("TesteAPI API (429)", str(ctx.exception))

    def test_400_com_tools_reenvia_sem_tools_e_obtem_sucesso(self):
        srv = self._service()
        res400 = _mock_response(
            400, body=b'{"error":{"message":"este modelo nao suporta tool calling"}}')
        sse = [
            'data: {"choices":[{"delta":{"content":"oi"}}]}',
            "data: [DONE]",
        ]
        res200 = _mock_response(200, lines=sse)
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([res400, res200])):
            resultado = list(srv.gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(resultado, ["oi"])


class TestRetriableAPIError(unittest.TestCase):

    def test_herda_de_runtime_error(self):
        self.assertTrue(issubclass(RetriableAPIError, RuntimeError))
        inst = RetriableAPIError("Groq API (429): limite")
        self.assertIn("429", str(inst))


if __name__ == "__main__":
    unittest.main()