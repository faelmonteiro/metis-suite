import mimetypes
import logging
import shutil
from datetime import datetime
from pathlib import Path

from agente import config
from agente.colors import *
from agente.history import HistoryManager
from agente.services.base import BaseService
from agente.utils import (
    COMANDOS_SAIDA,
    caminho_leitura_seguro,
    limitar_texto,
    safe_input,
    sanitizar_nome_sessao,
)

logger = logging.getLogger(__name__)


def handle_ajuda() -> None:
    from agente.ui.help import exibir_ajuda
    exibir_ajuda()


def handle_status(history_manager: HistoryManager) -> None:
    from agente.ui.status import exibir_status
    exibir_status(history_manager)


def handle_limpar(history_manager: HistoryManager) -> None:
    try:
        conf = input("Limpar histórico? (s/n): ").strip().lower()
        if conf == "s":
            history_manager.limpar()
            print(f"{GREEN}Histórico limpo.{RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


def handle_modelo(service: BaseService, user_input: str) -> BaseService:
    from agente.providers_manager import (
        obter_servidores_customizados,
        obter_modelos_provedor,
        salvar_variavel_env,
        salvar_preferencia,
        atualizar_modelo_ativo_servidor
    )
    custom_servidores = obter_servidores_customizados()
    custom_nomes = [s.get("id") for s in custom_servidores]

    parts = user_input.split(maxsplit=1)
    if len(parts) == 1:
        custom_hint = (" | " + " | ".join(custom_nomes)) if custom_nomes else ""
        print(f"\n{BOLD}{CYAN}--- MODELO ATUAL: {service.nome_provedor} ---{RESET}")
        print(f"{YELLOW}Uso: /modelo <provedor> [nome_do_modelo]{RESET}")
        print(f"{GRAY}Provedores disponíveis: ollama | gemini | groq | nvidia | g4f{custom_hint}{RESET}\n")
        return service

    arg = parts[1].strip()
    arg_tokens = arg.split(maxsplit=1)
    first_token = arg_tokens[0].lower()
    second_token = arg_tokens[1].strip() if len(arg_tokens) > 1 else None

    # 1. Provedores padrão
    if first_token == "ollama":
        from agente.services.ollama_service import OllamaService
        modelo = second_token or config.OLLAMA_MODEL
        config.OLLAMA_MODEL = modelo
        salvar_variavel_env("OLLAMA_MODEL", modelo)
        salvar_variavel_env("DEFAULT_PROVIDER", "ollama")
        salvar_preferencia("last_active_provider", "ollama")
        salvar_preferencia("last_active_model", modelo)
        print(f"{GREEN}Provedor alterado para Ollama ({modelo}).{RESET}")
        return OllamaService(model=modelo)

    elif first_token == "gemini":
        from agente.services.gemini_service import GeminiService
        modelo = second_token or config.GEMINI_MODEL
        config.GEMINI_MODEL = modelo
        salvar_variavel_env("GEMINI_MODEL", modelo)
        salvar_variavel_env("DEFAULT_PROVIDER", "gemini")
        salvar_preferencia("last_active_provider", "gemini")
        salvar_preferencia("last_active_model", modelo)
        print(f"{GREEN}Provedor alterado para Gemini ({modelo}).{RESET}")
        return GeminiService(model=modelo)

    elif first_token == "groq":
        from agente.services.groq_service import GroqService
        modelo = second_token or config.GROQ_MODEL
        config.GROQ_MODEL = modelo
        salvar_variavel_env("GROQ_MODEL", modelo)
        salvar_variavel_env("DEFAULT_PROVIDER", "groq")
        salvar_preferencia("last_active_provider", "groq")
        salvar_preferencia("last_active_model", modelo)
        print(f"{GREEN}Provedor alterado para Groq ({modelo}).{RESET}")
        return GroqService(model=modelo)

    elif first_token == "nvidia":
        from agente.services.nvidia_service import NvidiaService
        modelo = second_token or getattr(config, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
        config.NVIDIA_MODEL = modelo
        salvar_variavel_env("NVIDIA_MODEL", modelo)
        salvar_variavel_env("DEFAULT_PROVIDER", "nvidia")
        salvar_preferencia("last_active_provider", "nvidia")
        salvar_preferencia("last_active_model", modelo)
        print(f"{GREEN}Provedor alterado para Nvidia ({modelo}).{RESET}")
        return NvidiaService(model=modelo)

    elif first_token == "g4f":
        from agente.services.g4f_service import G4FService
        modelo = second_token or getattr(config, "G4F_MODEL", "gpt-4o-mini")
        config.G4F_MODEL = modelo
        salvar_variavel_env("G4F_MODEL", modelo)
        salvar_variavel_env("DEFAULT_PROVIDER", "g4f")
        salvar_preferencia("last_active_provider", "g4f")
        salvar_preferencia("last_active_model", modelo)
        print(f"{GREEN}Provedor alterado para G4F ({modelo}).{RESET}")
        return G4FService(model=modelo)

    # 2. Servidores customizados
    for s in custom_servidores:
        if s.get("id") == first_token or s.get("nome", "").lower() == first_token:
            from agente.services.custom_openai_service import CustomOpenAIService
            srv_copy = dict(s)
            if second_token:
                srv_copy["modelo_atual"] = second_token
            modelo = srv_copy.get("modelo_atual", "")
            salvar_variavel_env("DEFAULT_PROVIDER", f"custom:{s.get('id')}")
            salvar_preferencia("last_active_provider", f"custom:{s.get('id')}")
            salvar_preferencia("last_active_model", modelo)
            atualizar_modelo_ativo_servidor(s.get("id"), modelo)
            print(f"{GREEN}Provedor alterado para {s.get('nome')} ({modelo}).{RESET}")
            return CustomOpenAIService(srv_copy)

    # 3. Busca inteligente se o usuário digitou diretamente o nome do modelo
    from agente.services import ollama_service
    if arg in (ollama_service.listar_modelos() or []):
        from agente.services.ollama_service import OllamaService
        config.OLLAMA_MODEL = arg
        salvar_variavel_env("OLLAMA_MODEL", arg)
        salvar_variavel_env("DEFAULT_PROVIDER", "ollama")
        salvar_preferencia("last_active_provider", "ollama")
        salvar_preferencia("last_active_model", arg)
        print(f"{GREEN}Provedor alterado para Ollama ({arg}).{RESET}")
        return OllamaService(model=arg)

    if arg in obter_modelos_provedor("Gemini") or "gemini" in arg.lower():
        from agente.services.gemini_service import GeminiService
        config.GEMINI_MODEL = arg
        salvar_variavel_env("GEMINI_MODEL", arg)
        salvar_variavel_env("DEFAULT_PROVIDER", "gemini")
        salvar_preferencia("last_active_provider", "gemini")
        salvar_preferencia("last_active_model", arg)
        print(f"{GREEN}Provedor alterado para Gemini ({arg}).{RESET}")
        return GeminiService(model=arg)

    if arg in obter_modelos_provedor("Groq"):
        from agente.services.groq_service import GroqService
        config.GROQ_MODEL = arg
        salvar_variavel_env("GROQ_MODEL", arg)
        salvar_variavel_env("DEFAULT_PROVIDER", "groq")
        salvar_preferencia("last_active_provider", "groq")
        salvar_preferencia("last_active_model", arg)
        print(f"{GREEN}Provedor alterado para Groq ({arg}).{RESET}")
        return GroqService(model=arg)

    if arg in obter_modelos_provedor("NVIDIA") or "nvidia" in arg.lower():
        from agente.services.nvidia_service import NvidiaService
        config.NVIDIA_MODEL = arg
        salvar_variavel_env("NVIDIA_MODEL", arg)
        salvar_variavel_env("DEFAULT_PROVIDER", "nvidia")
        salvar_preferencia("last_active_provider", "nvidia")
        salvar_preferencia("last_active_model", arg)
        print(f"{GREEN}Provedor alterado para Nvidia ({arg}).{RESET}")
        return NvidiaService(model=arg)

    if arg in obter_modelos_provedor("G4F"):
        from agente.services.g4f_service import G4FService
        config.G4F_MODEL = arg
        salvar_variavel_env("G4F_MODEL", arg)
        salvar_variavel_env("DEFAULT_PROVIDER", "g4f")
        salvar_preferencia("last_active_provider", "g4f")
        salvar_preferencia("last_active_model", arg)
        print(f"{GREEN}Provedor alterado para G4F ({arg}).{RESET}")
        return G4FService(model=arg)

    for s in custom_servidores:
        if arg in s.get("modelos", []):
            from agente.services.custom_openai_service import CustomOpenAIService
            srv_copy = dict(s)
            srv_copy["modelo_atual"] = arg
            salvar_variavel_env("DEFAULT_PROVIDER", f"custom:{s.get('id')}")
            salvar_preferencia("last_active_provider", f"custom:{s.get('id')}")
            salvar_preferencia("last_active_model", arg)
            atualizar_modelo_ativo_servidor(s.get("id"), arg)
            print(f"{GREEN}Provedor alterado para {s.get('nome')} ({arg}).{RESET}")
            return CustomOpenAIService(srv_copy)

    print(f"{RED}Provedor ou modelo desconhecido: '{arg}'{RESET}")
    print(f"{YELLOW}Dica: Use /modelo sem parâmetros para ver as opções.{RESET}")
    return service


def handle_automode() -> None:
    from agente.services import tools_defs
    from agente.providers_manager import salvar_preferencia
    tools_defs.AUTO_APPROVE_MODE = not getattr(tools_defs, "AUTO_APPROVE_MODE", False)
    salvar_preferencia("auto_approve_mode", tools_defs.AUTO_APPROVE_MODE)
    status = "ATIVADO" if tools_defs.AUTO_APPROVE_MODE else "DESATIVADO"
    print(f"{GREEN}Modo automático de escrita de arquivos: {status}!{RESET}")


def handle_web(user_input: str, history_manager: HistoryManager, service: BaseService, processar_func) -> None:
    pergunta_limpa = user_input[5:].strip()
    if not pergunta_limpa:
        print(f"{YELLOW}Uso: /web <sua pergunta>{RESET}")
        return
    processar_func(pergunta_limpa, history_manager, service, forcar_web=True, iterativo=True)


def handle_retry(history_manager: HistoryManager, service: BaseService, forcar_web: bool, processar_func) -> None:
    turnos = history_manager.listar_turnos()
    if turnos:
        ultima_pergunta = turnos[-1].get("user", "")
        history_manager.deletar_ultimos(1)
        if ultima_pergunta:
            print(f"{YELLOW}Repetindo: {limitar_texto(ultima_pergunta, 60)}{RESET}")
            processar_func(ultima_pergunta, history_manager, service, forcar_web=forcar_web, iterativo=True)
        else:
            print(f"{YELLOW}Nenhuma pergunta para repetir.{RESET}")
    else:
        print(f"{YELLOW}Nenhuma pergunta para repetir.{RESET}")


def handle_arquivo(user_input: str, history_manager: HistoryManager, service: BaseService, processar_func) -> str:
    comando_resto = user_input[9:].strip()
    caminho_str = comando_resto

    try:
        try:
            caminho_validado = caminho_leitura_seguro(caminho_str)
        except ValueError as ve:
            if "diretório" in str(ve).lower():
                print(f"{YELLOW}⚠️ '{caminho_str}' é um diretório. Informe um arquivo.{RESET}")
                return "CONTINUE"
            raise

        if not caminho_validado.exists():
            print(f"{RED}Arquivo não encontrado: {caminho_validado}{RESET}")
            return "CONTINUE"

        mime, _ = mimetypes.guess_type(str(caminho_validado))
        is_media = mime and (mime.startswith("image/") or mime.startswith("audio/"))

        print(f"{YELLOW}Processando anexo: {caminho_str}...{RESET}")

        try:
            print("")
            pergunta_pre = safe_input(f"{BOLD}O que deseja fazer com este arquivo?{RESET} ", multiline=False).strip()
        except (KeyboardInterrupt, EOFError):
            return "CONTINUE"

        if not pergunta_pre:
            pergunta_pre = "Analise e descreva este arquivo detalhadamente."

        if pergunta_pre.lower() in COMANDOS_SAIDA:
            return "SAIR"

        if is_media:
            print(f"{GREEN}Mídia carregada: {caminho_validado.name} ({mime}){RESET}")
            processar_func(
                pergunta_pre,
                history_manager,
                service,
                forcar_web=False,
                iterativo=True,
                pular_web=True,
                media_paths=[str(caminho_validado)],
            )
        else:
            from agente.services.file_reader import ler_arquivo
            conteudo = ler_arquivo(str(caminho_validado), max_chars=25000)

            if conteudo.startswith("[Erro]"):
                print(f"{RED}{conteudo}{RESET}")
                return "CONTINUE"

            print(f"{GREEN}Texto lido: {caminho_validado.name} ({len(conteudo)} chars){RESET}")

            contexto = (
                f"Conteúdo do arquivo '{caminho_str}':\n"
                f"```\n{conteudo}\n```\n\n"
                f"{pergunta_pre}"
            )
            processar_func(contexto, history_manager, service, forcar_web=False, iterativo=True, pular_web=True)
    except Exception as e:
        print(f"{RED}Erro ao processar arquivo: {e}{RESET}")

    return "CONTINUE"


def _obter_diretorio_exportacao() -> Path:
    """Retorna um diretório seguro e gravável para exportações do usuário."""
    # 1. Prioridade: Downloads ou Documentos do usuário
    for d in [Path.home() / "Downloads", Path.home() / "Documentos", Path.home() / "Documents"]:
        if d.exists() and os.access(d, os.W_OK):
            target = d / "Metis_Exports"
            try:
                target.mkdir(parents=True, exist_ok=True)
                return target
            except Exception:
                pass

    # 2. Diretório XDG de dados do usuário (~/.local/share/metis/exports)
    xdg_exports = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "metis" / "exports"
    try:
        xdg_exports.mkdir(parents=True, exist_ok=True)
        return xdg_exports
    except Exception:
        pass

    # 3. Fallback no CWD do usuário
    fallback = Path.cwd() / "metis_exports"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def handle_exportar(history_manager: HistoryManager) -> None:
    turnos = history_manager.listar_turnos()
    if not turnos:
        print(f"{YELLOW}Histórico vazio.{RESET}")
        return

    try:
        export_dir = _obter_diretorio_exportacao()
    except Exception as e:
        print(f"{RED}Erro ao acessar diretório de exportação: {e}{RESET}")
        return

    data_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_nome = f"conversa_{data_str}.md"
    nome = export_dir / base_nome
    counter = 1
    while nome.exists():
        nome = export_dir / f"conversa_{data_str}_{counter}.md"
        counter += 1

    try:
        conteudo = f"# Conversa Metis — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        for t in turnos:
            conteudo += f"## 🧑 Você\n{t.get('user', '')}\n\n"
            conteudo += f"## 🤖 Assistente\n{t.get('assistant', '')}\n\n---\n\n"

        nome.write_text(conteudo, encoding="utf-8")
        print(f"{GREEN}✔ Conversa exportada com sucesso: {BOLD}{nome}{RESET}")
    except PermissionError:
        print(f"{RED}Erro de permissão: Não foi possível gravar em '{nome}'. Verifique as permissões da pasta.{RESET}")
    except Exception as e:
        print(f"{RED}Erro ao exportar conversa: {e}{RESET}")


def handle_sessoes(history_manager: HistoryManager) -> HistoryManager:
    sessoes = HistoryManager.listar_sessoes()
    if not sessoes:
        print(f"{YELLOW}Nenhuma sessão encontrada.{RESET}")
        return history_manager

    sessoes = sessoes[::-1]
    pagina_atual = 0
    itens_por_pagina = 15

    while True:
        inicio = pagina_atual * itens_por_pagina
        fim = inicio + itens_por_pagina
        sessoes_exibir = sessoes[inicio:fim]

        total_paginas = max(1, (len(sessoes) - 1) // itens_por_pagina + 1)
        print(f"\n{BOLD}Sessões: Página {pagina_atual+1} de {total_paginas}{RESET}")

        for i, s in enumerate(sessoes_exibir, inicio + 1):
            turnos_s = HistoryManager(s).contagem_conversas()
            if s == history_manager.sessao:
                print(f"  [{GREEN}{i}{RESET}] {GREEN}{s}{RESET} ({turnos_s} turnos) {GREEN}*(atual)*{RESET}")
            else:
                print(f"  [{BOLD}{i}{RESET}] {s} ({turnos_s} turnos)")

        tem_mais = fim < len(sessoes)
        opcoes = "número"

        if tem_mais:
            print(f"  {YELLOW}... digite '+' ou 'm' para ver a próxima página.{RESET}")
            opcoes += ", '+/m'"
        if pagina_atual > 0:
            print(f"  {YELLOW}... digite '-' ou 'v' para ver a página anterior.{RESET}")
            opcoes += ", '-/v'"

        try:
            print("")
            escolha = safe_input(f"{BOLD}Digite ({opcoes}) ou Enter para cancelar:{RESET} ", multiline=False).strip().lower()

            if not escolha:
                break

            if escolha in ["+", "m", "mais", "next", "n"] and tem_mais:
                pagina_atual += 1
                continue

            if escolha in ["-", "v", "menos", "prev", "voltar", "p"] and pagina_atual > 0:
                pagina_atual -= 1
                continue

            if escolha.isdigit():
                idx = int(escolha) - 1
                if 0 <= idx < len(sessoes):
                    novo_hm = HistoryManager(sessoes[idx])
                    print(f"{GREEN}Sessão trocada para: {novo_hm.sessao} ({novo_hm.contagem_conversas()} turnos){RESET}")

                    turnos = novo_hm.listar_turnos()
                    if turnos:
                        print(f"\n{CYAN}--- RESUMO DO HISTÓRICO CARREGADO ---{RESET}")
                        for t in turnos[-3:]:
                            print(f"\n{BOLD}Você:{RESET} {t['user']}")
                            print(f"{BOLD}Assistente:{RESET}\n{t['assistant']}")
                        print(f"\n{CYAN}-------------------------------------{RESET}")
                    return novo_hm
                else:
                    print(f"{RED}Número inválido.{RESET}")
                    continue

            print(f"{RED}Opção inválida.{RESET}")
        except (KeyboardInterrupt, EOFError):
            break

    return history_manager


def handle_novo_chat(user_input: str) -> HistoryManager:
    """Inicia imediatamente uma nova conversa/tópico sem fechar o programa."""
    parts = user_input.strip().split(maxsplit=1)
    if len(parts) >= 2 and parts[1].strip():
        nome_sessao = sanitizar_nome_sessao(parts[1].strip())
    else:
        nome_sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    novo_hm = HistoryManager(nome_sessao)
    print(f"\n{GREEN}✨ Nova conversa iniciada! (Sessão: {nome_sessao}){RESET}")
    return novo_hm


def handle_sessao(user_input: str, history_manager: HistoryManager) -> HistoryManager:
    """Lista sessões salvas ou troca/cria uma sessão de conversa pelo nome."""
    parts = user_input.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        # Se chamado como /sessao ou /sessoes sem nome, abre o gerenciador interativo
        return handle_sessoes(history_manager)

    nome_sessao = sanitizar_nome_sessao(parts[1].strip())
    novo_hm = HistoryManager(nome_sessao)
    print(f"{GREEN}Sessão trocada para: {nome_sessao} ({novo_hm.contagem_conversas()} turnos){RESET}")
    return novo_hm


def restaurar_servico_sessao(novo_hm: HistoryManager, current_service: BaseService) -> BaseService:
    """Restaura o provedor e modelo salvos na sessão, se existirem."""
    saved_prov = getattr(novo_hm, "saved_provider", "").lower()
    saved_model = getattr(novo_hm, "saved_model", "").strip()
    if not saved_prov and not saved_model:
        return current_service

    try:
        from agente.providers_manager import salvar_variavel_env, salvar_preferencia
        if saved_prov == "gemini" or (not saved_prov and "gemini" in saved_model.lower()):
            from agente.services.gemini_service import GeminiService
            modelo = saved_model or config.GEMINI_MODEL
            config.GEMINI_MODEL = modelo
            salvar_variavel_env("GEMINI_MODEL", modelo)
            salvar_variavel_env("DEFAULT_PROVIDER", "gemini")
            salvar_preferencia("last_active_provider", "gemini")
            salvar_preferencia("last_active_model", modelo)
            print(f"{GREEN}Provedor da sessão restaurado: Gemini ({modelo}).{RESET}")
            return GeminiService(model=modelo)
        elif saved_prov == "groq":
            from agente.services.groq_service import GroqService
            modelo = saved_model or config.GROQ_MODEL
            config.GROQ_MODEL = modelo
            salvar_variavel_env("GROQ_MODEL", modelo)
            salvar_variavel_env("DEFAULT_PROVIDER", "groq")
            salvar_preferencia("last_active_provider", "groq")
            salvar_preferencia("last_active_model", modelo)
            print(f"{GREEN}Provedor da sessão restaurado: Groq ({modelo}).{RESET}")
            return GroqService(model=modelo)
        elif saved_prov == "nvidia":
            from agente.services.nvidia_service import NvidiaService
            modelo = saved_model or getattr(config, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
            config.NVIDIA_MODEL = modelo
            salvar_variavel_env("NVIDIA_MODEL", modelo)
            salvar_variavel_env("DEFAULT_PROVIDER", "nvidia")
            salvar_preferencia("last_active_provider", "nvidia")
            salvar_preferencia("last_active_model", modelo)
            print(f"{GREEN}Provedor da sessão restaurado: NVIDIA ({modelo}).{RESET}")
            return NvidiaService(model=modelo)
        elif saved_prov == "g4f":
            from agente.services.g4f_service import G4FService
            modelo = saved_model or getattr(config, "G4F_MODEL", "gpt-4o-mini")
            config.G4F_MODEL = modelo
            salvar_variavel_env("G4F_MODEL", modelo)
            salvar_variavel_env("DEFAULT_PROVIDER", "g4f")
            salvar_preferencia("last_active_provider", "g4f")
            salvar_preferencia("last_active_model", modelo)
            print(f"{GREEN}Provedor da sessão restaurado: G4F ({modelo}).{RESET}")
            return G4FService(model=modelo)
        elif saved_prov.startswith("custom:"):
            server_id = saved_prov.split("custom:", 1)[1]
            from agente.providers_manager import obter_servidor_customizado
            from agente.services.custom_openai_service import CustomOpenAIService
            srv = obter_servidor_customizado(server_id)
            if srv:
                srv_copy = dict(srv)
                if saved_model:
                    srv_copy["modelo_atual"] = saved_model
                salvar_variavel_env("DEFAULT_PROVIDER", saved_prov)
                salvar_preferencia("last_active_provider", saved_prov)
                salvar_preferencia("last_active_model", srv_copy.get("modelo_atual", ""))
                print(f"{GREEN}Provedor da sessão restaurado: {srv.get('nome')} ({srv_copy['modelo_atual']}).{RESET}")
                return CustomOpenAIService(srv_copy)
        elif saved_prov == "ollama" or (saved_model and not saved_prov):
            from agente.services.ollama_service import OllamaService
            modelo = saved_model or config.OLLAMA_MODEL
            config.OLLAMA_MODEL = modelo
            salvar_variavel_env("OLLAMA_MODEL", modelo)
            salvar_variavel_env("DEFAULT_PROVIDER", "ollama")
            salvar_preferencia("last_active_provider", "ollama")
            salvar_preferencia("last_active_model", modelo)
            print(f"{GREEN}Provedor da sessão restaurado: Ollama ({modelo}).{RESET}")
            return OllamaService(model=modelo)
    except Exception as e:
        logger.warning(f"Não foi possível restaurar o serviço da sessão: {e}")
    return current_service


def handle_deletar_sessao(history_manager: HistoryManager) -> HistoryManager:
    """Deleta a sessão atual do disco e cria uma nova."""
    try:
        confirm = input(f"{RED}{BOLD}Deletar a sessão atual '{history_manager.sessao}'? (s/n): {RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return history_manager
    if confirm == "s":
        if history_manager.deletar_sessao():
            print(f"{GREEN}Sessão deletada.{RESET}")
            nome_sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return HistoryManager(nome_sessao)
        else:
            print(f"{RED}Erro ao deletar sessão.{RESET}")
    else:
        print("Operação cancelada.")
    return history_manager


def handle_deletar_tudo(history_manager: HistoryManager) -> HistoryManager:
    """Deleta TODAS as sessões do disco."""
    try:
        confirm = input(f"{RED}{BOLD}CUIDADO: Isso vai deletar TODAS as conversas. Tem certeza? (s/n): {RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return history_manager
    if confirm == "s":
        dir_path = Path(config.HISTORICO_DIR)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            dir_path.mkdir(exist_ok=True)
        print(f"{GREEN}Todos os históricos foram deletados.{RESET}")
        nome_sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return HistoryManager(nome_sessao)
    else:
        print("Operação cancelada.")
    return history_manager


def despachar_comando(user_input: str, history_manager: HistoryManager, service: BaseService, forcar_web: bool, processar_func) -> tuple[bool, HistoryManager, BaseService, str]:
    """
    Despacha comandos de barra (/ajuda, /status, /modelo, /sessao, etc).
    Retorna: (foi_comando, history_manager, service, acao)
    """
    l_input = user_input.lower().strip()

    if l_input in {"/ajuda", "/help"}:
        handle_ajuda()
        return True, history_manager, service, "CONTINUE"

    if l_input == "/status":
        handle_status(history_manager)
        return True, history_manager, service, "CONTINUE"

    if l_input == "/limpar":
        handle_limpar(history_manager)
        return True, history_manager, service, "CONTINUE"

    if l_input == "/deletar_sessao":
        history_manager = handle_deletar_sessao(history_manager)
        return True, history_manager, service, "CONTINUE"

    if l_input.startswith("/modelo"):
        service = handle_modelo(service, user_input)
        return True, history_manager, service, "CONTINUE"

    if l_input == "/automode":
        handle_automode()
        return True, history_manager, service, "CONTINUE"

    if l_input == "/web":
        print(f"{YELLOW}Uso: /web <sua pergunta>{RESET}")
        return True, history_manager, service, "CONTINUE"

    if l_input.startswith("/web "):
        handle_web(user_input, history_manager, service, processar_func)
        return True, history_manager, service, "CONTINUE"

    if l_input == "/retry":
        handle_retry(history_manager, service, forcar_web, processar_func)
        return True, history_manager, service, "CONTINUE"

    if l_input.startswith("/arquivo "):
        res = handle_arquivo(user_input, history_manager, service, processar_func)
        if res == "SAIR":
            return True, history_manager, service, "SAIR"
        return True, history_manager, service, "CONTINUE"

    if l_input.startswith("/exportar"):
        handle_exportar(history_manager)
        return True, history_manager, service, "CONTINUE"

    if l_input in {"/sessao", "/sessoes"} or l_input.startswith("/sessao "):
        history_manager = handle_sessao(user_input, history_manager)
        service = restaurar_servico_sessao(history_manager, service)
        return True, history_manager, service, "CONTINUE"

    if l_input in {"/novo", "/nova", "/new", "/reset"} or l_input.startswith("/novo ") or l_input.startswith("/nova ") or l_input.startswith("/new "):
        history_manager = handle_novo_chat(user_input)
        return True, history_manager, service, "CONTINUE"

    if l_input == "/deletar_tudo":
        history_manager = handle_deletar_tudo(history_manager)
        return True, history_manager, service, "CONTINUE"

    return False, history_manager, service, "NONE"
