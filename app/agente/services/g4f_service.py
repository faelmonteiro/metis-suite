from agente import config
from agente.services.base import BaseService

MODELOS_DISPONIVEIS = {
    "1": ("gpt-4o-mini", "GPT-4o Mini (OpenAI Nuvem Gratuita)"),
    "2": ("gpt-4o", "GPT-4o Completo (OpenAI Nuvem Gratuita)")
}


def gerar_resposta(mensagens: list, model: str = None) -> str:
    if not model:
        model = getattr(config, "G4F_MODEL", "gpt-4o-mini") or "gpt-4o-mini"

    try:
        from g4f.client import Client
    except ImportError:
        raise RuntimeError(
            "Pacote g4f não instalado ou incompatível. "
            "Se quiser usar este modo, instale com: pip install -U g4f"
        )

    # Limpeza e sanitização de mensagens para compatibilidade com o g4f
    clean_messages = []
    for m in mensagens:
        role = m.get("role", "user")
        if role in ["system", "user", "assistant"]:
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                content = " ".join(text_parts)
            clean_messages.append({"role": role, "content": str(content)})

    try:
        client = Client()
        max_toks = getattr(config, "MAX_OUTPUT_TOKENS", 4096)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=clean_messages,
                max_tokens=max_toks
            )
        except TypeError:
            response = client.chat.completions.create(
                model=model,
                messages=clean_messages
            )

        if hasattr(response, "choices") and response.choices:
            message = getattr(response.choices[0], "message", None)
            conteudo = getattr(message, "content", None)

            if conteudo:
                return str(conteudo)

        return "[Sem resposta]"

    except Exception as e:
        raise RuntimeError(f"Erro no provedor g4f ({model}): {e}")

class G4FService(BaseService):
    def __init__(self, model: str = None):
        self.model = model or getattr(config, "G4F_MODEL", "gpt-4o-mini") or "gpt-4o-mini"

    @property
    def nome_provedor(self) -> str:
        return f"G4F ({self.model})"

    def gerar_resposta_stream(self, mensagens: list):
        # G4F currently doesn't stream well, so we yield the full response
        yield gerar_resposta(mensagens, self.model)
