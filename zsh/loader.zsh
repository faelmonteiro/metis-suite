#!/usr/bin/env zsh
# =============================================================================
# METIS AI SUITE - MASTER LOADER FOR ZSH
# =============================================================================

# Diretório base do módulo ZSH
export ZSH_AI_DIR="${0:A:h}"
export METIS_ROOT="${ZSH_AI_DIR:h}"

# Adiciona o executável do venv e binários locais ao PATH se existirem
if [[ -d "$METIS_ROOT/venv/bin" ]]; then
    export PATH="$METIS_ROOT/venv/bin:$PATH"
fi
if [[ -d "$HOME/.local/bin" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Carrega os módulos da suíte ZSH
[[ -f "$ZSH_AI_DIR/ia_client.zsh" ]] && source "$ZSH_AI_DIR/ia_client.zsh"
[[ -f "$ZSH_AI_DIR/fix.zsh" ]] && source "$ZSH_AI_DIR/fix.zsh"
[[ -f "$ZSH_AI_DIR/correcao.zsh" ]] && source "$ZSH_AI_DIR/correcao.zsh"
[[ -f "$ZSH_AI_DIR/ia.zsh" ]] && source "$ZSH_AI_DIR/ia.zsh"
[[ -f "$ZSH_AI_DIR/aiman.zsh" ]] && source "$ZSH_AI_DIR/aiman.zsh"
[[ -f "$ZSH_AI_DIR/autocomplete.zsh" ]] && source "$ZSH_AI_DIR/autocomplete.zsh"
[[ -f "$ZSH_AI_DIR/git-ai.zsh" ]] && source "$ZSH_AI_DIR/git-ai.zsh"
[[ -f "$ZSH_AI_DIR/metis.zsh" ]] && source "$ZSH_AI_DIR/metis.zsh"
[[ -f "$ZSH_AI_DIR/history_split.zsh" ]] && source "$ZSH_AI_DIR/history_split.zsh"

# Aliases úteis
alias ai="ia"
if [[ -x "$METIS_ROOT/venv/bin/python" ]]; then
    alias ai-sync="\"$METIS_ROOT/venv/bin/python\" '$ZSH_AI_DIR/manage_models.py' sync"
else
    alias ai-sync="python3 '$ZSH_AI_DIR/manage_models.py' sync"
fi


alias screen-explain="source \"$ZSH_AI_DIR/explain_screen.zsh\""
alias explain_screen="source \"$ZSH_AI_DIR/explain_screen.zsh\""
alias explain="source \"$ZSH_AI_DIR/explain_screen.zsh\""

# Widget interativo para acionar o explain_screen direto no ZSH
_metis_explain_screen_widget() {
    zle -I
    source "$ZSH_AI_DIR/explain_screen.zsh"
    zle reset-prompt 2>/dev/null || true
}
zle -N _metis_explain_screen_widget 2>/dev/null || true

# Mapeamentos universais: Alt+E (compatível com GNOME Terminal, Konsole, Alacritty, Kitty, Xfce, etc.)
bindkey '^[e' _metis_explain_screen_widget 2>/dev/null || true
bindkey '^[E' _metis_explain_screen_widget 2>/dev/null || true

# Mapeamentos legados: Ctrl+Shift+E (suporta sequências CSI-u e Kitty/Xterm)
bindkey '^[[101;6u' _metis_explain_screen_widget 2>/dev/null || true
bindkey '^[[69;6u' _metis_explain_screen_widget 2>/dev/null || true
bindkey '^[[27;6;101~' _metis_explain_screen_widget 2>/dev/null || true
bindkey '^[[27;6;69~' _metis_explain_screen_widget 2>/dev/null || true
