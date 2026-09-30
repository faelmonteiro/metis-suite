#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import api_ask
import g4f_ask
import manage_models

# manage_models.py é um delegador para agente.models.cli e, no import, coloca a
# raiz do Metis no sys.path (é ele que o .zshrc e o loader invocam). Os módulos
# da suíte do agente são importados aqui, depois dele, por causa disso.
from agente.models import builtin
from agente.models import cli

def test_suite():
    print("🧪 Executando Testes da Suíte ZSH AI...")
    
    # 1. Teste de parsing de mensagens com tags
    prompt = "[Sistema]: Você é um assistente.\n[Usuário]: Olá\n[Assistente]: Como posso ajudar?\n[Usuário]: Teste"
    msgs_api = api_ask.parse_messages(prompt)
    msgs_g4f = g4f_ask.parse_messages(prompt)
    assert len(msgs_api) == 4, "Falha no parse_messages do api_ask"
    assert len(msgs_g4f) == 4, "Falha no parse_messages do g4f_ask"
    assert msgs_api[0]["role"] == "system"
    assert msgs_g4f[0]["role"] == "system"
    print("  ✓ parse_messages() [api_ask e g4f_ask] OK")

    # 2. Teste do payload Gemini
    gemini_req = api_ask.format_gemini_request(msgs_api)
    assert "system_instruction" in gemini_req
    assert gemini_req["system_instruction"]["parts"][0]["text"] == "Você é um assistente."
    assert len(gemini_req["contents"]) == 3
    print("  ✓ format_gemini_request() [system_instruction] OK")

    # 3. Teste de balanceamento JSON / Tool extraction
    raw = '{"name": "bash", "arguments": {"cmd": "uptime"'
    t = api_ask.extract_tool_from_json(raw)
    assert '<tool_call name="bash">' in t and "uptime" in t
    print("  ✓ extract_tool_from_json() [JSON balancer] OK")

    # 4. Teste de chaves de provedor
    # O get_provider_key() que este teste usava foi removido quando
    # manage_models.py virou delegador para agente.models.cli. A tabela de nomes
    # canônicos foi para agente/models/builtin.py, consumida por
    # vision/model_manager.py.
    canon = builtin._canonical_provider_name
    assert canon("gemini") == "Gemini", "Falha no nome canônico de gemini"
    assert canon("GROQ") == "Groq", "Falha no nome canônico de GROQ"
    assert canon("nvidia") == "NVIDIA", "Falha no nome canônico de nvidia"
    assert canon("OpenRouter") == "OpenRouter", "Falha no nome canônico de OpenRouter"
    print("  ✓ _canonical_provider_name() [agente.models.builtin] OK")

    # 5. O delegador tem que continuar expondo o main, que é o que o alias
    # ai-sync e o .zshrc executam.
    assert callable(manage_models.main), "manage_models.main deveria ser chamável"
    assert callable(cli.main), "agente.models.cli.main deveria ser chamável"
    print("  ✓ delegador manage_models -> agente.models.cli OK")

    # 5. Teste de formatação de tool calls limpas sem CDATA
    tool_formatted = api_ask.format_tool_call_xml("bash", {"cmd": "ip -4 addr show"})
    assert "<![CDATA[" not in tool_formatted and "ip -4 addr show" in tool_formatted
    # 6. Teste de mesclagem de roles consecutivas para Gemini (evita erro 400)
    consecutive_msgs = [
        {"role": "user", "content": "Primeira parte"},
        {"role": "user", "content": "Segunda parte"}
    ]
    gemini_merged = api_ask.format_gemini_request(consecutive_msgs)
    assert len(gemini_req["contents"]) >= 1
    assert len(gemini_merged["contents"]) == 1, "Roles consecutivas de user devem ser mescladas em um único turn"
    assert len(gemini_merged["contents"][0]["parts"]) == 2
    print("  ✓ format_gemini_request() [Mesclagem de roles consecutivas] OK")

    # 7. Teste de format_tool_call_xml com lista para ferramentas não-bash
    list_tool = api_ask.format_tool_call_xml("read_file", ["/etc/hosts"])
    assert '<tool_call name="read_file"' in list_tool and "/etc/hosts" in list_tool
    print("  ✓ format_tool_call_xml() [Tool call com lista preservando nome] OK")

    print("\n🎉 Todos os testes unitários passaram com sucesso!")

if __name__ == "__main__":
    test_suite()
