#!/usr/bin/env zsh
# =============================================================================
# screen/08-models-menu.zsh
# Menus interativos FZF para gestão de modelos, provedores e persistência.
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/models_menu.zsh" 2>/dev/null || source ~/.ZSH/ai/models_menu.zsh 2>/dev/null || true

_get_manage_models_script() {
  local s="${MANAGE_MODELS_SCRIPT:-${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py}"
  if [[ -f "$s" ]]; then
    print -r -- "$s"
  else
    local _alt="${0:A:h:h}/manage_models.py"
    if [[ -f "$_alt" ]]; then
      print -r -- "$_alt"
    else
      print -r -- "$s"
    fi
  fi
}

digitar_novo_modelo_para_provedor() {
  _ai_menu_digitar_novo_modelo "$@"
}

remover_modelo_salvo_provedor() {
  _ai_menu_remover_modelo_salvo "$@"
}

escolher_ou_digitar_modelo_provedor() {
  _ai_menu_selecionar_modelo "$@"
}

escolher_ou_digitar_modelo_ollama() {
  _ai_menu_selecionar_modelo_ollama "$@"
}

menu_provedor_ollama() {
  local cur_ollama="" FZF_DEFAULT_OPTS="" menu_ol_acao=""

  while true; do
    clear
    _print_header

    load_env_file "$HOME/Metis/.env"
    load_env_file "$HOME/.ZSH/ai/.env_local"
    load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"

    cur_ollama="${OLLAMA_MODEL:-llama3.2:3b}"

    menu_ol_acao="$(
      printf '🤖 1. Iniciar análise (Ativo: %s)\n📋 2. Gerenciar Modelos (Escolher / Digitar)\n↩️  0. Voltar\n' "$cur_ollama" |
      fzf --height=25% --reverse --border \
          --header="🤖 Ollama Local (ENTER = Confirmar / ESC = Voltar):" \
          --prompt="> "
    )"

    if [[ -z "$menu_ol_acao" ]]; then
      return 1
    fi

    case "$menu_ol_acao" in
      *"1. Iniciar"*)
        return 0
        ;;
      *"2. Gerenciar"*)
        escolher_ou_digitar_modelo_ollama
        ;;
      *)
        return 1
        ;;
    esac
  done
}

menu_provedor_api() {
  local prov_name="$1"
  local icon="${2:-✨}"

  local cur_model="" FZF_DEFAULT_OPTS="" menu_acao=""

  while true; do
    clear
    _print_header

    load_env_file "$HOME/Metis/.env"
    load_env_file "$HOME/.ZSH/ai/.env_local"
    load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"

    cur_model=""

    case "$prov_name" in
      Gemini)     cur_model="${GEMINI_MODEL:-gemini-2.0-flash}" ;;
      Groq)       cur_model="${GROQ_MODEL:-llama-3.3-70b-versatile}" ;;
      NVIDIA)     cur_model="${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}" ;;
      OpenRouter) cur_model="${OPENROUTER_MODEL:-minimax/minimax-m3:free}" ;;
      G4F)        cur_model="${G4F_MODEL:-gpt-4o}" ;;
    esac

    menu_acao="$(
      printf '%s 1. Iniciar análise (Ativo: %s)\n📋 2. Gerenciar Modelos (Escolher / Digitar / Remover)\n↩️  0. Voltar\n' "$icon" "$cur_model" |
      fzf --height=25% --reverse --border \
          --header="⚙️  Configuração de $prov_name (ENTER = Confirmar / ESC = Voltar):" \
          --prompt="> "
    )"

    if [[ -z "$menu_acao" ]]; then
      return 1
    fi

    case "$menu_acao" in
      *"1. Iniciar"*)
        return 0
        ;;
      *"2. Gerenciar"*)
        escolher_ou_digitar_modelo_provedor "$prov_name"
        ;;
      *)
        return 1
        ;;
    esac
  done
}

remover_servidor_customizado() {
  _ai_menu_remover_servidor_customizado "$@"
}

