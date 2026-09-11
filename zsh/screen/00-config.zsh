#!/usr/bin/env zsh
# =============================================================================
# screen/00-config.zsh
# Configurações gerais, inicialização de módulos ZSH, traps e helpers básicos.
# =============================================================================

zmodload zsh/zle 2>/dev/null || true
zmodload zsh/datetime 2>/dev/null || true

# Configurações de teclado e ZLE para navegação fluida com setas
bindkey -e 2>/dev/null || true
bindkey '^[[D' backward-char 2>/dev/null || true
bindkey '^[[C' forward-char 2>/dev/null || true
bindkey '^[OD' backward-char 2>/dev/null || true
bindkey '^[OC' forward-char 2>/dev/null || true
bindkey '^[[H' beginning-of-line 2>/dev/null || true
bindkey '^[[F' end-of-line 2>/dev/null || true
bindkey '^[[1~' beginning-of-line 2>/dev/null || true
bindkey '^[[4~' end-of-line 2>/dev/null || true
bindkey '^[[3~' delete-char 2>/dev/null || true
bindkey '^?' backward-delete-char 2>/dev/null || true
bindkey '^H' backward-delete-char 2>/dev/null || true

# Evita que Ctrl+C feche a janela do assistente de forma abrupta.
# O modo /auto usa AUTO_CANCEL para permitir cancelamento controlado.
trap ' ' INT

# -----------------------------------------------------------------------------
# Variáveis de Ambiente e Arquivos de Estado
# -----------------------------------------------------------------------------
FILE="${QWEN_TELA_FILE:-${XDG_RUNTIME_DIR:-/tmp}/qwen_tela.$UID.txt}"
if [[ ! -s "$FILE" && -s "/tmp/qwen_tela.txt" && ! -L "/tmp/qwen_tela.txt" ]]; then
  FILE="/tmp/qwen_tela.txt"
fi

ZSH_AI_DIR="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}"
METIS_ROOT="${METIS_ROOT:-$HOME/.local/share/metis}"

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  if [[ -x "$METIS_ROOT/venv/bin/python" ]]; then
    PYTHON_BIN="$METIS_ROOT/venv/bin/python"
  elif [[ -x "$HOME/Metis/.venv/bin/python" ]]; then
    PYTHON_BIN="$HOME/Metis/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

G4F_SCRIPT="${G4F_SCRIPT:-$ZSH_AI_DIR/g4f_ask.py}"
[[ -f "$G4F_SCRIPT" ]] || G4F_SCRIPT="$HOME/.ZSH/ai/g4f_ask.py"

API_SCRIPT="${API_SCRIPT:-$ZSH_AI_DIR/api_ask.py}"
[[ -f "$API_SCRIPT" ]] || API_SCRIPT="$HOME/.ZSH/ai/api_ask.py"

MANAGE_MODELS_SCRIPT="${MANAGE_MODELS_SCRIPT:-$ZSH_AI_DIR/manage_models.py}"
[[ -f "$MANAGE_MODELS_SCRIPT" ]] || MANAGE_MODELS_SCRIPT="$HOME/.ZSH/ai/manage_models.py"

OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
OLLAMA_URL="${OLLAMA_URL:-${AI_FIX_OLLAMA_URL:-http://localhost:11434/api/generate}}"
OLLAMA_THREADS="${OLLAMA_THREADS:-4}"

DEFAULT_SCREEN_LINES="${DEFAULT_SCREEN_LINES:-50}"
MAX_CONTEXT_TURNS="${MAX_CONTEXT_TURNS:-5}"

AI_ASSIST_WORD_WRAP="${AI_ASSIST_WORD_WRAP:-1}"
AI_ASSIST_TYPE_EFFECT="${AI_ASSIST_TYPE_EFFECT:-1}"

AI_AUTO_MAX_STEPS="${AI_AUTO_MAX_STEPS:-${METIS_MAX_STEPS:-6}}"
AI_AUTO_SLEEP="${AI_AUTO_SLEEP:-2}"
AI_AUTO_LOG_DIR="${AI_AUTO_LOG_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/metis/logs}"
AI_AUTO_ALLOW_MULTILINE="${AI_AUTO_ALLOW_MULTILINE:-0}"

ACTIVE_PROVIDER_FILE="${ACTIVE_PROVIDER_FILE:-${METIS_CONFIG_DIR:-$HOME/.config/metis}/.last_provider}"

ORIG_KITTY_ID="${ORIG_KITTY_ID:-$(cat /tmp/orig_kitty_id 2>/dev/null)}"
KITTY_LISTEN_ON="${KITTY_LISTEN_ON:-$(cat /tmp/orig_kitty_listen 2>/dev/null)}"
export ORIG_KITTY_ID KITTY_LISTEN_ON

# Validação das variáveis numéricas
[[ "$DEFAULT_SCREEN_LINES" =~ ^[0-9]+$ ]] || DEFAULT_SCREEN_LINES=50
[[ "$MAX_CONTEXT_TURNS" =~ ^[0-9]+$ ]] || MAX_CONTEXT_TURNS=5
[[ "$AI_AUTO_MAX_STEPS" =~ ^[0-9]+$ ]] || AI_AUTO_MAX_STEPS=6
[[ "$AI_AUTO_SLEEP" =~ ^[0-9]+$ ]] || AI_AUTO_SLEEP=2

# -----------------------------------------------------------------------------
# Variáveis Globais Compartilhadas
# -----------------------------------------------------------------------------
typeset -g TOOL_NAME="" TOOL_PATH="" TOOL_CONTENT=""
typeset -g PARSED_LINES=0 PARSED_QUERY="" PARSED_STEPS=""
typeset -g TARGET_KITTY_SOCK="" TARGET_KITTY_WIN=""
typeset -g SPINNER_RESULT="" SPINNER_CODE=0
typeset -g MODEL_SPEC_LATENCY="" MODEL_SPEC_CONTEXT=""
typeset -ga CURRENT_CODE_BLOCKS=()
typeset -g LAST_RESPONSE="" LAST_DURATION="" LAST_SELECTED_CODE="" CONTEXT=""

