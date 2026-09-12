import os
import re
import json
import subprocess
from pathlib import Path
from agente import config
from agente.colors import RED, GREEN, YELLOW, CYAN, BOLD, RESET, GRAY
from agente.utils import caminho_leitura_seguro

try:
    from agente.providers_manager import obter_preferencia
    AUTO_APPROVE_MODE = bool(obter_preferencia("auto_approve_mode", False))
except Exception:
    AUTO_APPROVE_MODE = False

def _resolver_caminho_amigavel(caminho_str: str) -> str:
    """
    Resolve dinamicamente qualquer caminho relativo, absoluto ou nome de pasta/arquivo
    no CWD ou na Home do usuário, com suporte inteligente a maiúsculas/minúsculas e acentos.
    """
    c_str = str(caminho_str or "").strip()
    if not c_str or c_str in (".", "./"):
        return "."

    p = Path(c_str).expanduser()
    if p.exists():
        return str(p)

    # 1. Tenta no CWD direto
    local_path = Path.cwd() / c_str
    if local_path.exists():
        return str(local_path)

    # 2. Tenta na Home direta
    home_path = Path.home() / c_str
    if home_path.exists():
        return str(home_path)

    # 3. Busca inteligente na Home e no CWD (insensível a acentos e maiúsculas/minúsculas)
    import unicodedata
    def unaccent(s):
        return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c)).lower()

    c_un = unaccent(c_str)

    try:
        for item in Path.home().iterdir():
            if unaccent(item.name) == c_un:
                return str(item)
    except Exception:
        pass

    try:
        for item in Path.cwd().iterdir():
            if unaccent(item.name) == c_un:
                return str(item)
    except Exception:
        pass

    # 4. Fallback para nomes e apelidos comuns de pastas
    termo_lower = c_str.lower()
    if termo_lower in {"download", "downloads"}:
        return "~/Downloads"
    elif termo_lower in {"documento", "documentos"}:
        return "~/Documentos"
    elif termo_lower in {"imagem", "imagens", "pictures", "fotos"}:
        return "~/Imagens"
    elif termo_lower in {"musica", "musicas", "música", "músicas", "music"}:
        return "~/Músicas"
    elif termo_lower in {"video", "videos", "vídeo", "vídeos"}:
        return "~/Vídeos"
    elif termo_lower in {"desktop", "área de trabalho", "area de trabalho"}:
        return "~/Área de trabalho"

    return c_str


def listar_diretorio(caminho: str = ".") -> str:
    if not caminho or not str(caminho).strip():
        caminho = "."

    caminho_str = _resolver_caminho_amigavel(str(caminho).strip())

    try:
        path = caminho_leitura_seguro(caminho_str, permitir_diretorio=True)
    except Exception as e:
        return f"Acesso negado ou caminho inválido: {e}"
        
    if not path.exists():
        return f"Erro: O diretório {caminho_str} não existe."
    if not path.is_dir():
        return f"Erro: {caminho_str} não é um diretório."
    
    try:
        items = list(path.iterdir())
        pastas = sorted([f"[DIR] {i.name}" for i in items if i.is_dir()])
        arquivos = sorted([f"[FILE] {i.name}" for i in items if not i.is_dir()])
        
        if not pastas and not arquivos:
            return "O diretório está vazio."
        return "\n".join(pastas + arquivos)
    except Exception as e:
        return f"Erro ao listar diretório: {e}"

def ler_arquivo(caminho: str) -> str:
    from agente.services.file_reader import ler_arquivo as _ler
    caminho_str = _resolver_caminho_amigavel(str(caminho).strip())
    try:
        path = caminho_leitura_seguro(caminho_str)
    except Exception as e:
        return f"Acesso negado para leitura: {e}"
    try:
        conteudo = _ler(str(path), max_chars=100000)
        return conteudo
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"

def pedir_confirmacao_usuario(mensagem: str) -> bool:
    import sys
    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        return False
    from agente.utils import desbloquear_teclado, bloquear_teclado
    desbloquear_teclado()
    try:
        resposta = input(mensagem).strip().lower()
        return resposta in {"s", "sim", "y", "yes"}
    except (KeyboardInterrupt, EOFError):
        print()
        return False
    finally:
        bloquear_teclado()