gerenciar_modelos() {
  local FZF_DEFAULT_OPTS="" escolha=""

  while true; do
    clear
    _print_header

    load_env_file "$HOME/Metis/.env"
    load_env_file "$HOME/.ZSH/ai/.env_local"
    load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"

    escolha="$(
      printf '✨ 1. Gemini (Ativo: %s)\n🚀 2. Groq (Ativo: %s)\n🟢 3. NVIDIA (Ativo: %s)\n🪐 4. OpenRouter (Ativo: %s)\n🤖 5. Ollama Local (Ativo: %s)\n🌍 6. Web G4F (Ativo: %s)\n🔄 7. Sincronizar com Metis\n🗑️  8. Remover Servidor Customizado\n↩️  0. Voltar\n' \
        "${GEMINI_MODEL:-gemini-2.0-flash}" \
        "${GROQ_MODEL:-llama-3.3-70b-versatile}" \
        "${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}" \
        "${OPENROUTER_MODEL:-minimax/minimax-m3:free}" \
        "${OLLAMA_MODEL:-llama3.2:3b}" \
        "${G4F_MODEL:-gpt-4o}" |
      fzf --height=40% --reverse --border \
          --header="⚙️  GERENCIAR MODELOS - Escolha o Provedor (ESC = Voltar):" \
          --prompt="> "
    )"

    if [[ -z "$escolha" || "$escolha" == *"Voltar"* ]]; then
      return 0
    fi

    case "$escolha" in
      "✨ 1."*)
        if menu_provedor_api "Gemini" "✨"; then
          PROVIDER=3
          _save_active_provider 3
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          return 0
        fi
        ;;
      "🚀 2."*)
        if menu_provedor_api "Groq" "🚀"; then
          PROVIDER=4
          _save_active_provider 4
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          return 0
        fi
        ;;
      "🟢 3."*)
        if menu_provedor_api "NVIDIA" "🟢"; then
          PROVIDER=5
          _save_active_provider 5
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          return 0
        fi
        ;;
      "🪐 4."*)
        if menu_provedor_api "OpenRouter" "🪐"; then
          PROVIDER=6
          _save_active_provider 6
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          return 0
        fi
        ;;
      "🤖 5."*)
        if menu_provedor_ollama; then
          PROVIDER=2
          _save_active_provider 2
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          return 0
        fi
        ;;
      "🌍 6."*)
        if menu_provedor_api "G4F" "🌍"; then
          PROVIDER=1
          _save_active_provider 1
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          return 0
        fi
        ;;
      "🔄 7."*)
        clear
        _print_header
        "$PYTHON_BIN" "$(_get_manage_models_script)" sync
        load_env_file "$HOME/Metis/.env"
        load_env_file "$HOME/.ZSH/ai/.env_local"
        printf '\n\033[36mPressione ENTER para continuar...\033[0m'
        read -r
        ;;
      "🗑️"*|"8."*)
        remover_servidor_customizado
        ;;
      *)
        return 0
        ;;
    esac
  done
}

