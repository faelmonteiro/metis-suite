#!/usr/bin/env zsh
# =============================================================================
# metis/04-screen-hook.zsh
# Shell Hook do Metis Screen para monitoramento de comandos e status de saída ($?)
# =============================================================================

# Escrita atômica de status.
#
# O nome do destino é previsível e o /tmp é world-writable, então um atacante
# local pode criar o arquivo como symlink para um arquivo seu. `>` e `cp -f`
# ABREM o destino seguindo o symlink e sobrescrevem o alvo. `mv` usa rename,
# que substitui o symlink em vez de escrever através dele — e, por ser atômico,
# o leitor nunca pega o arquivo pela metade.
#
# O temporário nasce via mktemp (O_EXCL, modo 0600) dentro do mesmo /tmp, para
# o rename ser no mesmo filesystem e o nome temporário não ser adivinhável.
#
# O nome do destino não pode ser trocado: o leitor real é o binário Go
# metis-screen, que ainda espera /tmp/metis_last_status e
# /tmp/metis_status_<win>. Por isso a defesa é na escrita, não no rename.
_metis_write_status() {
  local dest="$1" content="$2" tmp=""

  [[ -n "$dest" ]] || return 1

  tmp="$(mktemp /tmp/.metis_status.XXXXXX 2>/dev/null)" || return 1

  if ! print -r -- "$content" > "$tmp" 2>/dev/null; then
    rm -f "$tmp" 2>/dev/null
    return 1
  fi

  if ! mv -f "$tmp" "$dest" 2>/dev/null; then
    rm -f "$tmp" 2>/dev/null
    return 1
  fi

  return 0
}

# Salva informações do Kitty atual para detecção instantânea pelo Metis Screen
#
# Só a variante com $UID. As sem sufixo eram nome previsível em diretório
# world-writable, e `>` segue symlink: um atacante local criava
# /tmp/orig_kitty_listen apontando para um arquivo seu e o próximo preexec
# sobrescrevia o arquivo como este usuário. Pior: nada lia a variante sem
# $UID — conferido em ~/.ZSH/ai inteiro e no projeto Metis — então o risco
# não comprava nada.
_metis_record_kitty_env() {
  if [[ -n "$KITTY_LISTEN_ON" ]]; then
    echo "$KITTY_LISTEN_ON" > "/tmp/orig_kitty_listen.$UID" 2>/dev/null
  fi
  if [[ -n "$KITTY_WINDOW_ID" ]]; then
    echo "$KITTY_WINDOW_ID" > "/tmp/orig_kitty_id.$UID" 2>/dev/null
  fi
  if [[ -n "$KITTY_PID" ]]; then
    echo "$KITTY_PID" > "/tmp/orig_kitty_pid.$UID" 2>/dev/null
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
    _metis_write_status "/tmp/metis_status_${win_id}" "$content"
    _metis_write_status "/tmp/metis_last_status" "$content"

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
