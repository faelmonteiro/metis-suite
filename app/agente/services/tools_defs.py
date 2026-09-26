import logging
logger = logging.getLogger(__name__)
import os
import re
import json
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from agente import config
from agente.colors import RED, GREEN, YELLOW, CYAN, BOLD, RESET
from agente.utils import caminho_leitura_seguro

# ---------------------------------------------------------------------------
# Modo auto-approve por contexto (thread-local) em vez de flag global.
#
# Antes, "AUTO_APPROVE_MODE" era uma flag global no módulo: o AIWorker ligava
# em run() e desligava em finally(). Com dois QThreads concorrentes, um worker
# desligava a permissão do outro no meio da execução, fazendo ferramentas de
# escrita/edição serem NEGADAS mesmo no GUI (que não tem stdin interativo).
#
# Agora cada thread tem seu próprio valor. A flag global continua funcionando
# como fallback para o comando "/automode" (CLI) e para os testes.
# ---------------------------------------------------------------------------
_auto_approve_context = threading.local()


def definir_auto_approve(valor: bool) -> None:
    """Define o auto-approve apenas no contexto da thread atual."""
    _auto_approve_context.ativo = bool(valor)


@contextmanager
def auto_approve_temporario(valor: bool):
    """Habilita o auto-approve no contexto, e restaura o estado anterior.

    O `finally` tem que RESTAURAR, e nao forcar `False`. Um atributo definido
    na thread tem prioridade sobre o fallback global `AUTO_APPROVE_MODE`, e
    essa prioridade nao volta: quem forca `False` no fim deixa o `/automode` do
    CLI morto para sempre naquela thread, sem nenhum sintoma alem de ferramentas
    de escrita sendo negadas em silencio.
    """
    tinha_valor = hasattr(_auto_approve_context, "ativo")
    valor_anterior = getattr(_auto_approve_context, "ativo", None)
    definir_auto_approve(valor)
    try:
        yield
    finally:
        if tinha_valor:
            _auto_approve_context.ativo = valor_anterior
        else:
            del _auto_approve_context.ativo


def auto_approve_habilitado() -> bool:
    """True se o auto-approve estiver ativo no contexto atual.

    Prioriza o valor da thread; se nenhuma thread definiu, respeita a flag
    global AUTO_APPROVE_MODE (ex.: /automode no CLI e testes).
    """
    valor = getattr(_auto_approve_context, "ativo", None)
    if valor is not None:
        return valor
    mod = sys.modules[__name__]
    return bool(vars(mod).get("AUTO_APPROVE_MODE", False))


def __getattr__(name: str):
    if name == "AUTO_APPROVE_MODE":
        return auto_approve_habilitado()
    raise AttributeError(f"módulo {__name__!r} não possui o atributo {name!r}")

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
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    try:
        for item in Path.cwd().iterdir():
            if unaccent(item.name) == c_un:
                return str(item)
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

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

    auto = auto_approve_habilitado()
    
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

    auto = auto_approve_habilitado()

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

    auto = auto_approve_habilitado()
    
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
                except Exception as _silent_e:
                    logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

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
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+[/~*]",
    r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r?\s+[/~*]",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bparted\b",
    r"\bdd\s+if=",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\binit\s+[06]\b",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r">\s*/dev/(sd|nvme|hd)",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bchown\s+-R\s+.*?\s+/",
    # Vetores de execução indireta / injeção (bloqueados para QUALQUER comando)
    r"\$\(|`",
    r"\b(eval|source)\b",
    r"\b(?:sh|bash|zsh|python|python3|perl|ruby|php)\s+-[ce]\s+",
    r"\bbase64\s+-d",
    r"\b(curl|wget)\s+[^\|;&`]*\|\s*(?:sh|bash|sudo)\b",
    r"\b(?:printf|echo|cat)\s+[^\|;&`]*\|\s*(?:sh|bash)\b",
]

