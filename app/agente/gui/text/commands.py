"""Texto do chat: area de transferencia e interpretacao de comandos instantaneos.

Funcoes puras, sem dependencia de Qt: sao usadas tanto pela GUI quanto pela
camada de sessao/comandos do agente.
"""

from typing import Optional

import logging, re, shutil

logger = logging.getLogger(__name__)


def copiar_para_area_de_transferencia(texto: str) -> bool:
    """Copia o texto para a área de transferência usando Qt e fallbacks de sistema (wl-copy, xclip)."""
    if not texto:
        return False
    sucesso = False
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QClipboard
        app_clip = QApplication.clipboard()
        if app_clip:
            app_clip.setText(texto, QClipboard.Mode.Clipboard)
            app_clip.setText(texto, QClipboard.Mode.Selection)
            sucesso = True
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    try:
        from agente.ui.clipboard import _copiar_clipboard
        if _copiar_clipboard(texto):
            sucesso = True
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    return sucesso


def extrair_itens_comandos(resposta: str) -> list:
    """Extrai comandos executáveis e blocos de código formatados para exibição e cópia na GUI."""
    if not resposta:
        return []

    try:
        from agente.ui.clipboard import extrair_blocos, _extrair_comando_e_comentario
        blocos_shell, blocos_codigo = extrair_blocos(resposta)
        itens = []

        for bloco in blocos_shell:
            for linha in bloco.strip().split("\n"):
                linha_limpa = linha.strip()
                if not linha_limpa:
                    continue
                cmd, comentario = _extrair_comando_e_comentario(linha_limpa)
                if cmd:
                    itens.append(("comando", cmd, comentario))

        for lang, conteudo in blocos_codigo:
            linhas_code = conteudo.strip().split("\n")
            primeira_linha = linhas_code[0] if linhas_code else ""
            lang_label = lang if lang else "código"
            itens.append(("codigo", conteudo, f"{lang_label}: {primeira_linha}"))

        return itens
    except Exception:
        return []


def resolver_comando_instantaneo(pedido: str) -> Optional[str]:
    """
    Traduz pedidos comuns de '/executar' diretamente para comandos de terminal em 0.001s,
    eliminando latência de IA para abrir programas comuns ou executar comandos diretos.
    """
    p = pedido.strip()
    if not p:
        return None

    p_lower = p.lower()

    # 1. Navegador / Internet / Sites / Links
    if any(k in p_lower for k in [
        "navegador", "browser", "internet", "google", "chrome", "firefox",
        "brave", "youtube", "site", "web"
    ]):
        urls = re.findall(r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(?:com|org|net|io|dev|br|edu|gov)", p)
        if urls:
            url = urls[0]
            if not url.startswith("http"):
                url = "https://" + url
            return f"xdg-open {url}"
        if "youtube" in p_lower:
            return "xdg-open https://www.youtube.com"
        return "xdg-open https://google.com"

    # 2. Editor Kate
    if "kate" in p_lower:
        m = re.search(r"kate\s+([^\s]+)", p, re.IGNORECASE) or re.search(r"(?:abrir|abra|abre|editar|edita)\s+(?:o\s+arquivo\s+)?([^\s]+)\s+(?:no|com\s+o)?\s*kate", p, re.IGNORECASE)
        if m:
            arq = m.group(1).strip()
            return f"kate {arq}"
        return "kate"

    # 3. VSCode / Code
    if "vscode" in p_lower or "code" in p_lower:
        m = re.search(r"(?:code|vscode)\s+([^\s]+)", p, re.IGNORECASE) or re.search(r"(?:abrir|abra|abre|editar|edita)\s+(?:o\s+arquivo\s+)?([^\s]+)\s+(?:no|com\s+o)?\s*(?:vscode|code)", p, re.IGNORECASE)
        if m:
            arq = m.group(1).strip()
            return f"code {arq}"
        return "code ."

    # 4. Pastas / Diretórios
    if any(k in p_lower for k in ["pasta", "diretorio", "diretório", "downloads", "documentos", "imagens"]):
        if "download" in p_lower:
            return "xdg-open ~/Downloads"
        if "documento" in p_lower:
            return "xdg-open ~/Documentos"
        if "imagem" in p_lower or "foto" in p_lower:
            return "xdg-open ~/Imagens"
        if "musica" in p_lower or "música" in p_lower:
            return "xdg-open ~/Música"
        if "video" in p_lower or "vídeo" in p_lower:
            return "xdg-open ~/Vídeos"
        m = re.search(r"(?:pasta|diretorio|diretório)\s+([^\s]+)", p, re.IGNORECASE)
        if m:
            return f"xdg-open {m.group(1).strip()}"
        return "xdg-open ~"

    # 5. Terminal
    if "terminal" in p_lower:
        if shutil.which("kitty"):
            return "kitty"
        if shutil.which("alacritty"):
            return "alacritty"
        if shutil.which("konsole"):
            return "konsole"
        return "x-terminal-emulator"

    # 6. Se já é um comando direto de terminal válido no PATH (ex: 'ls', 'kate ideias.txt', 'pkill ...', 'git status')
    primeira_palavra = p.split()[0]
    if shutil.which(primeira_palavra) or primeira_palavra in (
        "ls", "cd", "mkdir", "rm", "cp", "mv", "cat", "grep", "find", "git",
        "df", "du", "free", "top", "htop", "ps", "curl", "wget", "ping", "ip",
        "systemctl", "journalctl", "uname", "python", "python3", "pip", "node", "npm"
    ):
        return p

    return None
