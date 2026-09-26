"""
Submódulo de configuração de modelos e provedores para o menu.
Permite alternar modelos salvos sem redigitar, cadastrar novos modelos,
remover modelos da lista, e gerenciar servidores personalizados.
"""
import re
import sys
from typing import Optional

from agente import config
from agente.colors import BOLD, RESET, YELLOW, GREEN, RED, CYAN, GRAY
from agente.utils import safe_input
from agente.services import ollama_service
from agente.providers_manager import (
    obter_modelos_provedor,
    adicionar_modelo_provedor,
    remover_modelo_provedor,
    obter_servidores_customizados,
    obter_servidor_customizado,
    salvar_servidor_customizado,
    remover_servidor_customizado,
    atualizar_modelo_ativo_servidor,
    salvar_variavel_env
)


def limpar_tela():
    if config.NO_COLOR:
        print("\n" * 2)
        return
    try:
        if not sys.stdout.isatty():
            print("\n" * 2)
            return
    except Exception:
        print("\n" * 2)
        return
    print("\033[H\033[2J\033[3J", end="", flush=True)


def _salvar_modelo_ativo(provedor: str, modelo: str, env_var: Optional[str] = None, server_id: Optional[str] = None):
    """Atualiza o modelo ativo tanto no .env/config quanto no arquivo de dados."""
    if env_var:
        salvar_variavel_env(env_var, modelo)
        setattr(config, env_var, modelo)
    if server_id:
        atualizar_modelo_ativo_servidor(server_id, modelo)
    adicionar_modelo_provedor(provedor, modelo, server_id=server_id)


def parse_indices_multiplos(texto: str, total: int) -> list:
    """
    Interpreta entradas de seleção múltipla como:
    - "1" -> [0]
    - "1 2 3" -> [0, 1, 2]
    - "1, 2, 3" ou "1,3" -> [0, 1, 2] ou [0, 2]
    - "1-3" -> [0, 1, 2]
    - "1-3 5" -> [0, 1, 2, 4]
    Retorna lista de índices (0-based) válidos e ordenados.
    """
    if not texto or not texto.strip():
        return []

    indices = set()
    tokens = re.split(r"[\s,]+", texto.strip())
    for tok in tokens:
        if not tok:
            continue
        m_range = re.match(r"^(\d+)-(\d+)$", tok)
        if m_range:
            start, end = int(m_range.group(1)), int(m_range.group(2))
            if start > end:
                start, end = end, start
            for n in range(start, end + 1):
                if 1 <= n <= total:
                    indices.add(n - 1)
        elif tok.isdigit():
            n = int(tok)
            if 1 <= n <= total:
                indices.add(n - 1)

    return sorted(list(indices))


