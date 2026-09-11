#!/usr/bin/env zsh
# =============================================================================
# screen/03-ai-caller.zsh
# Spinner visual, integração com Ollama Local e orquestrador de chamadas de IA.
# =============================================================================

run_with_spinner() {
  local msg="$1"
  shift
  SPINNER_RESULT=""
  SPINNER_CODE=0

  local tmp_out="" tmp_err="" old_int_trap=""
  tmp_out="$(mktemp)" || return 1
  tmp_err="$(mktemp)" || { rm -f "$tmp_out"; return 1; }

  old_int_trap="$(trap -p INT 2>/dev/null)"

  "$@" </dev/null >"$tmp_out" 2>"$tmp_err" &
  local bg_pid=$!

  local -a frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
  local i=1
  local interrupted=0

  tput civis 2>/dev/null >&2 || printf "\033[?25l" >&2

  trap "interrupted=1; kill -TERM $bg_pid 2>/dev/null; kill -KILL $bg_pid 2>/dev/null" INT

  local cols="${COLUMNS:-80}"
  local max_msg_len=$(( cols - 20 ))
  (( max_msg_len < 20 )) && max_msg_len=20

  local display_msg="$msg"
  if (( ${#display_msg} > max_msg_len )); then
    display_msg="${display_msg:0:$(( max_msg_len - 3 ))}..."
  fi

  while kill -0 "$bg_pid" 2>/dev/null; do
    printf "\r\033[2K\033[33m%s %s\033[0m \033[90m(Ctrl+C)\033[0m" "${frames[$i]}" "$display_msg" >&2
    i=$(( (i % 10) + 1 ))
    sleep 0.1
    if (( interrupted == 1 )); then
      break
    fi
  done

  if [[ -n "$old_int_trap" ]]; then
    eval "$old_int_trap"
  else
    trap - INT
  fi

  printf "\r\033[2K" >&2
  tput cnorm 2>/dev/null >&2 || printf "\033[?25h" >&2

  if (( interrupted == 1 )); then
    kill -TERM "$bg_pid" 2>/dev/null
    kill -KILL "$bg_pid" 2>/dev/null
    rm -f "$tmp_out" "$tmp_err" 2>/dev/null
    SPINNER_CODE=130
    SPINNER_RESULT=""
    return 130
  fi

  local exit_code=0
  wait "$bg_pid" 2>/dev/null || exit_code=$?

  if (( exit_code == 130 || exit_code == 143 || exit_code == 137 )); then
    rm -f "$tmp_out" "$tmp_err" 2>/dev/null
    SPINNER_CODE=130
    SPINNER_RESULT=""
    return 130
  fi

  local result="" err_msg=""
  result="$(cat "$tmp_out" 2>/dev/null)"
  err_msg="$(cat "$tmp_err" 2>/dev/null)"
  rm -f "$tmp_out" "$tmp_err" 2>/dev/null

  if [[ -n "$err_msg" && -z "$result" ]]; then
    _warn "$err_msg"
  fi

  SPINNER_RESULT="$result"
  SPINNER_CODE="$exit_code"
  return "$exit_code"
}

_ollama_query() {
  local prompt="$1"
  local model="${OLLAMA_MODEL:-llama3.2:3b}"
  local timeout="${AI_FIX_TIMEOUT:-360}"
  local threads="${OLLAMA_THREADS:-4}"

  [[ "$threads" =~ ^[0-9]+$ ]] || threads=4

  if command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    local payload="" response="" parsed=""

    payload=$(jq -n --arg model "$model" --arg prompt "$prompt" --argjson threads "$threads" '{
      model: $model,
      prompt: $prompt,
      stream: false,
      options: {
        num_thread: $threads
      }
    }' 2>/dev/null)

    if [[ -n "$payload" ]]; then
      response=$(print -r -- "$payload" | curl -fsS --max-time "$timeout" -H 'Content-Type: application/json' -d @- "$OLLAMA_URL" 2>/dev/null)
      parsed=$(print -r -- "$response" | jq -r '.response // empty' 2>/dev/null)

      if [[ -n "$parsed" ]]; then
        print -r -- "$parsed"
        return 0
      fi
    fi
  fi

  if command -v ollama >/dev/null 2>&1; then
    print -r -- "$prompt" | ollama run "$model" --nowordwrap 2>/dev/null
  else
    _warn "Ollama não está instalado ou em execução."
    return 1
  fi
}

chamar_ia() {
  local prompt="$1"
  local resp=""
  local code=0

  load_env_file "$HOME/Metis/.env"
  load_env_file "$HOME/.ZSH/ai/.env_local"

  local t_start=${EPOCHREALTIME:-$(date +%s 2>/dev/null)}

  case "$PROVIDER" in
    1)
      local g4f_m="${G4F_MODEL:-gpt-4o}"

      if _python_ok "$PYTHON_BIN" && [[ -f "$G4F_SCRIPT" ]]; then
        run_with_spinner "Consultando Web ($g4f_m)..." "$PYTHON_BIN" "$G4F_SCRIPT" "$g4f_m" "$prompt"
        code=$?
        resp="$SPINNER_RESULT"
      else
        code=1
      fi

      if (( code == 130 )); then
        return 130
      fi

      if [[ -z "$resp" || "$resp" == "[Sem resposta]" || "$resp" == *"Erro g4f"* ]]; then
        _warn "⚠️ Web falhou. Acionando fallback (Local Ollama)..."

        run_with_spinner "Consultando Ollama Local..." _ollama_query "$prompt"
        code=$?
        resp="$SPINNER_RESULT"
      fi
      ;;

    2)
      run_with_spinner "Consultando IA Local ($OLLAMA_MODEL)..." _ollama_query "$prompt"
      code=$?
      resp="$SPINNER_RESULT"
      ;;

    3)
      if ! _python_ok "$PYTHON_BIN" || [[ ! -f "$API_SCRIPT" ]]; then
        _warn "Python ou script de API indisponível para Gemini."
        return 1
      fi

      run_with_spinner "Consultando Gemini (${GEMINI_MODEL:-gemini-2.0-flash})..." "$PYTHON_BIN" "$API_SCRIPT" "GEMINI" "$prompt"
      code=$?
      resp="$SPINNER_RESULT"
      ;;

    4)
      if ! _python_ok "$PYTHON_BIN" || [[ ! -f "$API_SCRIPT" ]]; then
        _warn "Python ou script de API indisponível para Groq."
        return 1
      fi

      run_with_spinner "Consultando Groq (${GROQ_MODEL:-llama-3.3-70b-versatile})..." "$PYTHON_BIN" "$API_SCRIPT" "GROQ" "$prompt"
      code=$?
      resp="$SPINNER_RESULT"
      ;;

    5)
      if ! _python_ok "$PYTHON_BIN" || [[ ! -f "$API_SCRIPT" ]]; then
        _warn "Python ou script de API indisponível para NVIDIA."
        return 1
      fi

      run_with_spinner "Consultando NVIDIA (${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct})..." "$PYTHON_BIN" "$API_SCRIPT" "NVIDIA" "$prompt"
      code=$?
      resp="$SPINNER_RESULT"
      ;;

    6)
      if ! _python_ok "$PYTHON_BIN" || [[ ! -f "$API_SCRIPT" ]]; then
        _warn "Python ou script de API indisponível para OpenRouter."
        return 1
      fi

      run_with_spinner "Consultando OpenRouter (${OPENROUTER_MODEL:-minimax/minimax-m3:free})..." "$PYTHON_BIN" "$API_SCRIPT" "OPENROUTER" "$prompt"
      code=$?
      resp="$SPINNER_RESULT"
      ;;

    *)
      if ! _python_ok "$PYTHON_BIN" || [[ ! -f "$API_SCRIPT" ]]; then
        _warn "Python ou script de API indisponível para $PROVIDER."
        return 1
      fi

      local cur_m="$("$PYTHON_BIN" "${MANAGE_MODELS_SCRIPT:-${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py}" get_active "$PROVIDER" 2>/dev/null)"
      run_with_spinner "Consultando $PROVIDER (${cur_m:-automático})..." "$PYTHON_BIN" "$API_SCRIPT" "$PROVIDER" "$prompt"
      code=$?
      resp="$SPINNER_RESULT"
      ;;
  esac

  local t_end=${EPOCHREALTIME:-$(date +%s 2>/dev/null)}
  LAST_DURATION=$(( t_end - t_start ))

  if (( code == 130 )); then
    return 130
  fi

  print -r -- "$resp"
  return "$code"
}
