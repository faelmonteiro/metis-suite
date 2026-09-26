import unittest
from unittest.mock import MagicMock

from agente.services.base import (
    NonRetriableAPIError,
    RetriableAPIError,
    calcular_espera_retry_after,
)


def _res(status: int, body: bytes = b'{"error":{"message":"corpo simulado"}}', headers=None):
    res = MagicMock()
    res.status_code = status
    res.read.return_value = body
    res.headers = headers or {}
    return res


class TestCalcularEsperaRetryAfter(unittest.TestCase):

    def test_sem_header_usar_padrao(self):
        self.assertEqual(calcular_espera_retry_after(_res(429)), 3.0)

    def test_retry_after_segundos_respeitado_e_capado(self):
        self.assertEqual(calcular_espera_retry_after(_res(429, headers={"Retry-After": "12"})), 12.0)
        self.assertEqual(
            calcular_espera_retry_after(_res(429, headers={"Retry-After": "300"})), 90.0
        )

    def test_retry_after_data(self):
        headers = {
            "Retry-After": "Thu, 01 Jan 2026 00:00:07 GMT",
            "Date": "Thu, 01 Jan 2026 00:00:00 GMT",
        }
        self.assertEqual(calcular_espera_retry_after(_res(429, headers=headers)), 7.0)

    def test_retry_after_invalido_usar_padrao(self):
        self.assertEqual(calcular_espera_retry_after(_res(429, headers={"Retry-After": "abc"})), 3.0)


class TestNvidiaErroMapeado(unittest.TestCase):

    def setUp(self):
        from agente.services.nvidia_service import _handle_error
        self._handle_error = _handle_error

    def test_401_não_retriável_com_mensagem_ptbr(self):
        with self.assertRaises(NonRetriableAPIError) as ctx:
            self._handle_error(_res(401))
        self.assertIn("NVIDIA_API_KEY inválida", str(ctx.exception))

    def test_404_não_retriável(self):
        with self.assertRaises(NonRetriableAPIError):
            self._handle_error(_res(404, body=b'{"error":{"message":"model not found"}}'))

    def test_429_retriável(self):
        with self.assertRaises(RetriableAPIError):
            self._handle_error(_res(429))

    def test_5xx_retriável(self):
        with self.assertRaises(RetriableAPIError):
            self._handle_error(_res(503))

    def test_outro_4xx_não_retriável(self):
        with self.assertRaises(NonRetriableAPIError):
            self._handle_error(_res(418))


class TestExcecoesDominio(unittest.TestCase):

    def test_groq_400_não_retriável(self):
        from agente.services.groq_service import _handle_error
        with self.assertRaises(NonRetriableAPIError) as ctx:
            _handle_error(_res(400, body=b'{"error":{"message":"bad request"}}'))
        self.assertIn("Groq API (400)", str(ctx.exception))

    def test_custom_openai_401_não_retriável(self):
        from agente.services.custom_openai_service import CustomOpenAIService
        srv = CustomOpenAIService({"nome": "TesteAPI", "base_url": "https://example.com/v1"})
        with self.assertRaises(NonRetriableAPIError) as ctx:
            srv._handle_error(_res(401))
        self.assertIn("TesteAPI API (401)", str(ctx.exception))

    def test_groq_429_retriável_mantém_mensagem(self):
        from agente.services.groq_service import _handle_error
        with self.assertRaises(RetriableAPIError) as ctx:
            _handle_error(_res(429))
        self.assertIn("Groq API (429)", str(ctx.exception))

    def test_retriable_vale_para_custom_5xx(self):
        from agente.services.custom_openai_service import CustomOpenAIService
        srv = CustomOpenAIService({"nome": "TesteAPI", "base_url": "https://example.com/v1"})
        with self.assertRaises(RetriableAPIError):
            srv._handle_error(_res(502))


class TestHierarquiaExcecoes(unittest.TestCase):

    def test_ambas_são_runtime_error(self):
        self.assertTrue(issubclass(NonRetriableAPIError, RuntimeError))
        self.assertTrue(issubclass(RetriableAPIError, RuntimeError))


if __name__ == "__main__":
    unittest.main()