# -----------------------------------------------------------------------------
# Helpers Básicos
# -----------------------------------------------------------------------------
_trim() {
  local s="${1:-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  print -r -- "$s"
}

_remover_comentarios_linha() {
  local line="$1"
  local in_single=0
  local in_double=0
  local escaped=0
  local len=${#line}
  local i ch prev_ch=""
  local out=""

  for (( i = 1; i <= len; i++ )); do
    ch="${line[$i]}"

    if (( escaped )); then
      out+="$ch"
      escaped=0
      prev_ch="$ch"
      continue
    fi

    if [[ "$ch" == "\\" ]]; then
      escaped=1
      out+="$ch"
      prev_ch="$ch"
      continue
    fi

    if [[ "$ch" == "'" && in_double -eq 0 ]]; then
      in_single=$(( 1 - in_single ))
      out+="$ch"
      prev_ch="$ch"
      continue
    fi

    if [[ "$ch" == '"' && in_single -eq 0 ]]; then
      in_double=$(( 1 - in_double ))
      out+="$ch"
      prev_ch="$ch"
      continue
    fi

    if [[ "$ch" == "#" && in_single -eq 0 && in_double -eq 0 ]]; then
      if [[ -z "$prev_ch" || "$prev_ch" == [[:space:]] || "$prev_ch" == ";" || "$prev_ch" == "&" || "$prev_ch" == "|" ]]; then
        break
      fi
    fi

    out+="$ch"
    prev_ch="$ch"
  done

  out="${out%"${out##*[![:space:]]}"}"
  print -r -- "$out"
}

_remover_comentarios_comando() {
  local cmd="$1"
  local -a lines=("${(@f)cmd}")
  local clean_lines=()
  local l clean_l

  for l in "${lines[@]}"; do
    clean_l="$(_remover_comentarios_linha "$l")"
    if [[ -n "$clean_l" ]]; then
      clean_lines+=("$clean_l")
    fi
  done

  print -r -- "${(F)clean_lines}"
}

_has_fn() { [[ -n "${functions[$1]}" ]]; }

_resolve_path() {
  local p="${1/#\~/$HOME}"
  realpath -m -- "$p" 2>/dev/null || print -r -- "$p"
}

_die() {
  printf '\033[31mErro: %s\033[0m\n' "$1" >&2
  exit 1
}

_warn() {
  printf '\033[33m%s\033[0m\n' "$1" >&2
}

_print_header() {
  local icon="🏛️ "
  local icon_file="$HOME/Metis/assets/icons/metis_emoji_32x32.png"
  if [[ -f "$icon_file" ]] && [[ -n "$KITTY_PID" || -n "$KITTY_WINDOW_ID" || "$TERM" == *"kitty"* ]]; then
    local b64="$(base64 -w 0 "$icon_file" 2>/dev/null || base64 "$icon_file" 2>/dev/null | tr -d '\n')"
    if [[ -n "$b64" ]]; then
      icon="$(printf '\033_Ga=T,f=100,c=2,r=1;%s\033\\ ' "$b64")"
    fi
  fi

  local cols="$(tput cols 2>/dev/null || echo 80)"
  local title_str="Assistente de Terminal"
  local ver_str="v2.3.1"
  local status_str="● online"
  local status_color="\033[32m"
  
  # Checagem dinâmica ultra-rápida de conexão (150ms timeout)
  if ! timeout 0.15 bash -c 'exec 3<>/dev/tcp/1.1.1.1/53' 2>/dev/null; then
    status_str="○ offline"
    status_color="\033[31m"
  fi
  
  local left_len=$(( 4 + ${#title_str} + 2 + ${#ver_str} ))
  local pad=$(( cols - left_len - ${#status_str} - 4 ))
  (( pad < 2 )) && pad=2
  
  printf '\n  %s\033[1;38;2;240;195;115m%s\033[0m \033[90m%s\033[0m%*s%b%s\033[0m\n' \
    "$icon" "$title_str" "$ver_str" "$pad" "" "$status_color" "$status_str"
  printf '  \033[38;2;160;120;50m──────────────────────────────────────────\033[0m\n'
}

_python_ok() {
  local py="${1:-$PYTHON_BIN}"
  [[ -n "$py" ]] || return 1

  if [[ "$py" == */* ]]; then
    [[ -x "$py" ]]
  else
    command -v "$py" >/dev/null 2>&1
  fi
}

_auto_log() {
  local msg="$1"
  [[ -z "$AI_AUTO_LOG_DIR" ]] && return 0

  mkdir -p "$AI_AUTO_LOG_DIR" 2>/dev/null || return 0

  local logfile="$AI_AUTO_LOG_DIR/auto_$(date +%Y%m%d).log"
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$msg" >> "$logfile" 2>/dev/null || true
}

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || source ~/.ZSH/ai/ia_client.zsh 2>/dev/null || true

# -----------------------------------------------------------------------------
# Carregamento de Ambientes (.env)
# -----------------------------------------------------------------------------
load_env_file() {
  if _has_fn _ai_reload_all_envs; then
    _ai_reload_all_envs "$@" 2>/dev/null || true
  fi
}

load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
load_env_file "$HOME/Metis/.env"
load_env_file "$HOME/.ZSH/ai/.env_local"

if ! _python_ok "$PYTHON_BIN"; then
  PYTHON_BIN="$(_ai_get_python 2>/dev/null || which python3 2>/dev/null || echo python3)"
fi
