"""Testes de abort() para o GeminiService (N1): apoio real a interrupção no stream."""
import json
import unittest
from unittest.mock import patch

import httpx

from agente.services.gemini_service import GeminiService
import agente.services.gemini_service as gemini_service


def _linha_texto(texto: str) -> str:
    return "data: " + json.dumps({
        "candidates": [{"content": {"parts": [{"text": texto}]}}]
    })


def _linha_function_call():
    return "data: " + json.dumps({
        "candidates": [{
            "content": {"parts": [{
                "functionCall": {"name": "ler_arquivo", "args": {"caminho": "/tmp/x"}}
            }]}
        }]
    })


class _StubRes:
    def __init__(self, lines=(), iter_factory=None, status=200, body=b""):
        self.status_code = status
        self.body = body
        self.closed = False
        self._lines = list(lines)
        self._iter_factory = iter_factory

    def read(self):
        return self.body

    def iter_lines(self):
        if self._iter_factory is not None:
            yield from self._iter_factory()
            return
        yield from self._lines

    def close(self):
        self.closed = True


class _StubCtx:
    def __init__(self, res, exc=None):
        self._res = res
        self._exc = exc

    def __enter__(self):
        if self._exc is not None:
            raise self._exc
        return self._res

    def __exit__(self, *exc):
        if self._res is not None:
            self._res.close()
        return False


class _StubClient:
    def __init__(self, ctxs):
        self._ctxs = list(ctxs)
        self.calls = []

    def stream(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append({"method": method, "url": url})
        return self._ctxs.pop(0)


class TestGeminiAbort(unittest.TestCase):

    def setUp(self):
        key_patch = patch("agente.config.GEMINI_API_KEY", "chave-de-teste")
        key_patch.start()
        self.addCleanup(key_patch.stop)
        model_patch = patch("agente.config.GEMINI_MODEL", "gemini-teste-v1")
        model_patch.start()
        self.addCleanup(model_patch.stop)

    def test_init_chama_super(self):
        s = GeminiService(model="gemini-teste-v1")
        self.assertIsNone(s._active_stream)
        self.assertFalse(s._aborted)

    def test_abort_durante_stream_corta_silenciosamente(self):
        s = GeminiService(model="gemini-teste-v1")
        res = _StubRes()

        def _iter():
            yield "data: " + json.dumps({
                "candidates": [{"content": {"parts": [{"text": "chunk-1"}]}}]
            })
            s._aborted = True
            yield "data: " + json.dumps({
                "candidates": [{"content": {"parts": [{"text": "vazou-nao-deve-sair"}]}}]
            })

        res._iter_factory = _iter
        client = _StubClient([_StubCtx(res)])
        with patch("agente.services.http_client.get_http_client", return_value=client):
            outputs = list(s.gerar_resposta_stream([{"role": "user", "content": "oi"}]))

        self.assertEqual(outputs, ["chunk-1"])
        self.assertTrue(s._aborted)
        self.assertIsNone(s._active_stream)

    def test_request_error_sem_abort_vira_erro_amigavel(self):
        client = _StubClient([_StubCtx(None, exc=httpx.ConnectError("boom", request=None))])
        with patch("agente.services.http_client.get_http_client", return_value=client):
            with self.assertRaises(RuntimeError) as ctx:
                list(GeminiService(model="gemini-teste-v1").gerar_resposta_stream(
                    [{"role": "user", "content": "oi"}]))
        self.assertIn("Erro de conexão com Gemini API", str(ctx.exception))

    def test_request_error_abortado_retorna_silencioso(self):
        class _FakeService:
            _aborted = True
            _active_stream = None

        client = _StubClient([_StubCtx(None, exc=httpx.ConnectError("boom", request=None))])
        with patch("agente.services.http_client.get_http_client", return_value=client):
            outputs = list(gemini_service.gerar_resposta_stream(
                [{"role": "user", "content": "oi"}], model="gemini-teste-v1", service=_FakeService()))
        self.assertEqual(outputs, [])

    def test_recursao_de_tools_propaga_service_e_modelo(self):
        s = GeminiService(model="gemini-teste-v1")

        round2_probe = []
        round2_res = _StubRes()

        def _iter_round2():
            round2_probe.append(getattr(s, "_active_stream", None))
            yield _linha_texto("RESPOSTA-RODADA-2")

        round2_res._iter_factory = _iter_round2
        client = _StubClient([_StubCtx(_StubRes([_linha_function_call()])), _StubCtx(round2_res)])
        with patch("agente.services.http_client.get_http_client", return_value=client):
            with patch("agente.services.tool_executor.executar_tool") as executar_tool:
                executar_tool.return_value = "resultado simulado"
                outputs = list(s.gerar_resposta_stream([{"role": "user", "content": "abre o arquivo"}]))

        self.assertEqual(outputs, ["RESPOSTA-RODADA-2"])
        self.assertIs(round2_probe[0], round2_res)
        for chamada in client.calls:
            self.assertIn("gemini-teste-v1", chamada["url"])
        self.assertIsNone(s._active_stream)

    def test_http_error_404_nao_vaza_httpx(self):
        res = _StubRes(status=404, body=b'{"error":{"message":"nope"}}')
        client = _StubClient([_StubCtx(res)])
        with patch("agente.services.http_client.get_http_client", return_value=client):
            with self.assertRaises(RuntimeError) as ctx:
                list(GeminiService(model="gemini-teste-v1").gerar_resposta_stream(
                    [{"role": "user", "content": "oi"}]))
        self.assertIn("404", str(ctx.exception))
        self.assertFalse(isinstance(ctx.exception, httpx.HTTPStatusError))


if __name__ == "__main__":
    unittest.main()