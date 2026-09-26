import json
import unittest
from unittest.mock import MagicMock, patch

from agente.services.ollama_service import OllamaService


class _StubRes:
    def __init__(self, lines, iter_factory=None):
        self.status_code = 200
        self.body = b""
        self._lines = list(lines)
        self._iter_factory = iter_factory
        self.closed = False

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
    def __init__(self, res):
        self._res = res

    def __enter__(self):
        return self._res

    def __exit__(self, *exc):
        self._res.close()
        return False


def _linha_tool_call():
    return json.dumps({
        "message": {
            "tool_calls": [{
                "function": {"name": "ler_arquivo", "arguments": {"caminho": "/tmp/x"}}
            }]
        }
    })


def _linha_content(texto):
    return json.dumps({"message": {"content": texto}})


class TestOllamaToolRecursionAbort(unittest.TestCase):

    def test_duas_rodadas_de_tools_com_abort_na_segunda(self):
        service = OllamaService(model="meu-modelo-v2")

        payloads = []
        round2_res = _StubRes([])
        round2_probe = []

        def _iter_round2():
            # Entrega UM chunk e sinaliza abort no meio da 2ª rodada.
            round2_probe.append(getattr(service, "_active_stream", None))
            yield _linha_content("RESPOSTA-SEGUNDA-RODADA")
            service._aborted = True
            yield _linha_content("VAI-LEAK-NAO-DEVE-SAIR")

        round2_res._iter_factory = _iter_round2
        respostas = [_StubRes([_linha_tool_call()]), round2_res]

        def _fake_stream(method, url, json=None, timeout=None):
            payloads.append(json)
            res = respostas.pop(0)
            return _StubCtx(res)

        with patch("agente.services.http_client.get_http_client",
                   return_value=MagicMock(stream=_fake_stream)):
            with patch("agente.services.tool_executor.executar_tool") as executar_tool:
                executar_tool.return_value = "resultado simulado"
                outputs = list(service.gerar_resposta_stream(
                    [{"role": "user", "content": "abre o arquivo"}]))

        # B-A: na 2ª rodada o service original registrou o novo stream (abort funcionaria).
        self.assertIs(round2_probe[0], round2_res)
        # O modelo customizado foi propagado nas duas rodadas.
        for p in payloads:
            self.assertEqual(p["model"], "meu-modelo-v2")
        # A 2ª rodada entregou o 1º chunk e o abort cortou o restante.
        self.assertIn("RESPOSTA-SEGUNDA-RODADA", outputs)
        self.assertNotIn("VAI-LEAK-NAO-DEVE-SAIR", outputs)
        # Estado limpo: stream desregistrado e flag de abort persistida.
        self.assertIsNone(service._active_stream)
        self.assertTrue(service._aborted)


if __name__ == "__main__":
    unittest.main()