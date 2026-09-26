import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parent.parent)


class TestVisionPackage(unittest.TestCase):

    def test_import_como_pacote_de_dois_cwds(self):
        code = "import vision; import vision.ai_engine as e; print(e.VisionAIEngine.__name__)"
        env = dict(os.environ)
        env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        for cwd in ("/tmp", REPO_ROOT):
            with self.subTest(cwd=cwd):
                r = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=cwd, env=env, capture_output=True, text=True,
                )
                self.assertEqual(r.returncode, 0, msg=r.stderr)
                self.assertIn("VisionAIEngine", r.stdout)

    def test_entrypoint_python_m_vision_main(self):
        env = dict(os.environ)
        r = subprocess.run(
            [sys.executable, "-m", "vision.main", "--help"],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, msg=(r.stdout + r.stderr))
        self.assertIn("ScreenAI", r.stdout)

    def test_version_exportada(self):
        import vision
        self.assertTrue(hasattr(vision, "__version__"))

    def test_star_import_model_manager_nao_quebra(self):
        # Exercita __all__ (get_config_path precisa existir para o star import não levantar)
        env = dict(os.environ)
        env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        code = "from vision.model_manager import *; print(get_config_path())"
        r = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(r.stdout.strip().endswith("config_models.json"))


if __name__ == "__main__":
    unittest.main()