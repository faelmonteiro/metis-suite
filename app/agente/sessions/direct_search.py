from agente.colors import *
from agente.services import searxng_service
from agente.utils import COMANDOS_SAIDA

def iniciar():
    prov = searxng_service.obter_nome_provedor()
    print(f"\n{BOLD}Busca Web Direta ({prov})... Digite 0 ou /menu para voltar.{RESET}")

    while True:
        try:
            pergunta = input(f"\n{BOLD}Buscar:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not pergunta:
            continue

        if pergunta.lower() in COMANDOS_SAIDA:
            break

        print(f"{YELLOW}Buscando...{RESET}")
        try:
            conteudo = searxng_service.buscar_web(pergunta)
            if conteudo:
                print(f"{GREEN}Resultados:{RESET}\n")
                print(conteudo)
            else:
                print(f"{RED}Nenhum resultado encontrado ou falha na busca.{RESET}")
        except KeyboardInterrupt:
            print(f"\n{YELLOW}[Busca interrompida pelo usuário]{RESET}")
            continue
