#!/usr/bin/env sh
# =============================================================================
# screen/preview_mouse.sh
# Renderizador em tempo real para a seleção do mouse no preview do FZF.
# =============================================================================

sel=""

# 1. Wayland Primary Selection (seleção direta do mouse em tempo real)
if command -v wl-paste >/dev/null 2>&1; then
  sel="$(wl-paste --primary --no-newline 2>/dev/null)"
fi

# 2. Kitty Remote Control na janela de origem
if [ -z "$sel" ] && [ -n "$TARGET_KITTY_SOCK" ] && command -v kitty >/dev/null 2>&1; then
  if [ -n "$TARGET_KITTY_WIN" ]; then
    sel="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=selection --match="id:$TARGET_KITTY_WIN" 2>/dev/null)"
  fi
  [ -z "$sel" ] && sel="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=selection 2>/dev/null)"
fi

# 3. X11 Primary Selection fallback
if [ -z "$sel" ] && command -v xclip >/dev/null 2>&1; then
  sel="$(xclip -o -selection primary 2>/dev/null)"
elif [ -z "$sel" ] && command -v xsel >/dev/null 2>&1; then
  sel="$(xsel -o -p 2>/dev/null)"
fi

# Remove espaços e quebras vazias das pontas para validar conteúdo
clean_sel="$(printf '%s' "$sel" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [ -n "$clean_sel" ]; then
  # Atualiza o arquivo temporário com a seleção em tempo real
  printf '%s\n' "$clean_sel" > /tmp/qwen_selecao.txt 2>/dev/null
  lines="$(printf '%s\n' "$clean_sel" | wc -l)"
  snippet="$(printf '%s\n' "$clean_sel" | head -n 5)"
  printf '\033[1;33m⚡ SELEÇÃO DO MOUSE (TEMPO REAL)\033[0m\n────────────────────────\n• \033[1;37mIA Ativa:\033[0m %s\n• \033[1;37mAção:\033[0m Analisar texto selecionado no terminal\n• \033[1;37mLinhas:\033[0m %s\n• \033[1;37mLatência média:\033[0m %s\n• \033[1;37mContexto:\033[0m %s\n\n\033[1;36mTrecho marcado com o mouse:\033[0m\n%s\n' \
    "${PREV_ACTIVE_MODEL:-IA}" "$lines" "${PREV_MODEL_LAT:-~200ms}" "${PREV_MODEL_CTX:-128k}" "$snippet"
else
  rm -f /tmp/qwen_selecao.txt 2>/dev/null
  printf '\033[1;33m⚡ SELEÇÃO DO MOUSE\033[0m\n────────────────────────\n• \033[1;37mIA Ativa:\033[0m %s\n• \033[1;37mAção:\033[0m Analisar texto selecionado no terminal\n• \033[1;37mStatus:\033[0m \033[1;33mNenhuma seleção ativa detectada\033[0m\n• \033[1;37mLatência média:\033[0m %s\n• \033[1;37mContexto:\033[0m %s\n\n\033[1;30m(Dica: Selecione com o mouse no terminal antes ou agora,\nou confirme aqui para analisar a saída recente do terminal)\033[0m\n' \
    "${PREV_ACTIVE_MODEL:-IA}" "${PREV_MODEL_LAT:-~200ms}" "${PREV_MODEL_CTX:-128k}"
fi
