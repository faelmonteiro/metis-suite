"""Testes da camada de erro/retry da NVIDIA (N10/M4 residual)."""
import unittest
from unittest.mock import MagicMock, patch

import httpx

from agente.services.nvidia_service import NvidiaService
from agente.services.base import RetriableAPIError


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


def _srv():
    return NvidiaService(model="nvidia-teste")


class TestNvidiaErrors(unittest.TestCase):

    def setUp(self):
        key_patch = patch("agente.config.NVIDIA_API_KEY", "chave-de-teste")
        key_patch.start()
        self.addCleanup(key_patch.stop)

    def test_init_chama_super(self):
        s = NvidiaService(model="nvidia-teste")
        self.assertIsNone(s._active_stream)
        self.assertFalse(s._aborted)

    def test_401_falha_imediato_sem_retry(self):
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(401)])):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(_srv().gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        sleep.assert_not_called()
        self.assertIn("NVIDIA API (401)", str(ctx.exception))
        self.assertIn("simulado", str(ctx.exception))

    def test_404_nao_vaza_httpx_http_status_error(self):
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(404)])):
            with self.assertRaises(RuntimeError) as ctx:
                list(_srv().gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertIn("404", str(ctx.exception))
        self.assertFalse(isinstance(ctx.exception, httpx.HTTPStatusError))

    def test_429_retriado_ate_falhar(self):
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(429)] * 5)):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(_srv().gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(sleep.call_count, 4)
        self.assertIn("NVIDIA API (429)", str(ctx.exception))

    def test_500_retriado_ate_falhar(self):
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(500)] * 5)):
            with patch("time.sleep") as sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    list(_srv().gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(sleep.call_count, 4)
        self.assertIn("NVIDIA API (500)", str(ctx.exception))

    def test_200_stream_ok(self):
        sse = [
            'data: {"choices":[{"delta":{"content":"ciao"}}]}',
            "data: [DONE]",
        ]
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([_mock_response(200, lines=sse)])):
            outputs = list(_srv().gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(outputs, ["ciao"])

    def test_abort_durante_stream_retorna_silencioso(self):
        s = _srv()

        def _iter():
            s._aborted = True
            yield 'data: {"choices":[{"delta":{"content":"parcial"}}]}'
            raise httpx.ReadError("stream fechado pelo abort", request=None)

        res = _mock_response(200)
        res.iter_lines.side_effect = _iter
        with patch("agente.services.http_client.get_http_client",
                   return_value=_StubClient([res])):
            outputs = list(s.gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(outputs, ["parcial"])
        self.assertIsNone(s._active_stream)

    def test_retriable_error_herda_runtime_error(self):
        self.assertTrue(issubclass(RetriableAPIError, RuntimeError))


if __name__ == "__main__":
    unittest.main()