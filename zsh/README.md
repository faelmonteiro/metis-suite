# 🧠 Suíte de Inteligência Artificial para Terminal ZSH

Motor central e ferramentas integradas de IA para o terminal ZSH, compatível com Ollama (Local), Google Gemini, Groq, NVIDIA NIM, OpenRouter e G4F (Web).

---

## ⚡ Atalhos e Comandos Principais

| Atalho / Comando | Arquivo | Descrição |
| :--- | :--- | :--- |
| **`Ctrl + G`** | [`fix.zsh`](fix.zsh) | Menu interativo FZF: Comando Direto, Me Ensinar (chat didático, salvar notas `/nota`) e Gerenciador de Modelos. |
| **`metis [-p N] [-n L]`** | [`metis.zsh`](metis.zsh) | Copiloto autônomo para diagnóstico e resolução de erros com chamadas `<tool_call>` (ex: `metis -p 10` para 10 passos). |
| **`explain` / `explain_screen [-p N]`** | [`explain_screen.zsh`](explain_screen.zsh) | Assistente com captura de tela do Kitty, chat contínuo e modo `/auto` (suporta flag `-p`). |
| **`ia <prompt>`** | [`ia.zsh`](ia.zsh) | Consulta direta ou via pipe (ex: `cat log.txt \| ia 'o que quebrou?'`) com caixas coloridas. |
| **`aiman <cmd>`** | [`aiman.zsh`](aiman.zsh) | Manpage interativa expressa com exemplos práticos. |
| **`Ctrl + X Ctrl + P`** | [`autocomplete.zsh`](autocomplete.zsh) | Sugestão e autocompletar inline no prompt ZLE. |
| **`gca`** | [`git-ai.zsh`](git-ai.zsh) | Gerador automático de mensagens de commit no padrão Conventional Commits. |
| **`Alt + H` / `iah`** | [`history_split.zsh`](history_split.zsh) | Busca FZF no histórico exclusivo de prompts de IA (`~/.zsh_ai_history`). |
| **`repos` / `downloads`** | [`history_split.zsh`](history_split.zsh) | Registro histórico de downloads web e `git clone`. |
| **`ai-sync`** | [`manage_models.py`](manage_models.py) | Sincroniza modelos e chaves com o `Metis`. |

---

## ⚙️ Configuração de Variáveis de Ambiente

As configurações locais ficam salvas em [`~/.ZSH/ai/.env_local`](.env_local) (permissão `600`):

```bash
# Chaves de API
GEMINI_API_KEY="sua_chave"
GROQ_API_KEY="sua_chave"
NVIDIA_API_KEY="sua_chave"
OPENROUTER_API_KEY="sua_chave"

# Modelos Ativos
GEMINI_MODEL="gemini-2.0-flash"
GROQ_MODEL="llama-3.3-70b-versatile"
NVIDIA_MODEL="meta/llama-3.1-70b-instruct"
OPENROUTER_MODEL="openrouter/free"
OLLAMA_MODEL="qwen2.5-coder:7b"
G4F_MODEL="gpt-4o"
```

---

## 🧪 Testes

Para validar a integridade dos parsers e integrações:

```bash
python3 ~/.ZSH/ai/test_suite.py
```