def escrever_arquivo(caminho: str, conteudo: str) -> str:
    try:
        path = caminho_leitura_seguro(caminho)
    except Exception as e:
        return f"Acesso negado para escrita: {e}"
    
    import sys
    this_module = sys.modules[__name__]
    auto = getattr(this_module, "AUTO_APPROVE_MODE", False)
    
    if auto:
        print(f"\n{YELLOW}⚠️ Auto-approve ativado. Salvando arquivo: {BOLD}{path}{RESET}")
    else:
        print(f"\n{YELLOW}⚠️ A IA quer criar/sobrescrever o arquivo: {BOLD}{path}{RESET}")
        if not pedir_confirmacao_usuario(f"{YELLOW}Deseja permitir? (s/n): {RESET}"):
            return f"Ação negada pelo usuário para gravar no arquivo {caminho}."
        
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(conteudo)
        print(f"{GREEN}✔ Arquivo {path.name} salvo com sucesso!{RESET}")
        return f"Arquivo {caminho} gravado com sucesso."
    except Exception as e:
        return f"Erro ao gravar arquivo: {e}"

def editar_arquivo(caminho: str, trecho_antigo: str, trecho_novo: str) -> str:
    try:
        path = caminho_leitura_seguro(caminho)
    except Exception as e:
        return f"Acesso negado para edição: {e}"

    if not path.exists():
        return f"Erro: O arquivo {caminho} não existe. Use 'escrever_arquivo' para criar arquivos novos."
    if path.is_dir():
        return f"Erro: {caminho} não é um arquivo."

    try:
        with open(path, "r", encoding="utf-8") as f:
            conteudo = f.read()
    except Exception as e:
        return f"Erro ao ler arquivo para edição: {e}"

    if trecho_antigo not in conteudo:
        return f"Erro: O trecho antigo especificado não foi encontrado exatamente dentro do arquivo {path.name}."

    import sys
    this_module = sys.modules[__name__]
    auto = getattr(this_module, "AUTO_APPROVE_MODE", False)

    print(f"\n{YELLOW}📝 A IA quer fazer uma edição cirúrgica em: {BOLD}{path}{RESET}")
    print(f"{CYAN}--- Preview da Alteração (Diff) ---{RESET}")
    for linha in trecho_antigo.splitlines():
        print(f"{RED}- {linha}{RESET}")
    for linha in trecho_novo.splitlines():
        print(f"{GREEN}+ {linha}{RESET}")
    print(f"{CYAN}----------------------------------{RESET}")

    if auto:
        print(f"{YELLOW}⚠️ Auto-approve ativado. Aplicando diff...{RESET}")
    else:
        if not pedir_confirmacao_usuario(f"{YELLOW}Deseja aplicar esta alteração? (s/n): {RESET}"):
            return f"Edição cancelada pelo usuário no arquivo {path.name}."

    try:
        import shutil
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)

        novo_conteudo = conteudo.replace(trecho_antigo, trecho_novo, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(novo_conteudo)
        print(f"{GREEN}✔ Alteração aplicada com sucesso em {path.name}! (Backup salvo em {backup_path.name}){RESET}")
        return f"Arquivo {path.name} editado com sucesso via diff cirúrgico. Backup salvo em {backup_path.name}."
    except Exception as e:
        return f"Erro ao aplicar edição no arquivo: {e}"

def gerar_pdf(caminho_destino: str, texto: str) -> str:
    try:
        path = caminho_leitura_seguro(caminho_destino)
    except Exception as e:
        return f"Acesso negado para gerar PDF: {e}"
        
    if not path.name.lower().endswith(".pdf"):
        path = path.with_suffix(".pdf")
        
    import sys
    this_module = sys.modules[__name__]
    auto = getattr(this_module, "AUTO_APPROVE_MODE", False)
    
    if auto:
        print(f"\n{YELLOW}⚠️ Auto-approve ativado. Gerando PDF em: {BOLD}{path}{RESET}")
    else:
        print(f"\n{YELLOW}⚠️ A IA quer gerar um PDF em: {BOLD}{path}{RESET}")
        if not pedir_confirmacao_usuario(f"{YELLOW}Deseja permitir? (s/n): {RESET}"):
            return f"Ação negada pelo usuário para gerar o PDF {path}."
        
    try:
        try:
            from fpdf import FPDF
        except ImportError:
            return "Erro: A biblioteca fpdf2 não está instalada. Execute 'pip install fpdf2'."
            
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf = FPDF()
        pdf.add_page()
        
        fonte_carregada = False
        for caminho_ttf in [
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/noto/NotoSans-Regular.ttf"
        ]:
            if os.path.exists(caminho_ttf):
                try:
                    pdf.add_font("DejaVu", "", caminho_ttf)
                    pdf.set_font("DejaVu", size=12)
                    fonte_carregada = True
                    break
                except Exception:
                    pass

        if not fonte_carregada:
            pdf.set_font("Helvetica", size=12)

        try:
            pdf.multi_cell(0, 10, text=texto)
        except Exception:
            texto_seguro = texto.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, text=texto_seguro)
        
        pdf.output(str(path))
        print(f"{GREEN}✔ PDF {path.name} gerado com sucesso!{RESET}")
        return f"PDF {path} gerado com sucesso."
    except Exception as e:
        return f"Erro ao gerar PDF: {e}"

