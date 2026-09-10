# 🧠 Metis & ZSH AI Suite

> **Copiloto Autônomo de Terminal, Agente de IA e Ferramentas Inteligentes para Linux e ZSH.**

O **Metis AI Suite** integra modelos de inteligência artificial de ponta (Google Gemini, Groq, NVIDIA NIM, OpenRouter, Ollama local e G4F) diretamente ao fluxo de trabalho do seu terminal ZSH e sistema Linux.

---

## ⚡ Atalhos e Comandos Principais

| Atalho / Comando | Descrição |
| :--- | :--- |
| **`Ctrl + G`** | **Menu Interativo FZF**: Execução rápida de comandos gerados por IA, modo didático (ensino e notas `/nota`) e gerenciador dinâmico de modelos. |
| **`Ctrl + Shift + E`** | **Explain Screen**: Captura a tela atual do terminal e abre o assistente inteligente para analisar saídas, logs e erros na hora. |
| **`Alt + H`** ou **`iah`** | **Histórico de Prompts de IA**: Busca rápida via FZF em todas as suas consultas anteriores de IA. |
| **`Ctrl + X Ctrl + P`** | **Autocomplete Inline**: Sugestão de comandos com IA diretamente na linha de comando do ZSH. |
| **`metis`** | **Copiloto Autônomo**: Diagnóstico e resolução inteligente de erros do terminal com execução de ferramentas. |
| **`metis gui`** | **Interface Visual**: Abre a aplicação gráfica do Metis. |
| **`ia <pergunta>`** | **Consulta Rápida**: Resposta direta no terminal com suporte a pipes (ex: `cat erro.log | ia 'o que quebrou?'`). |
| **`aiman <comando>`** | **Manpage Express**: Manual interativo com explicações e exemplos práticos gerados por IA. |
| **`gca`** | **Git AI Commit**: Gera mensagens de commit automaticamente no padrão *Conventional Commits*. |

---

## 🚀 Instalação Rápida (1 Linha de Comando)

Você pode instalar o Metis em qualquer distribuição Linux executando:

```bash
# Clone o repositório e execute o instalador:
git clone https://github.com/faelmonteiro/metis-suite.git ~/.metis-suite
cd ~/.metis-suite && ./install.sh
```

*(Ou via comando direto se hospedado online):*
```bash
curl -fsSL https://raw.githubusercontent.com/faelmonteiro/metis-suite/main/install.sh | bash
```

### O que o instalador faz automaticamente:
- ✅ Detecta sua distribuição (`apt`, `dnf`, `pacman`, `zypper`, etc.) e instala ferramentas necessárias.
- ✅ Cria um ambiente virtual Python isolado (`venv`), sem afetar os pacotes do seu sistema.
- ✅ Inicializa arquivos de configuração **100% limpos e zerados** em `~/.config/metis/`.
- ✅ Integra os atalhos e widgets diretamente ao seu `~/.zshrc`.
- ✅ Cria o comando executável `metis` no seu `PATH` e cria o atalho no menu de aplicativos do Linux.

---

## ⚙️ Configuração de Chaves de API

As suas configurações e chaves ficam guardadas com segurança em `~/.config/metis/.env`:

```bash
# Edite o arquivo de configuração:
nano ~/.config/metis/.env
```

Preencha apenas as chaves dos serviços que você desejar usar:
```bash
GEMINI_API_KEY="sua_chave_gemini_aqui"
GROQ_API_KEY="sua_chave_groq_aqui"
NVIDIA_API_KEY="sua_chave_nvidia_aqui"
OPENROUTER_API_KEY="sua_chave_openrouter_aqui"
```

> 💡 **Dica:** Você também pode cadastrar, remover e alternar modelos a qualquer momento pressionando **`Ctrl + G`** no terminal!

---

## 🔄 Atualização

Para atualizar o Metis mantendo todas as suas chaves e preferências intactas:

```bash
metis update
# ou
~/.local/share/metis/update.sh
```

---

## 🗑️ Desinstalação

Para remover o Metis e limpar o seu `~/.zshrc`:

```bash
metis uninstall
# ou
~/.local/share/metis/uninstall.sh
```

---

## 📄 Licença

Distribuído sob a licença MIT. Sinta-se livre para usar, modificar e distribuir.
