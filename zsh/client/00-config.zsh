#!/usr/bin/env zsh
# =============================================================================
# client/00-config.zsh
# Guarda de carregamento, helpers de ambiente e ícone visual do Metis.
# =============================================================================

if [[ -n "${_AI_CLIENT_LOADED:-}" ]]; then
  return 0 2>/dev/null || true
fi
typeset -g _AI_CLIENT_LOADED=1

_ai_trim() {
  local s="${1:-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  print -r -- "$s"
}

_trim() {
  _ai_trim "$@"
}

_ai_get_python() {
  if [[ -n "$AI_FIX_PYTHON_BIN" && -x "$AI_FIX_PYTHON_BIN" ]]; then
    print -r -- "$AI_FIX_PYTHON_BIN"
    return 0
  fi

  local base_dir="${ZSH_AI_DIR:h}"
  for py in "$base_dir/venv/bin/python" \
            "$HOME/.local/share/metis/venv/bin/python" \
            "$HOME/Metis/.venv/bin/python" \
            "$HOME/.venv/bin/python"; do
    if [[ -x "$py" ]]; then
      print -r -- "$py"
      return 0
    fi
  done

  if command -v python3 >/dev/null 2>&1; then
    print -r -- "python3"
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    print -r -- "python"
    return 0
  fi

  return 1
}

_ai_get_metis_icon() {
  if [[ -n "$_METIS_ICON_ESC" ]]; then
    print -r -- "$_METIS_ICON_ESC"
    return 0
  fi

  local icon="🏛️ "
  local base_dir="${ZSH_AI_DIR:h}"
  local icon_file=""

  for f in "$base_dir/assets/icons/metis_emoji_32x32.png" \
           "$HOME/.local/share/metis/assets/icons/metis_emoji_32x32.png" \
           "$HOME/Metis/assets/icons/metis_emoji_32x32.png" \
           "$base_dir/assets/icons/icon_32x32.png" \
           "$HOME/.local/share/metis/assets/icons/icon_32x32.png" \
           "$HOME/Metis/assets/icons/icon_32x32.png"; do
    if [[ -f "$f" ]]; then
      icon_file="$f"
      break
    fi
  done

  if [[ -f "$icon_file" ]] && [[ -n "$KITTY_PID" || -n "$KITTY_WINDOW_ID" || "$TERM" == *"kitty"* ]] && command -v base64 >/dev/null 2>&1; then
    local b64
    b64="$(base64 -w 0 "$icon_file" 2>/dev/null || base64 "$icon_file" 2>/dev/null | tr -d '\n')"
    if [[ -n "$b64" ]]; then
      icon="$(printf '\033_Ga=T,f=100,c=2,r=1;%s\033\\ ' "$b64")"
    fi
  fi

  typeset -g _METIS_ICON_ESC="$icon"
  print -r -- "$icon"
}
