import sys
import signal
import socket
import re

# Garante encerramento imediato em SIGINT e SIGTERM
signal.signal(signal.SIGINT, lambda s, f: sys.exit(130))
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(130))

# Prioriza IPv4 para evitar hang de DNS/IPv6 nos provedores Web do G4F
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        res = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        if res:
            return res
    except Exception:
        pass
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

try:
    from g4f.client import Client
except ImportError:
    print("g4f não instalado. Rode: pip install -U g4f", file=sys.stderr)
    sys.exit(1)

TAG_SEARCH_RE = re.compile(
    r'\[(?:Assistente|Usuário|Sistema|Instruções|Instrução do Agente)\]:'
)

TAG_SPLIT_RE = re.compile(
    r'(\[(?:Assistente|Usuário|Sistema|Instruções|Instrução do Agente)\]:)'
)

def parse_messages(prompt: str):
    prompt = prompt or ""

    if not TAG_SEARCH_RE.search(prompt):
        return [{"role": "user", "content": prompt.strip()}]

    messages = []
    parts = TAG_SPLIT_RE.split(prompt)

    initial_text = parts[0].strip()
    if initial_text:
        messages.append({"role": "user", "content": initial_text})

    for i in range(1, len(parts), 2):
        tag = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""

        if not content:
            continue

        if "Assistente" in tag:
            role = "assistant"
        elif "Sistema" in tag or "Instruç" in tag:
            role = "system"
        else:
            role = "user"

        messages.append({"role": role, "content": content})

    if not messages:
        return [{"role": "user", "content": prompt.strip()}]

    if not any(m["role"] == "user" for m in messages):
        messages.append({"role": "user", "content": "Execute as instruções acima."})

    return messages

def main():
    if len(sys.argv) < 2:
        print("Uso: python g4f_ask.py <modelo> [prompt ou stdin]", file=sys.stderr)
        sys.exit(1)

    modelo = sys.argv[1]
    if len(sys.argv) >= 3:
        prompt = " ".join(sys.argv[2:]).strip()
    else:
        prompt = sys.stdin.read().strip()

    try:
        messages = parse_messages(prompt)
        client = Client()
        response = None

        # 1. Tenta o modelo solicitado
        try:
            response = client.chat.completions.create(
                model=modelo,
                messages=messages
            )
        except Exception:
            # 2. Se falhar, tenta modelos gratuitos conhecidos por estabilidade (priorizando gpt-4o e gpt-4o-mini)
            fallbacks = ["gpt-4o-mini", "gpt-4o", "llama-3.3-70b", "llama-3.1-70b", "deepseek-r1"]
            for fb in fallbacks:
                if fb == modelo:
                    continue
                try:
                    response = client.chat.completions.create(
                        model=fb,
                        messages=messages
                    )
                    if hasattr(response, "choices") and response.choices:
                        break
                except Exception:
                    continue

        if response and hasattr(response, "choices") and response.choices:
            message = getattr(response.choices[0], "message", None)
            conteudo = getattr(message, "content", None)
            if conteudo:
                print(conteudo)
                sys.exit(0)

        print("[Sem resposta]", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        err_str = str(e)
        if "executable not found" in err_str or "Chrome" in err_str or "RetryProvider" in err_str:
            print("⚠️ Provedores Web gratuitos do G4F indisponíveis no momento para este modelo.", file=sys.stderr)
            print("💡 Dica: instale o Chromium ('sudo apt install chromium-browser') ou selecione Groq/Gemini/Ollama em [Ctrl + G].", file=sys.stderr)
        else:
            print(f"⚠️ Erro no provedor G4F ({modelo}): {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
