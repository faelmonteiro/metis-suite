import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agente.models.preferences as preferences
import agente.models.storage as storage


class TestStorageCacheLockPropagacao(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._orig_dir = storage.CONFIG_DIR
        self._orig_file = storage.CONFIG_FILE
        self._orig_cache = storage._config_cache
        self._orig_env = preferences.ENV_FILE
        storage.CONFIG_DIR = self.root
        storage.CONFIG_FILE = self.root / "config_models.json"
        preferences.ENV_FILE = self.root / ".env"
        storage._config_cache = None

    def tearDown(self):
        storage.CONFIG_DIR = self._orig_dir
        storage.CONFIG_FILE = self._orig_file
        storage._config_cache = self._orig_cache
        preferences.ENV_FILE = self._orig_env
        self._tmp.cleanup()

    def _escreve(self, cfg):
        cfg.setdefault("schema_version", 2)
        storage.CONFIG_FILE.write_text(json.dumps(cfg), encoding="utf-8")

    def test_cache_por_mtime(self):
        self._escreve({"active_model": "A"})
        self.assertEqual(storage.load_config()["active_model"], "A")
        mtime = storage.CONFIG_FILE.stat().st_mtime_ns
        # Conteúdo muda, mas mtime volta ao cacheado -> leitura fica em cache
        self._escreve({"active_model": "B"})
        os.utime(storage.CONFIG_FILE, ns=(mtime, mtime))
        self.assertEqual(storage.load_config()["active_model"], "A")
        self.assertEqual(storage.load_config(force_reload=True)["active_model"], "B")

    def test_cache_invalida_apos_save(self):
        self._escreve({"active_model": "A"})
        cfg = storage.load_config()
        cfg["active_model"] = "B"
        storage.save_config(cfg)
        self.assertEqual(storage.load_config()["active_model"], "B")

    def test_retorna_copia_para_evitar_aliasing(self):
        self._escreve({"active_model": "A"})
        primeiro = storage.load_config()
        primeiro["active_model"] = "MUTADO"
        segundo = storage.load_config()
        self.assertEqual(segundo["active_model"], "A")

    def test_arquivo_corrompido_usa_default(self):
        storage.CONFIG_FILE.write_text("{corrompido", encoding="utf-8")
        data = storage.load_config()
        self.assertEqual(data["schema_version"], 2)

    def test_salvar_propaga_erro_de_io(self):
        with mock.patch.object(
            preferences, "save_config", side_effect=OSError("sem disco")
        ) as save_mock:
            with self.assertRaises(OSError):
                preferences.set_preference("chave", "valor")
            save_mock.assert_called_once()

    def test_save_provider_state_propaga_erro(self):
        with mock.patch.object(
            preferences, "save_config", side_effect=OSError("sem disco")
        ):
            with self.assertRaises(OSError):
                preferences.save_provider_state("g4f", "gpt-4o")

    def test_env_roundtrip_atomico(self):
        os.environ.pop("M7_TEST_ENV", None)
        preferences.save_env_var("M7_TEST_ENV", "abc")
        try:
            # Fallback para arquivo quando não está em os.environ
            os.environ.pop("M7_TEST_ENV", None)
            self.assertEqual(preferences.get_env_var("M7_TEST_ENV"), "abc")
            self.assertTrue(preferences.ENV_FILE.exists())
        finally:
            os.environ.pop("M7_TEST_ENV", None)


if __name__ == "__main__":
    unittest.main()