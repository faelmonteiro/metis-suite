#!/usr/bin/env zsh
# =============================================================================
# fix/02-models-menu.zsh
# Menus de seleção de modelos e integração com o gerenciador de IA.
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/models_menu.zsh" 2>/dev/null || true

_ai_fix_digitar_novo_modelo() {
  _ai_menu_digitar_novo_modelo "$@"
}

_ai_fix_remover_modelo_salvo() {
  _ai_menu_remover_modelo_salvo "$@"
}

_ai_fix_lista_selecao_e_digitacao() {
  _ai_menu_selecionar_modelo "$@"
}

_ai_fix_lista_selecao_e_digitacao_ollama() {
  _ai_menu_selecionar_modelo_ollama "$@"
}

_ai_fix_remover_servidor_customizado() {
  _ai_menu_remover_servidor_customizado "$@"
}

_ai_fix_get_active_ia_label() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  if (( $+functions[_ai_get_current_provider_info] )); then
    _ai_get_current_provider_info
    print -r -- "${AI_ACTIVE_LABEL:-Ollama Local (${OLLAMA_MODEL:-qwen2.5-coder:7b})}"
    return 0
  fi

  _ai_fix_reload_envs

  local conf_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
  local raw_conf="$(cat "$conf_file" 2>/dev/null)"

  if [[ "$raw_conf" == *"Groq"* ]]; then
    print -r -- "Groq (${GROQ_MODEL:-openai/gpt-oss-120b})"
  elif [[ "$raw_conf" == *"Gemini"* ]]; then
    print -r -- "Gemini (${GEMINI_MODEL:-gemini-2.0-flash})"
  elif [[ "$raw_conf" == *"NVIDIA"* ]]; then
    print -r -- "NVIDIA (${NVIDIA_MODEL:-moonshotai/kimi-k3})"
  elif [[ "$raw_conf" == *"OpenRouter"* ]]; then
    print -r -- "OpenRouter (${OPENROUTER_MODEL:-inclusionai/ling-3.0-flash-fin:free})"
  elif [[ "$raw_conf" == *"Web"* || "$raw_conf" == *"G4F"* ]]; then
    print -r -- "Web (${G4F_MODEL:-gpt-4o})"
  else
    print -r -- "Local (${OLLAMA_MODEL:-llama3.2:3b})"
  fi
}
