#!/usr/bin/env zsh
# =============================================================================
# fix/00-config.zsh
# Configurações gerais, variáveis de ambiente e funções auxiliares do Fix (Ctrl+G).
# =============================================================================

unalias fix 2>/dev/null || true

_ai_fix_trim() {
  local s="${1:-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  print -r -- "$s"
}

_ai_fix_python_ok() {
  local py="${1:-}"
  [[ -n "$py" ]] || return 1

  if [[ "$py" == */* ]]; then
    [[ -x "$py" ]]
  else
    command -v "$py" >/dev/null 2>&1
  fi
}

_ai_fix_safe_note_name() {
  local n="${1:-}"

  n="${n//[^A-Za-z0-9._-]/_}"

  while [[ "$n" == *__* ]]; do
    n="${n//__/_}"
  done

  if [[ -z "$n" ]]; then
    n="tutorial_$(date +%Y%m%d_%H%M%S)"
  fi

  n="${n%.md}.md"
  print -r -- "$n"
}

_ai_fix_pause() {
  printf 'Pressione Enter para voltar (ou aguarde 3s)...'
  stty sane 2>/dev/null
  read -t 3 -k 1 _ </dev/tty 2>/dev/null || read -t 3 -r _ </dev/tty 2>/dev/null || true
}

_ai_fix_metis_icon() {
  if (( ${+functions[_ai_get_metis_icon]} )); then
    _ai_get_metis_icon
  else
    print -r -- "🏛️ "
  fi
}

_ai_fix_check_deps() {
  local cmd
  for cmd in fzf jq curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      zle -M "Erro: dependência '$cmd' não encontrada."
      return 1
    fi
  done
  return 0
}

_ai_fix_get_python() {
  if (( ${+functions[_ai_get_python]} )); then
    _ai_get_python 2>/dev/null
  else
    command -v python3 2>/dev/null || command -v python 2>/dev/null
  fi
}

_ai_fix_load_env_file() {
  if (( ${+functions[_ai_load_env_file]} )); then
    _ai_load_env_file "$1"
  fi
}

_ai_fix_reload_envs() {
  if (( ${+functions[_ai_reload_all_envs]} )); then
    _ai_reload_all_envs
  fi
  if (( ${+functions[_ai_get_current_provider_info]} )); then
    _ai_get_current_provider_info
  fi
}
