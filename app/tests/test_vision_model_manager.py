import sys
import unittest
from pathlib import Path

# Adiciona o diretório vision ao sys.path para os testes
VISION_DIR = Path(__file__).resolve().parent.parent / "vision"
if str(VISION_DIR) not in sys.path:
    sys.path.insert(0, str(VISION_DIR))

import model_manager


class TestVisionModelManager(unittest.TestCase):
    def test_canonical_provider_name(self):
        self.assertEqual(model_manager._canonical_provider_name("openrouter"), "OpenRouter")
        self.assertEqual(model_manager._canonical_provider_name("OpenRouter"), "OpenRouter")
        self.assertEqual(model_manager._canonical_provider_name("openrouter.ai"), "OpenRouter")
        self.assertEqual(model_manager._canonical_provider_name("gemini"), "Gemini")
        self.assertEqual(model_manager._canonical_provider_name("nvidia"), "NVIDIA")
        self.assertEqual(model_manager._canonical_provider_name("groq"), "Groq")
        self.assertEqual(model_manager._canonical_provider_name("ollama"), "Ollama")
        self.assertEqual(model_manager._canonical_provider_name("g4f"), "G4F")

    def test_deduplication_of_openrouter(self):
        # Simula configuração com OpenRouter em builtin_models e múltiplos custom_servers
        mock_cfg = {
            "builtin_models": {
                "OpenRouter": ["liquid/lfm-2.5-2.6b:free", "inclusionai/ling-3.0-flash-fin:free"],
                "Groq": ["openai/gpt-oss-120b"]
            },
            "custom_servers": [
                {
                    "id": "openrouter",
                    "nome": "OpenRouter",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "modelos": ["minimax/minimax-m3:free"]
                },
                {
                    "id": "custom_openrouter",
                    "nome": "openrouter",
                    "base_url": "https://openrouter.ai/api/v1",
                    "modelos": ["poolside/laguna-s-2.1:free"]
                }
            ]
        }
        orig_loader = model_manager.load_models_config
        try:
            model_manager.load_models_config = lambda force_reload=False: mock_cfg

            # 1. get_providers deve conter exatamente um OpenRouter
            provs = model_manager.get_providers()
            self.assertEqual(provs.count("OpenRouter"), 1)
            self.assertEqual(sum(1 for p in provs if p.lower() == "openrouter"), 1)

            # 2. get_grouped_model_list deve conter exatamente um grupo openrouter
            grouped = model_manager.get_grouped_model_list()
            keys = [g["key"] for g in grouped]
            self.assertEqual(keys.count("openrouter"), 1)

            # 3. Modelos de todas as fontes devem ser mesclados
            models = model_manager.get_models_for_provider("OpenRouter")
            self.assertEqual(len(models), 4)
            self.assertIn("liquid/lfm-2.5-2.6b:free", models)
            self.assertIn("minimax/minimax-m3:free", models)
            self.assertIn("poolside/laguna-s-2.1:free", models)
        finally:
            model_manager.load_models_config = orig_loader


if __name__ == "__main__":
    unittest.main()
