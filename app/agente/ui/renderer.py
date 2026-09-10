import shutil
import sys
from agente import config as _config

def _criar_writer_com_word_wrap(write_func):
    """Wrapper que faz word wrap por palavra em vez de cortar no meio."""
    estado = {"col": 0, "palavra": "", "em_code": False}

    def flush_palavra():
        palavra = estado["palavra"]
        estado["palavra"] = ""
        if not palavra:
            return
        try:
            largura = shutil.get_terminal_size().columns
        except Exception:
            largura = 80
            
        if estado["col"] > 0 and estado["col"] + len(palavra) > largura:
            write_func("\n")
            estado["col"] = 0
            if estado["em_code"] and "code_wrap_callback" in estado and estado["code_wrap_callback"]:
                estado["code_wrap_callback"]()
        
        write_func(palavra)
        estado["col"] += len(palavra)

    def write(texto):
        i = 0
        while i < len(texto):
            char = texto[i]

            if char == "\x1b":
                flush_palavra()
                j = i
                while j < len(texto) and texto[j] != "m":
                    j += 1
                if j < len(texto):
                    j += 1
                write_func(texto[i:j])
                i = j
                continue

            if char == "\n":
                flush_palavra()
                write_func("\n")
                estado["col"] = 0
                i += 1
                continue

            if char == " ":
                flush_palavra()
                try:
                    largura = shutil.get_terminal_size().columns
                except Exception:
                    largura = 80
                    
                if estado["em_code"] or estado["col"] < largura:
                    write_func(" ")
                    estado["col"] += 1
                i += 1
                continue

            estado["palavra"] += char
            i += 1

        return len(texto)

    def set_code_mode(valor, callback=None):
        estado["em_code"] = valor
        estado["code_wrap_callback"] = callback

    write.set_code_mode = set_code_mode
    write.raw = write_func
    return write

