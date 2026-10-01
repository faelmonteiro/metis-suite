#!/usr/bin/env zsh
# =============================================================================
# METIS AI SUITE - MASTER LOADER FOR ZSH
# =============================================================================

# Raiz do código Python. `~/.local/share/metis` é só cópia de distribuição;
# o projeto que se edita tem o pacote `agente/` e por isso tem precedência.
# Precisa ser resolvida antes de trocar ZSH_AI_DIR, senão o venv sai do PATH.
export METIS_ROOT="${0:A:h:h}"
if [[ ! -d "$METIS_ROOT/agente" ]]; then
  if [[ -d "$HOME/Metis/agente" ]]; then
    export METIS_ROOT="$HOME/Metis"
  else
    export METIS_ROOT="$HOME/.local/share/metis"
  fi
fi

# O ambiente Python aparece como `venv` na cópia de distribuição e como `.venv`
# no projeto local. Aceitar os dois nomes evita depender de um só: sem isso o
# PATH nunca pegava o interpretador que tem o PyQt6 e o `ai-sync` caía no
# python do sistema.
METIS_PYENV=""
for _metis_cand in "$METIS_ROOT/.venv" "$METIS_ROOT/venv"; do
  if [[ -x "$_metis_cand/bin/python" ]]; then
    METIS_PYENV="$_metis_cand"
    break
  fi
done
unset _metis_cand
export METIS_PYENV

# Diretório base dos módulos ZSH. A árvore instalada em ~/.local/share/metis é
# apenas uma cópia de distribuição; a pasta real do usuário tem precedência,
# para que atalhos e módulos venham sempre do código que se edita.
export ZSH_AI_DIR="$HOME/.ZSH/ai"
[[ -f "$ZSH_AI_DIR/loader.zsh" ]] || ZSH_AI_DIR="${0:A:h}"

# Adiciona o executável do venv e binários locais ao PATH se existirem
if [[ -n "$METIS_PYENV" && -d "$METIS_PYENV/bin" ]]; then
    export PATH="$METIS_PYENV/bin:$PATH"
fi
if [[ -d "$HOME/.local/bin" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Desativa captura de mouse pelo fzf para manter a seleção nativa com mouse do terminal livre
if [[ "${FZF_DEFAULT_OPTS:-}" != *"--no-mouse"* ]]; then
    export FZF_DEFAULT_OPTS="--no-mouse ${FZF_DEFAULT_OPTS:-}"
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
[[ -f "$ZSH_AI_DIR/aith.zsh" ]] && source "$ZSH_AI_DIR/aith.zsh"

# Aliases úteis
alias ai="ia"
if [[ -n "$METIS_PYENV" && -x "$METIS_PYENV/bin/python" ]]; then
    alias ai-sync="\"$METIS_PYENV/bin/python\" '$ZSH_AI_DIR/manage_models.py' sync"
else
    alias ai-sync="python3 '$ZSH_AI_DIR/manage_models.py' sync"
fi


alias screen-explain="metis-screen"
alias explain_screen="metis-screen"
alias explain="metis-screen"

# Widget interativo para acionar o explain/metis-screen direto no ZSH
_metis_explain_screen_widget() {
    zle -I
    local cmd_file="${XDG_RUNTIME_DIR:-/tmp}/metis_bash_cmd.$UID"
    rm -f "$cmd_file" 2>/dev/null
    if command -v metis-screen >/dev/null 2>&1; then
        metis-screen </dev/tty >/dev/tty
    else
        print -u2 "Metis: metis-screen não encontrado no PATH."
    fi
    if [[ -f "$cmd_file" ]]; then
        local cmd="$(cat "$cmd_file" 2>/dev/null)"
        rm -f "$cmd_file" 2>/dev/null
        if [[ -n "$cmd" ]]; then
            BUFFER="$cmd"
            CURSOR=${#BUFFER}
        fi
    fi
    zle reset-prompt 2>/dev/null || true
}
zle -N _metis_explain_screen_widget 2>/dev/null || true

# Mapeamentos universais: Alt+E apenas para terminais padrão do sistema (GNOME Terminal, Mint Terminal, etc.)
# No terminal Kitty, o Alt+E é desativado para manter o Kitty com seu pipeline nativo [Ctrl + Shift + E]
if [[ -z "$KITTY_PID" && -z "$KITTY_WINDOW_ID" && "$TERM" != *"kitty"* ]]; then
    bindkey '^[e' _metis_explain_screen_widget 2>/dev/null || true
    bindkey '^[E' _metis_explain_screen_widget 2>/dev/null || true

    # Mapeamentos legados: Ctrl+Shift+E (suporta sequências CSI-u e Xterm em terminais comuns)
    bindkey '^[[101;6u' _metis_explain_screen_widget 2>/dev/null || true
    bindkey '^[[69;6u' _metis_explain_screen_widget 2>/dev/null || true
    bindkey '^[[27;6;101~' _metis_explain_screen_widget 2>/dev/null || true
    bindkey '^[[27;6;69~' _metis_explain_screen_widget 2>/dev/null || true
fi
