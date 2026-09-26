#!/usr/bin/env python3
"""
CLI para gerenciar modelos do Metis via terminal (substitui manage_models.py legacy).
"""

import logging
logger = logging.getLogger(__name__)

import sys
import json
import argparse
from pathlib import Path

# Adiciona path do Metis
metis_root = Path(__file__).parent.parent.parent
if str(metis_root) not in sys.path:
    sys.path.insert(0, str(metis_root))

from agente.models import (
    load_config,
    get_builtin_models,
    get_custom_servers,
    add_custom_server, remove_custom_server,
    add_model_to_server, remove_model_from_server, set_server_active_model,
    get_server_models,
    get_provider_active_model, set_provider_active_model,
    get_removed_servers, is_server_removed, remove_server, restore_server,
    get_env_var, save_env_var, remove_env_var,
    save_provider_state,
)


def cmd_list(args):
    """Lista modelos e servidores."""
    config = load_config()

    if args.provider:
        # Lista apenas modelos do provedor especificado
        models = get_server_models(args.provider)
        for m in models:
            print(m)
    else:
        print("\n=== MODELOS BUILTIN ===")
        for provider, models in get_builtin_models().items():
            print(f"\n  {provider}:")
            for m in models:
                print(f"    - {m}")

        print("\n=== SERVIDORES CUSTOMIZADOS ===")
        for s in get_custom_servers():
            status = " (REMOVIDO)" if is_server_removed(s["id"]) else ""
            print(f"\n  {s['nome']} ({s['id']}){status}")
            print(f"    URL: {s['base_url']}")
            print(f"    API Key Env: {s['api_key_env']}")
            print(f"    Modelo Atual: {s.get('modelo_atual', '(nenhum)')}")
            if s.get('modelos'):
                print(f"    Modelos: {', '.join(s['modelos'])}")

        print("\n=== PREFERÊNCIAS ===")
        prefs = config.get("preferences", {})
        print(f"  Modelo Ativo Global: {prefs.get('active_model', '(nenhum)')}")
        for prov, mod in prefs.get("active_models", {}).items():
            print(f"  {prov}: {mod}")


def cmd_add_server(args):
    """Adiciona servidor customizado."""
    server = add_custom_server(
        nome=args.nome,
        base_url=args.url,
        api_key=args.key or "",
        modelo_padrao=args.modelo or "",
        api_key_env=args.key_env or "",
        modelos_iniciais=args.modelos.split(",") if args.modelos else None,
    )
    print(f"✓ Servidor '{server['nome']}' adicionado/atualizado (ID: {server['id']})")


def cmd_remove_server(args):
    """Remove servidor customizado."""
    if remove_custom_server(args.id):
        print(f"✓ Servidor '{args.id}' removido")
    else:
        print(f"✗ Servidor '{args.id}' não encontrado", file=sys.stderr)
        sys.exit(1)


def cmd_add_model(args):
    """Adiciona modelo a servidor customizado ou provedor builtin."""
    if add_model_to_server(args.server, args.modelo):
        print(f"✓ Modelo '{args.modelo}' adicionado ao servidor '{args.server}'")
    else:
        print("✗ Falha ao adicionar modelo", file=sys.stderr)
        sys.exit(1)


def cmd_remove_model(args):
    """Remove modelo de servidor customizado."""
    if remove_model_from_server(args.server, args.modelo):
        print(f"✓ Modelo '{args.modelo}' removido do servidor '{args.server}'")
    else:
        print("✗ Modelo não encontrado", file=sys.stderr)
        sys.exit(1)


def cmd_set_active(args):
    """Define modelo ativo."""
    # Formato 1 (posicional): set-active <provider> <modelo>
    # Formato 2 (flag): set-active --provider <provider> <modelo>
    provider = args.provider_flag or args.provider
    modelo = args.modelo

    # Se usou --provider flag, o primeiro positional vira o modelo
    if args.provider_flag and modelo is None:
        modelo = args.provider
        provider = args.provider_flag

    if args.server:
        ok = set_server_active_model(args.server, modelo)
        set_provider_active_model(args.server, modelo)
        save_provider_state(args.server, modelo)
        if ok:
            print(f"✓ Modelo ativo do servidor '{args.server}' = '{modelo}'")
        else:
            print("✗ Falha", file=sys.stderr)
            sys.exit(1)
    elif provider and modelo:
        set_provider_active_model(provider, modelo)
        set_server_active_model(provider, modelo)
        save_provider_state(provider, modelo)
        print(f"✓ Modelo ativo do provedor '{provider}' = '{modelo}'")
    else:
        print("Erro: forneça <provider> <modelo> ou use --provider <provider> <modelo>", file=sys.stderr)
        sys.exit(1)


