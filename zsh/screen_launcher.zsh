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
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    [[ -S "$s" ]] || continue
    k_sock="unix:$s"
    k_pid="${s##*-}"
    break
  done
fi

# Se k_sock não veio pelo ambiente, descobre a janela ativa naquele Kitty
if [[ -n "$k_sock" && -z "$k_win" ]] && command -v kitty >/dev/null 2>&1; then
  if command -v jq >/dev/null 2>&1; then
    k_win="$(kitty @ --to "$k_sock" ls 2>/dev/null | jq -r '.[].tabs[].windows[] | select(.is_active == true) | .id' 2>/dev/null | head -n 1)"
  fi
fi

[[ -n "$k_pid" ]] && echo "$k_pid" > /tmp/orig_kitty_pid
[[ -n "$k_pid" ]] && echo "$k_pid" > "/tmp/orig_kitty_pid.$UID"
[[ -n "$k_sock" ]] && echo "$k_sock" > /tmp/orig_kitty_listen
[[ -n "$k_sock" ]] && echo "$k_sock" > "/tmp/orig_kitty_listen.$UID"
[[ -n "$k_win" ]] && echo "$k_win" > /tmp/orig_kitty_id
[[ -n "$k_win" ]] && echo "$k_win" > "/tmp/orig_kitty_id.$UID"

# Exporta variáveis para o processo do Metis Screen respeitar estritamente a janela de origem
[[ -n "$k_sock" ]] && export KITTY_LISTEN_ON="$k_sock"
[[ -n "$k_pid" ]] && export KITTY_PID="$k_pid"
[[ -n "$k_win" ]] && export KITTY_WINDOW_ID="$k_win"

# 3. Captura instantaneamente a seleção ativa no momento do disparo do atalho (isolamento estrito)
local sel=""

# Prioridade 1: Terminal Kitty com socket ativo (captura exclusivamente da janela onde o atalho foi chamado)
if [[ -n "$k_sock" ]] && command -v kitty >/dev/null 2>&1; then
  if [[ -n "$k_win" ]]; then
    sel="$(kitty @ --to "$k_sock" get-text --extent=selection --match="id:$k_win" 2>/dev/null)"
  else
    sel="$(kitty @ --to "$k_sock" get-text --extent=selection 2>/dev/null)"
  fi
else
  # Prioridade 2: Outros emuladores de terminal (apenas se não estiver no Kitty)
  if [[ -n "$WAYLAND_DISPLAY" ]] && command -v wl-paste >/dev/null 2>&1; then
    sel="$(wl-paste --primary --no-newline 2>/dev/null)"
  elif [[ -n "$DISPLAY" ]]; then
    if command -v xclip >/dev/null 2>&1; then
      sel="$(xclip -o -selection primary 2>/dev/null)"
    elif command -v xsel >/dev/null 2>&1; then
      sel="$(xsel -o -p 2>/dev/null)"
    fi
  fi
fi

sel="$(printf '%s' "$sel" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [[ -n "$sel" ]]; then
  print -r -- "$sel" > /tmp/qwen_selecao.txt
else
  rm -f /tmp/qwen_selecao.txt /tmp/qwen_selecao.*.txt 2>/dev/null
fi

# 4. Determina qual assistente executar (prioridade para o binário Go)
local go_bin=""
if command -v metis-screen >/dev/null 2>&1; then
  go_bin="$(command -v metis-screen)"
elif [[ -x "$HOME/metis-screen/metis-screen" ]]; then
  go_bin="$HOME/metis-screen/metis-screen"
elif [[ -x "$HOME/.local/bin/metis-screen" ]]; then
  go_bin="$HOME/.local/bin/metis-screen"
fi

if [[ -n "$go_bin" ]]; then
  exec "$go_bin"
fi

# Fallback: script ZSH legado (removido - agora usa metis-screen Go)
# Se chegou aqui, metis-screen não foi encontrado
print -r -- "Erro: metis-screen não encontrado no PATH" >&2
return 1

