#!/usr/bin/env zsh
# =============================================================================
# screen_launcher.zsh
# Launcher intermediário para o assistente de terminal Metis Screen.
# Acionado pelo atalho do Kitty (Ctrl + Shift + E).
# =============================================================================

# 1. Salva buffer de tela recebido via STDIN do pipe do Kitty
cat > /tmp/qwen_tela.txt

# 2. Identifica socket e janela do Kitty originador
local k_sock="${KITTY_LISTEN_ON}"
local k_pid="${KITTY_PID}"
local k_win="${KITTY_WINDOW_ID}"

# Se não estiverem no ambiente, busca pelo Hyprland activewindow
if [[ -z "$k_sock" ]] && command -v hyprctl >/dev/null 2>&1; then
  local hypr_pid="$(hyprctl activewindow -j 2>/dev/null | jq -r '.pid // empty' 2>/dev/null)"
  if [[ -n "$hypr_pid" && -S "/tmp/mykitty-$hypr_pid" ]]; then
    k_sock="unix:/tmp/mykitty-$hypr_pid"
    k_pid="$hypr_pid"
  fi
fi

# Se ainda não achou, busca nos ancestrais do processo
if [[ -z "$k_sock" ]]; then
  local p="$PPID"
  while [[ -n "$p" && "$p" -gt 1 ]]; do
    if [[ -S "/tmp/mykitty-$p" ]]; then
      k_sock="unix:/tmp/mykitty-$p"
      k_pid="$p"
      break
    fi
    p="$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')"
  done
fi

# Fallback: socket do Kitty mais recente modificado no sistema
if [[ -z "$k_sock" ]]; then
  local -a s_list
  s_list=(/tmp/mykitty*(N-om))
  for s in "${s_list[@]}"; do
    s="$(_trim "$s")"
    [[ -S "$s" ]] || continue
    k_sock="unix:$s"
    k_pid="${s##*-}"
    break
  done
fi

# Se k_win não veio pelo ambiente, descobre a janela ativa naquele Kitty
if [[ -n "$k_sock" && -z "$k_win" ]] && command -v kitty >/dev/null 2>&1; then
  if command -v jq >/dev/null 2>&1; then
    k_win="$(kitty @ --to "$k_sock" ls 2>/dev/null | jq -r '.[].tabs[].windows[] | select(.is_active == true) | .id' 2>/dev/null | head -n 1)"
  fi
fi

[[ -n "$k_pid" ]] && echo "$k_pid" > /tmp/orig_kitty_pid
[[ -n "$k_sock" ]] && echo "$k_sock" > /tmp/orig_kitty_listen
[[ -n "$k_win" ]] && echo "$k_win" > /tmp/orig_kitty_id

# 3. Captura instantaneamente a seleção ativa no momento do disparo do atalho
local sel=""
if command -v wl-paste >/dev/null 2>&1; then
  sel="$(wl-paste --primary --no-newline 2>/dev/null)"
fi

if [[ -z "$sel" && -n "$k_sock" ]] && command -v kitty >/dev/null 2>&1; then
  if [[ -n "$k_win" ]]; then
    sel="$(kitty @ --to "$k_sock" get-text --extent=selection --match="id:$k_win" 2>/dev/null)"
  fi
  [[ -z "$sel" ]] && sel="$(kitty @ --to "$k_sock" get-text --extent=selection 2>/dev/null)"
fi

if [[ -z "$sel" ]] && command -v xclip >/dev/null 2>&1; then
  sel="$(xclip -o -selection primary 2>/dev/null)"
elif [[ -z "$sel" ]] && command -v xsel >/dev/null 2>&1; then
  sel="$(xsel -o -p 2>/dev/null)"
fi

sel="$(printf '%s' "$sel" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [[ -n "$sel" ]]; then
  print -r -- "$sel" > /tmp/qwen_selecao.txt
else
  rm -f /tmp/qwen_selecao.txt 2>/dev/null
fi

# 4. Determina qual script de assistente executar
local script_dir="${0:A:h}"
[[ ! -d "$script_dir" || ! -f "$script_dir/loader.zsh" ]] && script_dir="$HOME/.local/share/metis/zsh"
export ZSH_AI_DIR="$script_dir"
export METIS_ROOT="${ZSH_AI_DIR:h}"

local assistant_script=""
if [[ -f "$script_dir/explain_screen.zsh" ]]; then
  assistant_script="$script_dir/explain_screen.zsh"
elif [[ -f "$HOME/.local/share/metis/zsh/explain_screen.zsh" ]]; then
  assistant_script="$HOME/.local/share/metis/zsh/explain_screen.zsh"
fi

# 5. Lança a janela do assistente
exec kitty --class kitty-screen-assistant \
  --config NONE \
  -o confirm_os_window_close=0 \
  -o "map shift+enter send_text all \x1b\r" \
  -o "map ctrl+enter send_text all \x1b\r" \
  env ZSH_AI_DIR="$ZSH_AI_DIR" METIS_ROOT="$METIS_ROOT" zsh -c "zsh \"$assistant_script\""
