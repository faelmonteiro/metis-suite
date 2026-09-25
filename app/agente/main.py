import sys
from agente import config
from agente.menu import iniciar_menu
from agente.history import HistoryManager
from agente.sessions import chat_session
from agente.services.base import BaseService
from agente.ui.help import exibir_ajuda

def obter_servico_padrao() -> BaseService:
    from pathlib import Path
    import os
    from agente.providers_manager import (
        obter_preferencia,
        obter_servidores_customizados,
        carregar_dados,
        obter_modelos_provedor,
    )
    from agente.services.gemini_service import GeminiService
    from agente.services.groq_service import GroqService
    from agente.services.nvidia_service import NvidiaService
    from agente.services.g4f_service import G4FService
    from agente.services.custom_openai_service import CustomOpenAIService
    from agente.services.ollama_service import OllamaService

    dados = carregar_dados()

    # 1. Estado salvo no arquivo de terminal ZSH/Bash (.last_provider)
    metis_cfg_dir = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis"))
    last_prov_file = metis_cfg_dir / ".last_provider"
    prov_file = ""
    if last_prov_file.exists():
        try:
            raw_last = last_prov_file.read_text(encoding="utf-8").strip()
            num_to_prov = {
                "1": "ollama",
                "2": "g4f",
                "3": "gemini",
                "4": "groq",
                "5": "nvidia",
                "6": "openrouter",
            }
            prov_file = num_to_prov.get(raw_last, raw_last.lower())
        except Exception:
            pass

    prov_pref = (obter_preferencia("last_active_provider", "") or "").strip().lower()
    prov_active = (dados.get("active_provider", "") or "").strip().lower()
    prov_env = (getattr(config, "DEFAULT_PROVIDER", "") or "").strip().lower()

    # Candidatos a provedor em ordem de prioridade
    candidatos_prov = [p for p in [prov_file, prov_pref, prov_active, prov_env] if p]

    model_pref = (obter_preferencia("last_active_model", "") or dados.get("active_model", "") or "").strip()

    def instanciar(p: str):
        p = p.lower()
        if p == "gemini" and getattr(config, "GEMINI_API_KEY", ""):
            gem_m = model_pref if ("gemini" in model_pref.lower()) else getattr(config, "GEMINI_MODEL", "gemini-2.0-flash")
            return GeminiService(model=gem_m)
        elif p == "groq" and getattr(config, "GROQ_API_KEY", ""):
            groq_m = ""
            if dados.get("active_provider") == "groq" and dados.get("active_model"):
                groq_m = dados.get("active_model")
            elif model_pref and any(k in model_pref.lower() for k in ["qwen", "llama", "mixtral", "compound", "oss"]):
                groq_m = model_pref
            if not groq_m or "gemini" in groq_m.lower():
                groq_m = "llama-3.3-70b-versatile"
            return GroqService(model=groq_m)
        elif p == "nvidia" and getattr(config, "NVIDIA_API_KEY", ""):
            nvd_m = model_pref if any(k in model_pref.lower() for k in ["meta/", "nvidia/"]) else getattr(config, "NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
            return NvidiaService(model=nvd_m)
        elif p == "g4f":
            g4f_m = model_pref if any(k in model_pref.lower() for k in ["gpt", "claude", "deepseek", "qwen"]) else getattr(config, "G4F_MODEL", "gpt-4o-mini")
            return G4FService(model=g4f_m)
        elif p == "ollama":
            oll_m = model_pref if (model_pref and not any(k in model_pref.lower() for k in ["gemini", "gpt", "claude", "70b"])) else getattr(config, "OLLAMA_MODEL", "llama3.2:3b")
            return OllamaService(model=oll_m)
        else:
            for s in obter_servidores_customizados():
                if s.get("id") == p or s.get("nome", "").lower() == p or f"custom:{s.get('id')}" == p:
                    s_copy = dict(s)
                    if model_pref and not any(k in model_pref.lower() for k in ["gemini", "llama"]):
                        s_copy["modelo_atual"] = model_pref
                    return CustomOpenAIService(s_copy)
        return None

    # Tenta cada candidato na ordem
    for c_prov in candidatos_prov:
        srv = instanciar(c_prov)
        if srv:
            return srv

    # Fallbacks se nenhum candidato pôde ser instanciado
    if getattr(config, "GROQ_API_KEY", ""):
        return GroqService(model="llama-3.3-70b-versatile")
    if getattr(config, "GEMINI_API_KEY", ""):
        return GeminiService(model=getattr(config, "GEMINI_MODEL", "gemini-2.0-flash"))
    if getattr(config, "NVIDIA_API_KEY", ""):
        return NvidiaService(model=getattr(config, "NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct"))
    if getattr(config, "OPENROUTER_API_KEY", ""):
        for s in obter_servidores_customizados():
            if s.get("id") == "openrouter":
                return CustomOpenAIService(s)

    return G4FService(model=getattr(config, "G4F_MODEL", "gpt-4o-mini"))

def main():
    from agente.completer import configurar_readline
    configurar_readline()
    args = sys.argv[1:]
    
    if not args:
        iniciar_menu()
    else:
        from datetime import datetime
        nome_sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        hm = HistoryManager(nome_sessao)
        if args[0] == "--gui":
            from agente.ui.gui_app import main as gui_main
            gui_main()
            return
        elif args[0] == "--web":
            if len(args) > 1:
                pergunta = " ".join(args[1:])
                chat_session.processar_pergunta(pergunta, hm, obter_servico_padrao(), forcar_web=True, iterativo=True)
            else:
                print("Erro: --web requer uma pergunta. Ex: python app.py --web Qual a capital do Brasil?")
                sys.exit(1)
        elif args[0] in ["--help", "-h"]:
            exibir_ajuda()
        else:
            pergunta = " ".join(args)
            chat_session.processar_pergunta(pergunta, hm, obter_servico_padrao(), forcar_web=False, iterativo=True)
