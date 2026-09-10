import unittest
from pathlib import Path

from agente.utils import caminho_leitura_seguro
from agente.services.tools_defs import validar_comando_seguro


class TestSecurity(unittest.TestCase):
    def test_bloqueia_sudo(self):
        ok, _ = validar_comando_seguro("sudo ls")
        self.assertFalse(ok)

    def test_bloqueia_rm_root(self):
        ok, _ = validar_comando_seguro("rm -rf /")
        self.assertFalse(ok)

    def test_bloqueia_mkfs(self):
        ok, _ = validar_comando_seguro("mkfs.ext4 /dev/sda1")
        self.assertFalse(ok)

    def test_caminho_fora_permitido(self):
        with self.assertRaises(ValueError):
            caminho_leitura_seguro("/etc/hosts")

    def test_caminho_pasta_sensivel(self):
        home = Path.home()
        caminho_perigoso = home / ".ssh" / "id_rsa"

        with self.assertRaises(ValueError):
            caminho_leitura_seguro(str(caminho_perigoso))

    def test_permite_caminho_config(self):
        home = Path.home()
        caminho_config = home / ".config" / "hypr" / "hyprland.conf"
        # Não deve levantar ValueError por estar em .config
        resolvido = caminho_leitura_seguro(str(caminho_config))
        self.assertEqual(resolvido, caminho_config.resolve())

    def test_cria_backup_editar_arquivo(self):
        import tempfile
        import shutil
        from agente.services import tools_defs
        
        tools_defs.AUTO_APPROVE_MODE = True
        with tempfile.NamedTemporaryFile(mode="w", dir=str(Path.cwd()), delete=False, suffix=".txt") as f:
            f.write("linha 1\nlinha 2 original\nlinha 3\n")
            temp_path = f.name

        try:
            res = tools_defs.editar_arquivo(temp_path, "linha 2 original", "linha 2 editada")
            self.assertIn("editado com sucesso", res)
            
            backup_path = Path(temp_path).with_suffix(Path(temp_path).suffix + ".bak")
            self.assertTrue(backup_path.exists(), "O arquivo .bak de backup não foi criado")
            with open(backup_path, "r", encoding="utf-8") as bf:
                self.assertIn("linha 2 original", bf.read())
            backup_path.unlink(missing_ok=True)
        finally:
            tools_defs.AUTO_APPROVE_MODE = False
            Path(temp_path).unlink(missing_ok=True)


    def test_normalizar_comando(self):
        from agente.services.tools_defs import normalizar_comando
        self.assertEqual(normalizar_comando("['ps aux']"), "ps aux")
        self.assertEqual(normalizar_comando(["ps", "-eo", "pcpu"]), "ps -eo pcpu")
        self.assertEqual(normalizar_comando('"ps aux"'), "ps aux")
        self.assertEqual(normalizar_comando('`uptime`'), "uptime")

    def test_ler_arquivo_bloqueia_pasta_sensivel(self):
        from agente.services.tools_defs import ler_arquivo
        res = ler_arquivo("~/.ssh/id_rsa")
        self.assertIn("Acesso negado", res)


if __name__ == "__main__":
    unittest.main()
