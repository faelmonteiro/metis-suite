import atexit
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from agente import config

COMANDOS_SAIDA = [
    "0", "voltar", "/voltar", "/menu", "menu", "exit", "sair", "/sair"
]


def limitar_texto(texto: str, limite: int) -> str:
    if not texto:
        return ""

    texto = " ".join(texto.split())

    if limite <= 0:
        return texto

    if len(texto) <= limite:
        return texto

    return texto[:limite].rstrip() + "..."

ARQUIVOS_SENSIVEIS = {
    ".env", ".netrc", ".npmrc", ".pypirc",
    "id_rsa", "id_ed25519", "id_ecdsa",
    "authorized_keys", "known_hosts",
    "credentials", "shadow", "passwd",
}

EXTENSOES_SENSIVEIS = {
    ".pem", ".key", ".crt", ".p12", ".pfx", ".jks", ".keystore",
}

PASTAS_SENSIVEIS = {
    ".env", ".git", ".ssh", ".gnupg", ".aws",
    ".kube", ".docker",
}


def sanitizar_nome_sessao(nome: str) -> str:
    nome = (nome or "").strip().lower()
    nome = re.sub(r"[^a-z0-9_\-]", "_", nome)
    nome = re.sub(r"_+", "_", nome)
    nome = nome[:50].strip("_")
    return nome or "sessao"


def caminho_leitura_seguro(caminho_str: str, permitir_diretorio: bool = False) -> Path:
    caminho = Path(caminho_str).expanduser().resolve(strict=False)
    home = Path.home().resolve()
    cwd = Path.cwd().resolve()

    try:
        if str(cwd) == "/":
            dentro = caminho.is_relative_to(home)
        else:
            dentro = caminho.is_relative_to(home) or caminho.is_relative_to(cwd)
    except Exception:
        dentro = False

    if not dentro:
        raise ValueError("Acesso negado: o caminho está fora do diretório permitido.")

    if not permitir_diretorio and caminho.is_dir():
        raise ValueError("Acesso negado: o caminho informado é um diretório.")

    partes = {parte.lower() for parte in caminho.parts}
    if partes & PASTAS_SENSIVEIS:
        raise ValueError("Acesso negado: pasta sensível.")

    nome = caminho.name.lower()
    if nome.startswith(".env") or nome in ARQUIVOS_SENSIVEIS:
        raise ValueError("Acesso negado: arquivo sensível.")

    if caminho.suffix.lower() in EXTENSOES_SENSIVEIS:
        raise ValueError("Acesso negado: extensão sensível.")

    return caminho

_PALAVRAS_CHAVE_BUSCA = [
    r"atual", r"hoje", r"agora", r"recente", r"novidade",
    r"preço", r"preco", r"cotação", r"cotacao",
    r"notícia", r"noticia", r"último", r"ultimo", r"última", r"ultima",
    r"aconteceu", r"resultado", r"placar", r"eleição", r"eleicao",
    r"lançamento", r"lancamento", r"estreia",
    r"2024", r"2025", r"2026", r"2027", r"tempo real",
    r"quem é", r"quem e",
    r"pesquise", r"busque", r"procure", r"pesquisar", r"buscar", r"procurar"
]
_PADRAO_BUSCA = re.compile(r"\b(?:{})\b".format("|".join(_PALAVRAS_CHAVE_BUSCA)), re.IGNORECASE)

_PADRAO_SISTEMA_LOCAL = re.compile(
    r"(?i)\b(?:mem[oó]ria|ram|disco|armazenamento|cpu|processador|processo|processos|hyprland|waybar|"
    r"meu\s+pc|meu\s+computador|meu\s+sistema|meu\s+arquivo|minha\s+pasta|meus?\s+arquivos?|"
    r"meu\s+desktop|meu\s+workspace|meu\s+monitor|meu\s+volume|meu\s+áudio|meu\s+audio)\b"
)

def detectar_intencao_busca(texto: str) -> bool:
    if not texto:
        return False
    if _PADRAO_SISTEMA_LOCAL.search(texto):
        return False
    return bool(_PADRAO_BUSCA.search(texto))


