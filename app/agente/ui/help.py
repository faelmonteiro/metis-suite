from agente.colors import (
    RESET,
    BOLD,
    GREEN,
    YELLOW,
    MAGENTA,
    CYAN,
    GRAY,
)


def exibir_ajuda():
    print(f"\n{BOLD}{CYAN}📖 AJUDA DO SISTEMA METIS{RESET}")
    print(
        f"{GRAY}O sistema permite conversar com diferentes modelos de IA "
        f"e realizar buscas na web tanto via CLI quanto via interface GUI flutuante.{RESET}"
    )
    print(f"{GRAY}--------------------------------------------------{RESET}")

    print(f"\n{BOLD}{MAGENTA}📌 ATALHOS GLOBAIS & GUI{RESET}")
    print(f" 🪟 {BOLD}Super + R{RESET}       : Inicia a interface gráfica moderna do Metis (GUI flutuante)")
    print(f" ⌨️  {BOLD}↑ / ↓ / ← / →{RESET}   : Navegação fluida entre opções, menus e modelos")
    print(f" ↵  {BOLD}Enter{RESET}           : Executa a opção ou envia a mensagem")
    print(f" ↵  {BOLD}Shift + Enter{RESET}   : Insere quebra de linha no prompt sem enviar")
    print(f" ⏹️  {BOLD}Ctrl + C{RESET}        : Interrompe a resposta da IA em andamento")
    print(f" ↩️  {BOLD}ESC{RESET}             : Interrompe geração, volta à tela anterior ou fecha")

    print(f"\n{BOLD}{MAGENTA}📌 MENU PRINCIPAL (CLI & DASHBOARD){RESET}")
    print(f" {GREEN}01{RESET} ➔ Consultar Metis (Chat com pesquisa web integrada)")
    print(f" {GREEN}02{RESET} ➔ Visão do Mundo / Oráculos (Chat inteligente e provedores de IA)")
    print(f" {GREEN}03{RESET} ➔ Outros Oráculos / Busca Web (APIs: Gemini, Groq, NVIDIA, g4f, Custom)")
    print(f" {GREEN}04{RESET} ➔ 📐 Buscar Conhecimento (Pesquisa direta de termos e páginas web)")
    print(f" {GREEN}05{RESET} ➔ Escolher Oráculo / Purificar Memória")
    print(f" {GREEN}06{RESET} ➔ Purificar Memória / Encerrar Sistema")
    print(f" {GREEN}07{RESET} ➔ Tábula de Métis (Gerenciar, truncar e editar turnos)")
    print(f" {GREEN}08{RESET} ➔ Encerrar Sistema (ou 0 / sair)")

    print(f"\n{BOLD}{YELLOW}💬 COMANDOS DENTRO DO CHAT / PROMPT{RESET}")
    print(f" 🌐 {BOLD}/web <pergunta>{RESET} : Força a busca web em tempo real para a pergunta")
    print(f" 🔄 {BOLD}/modelo [nome]{RESET}  : Mostra ou troca o modelo/provedor (ollama, gemini, groq, nvidia, g4f, custom)")
    print(f" 🔑 {BOLD}/apis{RESET}           : Configura chaves de API e URLs de serviços (/api, /chaves)")
    print(f" 🔁 {BOLD}/retry{RESET}         : Regenera a última resposta (/repetir)")
    print(f" 📂 {BOLD}/arquivo <path>{RESET}: Carrega e analisa arquivo, documento ou imagem")
    print(f" 📋 {BOLD}/exportar{RESET}      : Exporta a conversa atual para Markdown (.md)")
    print(f" 💬 {BOLD}/sessao [nome]{RESET} : Lista sessões salvas ou troca/cria por nome")
    print(f" ✨ {BOLD}/novo [nome]{RESET}   : Inicia imediatamente um novo assunto/conversa (/new, /nova)")
    print(f" 🎨 {BOLD}/tema{RESET}          : Abre o painel de Aparência, Temas visuais e Estilos (/temas, /aparencia)")
    print(f" 🗑️  {BOLD}/limpar{RESET}        : Limpa a conversa atual da tela e da memória (/clear)")
    print(f" 🗑️  {BOLD}/deletar_sessao{RESET}: Deleta a sessão atual do disco")
    print(f" ⚠️  {BOLD}/deletar_tudo{RESET}  : Deleta TODAS as conversas salvas do disco")
    print(f" 🤖 {BOLD}/automode{RESET}      : Liga/desliga modo automático de escrita")
    print(f" 📊 {BOLD}/status{RESET}        : Mostra o status e telemetria dos serviços")
    print(f" ❓ {BOLD}/ajuda{RESET}         : Mostra esta ajuda (ou /help)")
    print(f" ↩️  {BOLD}0, /menu, sair{RESET} : Retorna ao menu anterior")

    print(f"\n{BOLD}{CYAN}⚙️  PRINCIPAIS VARIÁVEIS NO .env{RESET}")
    print(f" {GRAY}•{RESET} OLLAMA_HOST, OLLAMA_MODEL")
    print(f" {GRAY}•{RESET} SEARXNG_URL")
    print(f" {GRAY}•{RESET} GEMINI_API_KEY, GEMINI_MODEL")
    print(f" {GRAY}•{RESET} GROQ_API_KEY, GROQ_MODEL")
    print(f" {GRAY}•{RESET} NVIDIA_API_KEY, NVIDIA_MODEL, NVIDIA_MAX_TOKENS")
    print(f" {GRAY}•{RESET} G4F_MODEL")
    print(f" {GRAY}•{RESET} MAX_SEARCH_RESULTS, SEARCH_TIMEOUT, API_TIMEOUT")
    print(f" {GRAY}•{RESET} MAX_HISTORY_MESSAGES, MAX_WEB_CONTENT_CHARS")

    print(f"{GRAY}--------------------------------------------------{RESET}\n")
