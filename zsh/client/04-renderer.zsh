#!/usr/bin/env zsh
# =============================================================================
# client/04-renderer.zsh
# Renderizador terminal de Markdown com realce ANSI, bordas e quebra de linhas.
# =============================================================================

_ai_render_formatted() {
  local text="$1"
  [[ -z "$text" ]] && return 0

  # 1. Glow se instalado no sistema
  if command -v glow >/dev/null 2>&1; then
    local glow_style="${AI_GLOW_STYLE:-}"
    if [[ -z "$glow_style" ]]; then
      if [[ -f "$HOME/.config/glow/metis.json" ]]; then
        glow_style="$HOME/.config/glow/metis.json"
      else
        glow_style="dracula"
      fi
    fi
    print -r -- "$text" | glow -s "$glow_style" -
    return 0
  fi

  # 2. Renderizador Python (Rich) da suíte Metis
  local py_bin="$(_ai_get_python 2>/dev/null)"
  local render_py="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/render_markdown.py"
  if [[ -n "$py_bin" && -f "$render_py" ]]; then
    if "$py_bin" "$render_py" "$text" 2>/dev/null; then
      return 0
    fi
  fi

  # 3. Fallback AWK nativo com realce ANSI
  print -r -- "$text" | awk -v width="${COLUMNS:-80}" '
BEGIN {
  ESC = sprintf("%c", 27)
  CLEAR = ESC "[0m"
  BOLD = ESC "[1;97m"
  C_CMD = ESC "[38;5;214m"
  C_TEXT = ESC "[0m"
  C_TITLE = ESC "[1;36m"
  C_EMPH = ESC "[1;37m"
  C_BORDER = ESC "[38;5;141m"
  C_BULLET = ESC "[38;5;42m"
  C_FLAG = ESC "[38;5;221m"

  in_block = 0
  last_empty = 0

  if (width + 0 > 20) width = width - 2
  else width = 78
}
{
  if ($0 ~ /^[ \t]*```/) {
    if (in_block == 0) {
      in_block = 1
      if (!last_empty) print ""
      last_empty = 0

      lang = $0
      sub(/^[ \t]*```/, "", lang)
      sub(/[ \t]*$/, "", lang)
      if (lang == "") lang = "shell"

      top = "╭─ " lang " "
      pad = 42 - length(lang)
      if (pad < 4) pad = 4

      for (k = 0; k < pad; k++) top = top "─"
      print C_BORDER top CLEAR
    } else {
      in_block = 0
      print C_BORDER "╰──────────────────────────────────────────" CLEAR
      print ""
      last_empty = 1
    }
    next
  }

  if (!in_block && $0 ~ /^[ \t]*$/) {
    if (last_empty) next
    last_empty = 1
    print ""
    next
  }

  last_empty = 0

  if (in_block == 1) {
    print C_BORDER "│ " C_CMD $0 CLEAR
    next
  }

  line = $0
  is_title = 0
  indent_prefix = ""
  indent_len = 0

  if (line ~ /^[ \t]*#+[ \t]*/) {
    sub(/^[ \t]*#+[ \t]*/, "◆ ", line)
    is_title = 1
  }

  if (line ~ /^[ \t]*[\*\-][ \t]+/) {
    sub(/^[ \t]*[\*\-][ \t]+/, C_BULLET "  • " CLEAR, line)
    indent_prefix = "    "
    indent_len = 4
  } else if (line ~ /^[ \t]*[0-9]+\.[ \t]+/) {
    match(line, /^[ \t]*[0-9]+\.[ \t]+/)
    num_prefix = substr(line, RSTART, RLENGTH)
    sub(/^[ \t]*[0-9]+\.[ \t]+/, C_BULLET "  " num_prefix CLEAR, line)
    indent_prefix = "     "
    indent_len = 5
  }

  while (match(line, /`[^`]+`/)) {
    val = substr(line, RSTART + 1, RLENGTH - 2)
    reset_color = is_title ? (CLEAR C_TITLE) : (CLEAR C_TEXT)
    line = substr(line, 1, RSTART - 1) C_CMD val reset_color substr(line, RSTART + RLENGTH)
  }

  while (match(line, /\*\*[^*]+\*\*/)) {
    val = substr(line, RSTART + 2, RLENGTH - 4)
    reset_color = is_title ? (CLEAR C_TITLE) : (CLEAR C_TEXT)
    line = substr(line, 1, RSTART - 1) C_EMPH val reset_color substr(line, RSTART + RLENGTH)
  }

  if (is_title) {
    line = C_TITLE line CLEAR
  }

  out = ""
  col = 0
  len = length(line)
  word = ""
  word_col = 0

  for (i = 1; i <= len; i++) {
    c = substr(line, i, 1)

    if (c == ESC) {
      ansi = c
      for (j = i + 1; j <= len; j++) {
        c2 = substr(line, j, 1)
        ansi = ansi c2
        if (c2 ~ /[a-zA-Z]/) {
          i = j
          break
        }
      }
      word = word ansi
    } else if (c == " " || c == "\t") {
      if (col + word_col > width && col > 0) {
        out = out "\n"
        col = 0
        if (indent_prefix != "") {
          out = out indent_prefix
          col = indent_len
        }
      }

      out = out word c
      col += word_col + 1
      word = ""
      word_col = 0
    } else {
      word = word c
      word_col++
    }
  }

  if (col + word_col > width && col > 0) {
    out = out "\n"
    col = 0
    if (indent_prefix != "") {
      out = out indent_prefix
      col = indent_len
    }
  }

  out = out word
  print out CLEAR
}
END {
  if (in_block == 1) {
    print C_BORDER "╰──────────────────────────────────────────" CLEAR
  }
}
'
}

# Inicializa o provedor e modelo ativos ao carregar a sessão
_ai_get_current_provider_info >/dev/null 2>&1 || true