def imprimir_stream_colorido(stream_chunks):
    """Imprime resposta da LLM em stream com cores ricas para markdown e word wrap."""
    resposta_completa = ""

    # Sem cor — imprimir direto
    if _config.NO_COLOR:
        for chunk in stream_chunks:
            resposta_completa += chunk
            sys.stdout.write(chunk)
            sys.stdout.flush()
        sys.stdout.write("\n")
        sys.stdout.flush()
        return resposta_completa

    # ── Terminal width ─────────────────────────────────────
    try:
        TERM_WIDTH = shutil.get_terminal_size().columns
    except Exception:
        TERM_WIDTH = 80

    # ── Paleta de cores ──────────────────────────────────────
    RST   = "\x1b[0m"
    BOLD  = "\x1b[1m"
    DIM   = "\x1b[2m"
    C_CODE_BLOCK  = "\x1b[38;5;78m"
    C_CODE_INLINE = "\x1b[38;5;214m"
    C_BORDER      = "\x1b[38;5;240m"
    C_HEADER      = "\x1b[38;5;75m"
    C_BULLET      = "\x1b[38;5;75m"
    C_LANG        = "\x1b[38;5;245m"
    C_BOLD        = "\x1b[1;97m"

    # ── Estado ────────────────────────────────────────────────
    in_block       = False
    in_inline      = False
    in_bold        = False
    backtick_count = 0
    asterisk_count = 0
    hash_count     = 0
    at_line_start  = True
    line_prefix    = ""
    block_lang     = ""
    reading_lang   = False
    block_opened   = False
    at_code_line_start = False

    w = _criar_writer_com_word_wrap(sys.stdout.write)

    def flush_code_prefix():
        nonlocal at_code_line_start
        if at_code_line_start:
            w(f"{C_BORDER}│{RST} {C_CODE_BLOCK}")
            at_code_line_start = False

    def flush_backticks():
        nonlocal backtick_count, in_block, in_inline
        nonlocal reading_lang, block_lang, block_opened, at_code_line_start

        if backtick_count >= 3:
            if not in_block:
                in_block = True
                w.set_code_mode(True, lambda: w.raw(f"{RST}{C_BORDER}│{RST} {C_CODE_BLOCK}"))
                reading_lang = True
                block_lang = ""
                block_opened = False
                at_code_line_start = False
            else:
                in_block = False
                reading_lang = False
                w.set_code_mode(False)
                if not at_code_line_start:
                    w(f"{RST}\n")
                w(f"{C_BORDER}╰{'─' * 34}{RST}\n")
                block_opened = False
        elif backtick_count > 0:
            if in_block:
                flush_code_prefix()
                w("`" * backtick_count)
            else:
                in_inline = not in_inline
                w(C_CODE_INLINE if in_inline else RST)

        backtick_count = 0

    # ── Imprime a borda de abertura do bloco ───────────────────
    def emit_block_header():
        nonlocal block_opened
        if block_opened:
            return
        block_opened = True
        lang = block_lang.strip()
        if lang:
            label = f" {lang} "
            pad = max(1, 33 - len(label))
            w(f"\n{C_BORDER}╭─{C_LANG}{label}{C_BORDER}{'─' * pad}{RST}\n")
        else:
            w(f"\n{C_BORDER}╭{'─' * 34}{RST}\n")

    # ── Flush asteriscos acumulados ────────────────────────────
    def flush_asterisks():
        nonlocal asterisk_count, in_bold
        if asterisk_count >= 2:
            in_bold = not in_bold
            w(C_BOLD if in_bold else RST)
            asterisk_count -= 2
            if asterisk_count > 0:
                w("*" * asterisk_count)
        elif asterisk_count == 1:
            w("*")
        asterisk_count = 0

    # ── Flush hashes acumulados ────────────────────────────────
    def flush_hashes():
        nonlocal hash_count
        if hash_count > 0:
            w("#" * hash_count)
            hash_count = 0

    # ── Flush prefixo de linha ─────────────────────────────────
    def flush_prefix():
        nonlocal line_prefix
        if line_prefix:
            w(line_prefix)
            line_prefix = ""

    # ─── LOOP PRINCIPAL ───────────────────────────────────────
    for chunk in stream_chunks:
        if "&nbsp;" in chunk or "<br" in chunk:
            chunk = (
                chunk.replace("&nbsp;", " ")
                .replace("<br>", "\n")
                .replace("<br/>", "\n")
                .replace("<br />", "\n")
            )
        resposta_completa += chunk

        for char in chunk:

            # ── Contagem de backticks ──
            if char == '`':
                if asterisk_count > 0:
                    flush_asterisks()
                flush_prefix()
                backtick_count += 1
                continue

            # ── Teve backticks e agora outro char ──
            if backtick_count > 0:
                was_in_block = in_block
                flush_backticks()

                if in_block and not was_in_block and reading_lang:
                    if char == '\n':
                        reading_lang = False
                        emit_block_header()
                        at_code_line_start = True
                        continue
                    else:
                        block_lang += char
                        continue

            # ── Lendo nome da linguagem ──
            if reading_lang:
                if char == '\n':
                    reading_lang = False
                    emit_block_header()
                    at_code_line_start = True
                    continue
                else:
                    block_lang += char
                    continue

            # ── Dentro de bloco de código ──
            if in_block:
                w.set_code_mode(True, lambda: w.raw(f"{RST}{C_BORDER}│{RST} {C_CODE_BLOCK}"))
                if char == '\n':
                    flush_code_prefix()
                    w(f"{RST}\n")
                    at_code_line_start = True
                else:
                    flush_code_prefix()
                    w(char)
                continue

            # ── Asteriscos (bold) fora de blocos ──
            if char == '*' and not in_inline:
                flush_prefix()
                asterisk_count += 1
                continue

            if asterisk_count > 0:
                flush_asterisks()

            # ── Headers (# no início da linha) ──
            if at_line_start and char == '#' and not in_inline:
                hash_count += 1
                continue

            if hash_count > 0 and char == ' ' and at_line_start:
                flush_prefix()
                w(f"\n{BOLD}{C_HEADER}")
                if hash_count == 1:
                    w("━━ ")
                elif hash_count == 2:
                    w("── ")
                else:
                    w("─ ")
                hash_count = 0
                at_line_start = False
                continue
            elif hash_count > 0 and char != '#':
                flush_hashes()

            # ── Newline ──
            if char == '\n':
                flush_prefix()

                if in_bold:
                    w(RST)
                    in_bold = False

                w(f"{RST}\n")
                at_line_start = True
                line_prefix = ""
                continue

            # ── Espaço ──
            if char == ' ':
                flush_prefix()
                w(" ")
                at_line_start = False
                continue

            # ── Bullets no início da linha ──
            if at_line_start and not in_block:
                if char in ('-', '•') and not line_prefix:
                    line_prefix += char
                    continue
                elif char == ' ' and line_prefix in ('-', '•'):
                    flush_prefix()
                    w(f"  {C_BULLET}●{RST} ")
                    line_prefix = ""
                    at_line_start = False
                    continue
                elif line_prefix:
                    flush_prefix()

            at_line_start = False
            w(char)

        sys.stdout.flush()

    # ── Limpar estado final ──
    if backtick_count > 0:
        flush_backticks()
    if asterisk_count > 0:
        flush_asterisks()
    flush_hashes()
    flush_prefix()

    w(f"{RST}\n")
    sys.stdout.flush()
    return resposta_completa