COMANDOS_BLOQUEADOS = [
    r"\bsudo\b",
    r"\bsu\s+-\b",
    r"\bdoas\b",
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+[/~*]",
    r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r?\s+[/~*]",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bparted\b",
    r"\bgdisk\b",
    r"\bdd\s+if=",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\binit\s+[06]\b",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r">\s*/dev/(sd|nvme|hd)",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bchown\s+-R\s+.*?\s+/"
]

COMANDOS_DIAGNOSTICO = (
    "free", "df", "uptime", "uname", "top", "ps", "ip", "ping",
    "hyprctl", "wpctl", "brightnessctl", "nmcli", "bluetoothctl", "systemctl",
    "journalctl", "cat", "head", "tail", "ls", "grep", "which", "whereis", "whoami",
    "lscpu", "lsblk", "lspci", "lsusb", "sensors", "fastfetch", "neofetch", "arch", "hostname", "w", "who", "id", "pwd",
    "curl", "wget", "dig", "host", "nslookup", "resolvectl", "systemd-resolve", "ifconfig",
    "ss", "netstat", "route", "traceroute", "tracepath", "mtr", "echo", "printf",
    "awk", "sed", "cut", "sort", "uniq", "wc"
)

SENSITIVE_TARGETS = (
    ".ssh", ".aws", ".gnupg", ".env", "id_rsa", "credentials",
    "shadow", "sudoers", ".netrc", ".kube", ".docker/config",
    "/root", ".git-credentials", ".bash_history", ".zsh_history"
)

OPERADORES_PERIGOSOS_SHELL = (">", "<", "`", "$(", "${", "\n", "\r")
OPERADORES_ENCADEAMENTO = (";", "&&", "||", "|")
OPERADORES_SHELL_RAW = OPERADORES_PERIGOSOS_SHELL + OPERADORES_ENCADEAMENTO

class PoliticaComando:
    SAFE = "SAFE"        # Diagnóstico estritamente somente-leitura. Pode executar diretamente.
    CONFIRM = "CONFIRM"  # Comandos de alteração, compostos desconhecidos ou scripts. Exigem confirmação do usuário.
    BLOCK = "BLOCK"      # Comandos destrutivos ou de alto risco. Bloqueados categoricamente.

def normalizar_comando(comando) -> str:
    """Limpa e normaliza argumentos de comando enviados por LLMs (listas, JSON, aspas)."""
    if isinstance(comando, (list, tuple)):
        if len(comando) == 1 and isinstance(comando[0], str):
            comando = comando[0]
        else:
            comando = " ".join(str(c) for c in comando)
    elif isinstance(comando, str):
        cmd_s = comando.strip()
        if (cmd_s.startswith("[") and cmd_s.endswith("]")) or (cmd_s.startswith("(") and cmd_s.endswith(")")):
            try:
                parsed = json.loads(cmd_s)
                if isinstance(parsed, list):
                    if len(parsed) == 1 and isinstance(parsed[0], str):
                        comando = parsed[0]
                    else:
                        comando = " ".join(str(c) for c in parsed)
            except Exception:
                comando = cmd_s.strip("[]() ")
    
    comando = str(comando).strip()
    if (comando.startswith('"') and comando.endswith('"')) or (comando.startswith("'") and comando.endswith("'")):
        comando = comando[1:-1].strip()
    if comando.startswith('`') and comando.endswith('`'):
        comando = comando[1:-1].strip()
    return comando

