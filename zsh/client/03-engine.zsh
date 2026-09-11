#!/usr/bin/env zsh
# =============================================================================
# client/03-engine.zsh
# Motor de requisição de IA (Ollama Local, Web G4F e provedores de API).
# =============================================================================

_ai_get_current_provider_info() {
  _ai_reload_all_envs

  local conf_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
  local last_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.last_provider"
  local raw_conf raw_last selected=""

  raw_conf="$(_ai_trim "$(cat "$conf_file" 2>/dev/null)")"
  raw_last="$(_ai_trim "$(cat "$last_file" 2>/dev/null)")"

  case "$raw_last" in
    1|*Ollama*|*ollama*|*Local*) selected="OLLAMA" ;;
    2|*G4F*|*Web*|*g4f*) selected="G4F" ;;
    3|*Gemini*|*gemini*) selected="GEMINI" ;;
    4|*Groq*|*groq*) selected="GROQ" ;;
    5|*NVIDIA*|*nvidia*) selected="NVIDIA" ;;
    6|*OpenRouter*|*openrouter*) selected="OPENROUTER" ;;
  esac

  if [[ -z "$selected" ]]; then
    case "$raw_conf" in
      *Groq*) selected="GROQ" ;;
      *Gemini*) selected="GEMINI" ;;
      *NVIDIA*) selected="NVIDIA" ;;
      *OpenRouter*) selected="OPENROUTER" ;;
      *Web*|*G4F*) selected="G4F" ;;
      *Ollama*) selected="OLLAMA" ;;
      *) selected="OLLAMA" ;;
    esac
  fi

  case "$selected" in
    GROQ)
      AI_ACTIVE_PROVIDER="GROQ"
      AI_ACTIVE_MODEL="${GROQ_MODEL:-llama-3.3-70b-versatile}"
      AI_ACTIVE_LABEL="Groq (${AI_ACTIVE_MODEL})"
      ;;
    GEMINI)
      AI_ACTIVE_PROVIDER="GEMINI"
      AI_ACTIVE_MODEL="${GEMINI_MODEL:-gemini-2.0-flash}"
      AI_ACTIVE_LABEL="Gemini (${AI_ACTIVE_MODEL})"
      ;;
    NVIDIA)
      AI_ACTIVE_PROVIDER="NVIDIA"
      AI_ACTIVE_MODEL="${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}"
      AI_ACTIVE_LABEL="NVIDIA (${AI_ACTIVE_MODEL})"
      ;;
    OPENROUTER)
      AI_ACTIVE_PROVIDER="OPENROUTER"
      AI_ACTIVE_MODEL="${OPENROUTER_MODEL:-minimax/minimax-m3:free}"
      AI_ACTIVE_LABEL="OpenRouter (${AI_ACTIVE_MODEL})"
      ;;
    G4F)
      AI_ACTIVE_PROVIDER="G4F"
      AI_ACTIVE_MODEL="${G4F_MODEL:-gpt-4o}"
      AI_ACTIVE_LABEL="Web G4F (${AI_ACTIVE_MODEL})"
      ;;
    *)
      AI_ACTIVE_PROVIDER="OLLAMA"
      AI_ACTIVE_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
      AI_ACTIVE_LABEL="Ollama Local (${AI_ACTIVE_MODEL})"
      ;;
  esac

  AI_ACTIVE_MODEL="$(_ai_trim "$AI_ACTIVE_MODEL")"
  AI_ACTIVE_LABEL="$(_ai_trim "$AI_ACTIVE_LABEL")"

  typeset -gx AI_ACTIVE_PROVIDER AI_ACTIVE_MODEL AI_ACTIVE_LABEL
}

_ai_ollama_generate() {
  local prompt="$1"
  local timeout="${2:-360}"
  local model="${3:-${OLLAMA_MODEL:-qwen2.5-coder:7b}}"

  if ! command -v curl >/dev/null 2>&1; then
    print -r -- "⚠️ O comando 'curl' é necessário para usar Ollama." >&2
    return 127
  fi

  if ! command -v jq >/dev/null 2>&1; then
    print -r -- "⚠️ O comando 'jq' é necessário para usar Ollama." >&2
    return 127
  fi

  [[ "$timeout" =~ ^[0-9]+$ ]] || timeout=360
  (( timeout > 0 )) || timeout=360

  local threads="${OLLAMA_THREADS:-4}"
  [[ "$threads" =~ ^[0-9]+$ ]] || threads=4
  (( threads > 0 )) || threads=4

  local payload raw_res curl_rc response err

  payload="$(jq -nc --arg model "$model" --arg prompt "$prompt" --argjson threads "$threads" '{
    model: $model,
    prompt: $prompt,
    stream: false,
    options: { num_thread: $threads }
  }' 2>/dev/null)" || {
    print -r -- "⚠️ Falha ao montar payload JSON para o Ollama." >&2
    return 1
  }

  raw_res="$(curl -fsS --max-time "$timeout" -H 'Content-Type: application/json' -d "$payload" 'http://127.0.0.1:11434/api/generate' 2>&1)"
  curl_rc=$?

  if (( curl_rc != 0 )); then
    print -r -- "⚠️ Falha ao conectar ao Ollama local (porta 11434). Verifique se o serviço 'ollama' está rodando." >&2
    [[ -n "$raw_res" ]] && print -r -- "$raw_res" >&2
    return 7
  fi

  err="$(print -r -- "$raw_res" | jq -r '.error // empty' 2>/dev/null)"
  if [[ -n "$err" ]]; then
    print -r -- "⚠️ Ollama retornou erro: $err" >&2
    return 1
  fi

  response="$(print -r -- "$raw_res" | jq -r '.response // empty' 2>/dev/null)"

  if [[ -z "$response" ]]; then
    print -r -- "⚠️ Ollama retornou resposta vazia." >&2
    return 1
  fi

  print -r -- "$response"
}

