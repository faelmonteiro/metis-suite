import unittest
import base64
import os
import tempfile
from pathlib import Path

from agente.services.media_cache import get_base64_media, _encode_base64


class TestMediaCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_base64_do_arquivo(self):
        p = Path(self.tmp) / "img.png"
        p.write_bytes(b"\x89PNG-fake")
        self.assertEqual(get_base64_media(str(p)), base64.b64encode(b"\x89PNG-fake").decode("utf-8"))

    def test_mtime_size_invalidam_o_cache(self):
        p = Path(self.tmp) / "img.png"
        p.write_bytes(b"aaaa")
        primeiro = get_base64_media(str(p))
        self.assertEqual(primeiro, base64.b64encode(b"aaaa").decode("utf-8"))

        p.write_bytes(b"bbbb")
        os.utime(p, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_001))
        segundo = get_base64_media(str(p))
        self.assertEqual(segundo, base64.b64encode(b"bbbb").decode("utf-8"))
        self.assertNotEqual(primeiro, segundo)

    def test_chave_inclui_mtime_ns(self):
        p = Path(self.tmp) / "img.png"
        p.write_bytes(b"conteudo")
        os.utime(p, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_010))
        chave_a = _encode_base64.cache_info()
        primeiro = get_base64_media(str(p))
        segundo = get_base64_media(str(p))

        cache_afer = _encode_base64.cache_info()
        self.assertEqual(primeiro, segundo)
        self.assertEqual(cache_afer.hits - chave_a.hits, 1)


if __name__ == "__main__":
    unittest.main()