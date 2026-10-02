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

# Valida ZSH_AI_DIR
if [[ ! -d "$ZSH_AI_DIR" ]]; then
    print -u2 "❌ Metis ZSH: diretório de módulos não encontrado em $ZSH_AI_DIR"
    print -u2 "   Execute o instalador ou verifique a instalação em ~/.local/share/metis"
    return 1
fi

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


explain() {
    if [[ "$1" == "screen" || "$1" == "tela" ]]; then
        shift
    fi

    # Metis só funciona no Kitty
    if [[ -z "${KITTY_PID:-}" && -z "${KITTY_WINDOW_ID:-}" ]] || ! command -v kitty >/dev/null 2>&1; then
        print -u2 "❌ Metis Explain Screen requer terminal Kitty."
        print -u2 "   Abra o Kitty e use Ctrl+Shift+E ou digite 'explain' lá dentro."
        return 1
    fi

    # Captura scrollback via kitty remote control
    if [[ $# -eq 0 ]]; then
        local kitty_socket="${KITTY_LISTEN_ON:-unix:/tmp/mykitty}"
        local scrollback
        scrollback="$(kitty @ --to "$kitty_socket" get-text --extent=screen --match="id:${KITTY_WINDOW_ID:-}" 2>/dev/null | head -n 100)"
        if [[ -n "$scrollback" ]]; then
            printf '%s\n' "$scrollback" | metis-screen -tui
            return
        fi
    fi

    if command -v metis-screen >/dev/null 2>&1; then
        metis-screen "$@"
    elif [[ -x "$HOME/.local/bin/metis-screen" ]]; then
        "$HOME/.local/bin/metis-screen" "$@"
    elif [[ -x "/usr/local/bin/metis-screen" ]]; then
        "/usr/local/bin/metis-screen" "$@"
    elif command -v metis >/dev/null 2>&1; then
        metis explain "$@"
    elif [[ -x "$METIS_INSTALL_DIR/bin/metis" ]]; then
        "$METIS_INSTALL_DIR/bin/metis" explain "$@"
    elif [[ -x "$METIS_INSTALL_DIR/app/vision/run.sh" ]]; then
        "$METIS_INSTALL_DIR/app/vision/run.sh" "$@"
    else
        print -u2 "❌ Não foi possível carregar o assistente screen."
        return 1
    fi
}

alias screen-explain="explain"
alias explain_screen="explain"

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

# Metis só funciona no Kitty - atalhos só ativos dentro do Kitty
# Ctrl+Shift+E é configurado via kitty.conf (pipe @screen_scrollback)
# Alt+E desabilitado no Kitty para não conflitar com o pipeline nativo
