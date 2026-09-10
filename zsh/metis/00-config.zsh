#!/usr/bin/env zsh
# =============================================================================
# metis/00-config.zsh
# Configurações, digitação visual (type live), localização de Python e checagens.
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || true

_metis_type_live() {
  local text="$1"
  local speed="${2:-0.015}"
  local len=${#text}
  local i char

  for (( i = 1; i <= len; i++ )); do
    char="${text[$i]}"
    printf "%s" "$char"
    sleep "$speed"
  done

  printf '\n'
}

_metis_get_python() {
  local py_bin=""

  if (( ${+functions[_ai_get_python]} )); then
    py_bin="$(_ai_get_python 2>/dev/null)"
  fi

  if [[ -z "$py_bin" ]]; then
    py_bin="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
  fi

  [[ -n "$py_bin" ]] && print -r -- "$py_bin"
}

_metis_require_deps() {
  local fn
  local missing=0

  for fn in _ai_query _ai_get_current_provider_info _ai_get_metis_icon; do
    if (( ! ${+functions[$fn]} )); then
      printf '\033[31m[Metis] Dependência ausente: %s. Verifique %s/ia_client.zsh.\033[0m\n' "$fn" "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}" >&2
      missing=1
    fi
  done

  if [[ -z "$(_metis_get_python)" ]]; then
    printf '\033[31m[Metis] Python não encontrado. Instale python3 ou configure _ai_get_python.\033[0m\n' >&2
    missing=1
  fi

  return "$missing"
}
