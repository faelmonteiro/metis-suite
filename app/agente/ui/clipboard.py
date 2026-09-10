import shutil
import subprocess
import sys
import re

def _copiar_clipboard(texto: str) -> bool:
    """Copia texto para a área de transferência com múltiplos fallbacks."""
    comandos_clipboard = [
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
        ["clip.exe"],
    ]

    for cmd in comandos_clipboard:
        try:
            subprocess.run(
                cmd,
                input=texto.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            return True
        except FileNotFoundError:
            continue
        except subprocess.CalledProcessError:
            continue
        except subprocess.TimeoutExpired:
            continue

    try:
        import pyperclip
        pyperclip.copy(texto)
        return True
    except Exception:
        pass

    return False

def extrair_blocos(resposta: str) -> tuple[list, list]:
    """Extrai blocos de código markdown separando por shell vs código geral."""
    SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh", "terminal", ""}

    padrao = re.compile(
        r"```([\w+#.-]*)[ \t]*\r?\n(.*?)\r?\n?[ \t]*```",
        re.DOTALL
    )
    blocos_encontrados = padrao.findall(resposta)

    blocos_shell = []
    blocos_codigo = []

    for lang, conteudo in blocos_encontrados:
        lang_lower = lang.lower()
        if lang_lower in SHELL_LANGS:
            blocos_shell.append(conteudo)
        else:
            blocos_codigo.append((lang, conteudo))
            
    return blocos_shell, blocos_codigo


def _extrair_comando_e_comentario(linha: str) -> tuple[str, str]:
    """Extrai apenas o comando executável limpo e separa qualquer descrição/comentário."""
    linha = linha.strip()
    if not linha:
        return "", ""

    # Remove marcadores de lista iniciais: '-', '*', '1.', '2.', '•', etc.
    linha = re.sub(r"^(?:[-*•]|\d+[\.)])\s*", "", linha)

    # Remove prefixos de terminal comuns como '$ ' ou '> '
    linha = re.sub(r"^[\$>]\s+", "", linha)

    if not linha:
        return "", ""

    # Caso 1: Comando envolvido em crases: `comando` : descrição ou `comando` - descrição
    m_backtick = re.match(r"^`([^`]+)`(?:\s*[:\-–—]\s*(.*))?$", linha)
    if m_backtick:
        cmd = m_backtick.group(1).strip()
        desc = m_backtick.group(2).strip() if m_backtick.group(2) else ""
        return cmd, ("# " + desc) if desc else ""

    # Caso 2: Comentário padrão com '#'
    if "#" in linha:
        partes = linha.split("#", 1)
        return partes[0].strip(), "# " + partes[1].strip()

    # Caso 3: Divisão por ' : ' ou ' - ' entre comando curto e explicação em português
    m_sep = re.match(r"^([a-zA-Z0-9_\-\./~]+(?:\s+[a-zA-Z0-9_\-\./~<>\$\*+]+)*)\s*[:\-–—]\s+([A-ZÀ-Úa-zà-ú].*)$", linha)
    if m_sep:
        cmd = m_sep.group(1).strip()
        desc = m_sep.group(2).strip()
        if len(cmd.split()) <= 5:
            return cmd, "# " + desc

    # Caso 4: Comando puro (ex: 'ls -la', 'df -h')
    return linha, ""


def oferecer_extracao_comandos(resposta: str, interativo: bool = True) -> bool:
    """Extrai código/comandos de blocos e oferece cópia rápida para o usuário com visual responsivo."""
    if not interativo:
        return False

    try:
        if not sys.stdin.isatty():
            return False
    except Exception:
        return False

    blocos_shell, blocos_codigo = extrair_blocos(resposta)
    
    if not blocos_shell and not blocos_codigo:
        return False

    itens_raw = []
    for bloco in blocos_shell:
        linhas = bloco.strip().split("\n")
        for linha in linhas:
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue

            cmd_exec, comentario = _extrair_comando_e_comentario(linha_limpa)
            if cmd_exec:
                itens_raw.append(("comando", cmd_exec, comentario))

    for lang, conteudo in blocos_codigo:
        linhas_code = conteudo.strip().split("\n")
        primeira_linha = linhas_code[0] if linhas_code else ""
        num_linhas = len(linhas_code)
        lang_label = lang if lang else "código"
        itens_raw.append(("codigo", conteudo, f"{lang_label} ({num_linhas} linhas): {primeira_linha}"))

    if not itens_raw:
        return False

    # ── Determina largura do terminal ──
    try:
        cols = max(40, shutil.get_terminal_size((66, 24)).columns)
    except Exception:
        cols = 66

    # ── Paleta de Cores ANSI ──
    C_BORDER = "\x1b[38;5;240m"
    C_TITLE  = "\x1b[1;38;5;75m"
    C_IDX    = "\x1b[1;38;5;214m"
    C_CMD    = "\x1b[38;5;78m"
    C_COMM   = "\x1b[38;5;244m"
    C_GREEN  = "\x1b[38;5;46m"
    C_DIM    = "\x1b[38;5;242m"
    RST      = "\x1b[0m"

    title = " 📋 Comandos Disponíveis para Copiar "
    bar_len = max(4, cols - len(title) - 4)
    print(f"\n{C_BORDER}╭─{RST}{C_TITLE}{title}{RST}{C_BORDER}{'─' * bar_len}╮{RST}")

    itens_disponiveis = {}
    inner_width = cols - 4

    for i, item in enumerate(itens_raw, 1):
        tipo = item[0]
        cmd_ou_conteudo = item[1]
        comentario = item[2]
        
        itens_disponiveis[i] = (tipo, cmd_ou_conteudo)
        num_str = f"[{i:2d}] "

        if tipo == "comando":
            left_visible_len = len(num_str) + len(cmd_ou_conteudo)
            
            if comentario:
                available_for_comm = inner_width - left_visible_len - 2
                if available_for_comm > 8:
                    if len(comentario) > available_for_comm:
                        comentario_visivel = comentario[:available_for_comm - 3] + "..."
                    else:
                        comentario_visivel = comentario
                    line_content = f"{C_IDX}{num_str}{RST}{C_CMD}{cmd_ou_conteudo}{RST}  {C_COMM}{comentario_visivel}{RST}"
                    visible_len = left_visible_len + 2 + len(comentario_visivel)
                else:
                    if len(cmd_ou_conteudo) > inner_width - len(num_str):
                        cmd_visivel = cmd_ou_conteudo[:inner_width - len(num_str) - 3] + "..."
                    else:
                        cmd_visivel = cmd_ou_conteudo
                    line_content = f"{C_IDX}{num_str}{RST}{C_CMD}{cmd_visivel}{RST}"
                    visible_len = len(num_str) + len(cmd_visivel)
            else:
                if len(cmd_ou_conteudo) > inner_width - len(num_str):
                    cmd_visivel = cmd_ou_conteudo[:inner_width - len(num_str) - 3] + "..."
                else:
                    cmd_visivel = cmd_ou_conteudo
                line_content = f"{C_IDX}{num_str}{RST}{C_CMD}{cmd_visivel}{RST}"
                visible_len = len(num_str) + len(cmd_visivel)
        else:
            # Bloco de código geral
            code_desc = f"📄 {comentario}"
            if len(code_desc) > inner_width - len(num_str):
                code_desc = code_desc[:inner_width - len(num_str) - 3] + "..."
            line_content = f"{C_IDX}{num_str}{RST}\x1b[38;5;75m{code_desc}{RST}"
            visible_len = len(num_str) + len(code_desc)

        padding = max(0, inner_width - visible_len)
        print(f"{C_BORDER}│{RST} {line_content}{' ' * padding} {C_BORDER}│{RST}")

    print(f"{C_BORDER}╰{'─' * (cols - 2)}╯{RST}")
    total = len(itens_raw)
    print(f"{C_DIM}💡 Digite o número [1-{total}] para copiar (ou ENTER para ignorar){RST}")

    while True:
        try:
            from prompt_toolkit import prompt
            escolha = prompt("Copiar > ").strip()
        except Exception:
            escolha = input("Copiar > ").strip()

        if not escolha:
            break

        if escolha.isdigit():
            idx = int(escolha)
            if idx in itens_disponiveis:
                tipo, conteudo = itens_disponiveis[idx]

                if _copiar_clipboard(conteudo):
                    if tipo == "codigo":
                        print(f"\n{C_GREEN}✔ Código [{escolha}] copiado inteiro para a área de transferência!{RST}")
                    else:
                        print(f"\n{C_GREEN}✔ Comando [{escolha}] copiado:{RST} {C_CMD}{conteudo}{RST}")
                    print(f"\x1b[38;5;214m📋 Cole com Ctrl+Shift+V no seu terminal.{RST}")
                    print(f"{C_DIM}(Digite outro número para copiar mais, ou ENTER para continuar){RST}\n")
                else:
                    print(f"\x1b[38;5;196mNenhum utilitário de clipboard encontrado (instale wl-clipboard ou xclip).{RST}")
            else:
                print(f"\x1b[38;5;196mNúmero inválido. Escolha entre 1 e {total}.{RST}")
        else:
            print(f"\x1b[38;5;196mDigite apenas o número do comando.{RST}")

    return False