def validar_comando_seguro(comando: str) -> tuple[bool, str]:
    cmd_lower = comando.lower().strip()
    for pattern in COMANDOS_BLOQUEADOS:
        if re.search(pattern, cmd_lower):
            return False, f"Comando bloqueado por segurança (padrão perigoso detectado: {pattern})"
    return True, ""

def avaliar_politica_comando_simples(cmd_simples: str) -> tuple[str, str, list[str] | None]:
    cmd_clean = cmd_simples.strip()
    if not cmd_clean:
        return PoliticaComando.CONFIRM, "Comando vazio", None

    seguro, motivo = validar_comando_seguro(cmd_clean)
    if not seguro:
        return PoliticaComando.BLOCK, motivo, None

    if cmd_clean.endswith("&") and not any(cmd_clean.startswith(a) for a in ["kate", "gedit", "xdg-open", "firefox", "chromium", "google-chrome", "code"]):
        return PoliticaComando.CONFIRM, "Comando em segundo plano (&) requer confirmação", None

    import shlex
    try:
        argv = shlex.split(cmd_clean)
    except ValueError as e:
        return PoliticaComando.CONFIRM, f"Parsing de argumentos shell inconclusivo: {e}", None

    if not argv:
        return PoliticaComando.CONFIRM, "Nenhum argumento executável identificado", None

    raw_bin = argv[0].strip()
    bin_name = os.path.basename(raw_bin).lower()

    if bin_name not in COMANDOS_DIAGNOSTICO:
        return PoliticaComando.CONFIRM, f"O utilitário '{bin_name}' requer confirmação para execução", argv

    # Validações adicionais para ferramentas específicas
    if bin_name == "find":
        flags_find = {arg.lower() for arg in argv[1:]}
        if any(f in flags_find for f in ["-exec", "-execdir", "-delete", "-ok", "-okdir"]):
            return PoliticaComando.CONFIRM, "Comando find contém parâmetros potencialmente modificadores (-exec/-delete)", argv

    if bin_name in {"cat", "head", "tail", "grep", "ls"}:
        for arg in argv[1:]:
            arg_l = arg.lower()
            if any(s in arg_l for s in SENSITIVE_TARGETS):
                return PoliticaComando.CONFIRM, "Acesso a arquivos de credenciais ou diretórios sensíveis do sistema", argv

    if bin_name == "systemctl":
        if len(argv) < 2 or argv[1].lower() not in {"status", "is-active", "is-enabled", "list-units", "list-unit-files"}:
            return PoliticaComando.CONFIRM, "Operações de alteração em serviços do systemctl exigem confirmação", argv

    if bin_name == "top" and "-b" not in argv:
        return PoliticaComando.CONFIRM, "Comando top interativo pode travar sem a opção em lote (-b)", argv

    if bin_name == "ping" and "-c" not in argv:
        return PoliticaComando.CONFIRM, "Comando ping contínuo requer limite de contagem (-c)", argv

    if bin_name == "curl":
        flags_mod = {"-o", "-O", "--output", "-d", "--data", "--data-raw", "--data-ascii", "--data-binary", "-F", "--form", "-T", "--upload-file"}
        for i, arg in enumerate(argv[1:]):
            arg_l = arg.lower()
            if arg_l in flags_mod or arg_l.startswith("-o") or arg_l.startswith("-O"):
                return PoliticaComando.CONFIRM, "Comando curl salva arquivo local ou envia dados", argv
            if arg in {"-X", "--request"} or arg_l in {"-x", "--request"}:
                if i + 2 < len(argv) and argv[i + 2].upper() not in {"GET", "HEAD"}:
                    return PoliticaComando.CONFIRM, "Comando curl com método HTTP não somente-leitura", argv
            if arg.startswith("-X") and len(arg) > 2 and arg[2:].upper() not in {"GET", "HEAD"}:
                return PoliticaComando.CONFIRM, "Comando curl com método HTTP não somente-leitura", argv

    if bin_name == "wget":
        has_stdout = any(arg in {"-O-", "-qO-"} or arg == "-" for arg in argv[1:])
        has_post = any(arg.startswith("--post") for arg in argv[1:])
        if has_post or not has_stdout:
            return PoliticaComando.CONFIRM, "Comando wget salva arquivo local ou envia dados", argv

    return PoliticaComando.SAFE, "Comando de diagnóstico somente leitura seguro", argv