COMANDOS_DIAGNOSTICO = (
    "free", "df", "uptime", "uname", "top -b", "ps", "ip ", "ip a", "ping -c",
    "hyprctl", "wpctl", "brightnessctl", "nmcli", "bluetoothctl", "systemctl status", "systemctl is-active",
    "journalctl", "cat ", "head ", "tail ", "ls ", "ls -", "find ", "grep ", "which ", "whereis ", "whoami",
    "lscpu", "lsblk", "lspci", "lsusb", "sensors", "fastfetch", "neofetch", "arch", "hostname", "w", "who", "id"
)

# Operadores de shell que desqualificam um comando de diagnóstico para o AUTO-APPROVE.
# O comando ainda pode ser executado se o usuário confirmar manualmente.
_OPERADORES_SHELL = re.compile(r"[;&|<>`]|\$\(")

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

def executar_comando(comando: str, diretorio: str = ".") -> str:
    if not config.ENABLE_COMMAND_TOOL:
        return "Erro: a ferramenta executar_comando está desabilitada. Defina ENABLE_COMMAND_TOOL=1 no .env somente se você realmente precisar executar comandos."

    comando = normalizar_comando(comando)

    seguro, motivo = validar_comando_seguro(comando)
    if not seguro:
        print(f"\n{RED}🚫 [Segurança] {motivo}{RESET}")
        return f"Erro de Segurança: {motivo}"

    try:
        cwd_path = caminho_leitura_seguro(diretorio, permitir_diretorio=True)
    except Exception as e:
        return f"Erro: Diretório de execução inválido ou inacessível: {e}"

    if not cwd_path.exists() or not cwd_path.is_dir():
        return f"Erro: Diretório de execução {diretorio} não existe."

    auto = auto_approve_habilitado()

    cmd_clean = comando.strip()
    cmd_lower = cmd_clean.lower()

    # Avaliação para comandos encapsulados ou com caminho absoluto
    cmd_eval = cmd_lower
    for prefix in ("sh -c ", "bash -c ", "/bin/sh -c ", "/bin/bash -c "):
        if cmd_eval.startswith(prefix):
            cmd_eval = cmd_eval[len(prefix):].strip().strip("'\"")
            break

    for bin_path in ("/usr/bin/", "/bin/", "/usr/local/bin/"):
        if cmd_eval.startswith(bin_path):
            cmd_eval = cmd_eval[len(bin_path):]
            break

    eh_diagnostico = (
        any(cmd_eval.startswith(d) or cmd_lower.startswith(d) for d in COMANDOS_DIAGNOSTICO)
        and not _OPERADORES_SHELL.search(cmd_lower)
    )

    if auto or eh_diagnostico:
        if auto:
            print(f"\n{YELLOW}⚡ [Metis Auto-Approve] Executando comando: {BOLD}{comando}{RESET}")
        else:
            print(f"\n{CYAN}🔍 [Diagnóstico do Sistema] Executando: {BOLD}{comando}{RESET}")
    else:
        print(f"\n{YELLOW}⚠️ A IA quer executar um comando no terminal:{RESET}")
        print(f"   {CYAN}${RESET} {BOLD}{comando}{RESET}")
        print(f"   {YELLOW}Diretório:{RESET} {cwd_path}")
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

        resultado = subprocess.run(
            comando,
            shell=True,
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
        timeout_s = int(getattr(config, "COMMAND_TIMEOUT", 60))
        return f"Erro: O comando excedeu o tempo limite de {timeout_s} segundos e foi interrompido."
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
            "description": "Executa um comando no terminal Linux com segurança, capturando a saída (stdout/stderr). Use para consultar status do sistema (free, df, ps, uptime), gerenciar o desktop Hyprland (hyprctl), áudio (wpctl/pamixer), processos (kill), verificar logs (journalctl), rodar testes (pytest) ou iniciar programas e scripts.",
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
            "description": "Executa um comando no terminal Linux com segurança, capturando a saída (stdout/stderr). Use para consultar status do sistema (free, df, ps, uptime), gerenciar o desktop Hyprland (hyprctl), áudio (wpctl/pamixer), processos (kill), verificar logs (journalctl), rodar testes (pytest) ou iniciar programas e scripts.",
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
