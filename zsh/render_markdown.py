#!/usr/bin/env python3
"""
render_markdown.py
Renderizador terminal de Markdown de alta qualidade para a suíte Metis.
Utiliza 'rich' se disponível para colorização completa, tabelas formatadas,
blocos de código com destaque de sintaxe e bordas estéticas.
"""
import sys
import shutil

def main():
    if len(sys.argv) < 2:
        text = sys.stdin.read()
    else:
        text = sys.argv[1]

    if not text.strip():
        return

    try:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.theme import Theme

        # Paleta temática do Metis (Dourado, Ciano, Verde Suave)
        custom_theme = Theme({
            "markdown.h1": "bold bright_cyan",
            "markdown.h2": "bold #f0a85d",
            "markdown.h3": "bold #fad094",
            "markdown.code": "bold bright_yellow on #1e2327",
            "markdown.table.header": "bold bright_cyan",
            "markdown.table.border": "#463e54",
            "markdown.bullet": "bright_green",
            "markdown.link": "underline cyan",
        })

        width = shutil.get_terminal_size((80, 24)).columns
        console = Console(theme=custom_theme, width=min(width, 100))
        console.print(Markdown(text))
    except Exception:
        # Fallback simples
        print(text)

if __name__ == "__main__":
    main()