def avaliar_politica_comando(comando: str) -> tuple[str, str, list[str] | None]:
    """
    Avalia a política de segurança de um comando.
    Retorna: (PoliticaComando, motivo, tokens_argv_se_simples)
    """
    cmd_clean = comando.strip()
    if not cmd_clean:
        return PoliticaComando.CONFIRM, "Comando vazio", None

    seguro, motivo = validar_comando_seguro(cmd_clean)
    if not seguro:
        return PoliticaComando.BLOCK, motivo, None

    # 1. Se contiver operadores de composição, redirecionamento ou substituição shell
    cmd_lower = cmd_clean.lower()
    for op in OPERADORES_SHELL_RAW:
        if op in cmd_lower:
            return PoliticaComando.CONFIRM, f"Comando composto ou com operador de shell detectado ('{op}')", None

    # 2. Comando simples
    return avaliar_politica_comando_simples(cmd_clean)

def executar_comando(comando: str, diretorio: str = ".") -> str:
    if not config.ENABLE_COMMAND_TOOL:
        return "Erro: a ferramenta executar_comando está desabilitada. Defina ENABLE_COMMAND_TOOL=1 no .env somente se você realmente precisar executar comandos."

    comando = normalizar_comando(comando)

    politica, motivo, argv = avaliar_politica_comando(comando)
    if politica == PoliticaComando.BLOCK:
        print(f"\n{RED}🚫 [Segurança] {motivo}{RESET}")
        return f"Erro de Segurança: {motivo}"

    try:
        cwd_path = caminho_leitura_seguro(diretorio, permitir_diretorio=True)
    except Exception as e:
        return f"Erro: Diretório de execução inválido ou inacessível: {e}"

    if not cwd_path.exists() or not cwd_path.is_dir():
        return f"Erro: Diretório de execução {diretorio} não existe."

    import sys
    this_module = sys.modules[__name__]
    auto = getattr(this_module, "AUTO_APPROVE_MODE", False)

    cmd_clean = comando.strip()

    # Se for SAFE, executa diretamente como diagnóstico
    if politica == PoliticaComando.SAFE:
        if auto:
            print(f"\n{YELLOW}⚡ [Metis Auto-Approve] Executando diagnóstico: {BOLD}{comando}{RESET}")
        else:
            print(f"\n{CYAN}🔍 [Diagnóstico do Sistema] Executando: {BOLD}{comando}{RESET}")
    else:
        # Requer confirmação explícita do usuário
        if auto:
            print(f"\n{YELLOW}⚡ [Metis Auto-Approve] Executando comando: {BOLD}{comando}{RESET}")
        else:
            print(f"\n{YELLOW}⚠️ A IA quer executar um comando no terminal:{RESET}")
            print(f"   {CYAN}${RESET} {BOLD}{comando}{RESET}")
            print(f"   {YELLOW}Diretório:{RESET} {cwd_path}")
            print(f"   {GRAY}Classificação:{RESET} {motivo}")
            if not pedir_confirmacao_usuario(f"{YELLOW}Deseja permitir a execução? (s/n): {RESET}"):
                return "Execução do comando cancelada pelo usuário."

    try:
        # Se for um aplicativo gráfico / desanexado comum (kate, xdg-open, navegador, etc.)
        is_gui = any(cmd_clean.startswith(app) for app in [
            "kate", "gedit", "xdg-open", "firefox", "chromium", "google-chrome",
            "brave", "code", "nautilus", "dolphin", "thunar", "nohup"
        ]) or (cmd_clean.endswith("&") and not cmd_clean.startswith("hyprctl"))

        if is_gui:
            subprocess.Popen(
                comando,
                shell=True,
                cwd=str(cwd_path),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return f"Aplicativo/comando '{comando}' iniciado com sucesso no sistema!"

        # Se for diagnóstico SAFE, executa estritamente com shell=False se argv estiver disponível
        if politica == PoliticaComando.SAFE and argv:
            use_shell = False
            exec_args = argv
        elif argv and not any(op in cmd_clean for op in OPERADORES_PERIGOSOS_SHELL + OPERADORES_ENCADEAMENTO):
            use_shell = False
            exec_args = argv
        else:
            use_shell = True
            exec_args = comando

        resultado = subprocess.run(
            exec_args,
            shell=use_shell,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(getattr(config, "COMMAND_TIMEOUT", 60))
        )
        
        saida = ""
        if resultado.stdout:
            saida += resultado.stdout
        if resultado.stderr:
            if saida:
                saida += "\n--- STDERR ---\n"
            saida += resultado.stderr

        if not saida.strip():
            saida = "(Comando executado com sucesso e sem saída no terminal)"

        if resultado.returncode != 0:
            saida = f"[Código de Saída: {resultado.returncode}]\n{saida}"

        if len(saida) > 8000:
            saida = saida[:4000] + "\n\n[... Saída truncada devido ao tamanho ...]\n\n" + saida[-4000:]

        return saida

    except subprocess.TimeoutExpired:
        return "Erro: O comando excedeu o tempo limite e foi interrompido."
    except Exception as e:
        return f"Erro ao executar comando: {e}"

# Mapa de chamadas para python
AVAILABLE_TOOLS_CALLABLE = {
    "listar_diretorio": listar_diretorio,
    "ler_arquivo": ler_arquivo,
    "escrever_arquivo": escrever_arquivo,
    "editar_arquivo": editar_arquivo,
    "executar_comando": executar_comando,
    "gerar_pdf": gerar_pdf
}

# Definição das ferramentas no formato esperado pelo Gemini
GEMINI_TOOLS_DECLARATION = [{
    "functionDeclarations": [
        {
            "name": "listar_diretorio",
            "description": "Lista os arquivos e subdiretórios de um caminho específico no sistema.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "caminho": {
                        "type": "STRING",
                        "description": "Caminho absoluto ou relativo para o diretório. Ex: /home/usuario/projetos"
                    }
                },
                "required": ["caminho"]
            }
        },
        {
            "name": "ler_arquivo",
            "description": "Lê o conteúdo de um arquivo de texto local.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "caminho": {
                        "type": "STRING",
                        "description": "Caminho do arquivo a ser lido."
                    }
                },
                "required": ["caminho"]
            }
        },
        {
            "name": "escrever_arquivo",
            "description": "Cria um novo arquivo ou sobrescreve um existente com o conteúdo fornecido. Use isso para salvar scripts, códigos ou textos.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "caminho": {
                        "type": "STRING",
                        "description": "Caminho do arquivo onde o conteúdo será salvo."
                    },
                    "conteudo": {
                        "type": "STRING",
                        "description": "O conteúdo que deve ser escrito no arquivo."
                    }
                },
                "required": ["caminho", "conteudo"]
            }
        },
        {
            "name": "editar_arquivo",
            "description": "Substitui um trecho específico de texto em um arquivo existente por um novo trecho (edição cirúrgica). IMPORTANTE: o trecho_antigo DEVE corresponder EXATAMENTE ao texto atual do arquivo, incluindo espaços e indentação. Se não tiver certeza do conteúdo exato, chame ler_arquivo primeiro.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "caminho": {
                        "type": "STRING",
                        "description": "Caminho do arquivo a ser editado."
                    },
                    "trecho_antigo": {
                        "type": "STRING",
                        "description": "O trecho exato de código ou texto atual que deve ser substituído."
                    },
                    "trecho_novo": {
                        "type": "STRING",
                        "description": "O novo trecho de código ou texto que entrará no lugar."
                    }
                },
                "required": ["caminho", "trecho_antigo", "trecho_novo"]
            }
        },
        {
            "name": "executar_comando",
            "description": "Executa um comando no terminal Linux com segurança, capturando a saída (stdout/stderr). Use SEMPRE para consultar status do sistema (free, df, ps, uptime), rede e internet (obter IP público via 'curl -s https://ifconfig.me', DNS via 'cat /etc/resolv.conf' ou 'resolvectl status', interfaces via 'ip a', portas via 'ss -tuln'), gerenciar o desktop (hyprctl), áudio (wpctl), logs (journalctl) ou rodar testes.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "comando": {
                        "type": "STRING",
                        "description": "O comando de linha de comando a ser executado."
                    },
                    "diretorio": {
                        "type": "STRING",
                        "description": "O diretório onde o comando deve ser executado (padrão: diretório atual '.')."
                    }
                },
                "required": ["comando"]
            }
        },
        {
            "name": "gerar_pdf",
            "description": "Gera um documento PDF com o texto especificado e salva no caminho destino.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "caminho_destino": {
                        "type": "STRING",
                        "description": "Caminho onde o arquivo .pdf será salvo."
                    },
                    "texto": {
                        "type": "STRING",
                        "description": "Conteúdo textual a ser inserido no PDF."
                    }
                },
                "required": ["caminho_destino", "texto"]
            }
        }
    ]
}]

