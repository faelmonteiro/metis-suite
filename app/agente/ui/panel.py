import base64
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from agente import config
from agente.colors import (
    RESET,
    BOLD,
    DIM,
    ITALIC,
    UNDERLINE,
    RED,
    GREEN,
    YELLOW,
    BLUE,
    MAGENTA,
    CYAN,
    WHITE,
    GRAY,
    METIS_GOLD,
    METIS_GOLD_BRIGHT,
    METIS_GOLD_MUTED,
    METIS_AMBER,
    METIS_CYAN,
    METIS_CYAN_SOFT,
    METIS_BLUE,
    METIS_GREEN,
    METIS_RED,
    METIS_WHITE,
    METIS_GRAY,
    METIS_GRAY_LIGHT,
    METIS_GRAY_DARK,
    METIS_BORDER,
    METIS_BORDER_BRIGHT,
    METIS_BG_CARD,
)
from agente.services import searxng_service

_INICIO_APP = datetime.now().strftime("%d/%m/%Y %H:%M")

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b_G[^\x1b]*\x1b\\')


def _strip_ansi(text: str) -> str:
    return ANSI_REGEX.sub('', text)


def _char_width(char: str) -> int:
    if char in ('\ufe0f', '\ufe0e'):
        return 0
    cp = ord(char)
    if cp in (0x25CF, 0x25CB):  # ●, ○
        return 1
    if cp in (0x21C4, 0x2194, 0x23FB):  # ⇄, ↔, ⏻
        return 1
    if cp in (0x203A, 0x25B8, 0x25B6, 0x27A4, 0x279C):  # ›, ▸, ▶, ➤, ➜
        return 1
    w = unicodedata.east_asian_width(char)
    if w in ('F', 'W'):
        return 2
    if (0x1F000 <= cp <= 0x1F9FF) or (0x2600 <= cp <= 0x27BF):
        return 2
    return 1


def _str_display_width(text: str) -> int:
    clean = _strip_ansi(text)
    total = 0
    i = 0
    while i < len(clean):
        c = clean[i]
        if unicodedata.combining(c):
            i += 1
            continue
        if i + 1 < len(clean) and clean[i+1] in ('\ufe0f', '\ufe0e'):
            total += 2
            i += 2
            continue
        total += _char_width(c)
        i += 1
    return total


def _pad(text: str, width: int, align: str = "left", pad_char: str = " ") -> str:
    w = _str_display_width(text)
    diff = max(0, width - w)
    if align == "left":
        return text + (pad_char * diff)
    elif align == "right":
        return (pad_char * diff) + text
    else:
        left = diff // 2
        right = diff - left
        return (pad_char * left) + text + (pad_char * right)