trocar_modelo_sessao() {
  local arg="$1"
  arg="$(_trim "$arg")"

  load_env_file "$HOME/Metis/.env"
  load_env_file "$HOME/.ZSH/ai/.env_local"
  load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"

  if [[ -n "$arg" ]]; then
    local arg_lower="${arg:l}"
    case "$arg_lower" in
      gemini*)
        PROVIDER=3
        _save_active_provider 3
        ;;
      groq*)
        PROVIDER=4
        _save_active_provider 4
        ;;
      nvidia*)
        PROVIDER=5
        _save_active_provider 5
        ;;
      openrouter*)
        PROVIDER=6
        _save_active_provider 6
        ;;
      ollama*|local*|qwen*)
        PROVIDER=2
        _save_active_provider 2
        ;;
      g4f*|web*)
        PROVIDER=1
        _save_active_provider 1
        ;;
      *)
        local py_b="${PYTHON_BIN:-python3}"
        if "$py_b" "$(_get_manage_models_script)" get_active "$arg" >/dev/null 2>&1; then
          PROVIDER="$arg"
          _save_active_provider "$arg"
        else
          arg=""
        fi
        ;;
    esac

    if [[ -n "$arg" ]]; then
      load_env_file "$HOME/Metis/.env"
      load_env_file "$HOME/.ZSH/ai/.env_local"
      return 0
    fi
  fi

  local -a api_menu_lines=()
  local line_item=""
  local fzf_entries=""

  while IFS= read -r line_item; do
    [[ -n "$line_item" ]] && api_menu_lines+=("$line_item")
  done < <("${PYTHON_BIN:-python3}" "$(_get_manage_models_script)" api_menu 2>/dev/null)

  for line_item in "${api_menu_lines[@]}"; do
    local display_text="${line_item%%|*}"
    fzf_entries+="$display_text"$'\n'
  done
  fzf_entries+="🤖 Ollama Local (${OLLAMA_MODEL:-llama3.2:3b})"$'\n'
  fzf_entries+="🌍 Web G4F (${G4F_MODEL:-gpt-4o})"$'\n'
  fzf_entries+="⚙️  [ Gerenciador Completo / Novo Modelo ]"$'\n'
  fzf_entries+="↩️  0. Cancelar / Manter Atual"$'\n'

  local cur_prov_info="$(_get_active_provider_info "$PROVIDER")"

  local prov_choice="$(
    printf '%s' "$fzf_entries" |
    fzf --height=42% --reverse --border \
        --header="🔄 IA Atual: $cur_prov_info | Escolha para trocar:" \
        --prompt="> "
  )"

  if [[ -z "$prov_choice" || "$prov_choice" == *"Cancelar"* || "$prov_choice" == *"0."* ]]; then
    return 0
  fi

  if [[ "$prov_choice" == *"Gerenciador Completo"* ]]; then
    gerenciar_modelos
    load_env_file "$HOME/Metis/.env"
    load_env_file "$HOME/.ZSH/ai/.env_local"
    load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
    return 0
  fi

  if [[ "$prov_choice" == *"Ollama Local"* || "$prov_choice" == *"Ollama"* ]]; then
    if escolher_ou_digitar_modelo_ollama; then
      PROVIDER=2
      _save_active_provider 2
    fi
  elif [[ "$prov_choice" == *"Web G4F"* || "$prov_choice" == *"G4F"* ]]; then
    if escolher_ou_digitar_modelo_provedor "G4F"; then
      PROVIDER=1
      _save_active_provider 1
    fi
  else
    local chosen_prov_id=""
    for line_item in "${api_menu_lines[@]}"; do
      local display_text="${line_item%%|*}"
      if [[ "$prov_choice" == "$display_text"* ]]; then
        local rest="${line_item#*|}"
        chosen_prov_id="${rest%%|*}"
        break
      fi
    done

    if [[ -z "$chosen_prov_id" ]]; then
      case "$prov_choice" in
        *"Gemini"*) chosen_prov_id="Gemini" ;;
        *"Groq"*) chosen_prov_id="Groq" ;;
        *"NVIDIA"*) chosen_prov_id="NVIDIA" ;;
        *"OpenRouter"*) chosen_prov_id="OpenRouter" ;;
      esac
    fi

    if [[ -n "$chosen_prov_id" ]]; then
      if escolher_ou_digitar_modelo_provedor "$chosen_prov_id"; then
        case "$chosen_prov_id" in
          Gemini) PROVIDER=3 ;;
          Groq) PROVIDER=4 ;;
          NVIDIA) PROVIDER=5 ;;
          OpenRouter|openrouter) PROVIDER=6 ;;
          *) PROVIDER="$chosen_prov_id" ;;
        esac
        _save_active_provider "$PROVIDER"
      fi
    fi
  fi

  load_env_file "$HOME/Metis/.env"
  load_env_file "$HOME/.ZSH/ai/.env_local"
  load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
}

