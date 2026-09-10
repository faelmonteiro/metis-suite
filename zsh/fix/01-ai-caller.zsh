#!/usr/bin/env zsh
# =============================================================================
# fix/01-ai-caller.zsh
# Comunicação com modelos (Ollama, Web G4F, APIs) e manipulação do buffer ZLE.
# =============================================================================

_ai_fix_query() {
  setopt LOCAL_OPTIONS TYPESET_SILENT
  local prompt="$1"
  local action_label="${2:-Processando}"
  local m_icon="$(_ai_fix_metis_icon)"

  if (( $+functions[_ai_get_current_provider_info] )); then
    _ai_get_current_provider_info
  fi

  local label="${AI_ACTIVE_LABEL:-IA ativa}"
  local tty_out="/dev/tty"
  [[ -w /dev/tty ]] || tty_out="/dev/stderr"
  printf '\n%s\033[38;2;250;208;148m[Metis]:\033[0m \033[33m%s com %s...\033[0m\n' "$m_icon" "$action_label" "$label" > "$tty_out" 2>/dev/null

  if (( $+functions[_ai_query] )); then
    _ai_query "$prompt" "${AI_FIX_TIMEOUT:-360}"
  else
    _ai_fix_ollama_qwen "$prompt" "${OLLAMA_MODEL:-qwen2.5-coder:7b}"
  fi
}

_ai_fix_ollama_qwen() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local prompt="$1"
  local model="${2:-${OLLAMA_MODEL:-${AI_FIX_OLLAMA_MODEL:-qwen2.5-coder:7b}}}"
  local url="${AI_FIX_OLLAMA_URL:-http://127.0.0.1:11434/api/generate}"
  local timeout="${AI_FIX_TIMEOUT:-360}"
  local threads="${OLLAMA_THREADS:-4}"
  local payload response error result

  if [[ ! "$timeout" =~ ^[0-9]+$ ]]; then
    timeout=360
  fi

  if [[ ! "$threads" =~ ^[0-9]+$ ]]; then
    threads=4
  fi

  payload=$(jq -n \
    --arg model "$model" \
    --arg prompt "$prompt" \
    --argjson threads "$threads" '{
      model: $model,
      prompt: $prompt,
      stream: false,
      options: {
        num_thread: $threads
      }
    }') || return 1

  if ! response=$(print -r -- "$payload" |
    curl -fsS --max-time "$timeout" \
      -H 'Content-Type: application/json' \
      -d @- \
      "$url" 2>/dev/null); then
    printf '\033[31mFalha ao conectar ao Ollama em %s\033[0m\n' "$url" >&2
    return 1
  fi

  error=$(print -r -- "$response" | jq -r '.error // empty' 2>/dev/null)
  if [[ -n "$error" ]]; then
    printf '\033[31mOllama: %s\033[0m\n' "$error" >&2
    return 1
  fi

  result=$(print -r -- "$response" | jq -r '.response // empty' 2>/dev/null)
  [[ -z "$result" ]] && return 1

  print -r -- "$result"
}

_ai_fix_g4f_ask() {
  setopt LOCAL_OPTIONS TYPESET_SILENT
  local model="${1:-${G4F_MODEL:-gpt-4o}}"
  local prompt="$2"
  local python_bin g4f_script resposta

  python_bin="$(_ai_fix_get_python)" || return 1
  g4f_script="${AI_FIX_G4F_SCRIPT:-${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/g4f_ask.py}"

  if ! _ai_fix_python_ok "$python_bin" || [[ ! -f "$g4f_script" ]]; then
    return 1
  fi

  if ! resposta=$("$python_bin" "$g4f_script" "$model" "$prompt" 2>/dev/null); then
    return 1
  fi

  resposta="$(_ai_fix_trim "$resposta")"

  if [[ -z "$resposta" || "$resposta" == "[Sem resposta]" || "$resposta" == *"Erro g4f"* ]]; then
    return 1
  fi

  print -r -- "$resposta"
}

_ai_fix_api_ask() {
  setopt LOCAL_OPTIONS TYPESET_SILENT
  local provider="$1"
  local prompt="$2"
  local python_bin api_script resposta

  python_bin="$(_ai_fix_get_python)" || return 1
  api_script="${AI_FIX_API_SCRIPT:-${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/api_ask.py}"

  if ! _ai_fix_python_ok "$python_bin" || [[ ! -f "$api_script" ]]; then
    return 1
  fi

  if ! resposta=$("$python_bin" "$api_script" "$provider" "$prompt" 2>/dev/null); then
    return 1
  fi

  resposta="$(_ai_fix_trim "$resposta")"

  if [[ -z "$resposta" || "$resposta" == "[Sem resposta]" ]]; then
    return 1
  fi

  print -r -- "$resposta"
}

_ai_fix_clean_command() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local text="$1"
  local code=""

  [[ -z "$text" ]] && return 1

  text="${text//$'\r'/}"

  code="$(print -r -- "$text" | awk '/^[[:space:]]*```/ { if (inside) exit; inside=1; next } inside')"

  if [[ -z "$code" ]]; then
    code="$(print -r -- "$text" | grep -oE '`[^`]+`' | head -n 1 | sed -E 's/^`//; s/`$//')"
  fi

  code="$(_ai_fix_trim "$code")"

  [[ -z "$code" ]] && return 1

  # Colapsa quebras de linha que possuem continuação de barra invertida (\)
  code="${code//$'\\\n'/ }"

  if [[ "$code" == *$'\n'* ]]; then
    code="${code%%$'\n'*}"
    code="$(_ai_fix_trim "$code")"
  fi

  print -r -- "$code"
}

_ai_fix_insert_command() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local cmd="$1"
  local confirm="${AI_FIX_CONFIRM:-1}"
  local yn

  if [[ -z "$cmd" || "$cmd" == *"Erro na API"* || "$cmd" == *"Erro g4f"* || "$cmd" == *"Falha ao conectar"* ]]; then
    printf '\033[31m⚠️ A IA não retornou um comando válido.\033[0m\n'
    _ai_fix_pause
    return 1
  fi

  if [[ "$confirm" == "1" || "$confirm" == "true" || "$confirm" == "yes" || "$confirm" == "on" ]]; then
    local m_icon="$(_ai_fix_metis_icon)"

    printf '\n%s\033[38;2;250;208;148m[Metis]:\033[0m \033[36mComando gerado:\033[0m\n' "$m_icon"
    print -r -- "$cmd"
    printf 'Inserir no prompt? (Y/n) '

    if ! read -r yn </dev/tty; then
      printf '\n\033[33mCancelado.\033[0m\n'
      return 2
    fi

    if [[ "$yn" == [nN]* ]]; then
      printf '\033[33mComando cancelado.\033[0m\n'
      return 2
    fi
  fi

  if [[ -n "$LBUFFER" && "$LBUFFER" != *[[:space:]] ]]; then
    LBUFFER+=' '
  fi

  LBUFFER+="$cmd"
  return 0
}
