"""
Cliente HTTP compartilhado com Connection Pooling e Keep-Alive para o Metis.
Reutiliza conexões TCP e handshakes TLS já abertos, economizando centenas de ms por chamada.
"""

import threading
import httpx
from agente import config

_client_instance: httpx.Client = None
_client_lock = threading.Lock()


def get_http_client(timeout: httpx.Timeout = None) -> httpx.Client:
    """
    Retorna a instância compartilhada de httpx.Client com Keep-Alive ativo e thread-safe.
    Se um timeout customizado for especificado, cria um cliente dedicado para evitar
    efeitos colaterais em outras partes da aplicação.
    """
    global _client_instance
    limits = httpx.Limits(
        max_keepalive_connections=20,
        max_connections=50,
        keepalive_expiry=60.0
    )
    read_sec = float(getattr(config, "API_TIMEOUT", 120))
    default_timeout = httpx.Timeout(connect=10.0, read=read_sec, write=15.0, pool=10.0)

    if timeout is not None and timeout != default_timeout:
        return httpx.Client(
            timeout=timeout,
            limits=limits,
            follow_redirects=True
        )

    with _client_lock:
        if _client_instance is None or _client_instance.is_closed:
            _client_instance = httpx.Client(
                timeout=default_timeout,
                limits=limits,
                follow_redirects=True
            )
        return _client_instance


def close_http_client():
    """Fecha o pool de conexões HTTP ao encerrar a aplicação de forma thread-safe."""
    global _client_instance
    with _client_lock:
        if _client_instance is not None and not _client_instance.is_closed:
            try:
                _client_instance.close()
            except Exception:
                pass
            _client_instance = None
