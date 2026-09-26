import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

from agente import config
from agente.utils import limitar_texto

logger = logging.getLogger(__name__)

_status_cache = {"ok": None, "timestamp": 0.0, "provider": "DuckDuckGo"}


def _obter_urls():
    base_url = (config.SEARXNG_URL or "").strip().rstrip("/")
    if not base_url:
        return "", "", ""

    if base_url.endswith("/search"):
        search_url = base_url
        health_base = base_url[:-7]
    else:
        search_url = f"{base_url}/search"
        health_base = base_url

    health_url = f"{health_base}/healthz"
    return search_url, health_url, health_base


def _is_searxng_configured() -> bool:
    url = (config.SEARXNG_URL or "").strip()
    if not url:
        return False
    if url in {"http://127.0.0.1:8080", "http://localhost:8080"}:
        return False
    return True


def obter_nome_provedor() -> str:
    if _status_cache.get("provider") == "SearXNG":
        return f"SearXNG ({config.SEARXNG_URL})"
    return "DuckDuckGo"


def verificar_status() -> bool:
    agora = time.monotonic()
    if _status_cache["ok"] is not None:
        if (agora - _status_cache["timestamp"]) < config.SEARXNG_STATUS_TTL:
            return _status_cache["ok"]

    # Se uma URL remota de SearXNG estiver configurada, testa ela
    if _is_searxng_configured():
        search_url, health_url, base_url = _obter_urls()
        from agente.services.http_client import get_http_client
        try:
            client = get_http_client()
            resposta = client.get(health_url, timeout=2.0)
            if resposta.status_code == 200:
                _status_cache.update(ok=True, timestamp=agora, provider="SearXNG")
                return True

            if resposta.status_code == 404:
                resposta_raiz = client.get(base_url, timeout=2.0)
                if resposta_raiz.status_code == 200:
                    _status_cache.update(ok=True, timestamp=agora, provider="SearXNG")
                    return True
        except Exception:
            logger.debug("SearXNG configurado indisponível, usando busca nativa...")

    # Verificação de conectividade para o provedor nativo (DuckDuckGo)
    from agente.services.http_client import get_http_client
    try:
        client = get_http_client()
        resposta = client.get("https://duckduckgo.com", timeout=3.0)
        ok = resposta.status_code in (200, 301, 302)
        _status_cache.update(ok=ok, timestamp=agora, provider="DuckDuckGo")
        return ok
    except Exception:
        _status_cache.update(ok=False, timestamp=agora, provider="Offline")
        return False


class _TextExtractor(HTMLParser):
    _SKIP_TAGS = {"script", "style", "nav", "header", "footer"}

    def __init__(self):
        super().__init__()
        self.textos = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.textos.append(data.strip())

    def get_text(self):
        return " ".join(t for t in self.textos if t)


def extrair_conteudo_url(url: str, timeout: int = 8, max_chars: int = 2000) -> str:
    from agente.services.http_client import get_http_client
    try:
        client = get_http_client()
        resp = client.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        if "text/html" not in resp.headers.get("content-type", ""):
            return ""
        parser = _TextExtractor()
        parser.feed(resp.text)
        texto = parser.get_text()
        return texto[:max_chars]
    except Exception as e:
        logger.debug("extrair_conteudo_url falhou para %s: %s", url, e)
        return ""


def buscar_ddgs(query: str, max_results: int = 5) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        ddgs = DDGS()
        raw_results = ddgs.text(query, max_results=max_results)
        
        resultados = []
        if raw_results:
            for r in raw_results:
                resultados.append({
                    "title": r.get("title", "").strip(),
                    "url": r.get("href", "").strip(),
                    "snippet": r.get("body", "").strip(),
                    "engine": "DuckDuckGo",
                })
        return resultados
    except Exception as e:
        logger.warning("Falha na busca nativa DuckDuckGo: %s", e)
        return []


def buscar_searxng_api(query: str, max_results: int = 5) -> list[dict]:
    search_url, _, _ = _obter_urls()
    if not search_url:
        return []

    params = {
        "q": query,
        "format": "json",
        "language": "pt-BR",
        "lang": "pt-BR",
        "safesearch": 0,
        "pageno": 1,
    }

    from agente.services.http_client import get_http_client
    try:
        client = get_http_client()
        resposta = client.get(search_url, params=params, timeout=config.SEARCH_TIMEOUT)
        resposta.raise_for_status()
        dados = resposta.json()
        itens = dados.get("results", [])[:max_results]
        
        resultados = []
        for r in itens:
            resultados.append({
                "title": str(r.get("title", "")).strip(),
                "url": str(r.get("url", "")).strip(),
                "snippet": str(r.get("content", "")).strip(),
                "engine": str(r.get("engine", "SearXNG")).strip(),
            })
        return resultados
    except Exception as e:
        logger.debug("SearXNG falhou ou indisponível: %s", e)
        return []


def buscar_estruturado(query: str, max_results: int = 5) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    # 1. Se SearXNG estiver configurado para uma instância ativa, tenta primeiro
    if _is_searxng_configured():
        res = buscar_searxng_api(query, max_results=max_results)
        if res:
            return res

    # 2. Busca Nativa em Python (DuckDuckGo)
    res = buscar_ddgs(query, max_results=max_results)
    if res:
        return res

    # 3. Fallback se SearXNG local ainda estiver configurado
    if config.SEARXNG_URL:
        res = buscar_searxng_api(query, max_results=max_results)
        if res:
            return res

    return []


# Alias para compatibilidade com gui_app e módulos legados
buscar_searxng = buscar_estruturado


def buscar_web(pergunta: str) -> str:
    pergunta = pergunta.strip()
    if not pergunta:
        return ""

    resultados = buscar_estruturado(pergunta, max_results=config.MAX_SEARCH_RESULTS)
    if not resultados:
        return ""

    limite_por_resultado = max(
        300,
        config.MAX_WEB_CONTENT_CHARS // max(1, config.MAX_SEARCH_RESULTS),
    )

    fetch_page = getattr(config, "FETCH_PAGE_CONTENT", False)
    conteudos_paginas = {}

    if fetch_page:
        links_para_buscar = [
            (idx, str(r.get("url", "")).strip())
            for idx, r in enumerate(resultados, 1)
            if str(r.get("url", "")).strip().startswith("http")
        ]
        if links_para_buscar:
            with ThreadPoolExecutor(max_workers=min(5, len(links_para_buscar))) as executor:
                futuros = {
                    executor.submit(extrair_conteudo_url, url, max_chars=limite_por_resultado): idx
                    for idx, url in links_para_buscar
                }
                try:
                    for f in as_completed(futuros, timeout=10.0):
                        idx = futuros[f]
                        try:
                            c = f.result()
                            if c:
                                conteudos_paginas[idx] = c
                        except Exception as _silent_e:
                            logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
                except Exception as _silent_e:
                    logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    partes = []
    for idx, r in enumerate(resultados, 1):
        titulo = limitar_texto(str(r.get("title", "")), 180)
        link = str(r.get("url", "")).strip()
        snippet = limitar_texto(str(r.get("snippet", "")), limite_por_resultado)
        engine = str(r.get("engine", "")).strip()

        bloco = f"[Fonte {idx}]\n"
        bloco += f"Título: {titulo}\n"
        bloco += f"Link: {link}\n"
        bloco += f"Resumo: {snippet}\n"

        if engine:
            bloco += f"Motor: {engine}\n"

        if idx in conteudos_paginas:
            bloco += f"Conteúdo da página:\n{conteudos_paginas[idx]}\n"

        partes.append(bloco)

    return "\n".join(partes)
