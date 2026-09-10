import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from agente import config
from agente.colors import *
from agente.history import HistoryManager
from agente.ui.panel import exibir_painel
from agente.ui.help import exibir_ajuda
from agente.ui.status import exibir_status
from agente.menu_config import limpar_tela, configurar_modelo_dinamico, trocar_modelo_ollama
from agente.menu_history import gerenciar_historico
from agente.services.ollama_service import OllamaService
from agente.sessions import chat_session, direct_search
from agente.utils import limitar_texto, configurar_api_key, safe_input, sanitizar_nome_sessao, hyprctl


def salvar_estado_chat(estado: dict):
    try:
        state_file = Path(config.HISTORICO_DIR) / ".last_chat_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(estado, f)
    except Exception:
        pass


def carregar_estado_chat() -> dict:
    try:
        state_file = Path(config.HISTORICO_DIR) / ".last_chat_state.json"
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def iniciar_menu():
    nome_sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    history_manager = HistoryManager(nome_sessao)

    estado = carregar_estado_chat()
    auto_start = estado if estado else None

    while True:
        hyprctl("dispatch centerwindow")
        
        limpar_tela()
        exibir_painel(history_manager)
        
        if auto_start:
            escolha = auto_start.get("escolha")
            sub_api = auto_start.get("sub_api")
            groq_model = auto_start.get("groq_model")
            nvidia_model = auto_start.get("nvidia_model")
            gemini_model = auto_start.get("gemini_model")
            g4f_model = auto_start.get("g4f_model")
            custom_server_id = auto_start.get("custom_server_id")
            auto_start = None  # Evita loop infinito se o usuario sair do chat
            
            if escolha in ["1", "01"]:
                chat_session.iniciar(history_manager, OllamaService(), forcar_web=True)
                continue
            elif escolha in ["2", "02"]:
                chat_session.iniciar(history_manager, OllamaService(), forcar_web=False)
                continue
            if escolha in ["3", "03"]:
                if custom_server_id:
                    from agente.providers_manager import obter_servidor_customizado
                    from agente.services.custom_openai_service import CustomOpenAIService
                    srv = obter_servidor_customizado(custom_server_id)
                    if srv:
                        chat_session.iniciar(history_manager, CustomOpenAIService(srv))
                        continue
                if sub_api == "3" and config.NVIDIA_API_KEY:
                    from agente.services.nvidia_service import NvidiaService
                    if nvidia_model:
                        config.NVIDIA_MODEL = nvidia_model
                    chat_session.iniciar(history_manager, NvidiaService())
                    continue
                elif sub_api == "2" and config.GROQ_API_KEY:
                    from agente.services.groq_service import GroqService
                    if groq_model:
                        config.GROQ_MODEL = groq_model
                    chat_session.iniciar(history_manager, GroqService())
                    continue
                elif sub_api == "1" and config.GEMINI_API_KEY:
                    from agente.services.gemini_service import GeminiService
                    if gemini_model:
                        config.GEMINI_MODEL = gemini_model
                    chat_session.iniciar(history_manager, GeminiService())
                    continue
                elif sub_api == "4":
                    try:
                        from agente.services.g4f_service import G4FService
                        chat_session.iniciar(history_manager, G4FService(model=g4f_model or "gpt-4o-mini"))
                    except ImportError:
                        print(f"{RED}[Erro] Módulo g4f não instalado. Rode: pip install g4f{RESET}")
                        input("\nPressione ENTER para voltar ao menu...")
                    continue
            elif escolha in ["4", "04"]:
                direct_search.iniciar()
                continue
            elif escolha in ["5", "05"]:
                trocar_modelo_ollama()
                continue

        try:
            escolha = safe_input(f"\n{METIS_GREEN}{BOLD}>_{RESET} {METIS_GOLD}{BOLD}METIS AGUARDA SUA CONSULTA:{RESET} ", multiline=False).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSaindo...")
            return

        if escolha in ["1", "01"]:
            salvar_estado_chat({"escolha": "1"})
            chat_session.iniciar(history_manager, OllamaService(), forcar_web=True)

        elif escolha in ["2", "02"]:
            salvar_estado_chat({"escolha": "2"})
            chat_session.iniciar(history_manager, OllamaService(), forcar_web=False)

        elif escolha in ["3", "03"]:
            from agente.providers_manager import obter_servidores_customizados, obter_servidor_customizado
            from agente.menu_config import adicionar_servidor_wizard, remover_servidor_wizard
            from agente.services.custom_openai_service import CustomOpenAIService

            servidores_custom = obter_servidores_customizados()

            gem_tag = f"{METIS_GREEN}[✓ Chave OK]{RESET}" if config.GEMINI_API_KEY else f"{METIS_GRAY}[○ Sem Chave]{RESET}"
            groq_tag = f"{METIS_GREEN}[✓ Chave OK]{RESET}" if config.GROQ_API_KEY else f"{METIS_GRAY}[○ Sem Chave]{RESET}"
            nv_tag = f"{METIS_GREEN}[✓ Chave OK]{RESET}" if config.NVIDIA_API_KEY else f"{METIS_GRAY}[○ Sem Chave]{RESET}"
            g4f_tag = f"{METIS_GREEN}[● Gratuito]{RESET}"

            print(f"\n{METIS_BORDER_BRIGHT}══════════════════════════════════════════════════{RESET}")
            print(f"{METIS_GOLD}{BOLD}✨ ESCOLHA DO ORÁCULO EXTERNO:{RESET}")
            print(f"{METIS_BORDER}──────────────────────────────────────────────────{RESET}")
            print(f"  {METIS_CYAN_SOFT}1.{RESET} Gemini (Google)                     {gem_tag}")
            print(f"  {METIS_CYAN_SOFT}2.{RESET} Groq (Llama, DeepSeek, Qwen)        {groq_tag}")
            print(f"  {METIS_CYAN_SOFT}3.{RESET} NVIDIA (Llama, Nemotron, Mistral)   {nv_tag}")
            print(f"  {METIS_CYAN_SOFT}4.{RESET} IA Web Direta (g4f)                 {g4f_tag}")

            offset = 5
            mapa_custom = {}
            if servidores_custom:
                print(f"\n{METIS_GOLD}  ─── Servidores Personalizados ─────────────────{RESET}")
                for idx, s in enumerate(servidores_custom, offset):
                    mapa_custom[str(idx)] = s
                    api_key_env = s.get("api_key_env", f"{s.get('id', 'custom').upper()}_API_KEY")
                    has_k = bool(os.getenv(api_key_env, "").strip() or s.get("api_key", "").strip())
                    srv_tag = f"{METIS_GREEN}[✓ Conectado]{RESET}" if has_k else f"{METIS_GRAY}[○ Sem Chave]{RESET}"
                    print(f"  {METIS_CYAN_SOFT}{idx}.{RESET} {s.get('nome')} ({s.get('modelo_atual')})  {srv_tag}")
                offset += len(servidores_custom)

            print(f"\n{METIS_GOLD}  ─── Gerenciamento & Chaves ────────────────────{RESET}")
            opt_keys = str(offset)
            opt_add = str(offset + 1)
            opt_rem = str(offset + 2)
            print(f"  {METIS_CYAN_SOFT}{opt_keys}.{RESET} 🔑 Configurar/Alterar Chaves de API")
            print(f"  {METIS_CYAN_SOFT}{opt_add}.{RESET} ➕ Cadastrar Novo Servidor (OpenRouter, DeepSeek, etc.)")
            print(f"  {METIS_CYAN_SOFT}{opt_rem}.{RESET} 🗑️  Remover Servidor Personalizado")
            print(f"{METIS_BORDER_BRIGHT}══════════════════════════════════════════════════{RESET}")

            sub_api = safe_input(f"\n{METIS_GOLD}{BOLD}Opção (1-{opt_rem}) [padrão 1]: {RESET}", multiline=False).strip()
            if not sub_api:
                sub_api = "1"

            if sub_api.lower() in ["/voltar", "/v", "0", "voltar"]:
                continue

            if sub_api == opt_keys:
                print(f"\n{BOLD}Qual chave de API você quer alterar?{RESET}")
                print(f"  1. Gemini (GEMINI_API_KEY) [{config.GEMINI_API_KEY[:6]}...]" if config.GEMINI_API_KEY else "  1. Gemini (GEMINI_API_KEY) [Não configurada]")
                print(f"  2. Groq (GROQ_API_KEY) [{config.GROQ_API_KEY[:6]}...]" if config.GROQ_API_KEY else "  2. Groq (GROQ_API_KEY) [Não configurada]")
                print(f"  3. NVIDIA (NVIDIA_API_KEY) [{config.NVIDIA_API_KEY[:6]}...]" if config.NVIDIA_API_KEY else "  3. NVIDIA (NVIDIA_API_KEY) [Não configurada]")
                if servidores_custom:
                    for i, s in enumerate(servidores_custom, 4):
                        k_env = s.get("api_key_env", f"{s.get('id', 'custom').upper()}_API_KEY")
                        k_val = os.getenv(k_env, "") or s.get("api_key", "")
                        preview = f"[{k_val[:6]}...]" if k_val else "[Não configurada]"
                        print(f"  {i}. {s.get('nome')} ({k_env}) {preview}")

                chave_esc = safe_input(f"\n{BOLD}Escolha a opção: {RESET}", multiline=False).strip()
                if chave_esc == "1":
                    configurar_api_key("GEMINI_API_KEY")
                elif chave_esc == "2":
                    configurar_api_key("GROQ_API_KEY")
                elif chave_esc == "3":
                    configurar_api_key("NVIDIA_API_KEY")
                elif chave_esc.isdigit() and int(chave_esc) >= 4 and int(chave_esc) < 4 + len(servidores_custom):
                    s_target = servidores_custom[int(chave_esc) - 4]
                    configurar_api_key(s_target.get("api_key_env", f"{s_target['id'].upper()}_API_KEY"))

                input("\nPressione ENTER para voltar ao menu...")
                continue

            elif sub_api == opt_add or sub_api in ["+", "a", "add"]:
                adicionar_servidor_wizard()
                input("\nPressione ENTER para voltar ao menu...")
                continue

            elif sub_api == opt_rem or sub_api in ["-", "r", "rem"]:
                remover_servidor_wizard()
                input("\nPressione ENTER para voltar ao menu...")
                continue

            elif sub_api in mapa_custom:
                srv = mapa_custom[sub_api]
                api_key_env = srv.get("api_key_env", f"{srv['id'].upper()}_API_KEY")
                chave_val = os.getenv(api_key_env, "").strip() or srv.get("api_key", "").strip()
                if not chave_val:
                    if not configurar_api_key(api_key_env):
                        input("\nPressione ENTER para voltar ao menu...")
                        continue

                configurar_modelo_dinamico(srv.get("nome", "Custom API"), server_id=srv["id"])
                # Recarrega dados atualizados do servidor
                srv = obter_servidor_customizado(srv["id"]) or srv
                salvar_estado_chat({"escolha": "3", "sub_api": sub_api, "custom_server_id": srv["id"]})
                chat_session.iniciar(history_manager, CustomOpenAIService(srv))

            elif sub_api == "4":
                try:
                    import g4f  # noqa: F401
                    modelo_sel = configurar_modelo_dinamico("G4F", "G4F_MODEL")
                    from agente.services.g4f_service import G4FService
                    salvar_estado_chat({"escolha": "3", "sub_api": "4", "g4f_model": modelo_sel})
                    chat_session.iniciar(history_manager, G4FService(model=modelo_sel))
                except ImportError:
                    print(f"{RED}[Erro] Módulo g4f não instalado. Rode: pip install g4f{RESET}")
                    input("\nPressione ENTER para voltar ao menu...")

            elif sub_api == "3":
                from agente.services.nvidia_service import NvidiaService
                if not config.NVIDIA_API_KEY:
                    if not configurar_api_key("NVIDIA_API_KEY"):
                        input("\nPressione ENTER para voltar ao menu...")
                        continue

                configurar_modelo_dinamico("NVIDIA", "NVIDIA_MODEL")

                salvar_estado_chat({"escolha": "3", "sub_api": "3", "nvidia_model": config.NVIDIA_MODEL})
                chat_session.iniciar(history_manager, NvidiaService())

            elif sub_api == "2":
                from agente.services.groq_service import GroqService
                if not config.GROQ_API_KEY:
                    if not configurar_api_key("GROQ_API_KEY"):
                        input("\nPressione ENTER para voltar ao menu...")
                        continue

                configurar_modelo_dinamico("Groq", "GROQ_MODEL")

                salvar_estado_chat({"escolha": "3", "sub_api": "2", "groq_model": config.GROQ_MODEL})
                chat_session.iniciar(history_manager, GroqService())

            else:
                from agente.services.gemini_service import GeminiService
                if not config.GEMINI_API_KEY:
                    if not configurar_api_key("GEMINI_API_KEY"):
                        input("\nPressione ENTER para voltar ao menu...")
                        continue

                configurar_modelo_dinamico("Gemini", "GEMINI_MODEL")

                salvar_estado_chat({"escolha": "3", "sub_api": "1", "gemini_model": config.GEMINI_MODEL})
                chat_session.iniciar(history_manager, GeminiService())

        elif escolha in ["4", "04"]:
            direct_search.iniciar()

        elif escolha in ["5", "05"]:
            trocar_modelo_ollama()

        elif escolha in ["6", "06"]:
            confirm = input(f"{METIS_RED}{BOLD}CUIDADO: Isso vai deletar TODAS as conversas armazenadas no seu HD. Tem certeza? (s/n): {RESET}").strip().lower()
            if confirm == "s":
                dir_path = Path(config.HISTORICO_DIR)
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    dir_path.mkdir(exist_ok=True)
                print(f"{METIS_GREEN}Todos os históricos foram purificados fisicamente da pasta.{RESET}")
                history_manager.limpar()
            else:
                print(f"{METIS_GOLD}Operação cancelada.{RESET}")
            input("\nPressione ENTER para continuar...")

        elif escolha in ["7", "07"]:
            gerenciar_historico(history_manager)

        elif escolha in ["8", "08", "0", "00", "sair", "exit", "/sair", "/exit"]:
            limpar_tela()
            print(f"{METIS_GOLD}Saindo do Metis Oracle System... Até logo.{RESET}")
            return

        elif escolha.lower() == "/g4f":
            try:
                import g4f  # noqa: F401
                modelo_sel = configurar_modelo_dinamico("G4F", "G4F_MODEL")
                from agente.services.g4f_service import G4FService
                chat_session.iniciar(history_manager, G4FService(model=modelo_sel))
            except ImportError:
                print(f"{RED}[Erro] Módulo g4f não instalado. Rode: pip install g4f{RESET}")
                input("\nPressione ENTER para voltar ao menu...")

        elif escolha.lower() in {"/help", "/ajuda"}:
            exibir_ajuda()
            input("\nPressione ENTER para continuar...")

        elif escolha.lower() == "/status":
            exibir_status(history_manager)
            input("\nPressione ENTER para continuar...")

        elif escolha.lower().startswith("/web "):
            pergunta_web = escolha[5:].strip()
            if not pergunta_web:
                print(f"{YELLOW}Uso: /web <sua pergunta>{RESET}")
                input("\nPressione ENTER para tentar novamente...")
                continue
            chat_session.processar_pergunta(pergunta_web, history_manager, OllamaService(), forcar_web=True, iterativo=True)

        elif escolha.lower() in {"/sessao", "/sessoes"} or escolha.lower().startswith("/sessao "):
            from agente.sessions.command_handlers import handle_sessao
            history_manager = handle_sessao(escolha, history_manager)
            input("\nPressione ENTER para continuar...")

        elif escolha.lower() == "/limpar":
            from agente.sessions.command_handlers import handle_limpar
            handle_limpar(history_manager)
            input("\nPressione ENTER para continuar...")

        elif escolha.lower() == "/deletar_sessao":
            from agente.sessions.command_handlers import handle_deletar_sessao
            history_manager = handle_deletar_sessao(history_manager)
            input("\nPressione ENTER para continuar...")

        elif escolha.lower() == "/deletar_tudo":
            from agente.sessions.command_handlers import handle_deletar_tudo
            history_manager = handle_deletar_tudo(history_manager)
            input("\nPressione ENTER para continuar...")

        elif escolha.lower().startswith("/exportar"):
            from agente.sessions.command_handlers import handle_exportar
            handle_exportar(history_manager)
            input("\nPressione ENTER para continuar...")

        else:
            print(f"{RED}Opção inválida.{RESET}")
            input("\nPressione ENTER para tentar novamente...")
