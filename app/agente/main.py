import sys
from agente import config
from agente.menu import iniciar_menu
from agente.history import HistoryManager
from agente.sessions import chat_session
from agente.services.base import BaseService
from agente.ui.help import exibir_ajuda

def obter_servico_padrao() -> BaseService:
    from agente.providers_manager import obter_preferencia
    prov_pref = (obter_preferencia("last_active_provider", "") or "").strip().lower()
    prov_env = (getattr(config, "DEFAULT_PROVIDER", "") or "").strip().lower()
    prov = prov_pref or prov_env or "ollama"
    model_pref = (obter_preferencia("last_active_model", "") or "").strip()

    if prov == "gemini" and getattr(config, "GEMINI_API_KEY", ""):
        from agente.services.gemini_service import GeminiService
        return GeminiService(model=model_pref or getattr(config, "GEMINI_MODEL", None))
    elif prov == "groq" and getattr(config, "GROQ_API_KEY", ""):
        from agente.services.groq_service import GroqService
        return GroqService(model=model_pref or getattr(config, "GROQ_MODEL", None))
    elif prov == "nvidia" and getattr(config, "NVIDIA_API_KEY", ""):
        from agente.services.nvidia_service import NvidiaService
        return NvidiaService(model=model_pref or getattr(config, "NVIDIA_MODEL", None))
    elif prov == "g4f":
        from agente.services.g4f_service import G4FService
        return G4FService()
    else:
        from agente.providers_manager import obter_servidores_customizados
        for s in obter_servidores_customizados():
            if s.get("id") == prov or s.get("nome", "").lower() == prov or f"custom:{s.get('id')}" == prov:
                from agente.services.custom_openai_service import CustomOpenAIService
                s_copy = dict(s)
                if model_pref:
                    s_copy["modelo_atual"] = model_pref
                return CustomOpenAIService(s_copy)
        from agente.services.ollama_service import OllamaService
        return OllamaService(model=model_pref or getattr(config, "OLLAMA_MODEL", None))

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
