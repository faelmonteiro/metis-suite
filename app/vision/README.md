# 🚀 ScreenAI • Assistente Visual & de Contexto com IA

Assistente inteligente e multimodal para Linux (Wayland / Hyprland e X11). Ao acionar um atalho de teclado ou comando no terminal, ele captura a janela atual, tela ou pasta/arquivo selecionado e abre uma interface flutuante moderna para responder perguntas, resumir conteúdos, traduzir ou diagnosticar erros instantaneamente.

---

## ✨ Recursos

* **📸 Captura Visual Ultrarrápida em Memória:** Suporte nativo a Wayland (`grim` / `slurp` / `hyprctl`) e X11.
* **📁 Varredura Inteligente de Pastas e Arquivos:** Passe o caminho de qualquer pasta ou arquivo para analisar árvores de diretório e conteúdos locais.
* **🧠 Múltiplos Motores de IA com Streaming:**
  * **NVIDIA NIM** (`meta/llama-3.2-11b-vision-instruct` / `90b`)
  * **Google Gemini** (`gemini-2.0-flash` / `gemini-1.5-flash`)
  * **OpenRouter** (qualquer modelo multimodal)
  * **Ollama Local** (`llama3.2-vision`, `minicpm-v`, `qwen2-vl`)
* **🎨 Interface Flutuante Elegante (PyQt6):**
  * Estilo *Raycast/Spotlight* com tema escuro moderno.
  * Botões de ação rápida: `[⚡ Resumo Geral]`, `[🐛 Explicar Erro]`, `[🌐 Traduzir]`, `[📋 Extrair Texto]`, `[🎯 Recortar Área]`, `[❓ Ajuda]`.
  * Visualizador de Markdown em tempo real com realce de sintaxe.
  * Botão de cópia rápida para o clipboard e tecla `Esc` para fechar.

---

## ⌨️ Atalhos do Teclado (Hyprland)

| Atalho | Ação |
| :--- | :--- |
| **`Alt + Z`** | 🪟 Captura **apenas a Janela Atual** |
| **`Alt + Shift + Z`** | 🎯 Seleciona uma **Área Retangular** com o mouse |
| **`Alt + Ctrl + Z`** | 🖥️ Captura a **Tela Inteira** |

---

## 💻 Como Usar pelo Terminal

Como o comando `screenai` está instalado globalmente, você pode executá-lo em qualquer diretório:

```bash
# 1. Abre a interface com a janela atual
screenai

# 2. Analisa a pasta atual
screenai .

# 3. Analisa qualquer pasta do sistema
screenai ~/Downloads
screenai ~/Projetos/meu-app

# 4. Analisa e resume um arquivo de código ou texto
screenai config.py
screenai main.py --action explicar

# 5. Modo silencioso no terminal (sem janela gráfica)
screenai ~/Downloads --headless --action resumo
```
