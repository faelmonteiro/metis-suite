"""
Submódulo de gerenciamento de histórico de conversas para o menu principal.
"""
from agente.colors import BOLD, RESET, YELLOW, GREEN, RED, CYAN
from agente.history import HistoryManager
from agente.sessions import chat_session
from agente.services.ollama_service import OllamaService
from agente.utils import limitar_texto


def gerenciar_historico(hm: HistoryManager):
    """Submenu interativo para visualização, exclusão e viagem no tempo do histórico."""
    while True:
        print(f"\n{BOLD}--- Gerenciar Histórico ---{RESET}")
        print("1. Continuar conversa atual")
        print("2. Listar turnos")
        print("3. Escolher um turno para continuar (truncar posteriores)")
        print("4. Excluir um turno específico")
        print("5. Excluir os últimos N turnos")
        print("6. Limpar todo o histórico")
        print("7. Voltar")

        try:
            op = input("Escolha uma opção: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if op == "1":
            chat_session.iniciar(hm, OllamaService(), forcar_web=False)
            break

        if op == "7":
            break

        if op == "2":
            turnos = hm.listar_turnos()
            if not turnos:
                print("Histórico vazio.")
            else:
                for i, t in enumerate(turnos, 1):
                    user_resumo = limitar_texto(t.get("user", ""), 50).replace("\n", " ")
                    assist_resumo = limitar_texto(t.get("assistant", ""), 50).replace("\n", " ")
                    print(f"[{i}] User: {user_resumo} | IA: {assist_resumo}")

                print()
                escolha_turno = input("Digite o número do turno para ler completo (ou Enter para voltar): ").strip()
                if escolha_turno.isdigit():
                    idx = int(escolha_turno) - 1
                    if 0 <= idx < len(turnos):
                        t = turnos[idx]
                        print(f"\n{BOLD}{CYAN}--- Turno [{escolha_turno}] ---{RESET}")
                        print(f"{BOLD}🧑 Você:{RESET}\n{t.get('user', '')}\n")
                        print(f"{BOLD}🤖 Assistente:{RESET}\n{t.get('assistant', '')}\n")
                        print(f"{CYAN}-------------------{RESET}\n")

                        acao = input(f"{YELLOW}Aperte 'C' para continuar a conversa a partir daqui (apagando o futuro) ou Enter para voltar:{RESET} ").strip().lower()
                        if acao == "c":
                            if hm.truncar_ate(idx):
                                print(f"{GREEN}Pronto! Voltamos no tempo para o turno {escolha_turno}.{RESET}")
                                chat_session.iniciar(hm, OllamaService(), forcar_web=False)
                                break
                    else:
                        print(f"{RED}Número inválido.{RESET}")

        elif op == "3":
            idx = input("Digite o número do turno para manter (exclui posteriores): ").strip()
            if idx.isdigit():
                idx_real = int(idx) - 1
                if hm.truncar_ate(idx_real):
                    print(f"{GREEN}Histórico truncado.{RESET}")
                else:
                    print(f"{RED}Índice inválido.{RESET}")
            else:
                print(f"{RED}Índice inválido.{RESET}")

        elif op == "4":
            idx = input("Digite o número do turno a remover: ").strip()
            if idx.isdigit():
                idx_real = int(idx) - 1
                if hm.remover_turno(idx_real):
                    print(f"{GREEN}Turno removido.{RESET}")
                else:
                    print(f"{RED}Índice inválido.{RESET}")
            else:
                print(f"{RED}Índice inválido.{RESET}")

        elif op == "5":
            qtd = input("Quantos turnos deseja excluir do final? ").strip()
            if qtd.isdigit() and hm.deletar_ultimos(int(qtd)):
                print(f"{GREEN}Turnos removidos.{RESET}")
            else:
                print(f"{RED}Quantidade inválida.{RESET}")

        elif op == "6":
            if input("Confirmar limpeza total (Deletar arquivo fisicamente)? (s/n): ").strip().lower() == "s":
                hm.deletar_sessao()
                print(f"{GREEN}Histórico deletado do PC.{RESET}")
                break

        else:
            print(f"{RED}Opção inválida.{RESET}")
