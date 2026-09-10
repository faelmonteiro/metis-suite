from agente.colors import (
    RESET,
    BOLD,
    RED,
    GREEN,
    YELLOW,
    CYAN,
    GRAY,
)

from agente import config
from agente.services import ollama_service, searxng_service
from agente.history import HistoryManager


def exibir_status(hm: HistoryManager = None):
    print(f"\n{BOLD}{CYAN}📊 STATUS DO SISTEMA{RESET}")
    print(f"{GRAY}--------------------------------------------------{RESET}")

    # Ollama
    try:
        ollama_ok = ollama_service.verificar_status()
    except Exception:
        ollama_ok = False

    if ollama_ok:
        print(
            f" {GREEN}✅{RESET} {BOLD}Ollama:{RESET}  {GREEN}Online{RESET} "
            f"{GRAY}(Modelo: {config.OLLAMA_MODEL}){RESET}"
        )
    else:
        print(f" {RED}❌{RESET} {BOLD}Ollama:{RESET}  {RED}Offline{RESET}")

    # Busca Web
    try:
        web_ok = searxng_service.verificar_status()
        prov_nome = searxng_service.obter_nome_provedor()
    except Exception:
        web_ok = False
        prov_nome = "Indisponível"

    if web_ok:
        print(
            f" {GREEN}✅{RESET} {BOLD}Busca Web:{RESET} {GREEN}Online{RESET} "
            f"{GRAY}(Motor: {prov_nome}){RESET}"
        )
    else:
        print(f" {RED}❌{RESET} {BOLD}Busca Web:{RESET} {RED}Offline{RESET}")

    # Gemini
    if config.GEMINI_API_KEY:
        print(f" {GREEN}✅{RESET} {BOLD}Gemini:{RESET}  {GREEN}Configurado{RESET}")
    else:
        print(f" {GRAY}⚪{RESET} {BOLD}Gemini:{RESET}  {YELLOW}Não configurado{RESET}")

    # Groq
    if config.GROQ_API_KEY:
        print(f" {GREEN}✅{RESET} {BOLD}Groq:{RESET}    {GREEN}Configurado{RESET}")
    else:
        print(f" {GRAY}⚪{RESET} {BOLD}Groq:{RESET}    {YELLOW}Não configurado{RESET}")

    # NVIDIA
    if config.NVIDIA_API_KEY:
        print(f" {GREEN}✅{RESET} {BOLD}NVIDIA:{RESET}  {GREEN}Configurado{RESET}")
    else:
        print(f" {GRAY}⚪{RESET} {BOLD}NVIDIA:{RESET}  {YELLOW}Não configurado{RESET}")

    # Histórico
    try:
        if hm is None:
            hm = HistoryManager()
        turnos = hm.contagem_conversas()
        sessao = hm.sessao
    except Exception:
        turnos = 0
        sessao = "default"

    print(f" {CYAN}💾{RESET} {BOLD}Histórico:{RESET} {CYAN}{turnos} turno(s) — sessão: {sessao}{RESET}")

    print(f"{GRAY}--------------------------------------------------{RESET}\n")