def configurar_modelo_dinamico(provedor: str, env_var: Optional[str] = None, server_id: Optional[str] = None) -> str:
    """
    Menu interativo para gerenciar e alternar modelos salvos do provedor/servidor.
    - Exibe modelos salvos numerados
    - Permite manter o atual apertando ENTER
    - Permite escolher digitando o número
    - Permite adicionar novo modelo (+)
    - Permite remover múltiplos modelos da lista (-) (ex: 1 2 3 ou 1, 2)
    """
    while True:
        # Obtém modelo atual
        if env_var:
            modelo_atual = getattr(config, env_var, "")
        elif server_id:
            srv = obter_servidor_customizado(server_id)
            modelo_atual = srv.get("modelo_atual", "") if srv else ""
        else:
            modelo_atual = ""

        modelos = obter_modelos_provedor(provedor, server_id=server_id)

        # Garante que o modelo atual esteja na lista
        if modelo_atual and modelo_atual not in modelos:
            adicionar_modelo_provedor(provedor, modelo_atual, server_id=server_id)
            modelos = obter_modelos_provedor(provedor, server_id=server_id)

        print(f"\n{BOLD}══════════════════════════════════════════════════{RESET}")
        print(f"{CYAN}🤖 Modelos Salvos para {provedor}:{RESET}")
        print(f"{BOLD}──────────────────────────────────────────────────{RESET}")

        for i, m in enumerate(modelos, 1):
            if m == modelo_atual:
                print(f"  {GREEN}{BOLD}{i}. [*] {m} (Ativo){RESET}")
            else:
                print(f"  {i}. [ ] {m}")

        print(f"{BOLD}──────────────────────────────────────────────────{RESET}")
        print(f"  {RED}[-] Remover modelo(s) da lista{RESET}")
        print(f"{BOLD}══════════════════════════════════════════════════{RESET}")
        print(f"{GRAY}• Pressione ENTER para manter o atual ({modelo_atual}).{RESET}")
        print(f"{GRAY}• Digite o número (1-{len(modelos)}) para alternar.{RESET}")
        print(f"{GRAY}• Ou digite o ID do novo modelo para adicionar e usar.{RESET}")

        escolha = safe_input(f"\n{BOLD}Opção (1-{len(modelos)}), [-] ou ID do modelo: {RESET}", multiline=False).strip()

        # ENTER = Manter atual
        if not escolha:
            print(f"{GREEN}Mantendo modelo ativo: {modelo_atual}{RESET}")
            return modelo_atual

        # Cancelar / Voltar
        if escolha.lower() in ["/voltar", "/v", "voltar", "0"]:
            print(f"{YELLOW}Mantendo modelo atual.{RESET}")
            return modelo_atual

        # Remover modelo(s) (-)
        if escolha in ["-", "r", "rem", "remover"]:
            if len(modelos) <= 1:
                print(f"\n{YELLOW}⚠️  A lista possui apenas 1 modelo salvo. Não é possível remover o único modelo.{RESET}")
                continue

            print(f"\n{RED}{BOLD}Selecione o(s) número(s) para remover (ex: 1 ou 1 2 3 ou 1, 2):{RESET}")
            for i, m in enumerate(modelos, 1):
                marca = " (Ativo)" if m == modelo_atual else ""
                print(f"  {i}. {m}{marca}")

            idx_rem = safe_input(f"\n{BOLD}Número(s) para remover (1-{len(modelos)}) ou ENTER para cancelar: {RESET}", multiline=False).strip()
            if not idx_rem or idx_rem in ["0", "/voltar", "/v"]:
                print(f"{YELLOW}Remoção cancelada.{RESET}")
                continue

            indices = parse_indices_multiplos(idx_rem, len(modelos))
            if not indices:
                print(f"{RED}Nenhum número válido informado.{RESET}")
                continue

            if len(indices) >= len(modelos):
                print(f"\n{YELLOW}⚠️  Não é possível remover todos os modelos da lista. Pelo menos 1 modelo deve permanecer.{RESET}")
                continue

            mods_para_remover = [modelos[idx] for idx in indices]
            for mod in mods_para_remover:
                remover_modelo_provedor(provedor, mod, server_id=server_id)

            print(f"\n{GREEN}🗑️  {len(mods_para_remover)} modelo(s) removido(s) com sucesso:{RESET}")
            for mod in mods_para_remover:
                print(f"  {RED}• {mod}{RESET}")

            # Se removeu o modelo atual, ativa o primeiro da lista restante
            if modelo_atual in mods_para_remover:
                modelos_restantes = obter_modelos_provedor(provedor, server_id=server_id)
                if modelos_restantes:
                    novo_ativo = modelos_restantes[0]
                    _salvar_modelo_ativo(provedor, novo_ativo, env_var=env_var, server_id=server_id)
                    print(f"{YELLOW}Novo modelo ativo definido automaticamente: {novo_ativo}{RESET}")
            continue

        # Seleção por número (1..N)
        if escolha.isdigit():
            idx = int(escolha) - 1
            if 0 <= idx < len(modelos):
                selecionado = modelos[idx]
                if selecionado != modelo_atual:
                    _salvar_modelo_ativo(provedor, selecionado, env_var=env_var, server_id=server_id)
                    print(f"\n{GREEN}✅ Modelo alterado para '{selecionado}' com sucesso!{RESET}")
                else:
                    print(f"\n{GREEN}Modelo '{selecionado}' já é o ativo.{RESET}")
                return selecionado
            else:
                print(f"{RED}Opção inválida.{RESET}")
                continue

        # Se digitou diretamente um nome de modelo que não é número
        novo_modelo = escolha
        _salvar_modelo_ativo(provedor, novo_modelo, env_var=env_var, server_id=server_id)
        print(f"\n{GREEN}✅ Modelo '{novo_modelo}' salvo na lista e definido como ativo!{RESET}")
        return novo_modelo


