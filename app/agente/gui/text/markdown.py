"""Conversao de markdown para HTML para exibicao no chat (Qlabel)."""

import logging

logger = logging.getLogger(__name__)


def format_markdown_to_html(text: str) -> str:
    """Converte markdown com blocos de código estilo ChatGPT, destaques, listas e tags em HTML para QLabel."""
    if not text:
        return ""

    try:
        import html
        import re

        # Se já é tag HTML gerada pelo sistema (anexos, busca, status de carregamento, etc.), retorna direto
        if text.startswith("📎 <b>") or text.startswith("❌ ") or text.startswith("🔍 ") or text.startswith("● ") or text.startswith("🌐 ") or text.startswith("<span ") or text.startswith("<div "):
            return text

        # Escapa caracteres HTML para segurança
        escaped = html.escape(text)

        # Blocos de código estilo Mica / Acrílico Dourado Metis ```lang ... ```
        def _code_block_repl(m):
            lang = (m.group(1).strip() or "terminal").upper()
            code = m.group(2).strip()
            return (
                f'<div style="background-color: rgba(15, 20, 32, 0.75); border: 1px solid rgba(250, 208, 148, 0.25); '
                f'border-left: 3.5px solid #fad094; border-radius: 8px; margin: 8px 0; overflow: hidden;">'
                f'<div style="background-color: rgba(30, 35, 48, 0.65); border-bottom: 1px solid rgba(250, 208, 148, 0.18); '
                f'padding: 4px 12px; color: #fad094; font-size: 10px; font-weight: bold; '
                f'font-family: sans-serif; letter-spacing: 0.5px;">'
                f'⚡ {lang}'
                f'</div>'
                f'<div style="padding: 9px 14px; font-family: Monospace; '
                f'font-size: 11.5px; color: #fde047; line-height: 145%; white-space: pre-wrap;">'
                f'{code}</div>'
                f'</div>'
            )

        escaped = re.sub(r"```([\w+#.-]*)\s*\n(.*?)```", _code_block_repl, escaped, flags=re.DOTALL)

        # Headers Markdown
        escaped = re.sub(
            r"^### (.*?)$",
            r'<div style="color: #fad094; font-size: 12.5px; font-weight: bold; margin: 8px 0 2px 0;">\1</div>',
            escaped,
            flags=re.MULTILINE
        )
        escaped = re.sub(
            r"^## (.*?)$",
            r'<div style="color: #67e8f9; font-size: 13.5px; font-weight: bold; margin: 10px 0 3px 0;">\1</div>',
            escaped,
            flags=re.MULTILINE
        )
        escaped = re.sub(
            r"^# (.*?)$",
            r'<div style="color: #fde047; font-size: 14.5px; font-weight: bold; margin: 12px 0 4px 0; border-bottom: 1px solid #1e293b; padding-bottom: 3px;">\1</div>',
            escaped,
            flags=re.MULTILINE
        )

        # Divisores horizontais ---
        escaped = re.sub(
            r"^---+$",
            r'<div style="border-top: 1px solid #1e293b; margin: 10px 0;"></div>',
            escaped,
            flags=re.MULTILINE
        )

        # Bullet lists (- item ou * item)
        escaped = re.sub(
            r"^[ \t]*[-*] (.*?)$",
            r'<div style="margin-left: 10px; color: #f1f5f9;"><span style="color: #38bdf8;">•</span> \1</div>',
            escaped,
            flags=re.MULTILINE
        )

        # Numbered lists (1. item)
        escaped = re.sub(
            r"^[ \t]*(\d+)\. (.*?)$",
            r'<div style="margin-left: 10px; color: #f1f5f9;"><span style="color: #facc15; font-weight: bold;">\1.</span> \2</div>',
            escaped,
            flags=re.MULTILINE
        )

        # Links Markdown [texto](https://...)
        def _link_repl(m):
            label = m.group(1).strip()
            url = m.group(2).strip()
            return f'<a href="{url}" style="color: #38bdf8; text-decoration: underline; font-weight: bold;">{label}</a>'

        escaped = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", _link_repl, escaped)

        # URLs soltas (http/https)
        escaped = re.sub(r'(?<!href=")(?<!">)(https?://[^\s<"\)]+)', r'<a href="\1" style="color: #38bdf8; text-decoration: underline;">\1</a>', escaped)

        # Inline code `...` (Destaque Mica Dourado Metis)
        escaped = re.sub(
            r"`([^`]+)`",
            r'<span style="background-color: rgba(250, 208, 148, 0.12); border: 1px solid rgba(250, 208, 148, 0.28); border-radius: 4px; padding: 2px 6px; font-family: Monospace; font-size: 11px; color: #fde047; font-weight: bold;">\1</span>',
            escaped
        )

        # Negrito **...**
        escaped = re.sub(r"\*\*([^*]+)\*\*", r'<b style="color: #fef08a;">\1</b>', escaped)

        # Itálico *...* ou _..._
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r'<i style="color: #cbd5e1;">\1</i>', escaped)

        # Quebras de linha
        escaped = escaped.replace("\n", "<br>")
        escaped = re.sub(r'(</div>)<br>', r'\1', escaped)

        return escaped
    except Exception as e:
        logger.error(f"Erro em format_markdown_to_html: {e}")
        import html
        return html.escape(str(text)).replace("\n", "<br>")