def _stdin_e_tty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def bloquear_teclado():
    if not _stdin_e_tty():
        return
    try:
        import termios
        fd = sys.stdin.fileno()
        attr = termios.tcgetattr(fd)
        attr[3] = attr[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        atexit.register(desbloquear_teclado)
    except Exception:
        pass


def desbloquear_teclado():
    if not _stdin_e_tty():
        return
    try:
        import termios
        fd = sys.stdin.fileno()
        attr = termios.tcgetattr(fd)
        attr[3] = attr[3] | termios.ECHO
        termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def hyprctl(command: str):
    """Executa comando hyprctl somente se o Hyprland estiver ativo."""
    if config.HYPRLAND_ENABLED:
        try:
            subprocess.run(
                ["hyprctl"] + command.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass


def mover_janela_canto_superior_direito(fallback_w: int = 860, fallback_h: int = 550) -> tuple[int, int]:
    """
    Calcula e posiciona a janela ativa no canto superior direito da tela de forma precisa,
    garantindo modo flutuante e respeitando a resolução do monitor, barras (Waybar) e gaps.
    """
    if config.HYPRLAND_ENABLED or shutil.which("hyprctl"):
        try:
            import json
            win_res = subprocess.run(["hyprctl", "activewindow", "-j"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.4)
            mon_res = subprocess.run(["hyprctl", "monitors", "-j"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.4)
            if win_res.returncode == 0 and mon_res.returncode == 0:
                win = json.loads(win_res.stdout)
                monitors = json.loads(mon_res.stdout)
                
                mon_id = win.get("monitor", 0)
                target_mon = next((m for m in monitors if m.get("id") == mon_id), monitors[0] if monitors else None)
                if target_mon:
                    mon_x = target_mon.get("x", 0)
                    mon_y = target_mon.get("y", 0)
                    mon_w = target_mon.get("width", 1920)
                    reserved = target_mon.get("reserved", [0, 42, 0, 0])
                    top_bar = reserved[1] if len(reserved) > 1 else 0
                    right_bar = reserved[2] if len(reserved) > 2 else 0

                    addr = win.get("address")
                    is_floating = win.get("floating", True)
                    win_size = win.get("size", [fallback_w, fallback_h])
                    win_w = win_size[0] if win_size and len(win_size) > 0 else fallback_w
                    win_h = win_size[1] if win_size and len(win_size) > 1 else fallback_h

                    # Se a janela estiver em modo tiled ou esticada como fullscreen (> 1150px), força float e redimensiona
                    if not is_floating or win_w > (mon_w - 150):
                        win_w = fallback_w
                        win_h = fallback_h
                        if addr:
                            hyprctl(f"dispatch setfloating address:{addr}")
                            hyprctl(f"dispatch resizewindowpixel exact {win_w} {win_h},address:{addr}")
                        else:
                            hyprctl("dispatch setfloating")
                            hyprctl(f"dispatch resizeactive exact {win_w} {win_h}")

                    gap_x = 10
                    gap_y = 14
                    target_x = int(mon_x + mon_w - right_bar - win_w - gap_x)
                    target_y = int(mon_y + top_bar + gap_y)

                    if addr:
                        hyprctl(f"dispatch movewindowpixel exact {target_x} {target_y},address:{addr}")
                    else:
                        hyprctl(f"dispatch moveactive exact {target_x} {target_y}")
                    return target_x, target_y
        except Exception:
            pass
    return (max(10, 1920 - fallback_w - 10), 56)

def _register_enhanced_terminal_sequences():
    try:
        import re
        from prompt_toolkit.input.vt100_parser import Vt100Parser, ANSI_SEQUENCES, _IS_PREFIX_OF_LONGER_MATCH_CACHE
        from prompt_toolkit.keys import Keys

        _csi_u_key13_re = re.compile(r"^\x1b\[(13|10)(?:;|\:)(\d+)(?:[;\:]\d+)*u$")
        _xterm_key13_re = re.compile(r"^\x1b\[27;(\d+);(13|10)~?$")
        _csi_tilde_key13_re = re.compile(r"^\x1b\[(13|10);(\d+)~$")

        if not hasattr(Vt100Parser, "_orig_get_match_patched"):
            orig_get_match = Vt100Parser._get_match
            Vt100Parser._orig_get_match_patched = orig_get_match

            def patched_get_match(self, prefix: str):
                m = _csi_u_key13_re.match(prefix)
                if m:
                    mod = int(m.group(2)) - 1
                    return Keys.ControlJ if (mod & (1 | 2 | 4)) else Keys.ControlM

                m2 = _xterm_key13_re.match(prefix)
                if m2:
                    mod = int(m2.group(1)) - 1
                    return Keys.ControlJ if (mod & (1 | 2 | 4)) else Keys.ControlM

                m3 = _csi_tilde_key13_re.match(prefix)
                if m3:
                    mod = int(m3.group(2)) - 1
                    return Keys.ControlJ if (mod & (1 | 2 | 4)) else Keys.ControlM

                return orig_get_match(self, prefix)

            Vt100Parser._get_match = patched_get_match

        # Preenche ANSI_SEQUENCES para todas as combinações de modificadores (NumLock, CapsLock, Shift, etc.)
        for mod in range(1, 256):
            target_key = Keys.ControlJ if ((mod - 1) & (1 | 2 | 4)) else Keys.ControlM
            for k in ("13", "10"):
                for suffix in ("u", ";1u", ":1u", ":1;1u"):
                    ANSI_SEQUENCES[f"\x1b[{k};{mod}{suffix}"] = target_key
                ANSI_SEQUENCES[f"\x1b[27;{mod};{k}~"] = target_key
                ANSI_SEQUENCES[f"\x1b[{k};{mod}~"] = target_key

        _IS_PREFIX_OF_LONGER_MATCH_CACHE.clear()
    except Exception:
        pass

_register_enhanced_terminal_sequences()

def _apply_word_wrap(buffer, prompt_len: int = 3) -> None:
    """Quebra de linha por palavra completa (Word Wrap) sem cortar palavras ao meio em nenhuma linha."""
    import shutil
    try:
        cols = shutil.get_terminal_size((80, 24)).columns
    except Exception:
        cols = 80
    if cols < 20:
        cols = 80

    try:
        doc = buffer.document
        col = doc.cursor_position_col
        line = doc.current_line

        # Largura útil da linha considerando o recuo/indentação do prompt e margem de segurança de 2 colunas
        available_width = max(15, cols - prompt_len - 2)

        if len(line) >= available_width:
            space_idx = line.rfind(' ', 0, available_width + 1)
            if space_idx > 0:
                line_start_idx = doc.cursor_position - col
                global_space_idx = line_start_idx + space_idx

                full_text = buffer.text
                if 0 <= global_space_idx < len(full_text) and full_text[global_space_idx] == ' ':
                    new_text = full_text[:global_space_idx] + '\n' + full_text[global_space_idx + 1:]
                    from prompt_toolkit.document import Document
                    buffer.set_document(Document(new_text, buffer.cursor_position), bypass_readonly=True)
    except Exception:
        pass


def safe_input(prompt_text: str, multiline: bool = True) -> str:
    import sys
    if sys.stdout.isatty():
        try:
            import re
            from prompt_toolkit import PromptSession
            from prompt_toolkit.formatted_text import ANSI
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.keys import Keys
            
            clean_prompt = prompt_text.lstrip("\n")
            visible_prompt = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', clean_prompt)
            prompt_len = len(visible_prompt.split('\n')[-1]) if visible_prompt else 3

            kb = KeyBindings()

            @kb.add(Keys.Any)
            def _(event):
                event.current_buffer.insert_text(event.data)
                _apply_word_wrap(event.current_buffer, prompt_len=prompt_len)

            if multiline:
                @kb.add('c-j')
                @kb.add('escape', 'enter')
                def _(event):
                    event.current_buffer.insert_text('\n')
            else:
                @kb.add('c-j')
                @kb.add('escape', 'enter')
                def _(event):
                    event.current_buffer.validate_and_handle()
                
            @kb.add('enter')
            def _(event):
                event.current_buffer.validate_and_handle()

            from agente.completer import ChatCompleter
            completer = ChatCompleter if ChatCompleter else None
            
            from prompt_toolkit.styles import Style
            custom_style = Style.from_dict({
                'completion-menu.completion': 'bg:ansiblack ansiyellow',
                'completion-menu.completion.current': 'bg:ansigreen ansiblack bold',
                'scrollbar.background': 'bg:ansigray',
                'scrollbar.button': 'bg:ansiwhite',
            })

            def prompt_continuation(width, line_number, is_soft_wrap):
                return " " * prompt_len

            session = PromptSession(
                key_bindings=kb, 
                multiline=multiline,
                wrap_lines=True,
                prompt_continuation=prompt_continuation if multiline else None,
                completer=completer,
                complete_while_typing=True,
                style=custom_style
            )
            
            if prompt_text.startswith("\n"):
                sys.stdout.write("\n")

            raw_input = session.prompt(ANSI(clean_prompt), wrap_lines=True)
            return normalizar_prompt_enviado(raw_input)
        except ImportError:
            import re
            prompt_safe = re.sub(r'(\033\[[0-9;]*m)', r'\x01\g<1>\x02', prompt_text)
            return normalizar_prompt_enviado(input(prompt_safe))
    return normalizar_prompt_enviado(input(prompt_text))


def normalizar_prompt_enviado(texto: str) -> str:
    """
    Normaliza o texto digitado pelo usuário antes de processar.
    Une quebras de linha automáticas de tela contínua mantendo blocos de código (```),
    parágrafos explícitos (\n\n) e itens de listas.
    """
    if not texto or "\n" not in texto:
        return (texto or "").strip()

    if "```" in texto or "\n\n" in texto:
        return texto.strip()

    import re
    linhas = texto.splitlines()
    if any(re.match(r"^\s*([-*•>]|\d+\.)\s+", l) for l in linhas):
        return texto.strip()

    return " ".join(texto.split())

def configurar_api_key(chave_nome: str) -> bool:
    from agente.colors import YELLOW, RESET, BOLD, GREEN
    from agente.providers_manager import sincronizar_config

    print(f"\n{YELLOW}A chave {chave_nome} não está configurada ou é inválida.{RESET}")
    nova_chave = input(f"{BOLD}Cole sua {chave_nome} (ou Enter para cancelar): {RESET}").strip()

    if not nova_chave:
        print("Operação cancelada.")
        return False

    sincronizar_config(chave_nome, nova_chave)
    print(f"{GREEN}Chave salva com sucesso no arquivo .env e sincronizada em memória!{RESET}")
    return True


def verificar_conexao_internet(timeout: float = 1.2) -> bool:
    """Verifica se o sistema possui conexão ativa com a internet de forma rápida."""
    import socket
    for host in ("1.1.1.1", "8.8.8.8", "208.67.222.222"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((host, 53))
            return True
        except Exception:
            continue
    return False