OPENAI_TOOLS_DECLARATION = [
    {
        "type": "function",
        "function": {
            "name": "listar_diretorio",
            "description": "Lista os arquivos e subdiretórios de um caminho específico no sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Caminho absoluto ou relativo para o diretório. Ex: /home/usuario/projetos"
                    }
                },
                "required": ["caminho"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ler_arquivo",
            "description": "Lê o conteúdo de um arquivo de texto local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Caminho do arquivo a ser lido."
                    }
                },
                "required": ["caminho"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escrever_arquivo",
            "description": "Cria um novo arquivo ou sobrescreve um existente com o conteúdo fornecido. Use isso para salvar scripts, códigos ou textos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Caminho do arquivo onde o conteúdo será salvo."
                    },
                    "conteudo": {
                        "type": "string",
                        "description": "O conteúdo que deve ser escrito no arquivo."
                    }
                },
                "required": ["caminho", "conteudo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "editar_arquivo",
            "description": "Substitui um trecho específico de texto em um arquivo existente por um novo trecho (edição cirúrgica). IMPORTANTE: o trecho_antigo DEVE corresponder EXATAMENTE ao texto atual do arquivo, incluindo espaços e indentação. Se não tiver certeza do conteúdo exato, chame ler_arquivo primeiro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Caminho do arquivo a ser editado."
                    },
                    "trecho_antigo": {
                        "type": "string",
                        "description": "O trecho exato de código ou texto atual que deve ser substituído."
                    },
                    "trecho_novo": {
                        "type": "string",
                        "description": "O novo trecho de código ou texto que entrará no lugar."
                    }
                },
                "required": ["caminho", "trecho_antigo", "trecho_novo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executar_comando",
            "description": "Executa um comando no terminal Linux com segurança, capturando a saída (stdout/stderr). Use SEMPRE para consultar status do sistema (free, df, ps, uptime), rede e internet (obter IP público via 'curl -s https://ifconfig.me', DNS via 'cat /etc/resolv.conf' ou 'resolvectl status', interfaces via 'ip a', portas via 'ss -tuln'), gerenciar o desktop (hyprctl), áudio (wpctl), logs (journalctl) ou rodar testes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {
                        "type": "string",
                        "description": "O comando de linha de comando a ser executado."
                    },
                    "diretorio": {
                        "type": "string",
                        "description": "O diretório onde o comando deve ser executado (padrão: diretório atual '.')."
                    }
                },
                "required": ["comando"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_pdf",
            "description": "Gera um documento PDF com o texto especificado e salva no caminho destino.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho_destino": {
                        "type": "string",
                        "description": "Caminho onde o arquivo .pdf será salvo."
                    },
                    "texto": {
                        "type": "string",
                        "description": "Conteúdo textual a ser inserido no PDF."
                    }
                },
                "required": ["caminho_destino", "texto"]
            }
        }
    }
]

# Segurança: remove executar_comando do catálogo quando desabilitado
if not config.ENABLE_COMMAND_TOOL:
    AVAILABLE_TOOLS_CALLABLE.pop("executar_comando", None)

    OPENAI_TOOLS_DECLARATION[:] = [
        tool for tool in OPENAI_TOOLS_DECLARATION
        if tool.get("function", {}).get("name") != "executar_comando"
    ]

    if GEMINI_TOOLS_DECLARATION and isinstance(GEMINI_TOOLS_DECLARATION, list):
        GEMINI_TOOLS_DECLARATION[0]["functionDeclarations"] = [
            func for func in GEMINI_TOOLS_DECLARATION[0].get("functionDeclarations", [])
            if func.get("name") != "executar_comando"
        ]