def cmd_remove(args):
    """Marca servidor como removido (soft delete) ou remove modelo de servidor."""
    if hasattr(args, "modelo") and args.modelo:
        if remove_model_from_server(args.id, args.modelo):
            print(f"✓ Modelo '{args.modelo}' removido do servidor '{args.id}'")
        else:
            print("✗ Modelo não encontrado", file=sys.stderr)
            sys.exit(1)
    else:
        remove_server(args.id)
        print(f"✓ Servidor '{args.id}' marcado como removido")


def cmd_restore(args):
    """Restaura servidor removido."""
    restore_server(args.id)
    print(f"✓ Servidor '{args.id}' restaurado")


def cmd_env_set(args):
    """Define variável no .env."""
    save_env_var(args.key, args.value)
    print(f"✓ {args.key}={args.value}")


def cmd_env_get(args):
    """Lê variável do .env."""
    val = get_env_var(args.key)
    if val:
        print(val)
    else:
        print(f"✗ Variável '{args.key}' não encontrada", file=sys.stderr)
        sys.exit(1)


def cmd_env_remove(args):
    """Remove variável do .env."""
    remove_env_var(args.key)
    print(f"✓ Variável '{args.key}' removida")


def cmd_show_config(args):
    """Mostra configuração completa (JSON)."""
    config = load_config()
    print(json.dumps(config, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        prog="metis-models",
        description="Gerenciador de modelos do Metis",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="Lista modelos e servidores (opcional: provedor)")
    p.add_argument("provider", nargs="?", help="Provedor para listar modelos (ex: Gemini, Groq, NVIDIA)")
    p.set_defaults(func=cmd_list)

    # add-server
    p = sub.add_parser("add-server", help="Adiciona servidor customizado")
    p.add_argument("nome", help="Nome do servidor (ex: Meu OpenRouter)")
    p.add_argument("url", help="Base URL (ex: https://openrouter.ai/api/v1)")
    p.add_argument("--key", help="API Key (opcional, salva no .env)")
    p.add_argument("--key-env", help="Nome da variável de ambiente para a key")
    p.add_argument("--modelo", help="Modelo padrão")
    p.add_argument("--modelos", help="Lista de modelos separados por vírgula")
    p.set_defaults(func=cmd_add_server)

    # remove-server
    p = sub.add_parser("remove-server", help="Remove servidor customizado")
    p.add_argument("id", help="ID do servidor")
    p.set_defaults(func=cmd_remove_server)

    # add-model e alias add (para ZSH)
    p = sub.add_parser("add-model", help="Adiciona modelo a servidor")
    p.add_argument("server", help="ID do servidor")
    p.add_argument("modelo", help="ID do modelo")
    p.set_defaults(func=cmd_add_model)

    p_add = sub.add_parser("add", help=argparse.SUPPRESS)
    p_add.add_argument("server", help="ID do servidor ou provedor")
    p_add.add_argument("modelo", help="ID do modelo")
    p_add.set_defaults(func=cmd_add_model)

    # remove-model
    p = sub.add_parser("remove-model", help="Remove modelo de servidor")
    p.add_argument("server", help="ID do servidor")
    p.add_argument("modelo", help="ID do modelo")
    p.set_defaults(func=cmd_remove_model)

    # set-active
    p = sub.add_parser("set-active", help="Define modelo ativo")
    # Suporta ambos formatos:
    # 1. Posicional (ZSH): set-active <provider> <modelo>
    # 2. Flag: set-active --provider <provider> <modelo>
    p.add_argument("provider", nargs="?", help="Provedor (ex: NVIDIA, Groq) - positional")
    p.add_argument("modelo", nargs="?", help="ID do modelo")
    p.add_argument("--provider", dest="provider_flag", help="Provedor (ex: NVIDIA, Groq) - flag")
    p.add_argument("--server", help="ID do servidor customizado")
    p.set_defaults(func=cmd_set_active)

    # remove (soft delete servidor OU remove modelo de servidor se informado modelo)
    p = sub.add_parser("remove", help="Marca servidor como removido ou remove modelo")
    p.add_argument("id", help="ID do servidor ou provedor")
    p.add_argument("modelo", nargs="?", help="ID do modelo (opcional)")
    p.set_defaults(func=cmd_remove)

    # restore
    p = sub.add_parser("restore", help="Restaura servidor removido")
    p.add_argument("id", help="ID do servidor")
    p.set_defaults(func=cmd_restore)

    # env-set
    p = sub.add_parser("env-set", help="Define variável no .env")
    p.add_argument("key", help="Nome da variável")
    p.add_argument("value", help="Valor")
    p.set_defaults(func=cmd_env_set)

    # env-get
    p = sub.add_parser("env-get", help="Lê variável do .env")
    p.add_argument("key", help="Nome da variável")
    p.set_defaults(func=cmd_env_get)

    # env-remove
    p = sub.add_parser("env-remove", help="Remove variável do .env")
    p.add_argument("key", help="Nome da variável")
    p.set_defaults(func=cmd_env_remove)

    # api_menu (para ZSH Ctrl+G menu)
    def cmd_api_menu(args):
        """Lista provedores de API para menu FZF do ZSH."""
        from agente.models import (
            get_provider_active_model,
            get_custom_servers,
            get_server_models,
            is_server_removed,
        )

        icons = {
            "gemini": "✨",
            "groq": "🚀",
            "nvidia": "🟢",
            "openrouter": "🪐",
            "openai": "⚡",
            "claude": "🎭",
            "anthropic": "🎭",
            "mistral": "🌪️",
            "deepseek": "🐋",
        }

        # Ordem de exibição priorizando servidores mais usados
        priority_map = {
            "groq": 1,
            "nvidia": 2,
            "openrouter": 3,
        }

        custom_servers = get_custom_servers()
        # Filtra servidores customizados removidos
        valid_custom = [
            s for s in custom_servers
            if s.get("id") and not is_server_removed(s["id"])
        ]
        # Ordena: conhecidos primeiro, depois por nome
        valid_custom.sort(key=lambda s: (priority_map.get(s["id"].lower(), 100), s.get("nome", "").lower()))

        seen = set()
        idx = 1

        for srv in valid_custom:
            srv_id = srv.get("id", "").strip().lower()
            seen.add(srv_id)

            srv_nome = srv.get("nome", srv_id)
            if srv_id == "nvidia":
                srv_nome = "NVIDIA"
            elif srv_id == "groq":
                srv_nome = "Groq"
            elif srv_id == "openrouter":
                srv_nome = "OpenRouter"

            model = srv.get("modelo_atual") or get_provider_active_model(srv_id)
            if not model:
                models = get_server_models(srv_id)
                if models:
                    model = models[0]

            icon = "🌐"
            for k, ic in icons.items():
                if k in srv_id or k in srv_nome.lower():
                    icon = ic
                    break

            display = f"{icon} {idx}. {srv_nome} ({model})" if model else f"{icon} {idx}. {srv_nome}"
            print(f"{display}|{srv_id}|{model}")
            idx += 1

        # Provedores builtin que NÃO estão em custom_servers e NÃO estão em removed_servers
        builtin_providers = [
            ("Groq", "groq"),
            ("NVIDIA", "nvidia"),
            ("Gemini", "gemini"),
        ]
        for name, key in builtin_providers:
            key_lower = key.strip().lower()
            if key_lower in seen or is_server_removed(key_lower):
                continue
            seen.add(key_lower)

            model = get_provider_active_model(key_lower)
            if not model:
                models = get_server_models(key_lower)
                if models:
                    model = models[0]

            icon = icons.get(key_lower, "✨")
            display = f"{icon} {idx}. {name} ({model})" if model else f"{icon} {idx}. {name}"
            print(f"{display}|{key_lower}|{model}")
            idx += 1

    sub.add_parser("api_menu", help="Lista provedores para menu FZF (formato: Display|ID|Model)").set_defaults(func=cmd_api_menu)

    # show-config
    sub.add_parser("show-config", help="Mostra config completo (JSON)").set_defaults(func=cmd_show_config)

    # get_active (para ZSH ler modelo ativo do provedor)
    def cmd_get_active(args):
        """Retorna modelo ativo do provedor."""
        model = get_provider_active_model(args.provider)
        if model:
            print(model)

    p = sub.add_parser("get_active", help="Retorna modelo ativo do provedor (para ZSH)")
    p.add_argument("provider", help="Provedor (ex: NVIDIA, Groq, OpenRouter, etc.)")
    p.set_defaults(func=cmd_get_active)

    # sync (sincronização real com o terminal ZSH e arquivos canônicos)
    def cmd_sync(args):
        """Sincroniza estado do Metis com o terminal ZSH e arquivos canônicos."""
        from agente.models import CONFIG_FILE

        config = load_config()
        prefs = config.get("preferences", {})
        active_models = prefs.get("active_models", {})

        print("\033[1;36m🏛️ Sincronizando Metis com o Terminal ZSH...\033[0m\n")

        # 1. Determina o provedor e modelo ativos atuais no Metis
        last_provider = (
            prefs.get("last_active_provider")
            or config.get("active_provider")
            or get_env_var("DEFAULT_PROVIDER")
            or "nvidia"
        )
        norm_provider = str(last_provider).strip().lower()
        if norm_provider.startswith("custom:"):
            clean_provider = norm_provider[len("custom:"):]
        else:
            clean_provider = norm_provider

        # Se o provedor ativo estiver removido, faz fallback para um ativo válido
        if is_server_removed(clean_provider):
            for candidate in ["nvidia", "groq", "openrouter", "ollama", "g4f"]:
                if not is_server_removed(candidate):
                    clean_provider = candidate
                    break

        # Modelo ativo para este provedor
        active_model = (
            prefs.get("last_active_model")
            or get_provider_active_model(clean_provider)
            or active_models.get(clean_provider, "")
        )
        if not active_model:
            for s in get_custom_servers():
                if s.get("id", "").lower() == clean_provider:
                    active_model = s.get("modelo_atual") or (s.get("modelos", [""])[0] if s.get("modelos") else "")
                    break

        # 2. Salva estado do provedor canônico (.fix_ia_selected, .last_provider, .env)
        save_provider_state(clean_provider, active_model)

        # 3. Sincroniza modelos de todos os servidores ativos para as variáveis de ambiente no .env
        env_synced = []
        for srv in get_custom_servers():
            srv_id = srv.get("id", "").strip().lower()
            if is_server_removed(srv_id):
                continue
            srv_model = srv.get("modelo_atual") or get_provider_active_model(srv_id)
            if srv_model:
                env_key = f"{srv_id.upper()}_MODEL"
                save_env_var(env_key, srv_model)
                env_synced.append(f"{env_key}={srv_model}")

        # Builtin modelos (Ollama, G4F)
        for b_key in ["ollama", "g4f"]:
            if not is_server_removed(b_key):
                b_model = active_models.get(b_key) or get_provider_active_model(b_key)
                if b_model:
                    env_key = f"{b_key.upper()}_MODEL"
                    save_env_var(env_key, b_model)
                    env_synced.append(f"{env_key}={b_model}")

        # 4. Sincroniza cópia local /home/reator/Metis/config_models.json se existir
        metis_repo_config = metis_root / "config_models.json"
        if metis_repo_config.exists() and CONFIG_FILE.exists():
            try:
                content = CONFIG_FILE.read_text(encoding="utf-8")
                metis_repo_config.write_text(content, encoding="utf-8")
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

        # 5. Exibe resumo amigável ao usuário
        prov_display = clean_provider.upper() if clean_provider in ("nvidia", "g4f") else clean_provider.title()
        print(f"\033[1;32m✓ Provedor Ativo:\033[0m {prov_display} \033[90m({active_model})\033[0m")
        print("\033[1;33m✓ Modelos Sincronizados no .env:\033[0m")
        for item in env_synced:
            k, v = item.split("=", 1)
            print(f"  • {k} = \033[1;37m{v}\033[0m")

        removed = get_removed_servers()
        if removed:
            print(f"\033[90m✓ Servidores excluídos mantidos fora: {', '.join(removed)}\033[0m")

        print("\033[1;32m✓ Arquivos ~/.config/metis/.fix_ia_selected e ~/.ZSH/ai/.fix_ia_selected atualizados!\033[0m")
        print("\033[1;32m✓ Sincronização concluída com sucesso!\033[0m")

    sub.add_parser("sync", help="Sincroniza configurações e estado do Metis para o terminal").set_defaults(func=cmd_sync)

    # Alias compatibilidade: set_active (com underscore) para ZSH
    p_alias = sub.add_parser("set_active", help=argparse.SUPPRESS)
    p_alias.add_argument("provider", nargs="?", help="Provedor (ex: NVIDIA, Groq) - positional")
    p_alias.add_argument("modelo", nargs="?", help="ID do modelo")
    p_alias.add_argument("--provider", dest="provider_flag", help="Provedor (ex: NVIDIA, Groq) - flag")
    p_alias.add_argument("--server", help="ID do servidor customizado")
    p_alias.set_defaults(func=cmd_set_active)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