def _obter_icone_kitty() -> str:
    """Retorna o ícone inline para Kitty Graphics Protocol ou vazio para fallback."""
    is_kitty = bool(os.getenv("KITTY_PID") or os.getenv("KITTY_WINDOW_ID") or ("kitty" in os.getenv("TERM", "").lower()))
    if is_kitty and sys.stdout.isatty():
        icon_path = config.PROJECT_ROOT / "assets" / "icons" / "glyph_48x48.png"
        if not icon_path.exists():
            icon_path = config.PROJECT_ROOT / "assets" / "icons" / "metis_emoji_32x32.png"
        if icon_path.exists():
            try:
                with open(icon_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                return f"\x1b_Ga=T,f=100,c=2,r=1;{b64}\x1b\\"
            except Exception:
                pass
    return ""


def _contar_registros_memoria(hm=None) -> int:
    if hm and hasattr(hm, "historico") and hm.historico:
        return len(hm.historico)
    total = 0
    try:
        hist_dir = Path(config.HISTORICO_DIR)
        if hist_dir.exists():
            for f in hist_dir.glob("*.json"):
                if f.name.startswith("."):
                    continue
                try:
                    with open(f, "r", encoding="utf-8") as jf:
                        dados = json.load(jf)
                        if isinstance(dados, list):
                            total += len(dados)
                        elif isinstance(dados, dict):
                            total += len(dados.get("historico", []))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def exibir_painel(history_manager=None):
    W_LEFT = 59
    W_RIGHT = 38
    TOTAL_W = W_LEFT + W_RIGHT + 3

    # Provedor e Modelo Ativos
    def_prov = getattr(config, "DEFAULT_PROVIDER", "ollama").strip().lower()
    if def_prov == "gemini" and config.GEMINI_API_KEY:
        provedor = "Gemini (Google)"
        modelo = getattr(config, "GEMINI_MODEL", "gemini-1.5-flash")
    elif def_prov == "groq" and config.GROQ_API_KEY:
        provedor = "Groq Cloud"
        modelo = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")
    elif def_prov == "nvidia" and config.NVIDIA_API_KEY:
        provedor = "NVIDIA NIM"
        modelo = getattr(config, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    elif def_prov == "g4f":
        provedor = "G4F (Web Direta)"
        modelo = getattr(config, "G4F_MODEL", "gpt-4o-mini")
    elif def_prov == "ollama":
        provedor = "Ollama (Local)"
        modelo = getattr(config, "OLLAMA_MODEL", "llama3.2:3b")
    else:
        # Fallback inteligente se DEFAULT_PROVIDER for genérico
        if config.GEMINI_API_KEY:
            provedor = "Gemini (Google)"
            modelo = getattr(config, "GEMINI_MODEL", "gemini-1.5-flash")
        elif config.GROQ_API_KEY:
            provedor = "Groq Cloud"
            modelo = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")
        elif config.NVIDIA_API_KEY:
            provedor = "NVIDIA NIM"
            modelo = getattr(config, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
        else:
            provedor = "Ollama (Local)"
            modelo = getattr(config, "OLLAMA_MODEL", "llama3.2:3b")

    if len(modelo) > 23:
        modelo = modelo[:20] + "..."

    # Web Status
    try:
        web_ok = searxng_service.verificar_status()
        prov_nome = searxng_service.obter_nome_provedor()
    except Exception:
        web_ok = False
        prov_nome = "Web"
    
    web_status_txt = f"{METIS_GREEN}Ativa ({prov_nome}){RESET}" if web_ok else f"{METIS_RED}Inativa{RESET}"

    # Sessão & Registros
    if history_manager and hasattr(history_manager, "sessao"):
        sessao_nome = history_manager.sessao
    else:
        sessao_nome = "Atual"
    if len(sessao_nome) > 14:
        sessao_nome = sessao_nome[:12] + ".."

    total_registros = _contar_registros_memoria(history_manager)

    lines = []
    lines.append(f"{METIS_BORDER}╭{'─' * (TOTAL_W + 2)}╮{RESET}")

    # Header Box à direita (Status)
    status_w = 34
    s_top = f"{METIS_BORDER_BRIGHT}╭─ {METIS_GREEN}● SISTEMA ONLINE{RESET}{METIS_BORDER_BRIGHT} {'─' * (status_w - 20)}╮{RESET}"
    s_mid = f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f' {METIS_GRAY}Todos os sistemas operacionais{RESET}', status_w - 2)}{METIS_BORDER_BRIGHT}│{RESET}"
    s_bot = f"{METIS_BORDER_BRIGHT}╰{'─' * (status_w - 2)}╯{RESET}"

    # Títulos à esquerda
    kitty_icon = _obter_icone_kitty()
    icon_prefix = f"{kitty_icon} " if kitty_icon else "🏛️  "
    
    h_1 = f" {icon_prefix}{METIS_GOLD_BRIGHT}{BOLD}M E T I S{RESET}"
    h_2 = f"   {METIS_GRAY}{BOLD}AGENTE DE INTELIGÊNCIA{RESET} {METIS_GRAY_DARK}• ORÁCULO & ESTRATÉGIA{RESET}"
    h_3 = f"   {METIS_GRAY_DARK}Assistente neural integrado com oráculos e busca web{RESET}"

    rem_1 = TOTAL_W - _str_display_width(h_1) - _str_display_width(s_top)
    lines.append(f"{METIS_BORDER}│{RESET} {h_1}{' ' * max(0, rem_1)}{s_top} {METIS_BORDER}│{RESET}")

    rem_2 = TOTAL_W - _str_display_width(h_2) - _str_display_width(s_mid)
    lines.append(f"{METIS_BORDER}│{RESET} {h_2}{' ' * max(0, rem_2)}{s_mid} {METIS_BORDER}│{RESET}")

    rem_3 = TOTAL_W - _str_display_width(h_3) - _str_display_width(s_bot)
    lines.append(f"{METIS_BORDER}│{RESET} {h_3}{' ' * max(0, rem_3)}{s_bot} {METIS_BORDER}│{RESET}")

    lines.append(f"{METIS_BORDER}├{'─' * (TOTAL_W + 2)}┤{RESET}")

    # Coluna Esquerda: Itens do Menu
    left_rows = [
        f" {METIS_GOLD}{BOLD}> MENU PRINCIPAL{RESET}",
        f" {METIS_GOLD_BRIGHT}{BOLD}› 01{RESET}  🦉 {METIS_WHITE}{BOLD}CONSULTAR METIS{RESET}      {METIS_GRAY}IA avançada com pesquisa web{RESET}",
        f"   {METIS_CYAN_SOFT}{BOLD}02{RESET}  🌐 {METIS_WHITE}{BOLD}VISÃO DO MUNDO{RESET}       {METIS_GRAY}Pesquisa e informações da web{RESET}",
        f"   {METIS_CYAN_SOFT}{BOLD}03{RESET}  🔮 {METIS_WHITE}{BOLD}OUTROS ORÁCULOS{RESET}      {METIS_GRAY}Modelos externos (Gemini, Groq){RESET}",
        f"",
        f" {METIS_GOLD}{BOLD}> MEMÓRIA E HISTÓRICO{RESET}",
        f"   {METIS_CYAN_SOFT}{BOLD}04{RESET}  📐 {METIS_WHITE}{BOLD}BUSCAR CONHECIMENTO{RESET}  {METIS_GRAY}Pesquisa direta sem usar IA{RESET}",
        f"   {METIS_CYAN_SOFT}{BOLD}05{RESET}  ⇄  {METIS_WHITE}{BOLD}ESCOLHER ORÁCULO{RESET}     {METIS_GRAY}Trocar modelo local ou remoto{RESET}",
        f"   {METIS_CYAN_SOFT}{BOLD}06{RESET}  🔥 {METIS_WHITE}{BOLD}PURIFICAR MEMÓRIA{RESET}    {METIS_GRAY}Limpar todo o histórico e sessões{RESET}",
        f"   {METIS_CYAN_SOFT}{BOLD}07{RESET}  📜  {METIS_WHITE}{BOLD}TÁBULA DE MÉTIS{RESET}      {METIS_GRAY}Gerenciar e editar turnos salvos{RESET}",
        f"",
        f"   {METIS_RED}{BOLD}08{RESET}  🗝️  {METIS_RED}{BOLD}ENCERRAR SISTEMA{RESET}     {METIS_GRAY}Encerrar aplicação com segurança{RESET}",
        f"",
        f"",
    ]

    # Coluna Direita: Caixa de Informações
    inner_w = W_RIGHT - 2
    right_box = [
        f"{METIS_BORDER_BRIGHT}╭─ {METIS_GOLD}{BOLD}INFORMAÇÕES DO SISTEMA{RESET}{METIS_BORDER_BRIGHT} {'─' * max(0, inner_w - 24)}╮{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'  🦉 {METIS_GOLD}ORÁCULO ATUAL{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'     {METIS_CYAN}{modelo}{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}├{'─' * inner_w}┤{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'  🖧  {METIS_GOLD}PROVEDOR{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'     {METIS_CYAN}{provedor}{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}├{'─' * inner_w}┤{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'  📶 {METIS_GOLD}CONEXÃO COSMOS{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'     {web_status_txt}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}├{'─' * inner_w}┤{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'  ⏳ {METIS_GOLD}SESSÃO{RESET} / 📜 {METIS_GOLD}TÁBULA DE MÉTIS{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'     {METIS_CYAN}{sessao_nome}{RESET} {METIS_GRAY_DARK}•{RESET} {METIS_CYAN}{total_registros} registros{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}├{'─' * inner_w}┤{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'  ☀️ {METIS_GOLD}DESPERTO EM{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}│{RESET}{_pad(f'     {METIS_GRAY}{_INICIO_APP}{RESET}', inner_w)}{METIS_BORDER_BRIGHT}│{RESET}",
        f"{METIS_BORDER_BRIGHT}╰{'─' * inner_w}╯{RESET}",
    ]

    max_linhas = max(len(left_rows), len(right_box))
    for i in range(max_linhas):
        l_str = left_rows[i] if i < len(left_rows) else ""
        r_str = right_box[i] if i < len(right_box) else ""
        
        l_padded = _pad(l_str, W_LEFT)
        r_padded = _pad(r_str, W_RIGHT)
        
        lines.append(f"{METIS_BORDER}│{RESET} {l_padded} {r_padded} {METIS_BORDER}│{RESET}")

    lines.append(f"{METIS_BORDER}├{'─' * (TOTAL_W + 2)}┤{RESET}")

    # Comandos Rápidos e Sessões
    cmd_w_left = 52
    cmd_w_right = TOTAL_W - cmd_w_left - 3

    b_top_left = f" {METIS_GOLD}{BOLD}> COMANDOS RÁPIDOS{RESET}"
    b_top_right = f" {METIS_GOLD}{BOLD}> SESSÕES{RESET}"

    b_bot_left = f"   {METIS_CYAN_SOFT}/web <termo>{RESET}  {METIS_BORDER_BRIGHT}│{RESET}  {METIS_CYAN_SOFT}/status{RESET}  {METIS_BORDER_BRIGHT}│{RESET}  {METIS_CYAN_SOFT}/ajuda{RESET}"
    b_bot_right = f"   {METIS_CYAN_SOFT}/sessao{RESET}  {METIS_BORDER_BRIGHT}│{RESET}  {METIS_CYAN_SOFT}/exportar{RESET}"

    l1 = _pad(b_top_left, cmd_w_left)
    r1 = _pad(b_top_right, cmd_w_right)
    lines.append(f"{METIS_BORDER}│{RESET} {l1} {METIS_BORDER}│{RESET} {r1} {METIS_BORDER}│{RESET}")

    l2 = _pad(b_bot_left, cmd_w_left)
    r2 = _pad(b_bot_right, cmd_w_right)
    lines.append(f"{METIS_BORDER}│{RESET} {l2} {METIS_BORDER}│{RESET} {r2} {METIS_BORDER}│{RESET}")

    lines.append(f"{METIS_BORDER}╰{'─' * (TOTAL_W + 2)}╯{RESET}")
    print("\n" + "\n".join(lines))
