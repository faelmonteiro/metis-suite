import base64
import logging
import os
from functools import lru_cache

MAX_MEDIA_CACHE_SIZE = 25 * 1024 * 1024  # 25MB

@lru_cache(maxsize=8)
def get_base64_media(path: str) -> str:
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_MEDIA_CACHE_SIZE:
            raise ValueError(f"Arquivo de mídia excede o limite máximo suportado para Base64 ({MAX_MEDIA_CACHE_SIZE // (1024*1024)}MB).")
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logging.error(f"Erro ao ler midia {path}: {e}")
        raise