_ai_query() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local prompt="$1"
  local timeout="${2:-${AI_FIX_TIMEOUT:-360}}"

  _ai_get_current_provider_info

  [[ "$timeout" =~ ^[0-9]+$ ]] || timeout=360
  (( timeout > 0 )) || timeout=360

  local max_prompt_chars="${AI_MAX_PROMPT_CHARS:-100000}"
  if [[ "$max_prompt_chars" =~ ^[0-9]+$ ]] && (( ${#prompt} > max_prompt_chars )); then
    prompt="${prompt:0:max_prompt_chars}

[CONTEÚDO TRUNCADO AUTOMATICAMENTE POR SEGURANÇA]"
  fi

  local py_bin api_script g4f_script response="" exit_code=0
  api_script="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/api_ask.py"
  g4f_script="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/g4f_ask.py"

  local err_file
  err_file="$(mktemp "${TMPDIR:-/tmp}/ai_query.XXXXXX" 2>/dev/null)" || err_file="${TMPDIR:-/tmp}/ai_query.${$}.${RANDOM}"
  : > "$err_file"

  case "$AI_ACTIVE_PROVIDER" in
    OLLAMA|LOCAL)
      response="$(_ai_ollama_generate "$prompt" "$timeout" "${AI_ACTIVE_MODEL:-qwen2.5-coder:7b}")"
      exit_code=$?
      if (( exit_code != 0 )); then
        rm -f "$err_file"
        return $exit_code
      fi
      ;;

    G4F)
      py_bin="$(_ai_get_python)" || py_bin=""

      if [[ ! -f "$g4f_script" ]]; then
        print -r -- "⚠️ g4f_ask.py não encontrado em $g4f_script" >&2
        rm -f "$err_file"
        return 127
      fi

      if [[ -z "$py_bin" ]]; then
        print -r -- "⚠️ Python não encontrado para executar Web G4F." >&2
        rm -f "$err_file"
        return 127
      fi

      if command -v timeout >/dev/null 2>&1; then
        response="$(AI_ACTIVE_MODEL="$AI_ACTIVE_MODEL" timeout "$timeout" "$py_bin" "$g4f_script" "$AI_ACTIVE_MODEL" "$prompt" 2>"$err_file")"
        exit_code=$?
      else
        response="$(AI_ACTIVE_MODEL="$AI_ACTIVE_MODEL" "$py_bin" "$g4f_script" "$AI_ACTIVE_MODEL" "$prompt" 2>"$err_file")"
        exit_code=$?
      fi

      if (( exit_code != 0 )) || [[ -z "$response" || "$response" == "[Sem resposta]" || "$response" == *"Erro g4f"* || "$response" == Traceback* || "$response" == ⚠️* ]]; then
        if [[ -s "$err_file" ]]; then
          cat "$err_file" >&2
        else
          print -r -- "⚠️ Falha ao comunicar com Web G4F (${AI_ACTIVE_MODEL})." >&2
        fi
        rm -f "$err_file"
        return 1
      fi
      ;;

    *)
      if [[ ! -f "$api_script" ]]; then
        print -r -- "⚠️ api_ask.py não encontrado em $api_script" >&2
        rm -f "$err_file"
        return 127
      fi

      py_bin="$(_ai_get_python)" || {
        print -r -- "⚠️ Python não encontrado para consultar ${AI_ACTIVE_LABEL}." >&2
        rm -f "$err_file"
        return 127
      }

      if command -v timeout >/dev/null 2>&1; then
        response="$(AI_ACTIVE_PROVIDER="$AI_ACTIVE_PROVIDER" AI_ACTIVE_MODEL="$AI_ACTIVE_MODEL" timeout "$timeout" "$py_bin" "$api_script" "$AI_ACTIVE_PROVIDER" "$prompt" 2>"$err_file")"
        exit_code=$?
      else
        response="$(AI_ACTIVE_PROVIDER="$AI_ACTIVE_PROVIDER" AI_ACTIVE_MODEL="$AI_ACTIVE_MODEL" "$py_bin" "$api_script" "$AI_ACTIVE_PROVIDER" "$prompt" 2>"$err_file")"
        exit_code=$?
      fi

      if (( exit_code != 0 )); then
        if [[ -s "$err_file" ]]; then
          cat "$err_file" >&2
        else
          print -r -- "⚠️ Falha ao consultar ${AI_ACTIVE_LABEL}." >&2
        fi
        rm -f "$err_file"
        return $exit_code
      fi
      ;;
  esac

  rm -f "$err_file"
  response="${response//$'\r'/}"
  print -r -- "$response"
  return 0
}