_get_saved_provider() {
  local p="4"

  if [[ -f "$ACTIVE_PROVIDER_FILE" ]]; then
    p="$(_trim "$(cat "$ACTIVE_PROVIDER_FILE" 2>/dev/null)")"
  fi

  [[ -n "$p" ]] || p="4"

  print -r -- "$p"
}

_get_model_specs() {
  local prov="$1"
  local model="${2:l}"
  local lat="" ctx=""

  case "$prov" in
    1|G4F|Web|g4f)
      lat="2.5s - 4.5s"
      ctx="128k"
      ;;
    2|Ollama|ollama|Local)
      if [[ "$model" == *3b* || "$model" == *4b* ]]; then
        lat="0.8s - 1.5s"
      elif [[ "$model" == *7b* || "$model" == *8b* || "$model" == *9b* ]]; then
        lat="1.8s - 3.0s"
      elif [[ "$model" == *11b* || "$model" == *14b* || "$model" == *32b* || "$model" == *70b* ]]; then
        lat="3.5s - 7.5s"
      else
        lat="1.5s - 3.5s"
      fi

      if [[ "$model" == *qwen* || "$model" == *llama3.2* ]]; then
        ctx="128k"
      elif [[ "$model" == *deepseek* ]]; then
        ctx="64k"
      else
        ctx="32k - 128k"
      fi
      ;;
    3|Gemini|gemini)
      if [[ "$model" == *pro* ]]; then
        lat="2.0s - 3.5s"
        ctx="2M"
      elif [[ "$model" == *flash-lite* ]]; then
        lat="0.5s - 0.9s"
        ctx="1M"
      else
        lat="0.8s - 1.2s"
        ctx="1M"
      fi
      ;;
    4|Groq|groq)
      lat="0.4s - 0.8s"
      ctx="128k"
      ;;
    5|NVIDIA|nvidia)
      lat="1.0s - 1.6s"
      ctx="128k"
      ;;
    6|OpenRouter|openrouter)
      if [[ "$model" == *minimax* ]]; then
        lat="1.2s - 2.2s"
        ctx="200k"
      elif [[ "$model" == *flash-exp* || "$model" == *gemini* ]]; then
        lat="1.0s - 1.8s"
        ctx="1M"
      else
        lat="1.2s - 2.5s"
        ctx="128k"
      fi
      ;;
    *)
      lat="1.0s - 2.5s"
      ctx="128k"
      ;;
  esac

  MODEL_SPEC_LATENCY="$lat"
  MODEL_SPEC_CONTEXT="$ctx"
}

_get_active_provider_info() {
  local p="${1:-$(_get_saved_provider)}"

  case "$p" in
    1) print -r -- "Web G4F: ${G4F_MODEL:-gpt-4o}" ;;
    2) print -r -- "Ollama Local: ${OLLAMA_MODEL:-llama3.2:3b}" ;;
    3) print -r -- "Gemini: ${GEMINI_MODEL:-gemini-2.0-flash}" ;;
    4) print -r -- "Groq: ${GROQ_MODEL:-llama-3.3-70b-versatile}" ;;
    5) print -r -- "NVIDIA: ${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}" ;;
    6) print -r -- "OpenRouter: ${OPENROUTER_MODEL:-liquid/lfm-2.5-2.6b:free}" ;;
    *)
      local py_b="${PYTHON_BIN:-python3}"
      local cur_m="$("$py_b" "$(_get_manage_models_script)" get_active "$p" 2>/dev/null)"
      if [[ -n "$cur_m" ]]; then
        print -r -- "$p: $cur_m"
      else
        print -r -- "Groq: ${GROQ_MODEL:-llama-3.3-70b-versatile}"
      fi
      ;;
  esac
}

_save_active_provider() {
  local p="$1"
  if _has_fn _ai_save_provider_state; then
    _ai_save_provider_state "$p"
    return $?
  fi

  mkdir -p "${ACTIVE_PROVIDER_FILE:h}" 2>/dev/null
  print -r -- "$p" >| "$ACTIVE_PROVIDER_FILE" 2>/dev/null || true
}