def adicionar_servidor_wizard() -> Optional[dict]:
    """Assistente interativo para cadastrar um novo servidor de API personalizada."""
    print(f"\n{BOLD}══════════════════════════════════════════════════{RESET}")
    print(f"{CYAN}➕ Cadastrar Novo Servidor / Provedor de API{RESET}")
    print(f"{GRAY}(Compatível com OpenRouter, DeepSeek, LocalAI, vLLM, LM Studio, etc.){RESET}")
    print(f"{BOLD}──────────────────────────────────────────────────{RESET}")

    nome = safe_input(f"{BOLD}1. Nome do Servidor (ex: OpenRouter, DeepSeek, etc.): {RESET}", multiline=False).strip()
    if not nome or nome in ["0", "/voltar", "/v"]:
        print(f"{YELLOW}Operação cancelada.{RESET}")
        return None

    print(f"\n{GRAY}Exemplos de URL Base:{RESET}")
    print(f"{GRAY}  • OpenRouter: https://openrouter.ai/api/v1{RESET}")
    print(f"{GRAY}  • DeepSeek:   https://api.deepseek.com/v1{RESET}")
    print(f"{GRAY}  • Local/vLLM: http://127.0.0.1:8000/v1{RESET}")
    base_url = safe_input(f"{BOLD}2. URL Base da API: {RESET}", multiline=False).strip()
    if not base_url or base_url in ["0", "/voltar", "/v"]:
        print(f"{YELLOW}Operação cancelada.{RESET}")
        return None

    api_key = safe_input(f"\n{BOLD}3. Chave de API (Cole a chave ou deixe em branco se não exigir): {RESET}", multiline=False).strip()

    print(f"\n{GRAY}Exemplo de modelo: anthropic/claude-3.5-sonnet, deepseek-chat, etc.{RESET}")
    modelo_padrao = safe_input(f"{BOLD}4. Modelo Padrão Inicial: {RESET}", multiline=False).strip()
    if not modelo_padrao:
        modelo_padrao = "default"

    servidor = salvar_servidor_customizado(
        nome=nome,
        base_url=base_url,
        api_key=api_key,
        modelo_padrao=modelo_padrao
    )

    print(f"\n{GREEN}✅ Servidor '{servidor['nome']}' cadastrado com sucesso!{RESET}")
    print(f"{GRAY}Ele agora aparece diretamente no menu de IA Externa.{RESET}")
    return servidor


def remover_servidor_wizard() -> None:
    """Assistente interativo para remover servidores personalizados."""
    servidores = obter_servidores_customizados()
    if not servidores:
        print(f"\n{YELLOW}Nenhum servidor personalizado cadastrado no momento.{RESET}")
        return

    print(f"\n{RED}{BOLD}🗑️  Selecione o(s) Servidor(es) Personalizado(s) para Remover (ex: 1 ou 1 2):{RESET}")
    for i, s in enumerate(servidores, 1):
        print(f"  {i}. {s.get('nome')} ({s.get('base_url')})")

    escolha = safe_input(f"\n{BOLD}Digite o(s) número(s) (1-{len(servidores)}) ou ENTER para cancelar: {RESET}", multiline=False).strip()
    if not escolha or escolha in ["0", "/voltar", "/v"]:
        print(f"{YELLOW}Operação cancelada.{RESET}")
        return

    indices = parse_indices_multiplos(escolha, len(servidores))
    if not indices:
        print(f"{RED}Nenhum número válido selecionado.{RESET}")
        return

    srvs_para_remover = [servidores[idx] for idx in indices]
    for srv in srvs_para_remover:
        remover_servidor_customizado(srv["id"])
        print(f"{GREEN}✅ Servidor '{srv['nome']}' removido com sucesso!{RESET}")


def trocar_modelo_ollama():
    """Menu interativo para trocar o modelo ativo do Ollama."""
    while True:
        limpar_tela()
        modelos = ollama_service.listar_modelos()

        if not modelos:
            print(f"{RED}[Erro] Não foi possível obter modelos do Ollama (offline?).{RESET}")
            input("\nPressione ENTER para continuar...")
            return

        print(f"\n{BOLD}Modelos disponíveis no Ollama:{RESET}")
        for i, m in enumerate(modelos, 1):
            marca = "*" if m == config.OLLAMA_MODEL else " "
            print(f"{i}. [{marca}] {m}")

        print("\n  [R] Atualizar Lista (Refresh)")

        escolha = input("\nDigite o número do modelo, nome real, 'r' para atualizar ou 0 para cancelar: ").strip().lower()

        if not escolha or escolha == "0":
            print("Operação cancelada.")
            return

        if escolha == "r":
            continue

        if escolha.isdigit():
            idx = int(escolha) - 1
            if 0 <= idx < len(modelos):
                config.OLLAMA_MODEL = modelos[idx]
                print(f"{GREEN}Modelo alterado para: {config.OLLAMA_MODEL}{RESET}")
            else:
                print(f"{RED}Número inválido.{RESET}")
            input("\nPressione ENTER para continuar...")
            return

        if escolha in modelos:
            config.OLLAMA_MODEL = escolha
            print(f"{GREEN}Modelo alterado para: {config.OLLAMA_MODEL}{RESET}")
            input("\nPressione ENTER para continuar...")
            return

        confirma = input(f"O modelo '{escolha}' não está listado. Usar mesmo assim? (s/n): ").strip().lower()

        if confirma == "s":
            config.OLLAMA_MODEL = escolha
            print(f"{GREEN}Modelo alterado para: {config.OLLAMA_MODEL}{RESET}")
        else:
            print("Operação cancelada.")

        input("\nPressione ENTER para continuar...")
        return
