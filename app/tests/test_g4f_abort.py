"""Testes do G4FService após suporte mínimo a abort (N2)."""
import unittest
from unittest.mock import patch

from agente.services.g4f_service import G4FService


class TestG4FAbort(unittest.TestCase):

    def test_init_chama_super(self):
        s = G4FService(model="gpt-4o-mini")
        self.assertIsNone(s._active_stream)
        self.assertFalse(s._aborted)

    def test_yield_resposta_completa(self):
        s = G4FService(model="gpt-4o-mini")
        with patch("agente.services.g4f_service.gerar_resposta", return_value="resposta g4f"):
            outputs = list(s.gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(outputs, ["resposta g4f"])

    def test_abort_durante_geracao_descarta_resultado(self):
        s = G4FService(model="gpt-4o-mini")

        def _gerar(mensagens, model):
            s._aborted = True
            return "resposta que deve ser descartada"

        with patch("agente.services.g4f_service.gerar_resposta", side_effect=_gerar):
            outputs = list(s.gerar_resposta_stream([{"role": "user", "content": "oi"}]))
        self.assertEqual(outputs, [])


if __name__ == "__main__":
    unittest.main()