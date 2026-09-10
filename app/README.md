# Metis - Agente de IA com Busca Web Nativa

Projeto modular em Python de um Agente de IA (Metis) capaz de consultar a web nativamente (DuckDuckGo com privacidade por padrão ou SearXNG opcional), conversar via Ollama local e conectar-se às APIs Gemini, Groq, NVIDIA, OpenRouter e g4f. Tudo gerenciado com uma interface interativa em terminal (CLI) ou interface gráfica (GUI) com sistema de persistência inteligente de histórico.

## Funcionalidades

- Chat contínuo com persistência JSON à prova de falhas.
- **Busca Web Nativa sem Docker**: Pesquisa em tempo real com DuckDuckGo (rápido, privado, zero containers).
- Detecção automática de intenção de busca web (para notícias, cotações, novidades).
- Modos múltiplos: Ollama local, Gemini, Groq, NVIDIA, OpenRouter, g4f (experimental) e busca web direta.
- Gerenciamento detalhado de histórico (truncamento e exclusão de turnos).
- Integração resiliente, não quebra se algum serviço cair.

## Estrutura do Projeto

- `app.py`: Ponto de entrada no terminal (CLI).
- `gui.py`: Ponto de entrada gráfico (GUI).
- `agente/`: Lógica central do agente (UI, Sessões, Histórico, Configurações, Serviços).

## Como Rodar Localmente (100% Livre de Docker)

1. Instale as dependências: `pip install -r requirements.txt`
2. Copie `.env.example` para `.env` e configure suas chaves/modelos desejados.
3. Se for usar modelos locais, tenha o Ollama rodando localmente (porta 11434).
4. Inicie o app: `python app.py` ou `python gui.py`

## Uso via CLI

- `python app.py` (Abre o menu interativo)
- `python app.py "qual o clima hoje?"` (Pergunta rápida automática)
- `python app.py --web "quem ganhou a copa"` (Pergunta rápida com busca web forçada)
- `python app.py --help` (Exibe ajuda)
