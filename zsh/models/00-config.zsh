#!/usr/bin/env zsh
# =============================================================================
# models/00-config.zsh
# Inicialização, helpers básicos e validação de dependências do menu de modelos.
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || source ~/.ZSH/ai/ia_client.zsh 2>/dev/null || true

_ai_menu_resolve_provider() {
  local prov="$1"
  local backend_name="$prov"
  local state_name="$prov"

  case "${(U)prov}" in
    OLLAMA|LOCAL)
      backend_name="OLLAMA"
      state_name="Ollama"
      ;;
    OPENROUTER)
      backend_name="OpenRouter"
      state_name="OpenRouter"
      ;;
    GEMINI)
      backend_name="Gemini"
      state_name="Gemini"
      ;;
    GROQ)
      backend_name="Groq"
      state_name="Groq"
      ;;
    NVIDIA)
      backend_name="NVIDIA"
      state_name="NVIDIA"
      ;;
    G4F|WEB)
      backend_name="G4F"
      state_name="G4F"
      ;;
    *)
      backend_name="$prov"
      state_name="$prov"
      ;;
  esac

  print -r -- "$backend_name" "$state_name"
}

_ai_menu_get_default_model() {
  local backend_name="$1"
  local cur_model=""

  case "${(U)backend_name}" in
    OLLAMA|LOCAL)
      cur_model="${OLLAMA_MODEL:-llama3.2:3b}"
      ;;
    GEMINI)
      cur_model="${GEMINI_MODEL:-gemini-2.0-flash}"
      ;;
    GROQ)
      cur_model="${GROQ_MODEL:-llama-3.3-70b-versatile}"
      ;;
    NVIDIA)
      cur_model="${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}"
      ;;
    OPENROUTER)
      cur_model="${OPENROUTER_MODEL:-minimax/minimax-m3:free}"
      ;;
    G4F|WEB)
      cur_model="${G4F_MODEL:-gpt-4o}"
      ;;
    *)
      if [[ -n "$AI_MENU_PY_BIN" && -n "$AI_MENU_MANAGE_SCRIPT" ]]; then
        cur_model="$("$AI_MENU_PY_BIN" "$AI_MENU_MANAGE_SCRIPT" get_active "$backend_name" 2>/dev/null)"
      fi
      ;;
  esac

  print -r -- "$cur_model"
}

_ai_menu_check_core_functions() {
  local fn
  for fn in _ai_get_python _ai_reload_all_envs _ai_save_provider_state; do
    if (( ! $+functions[$fn] )); then
      printf '\033[31mErro: função necessária "%s" não está definida.\033[0m\n' "$fn"
      sleep 1
      return 1
    fi
  done
  return 0
}

_ai_menu_prepare() {
  _ai_menu_check_core_functions || return 1

  if ! command -v fzf >/dev/null 2>&1; then
    printf '\033[31mErro: fzf não está instalado.\033[0m\n'
    sleep 1
    return 1
  fi

  typeset -g AI_MENU_PY_BIN AI_MENU_MANAGE_SCRIPT

  AI_MENU_PY_BIN="$(_ai_get_python)" || {
    printf '\033[31mPython não encontrado.\033[0m\n'
    sleep 1
    return 1
  }

  if [[ -z "$AI_MENU_PY_BIN" ]]; then
    printf '\033[31mPython não encontrado.\033[0m\n'
    sleep 1
    return 1
  fi

  AI_MENU_MANAGE_SCRIPT="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py"
  if [[ ! -f "$AI_MENU_MANAGE_SCRIPT" ]]; then
    local _mod_dir="${0:A:h:h}"
    if [[ -f "$_mod_dir/manage_models.py" ]]; then
      AI_MENU_MANAGE_SCRIPT="$_mod_dir/manage_models.py"
    fi
  fi

  if [[ ! -f "$AI_MENU_MANAGE_SCRIPT" ]]; then
    printf '\033[31mErro: manage_models.py indisponível em %s.\033[0m\n' "$AI_MENU_MANAGE_SCRIPT"
    sleep 1
    return 1
  fi

  return 0
}
