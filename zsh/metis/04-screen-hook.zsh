#!/usr/bin/env zsh
# =============================================================================
# metis/04-screen-hook.zsh
# Shell Hook do Metis Screen para monitoramento de comandos e status de saída ($?)
# =============================================================================

# Salva informações do Kitty atual para detecção instantânea pelo Metis Screen
_metis_record_kitty_env() {
  if [[ -n "$KITTY_LISTEN_ON" ]]; then
    echo "$KITTY_LISTEN_ON" > "/tmp/orig_kitty_listen.$UID" 2>/dev/null
    echo "$KITTY_LISTEN_ON" > "/tmp/orig_kitty_listen" 2>/dev/null
  fi
  if [[ -n "$KITTY_WINDOW_ID" ]]; then
    echo "$KITTY_WINDOW_ID" > "/tmp/orig_kitty_id.$UID" 2>/dev/null
    echo "$KITTY_WINDOW_ID" > "/tmp/orig_kitty_id" 2>/dev/null
  fi
  if [[ -n "$KITTY_PID" ]]; then
    echo "$KITTY_PID" > "/tmp/orig_kitty_pid.$UID" 2>/dev/null
    echo "$KITTY_PID" > "/tmp/orig_kitty_pid" 2>/dev/null
  fi
}

# Hook disparado imediatamente antes de executar o comando
_metis_screen_preexec() {
  typeset -g _METIS_SCREEN_LAST_CMD="$1"
  typeset -g _METIS_SCREEN_CMD_START="$(date +%s)"
  _metis_record_kitty_env
}

# Hook disparado imediatamente após o término do comando
_metis_screen_precmd() {
  local exit_code=$?
  
  if [[ -n "$_METIS_SCREEN_LAST_CMD" ]]; then
    local win_id="${KITTY_WINDOW_ID:-$$}"
    local content="CMD: $_METIS_SCREEN_LAST_CMD
EXIT_CODE: $exit_code
TIME: ${_METIS_SCREEN_CMD_START:-$(date +%s)}
WIN: $win_id"

    # Grava por Window ID e como último status geral
    echo "$content" > "/tmp/metis_status_${win_id}" 2>/dev/null
    echo "$content" > "/tmp/metis_last_status" 2>/dev/null

    unset _METIS_SCREEN_LAST_CMD
    unset _METIS_SCREEN_CMD_START
  fi
}

# Hooks de rastreamento movidos para history_split.zsh (_metis_track_preexec/_metis_track_precmd)
# Esta função mantém compatibilidade para gravação do ambiente Kitty
_metis_record_kitty_env

# Limpa status de sessões anteriores
if [[ -n "$KITTY_WINDOW_ID" ]]; then
  rm -f "/tmp/metis_status_${KITTY_WINDOW_ID}" 2>/dev/null
fi
