#!/usr/bin/env bash
# =============================================================================
# METIS AI SUITE - BASH INTEGRATION LOADER
# Suporte universal para Bash (Alt+E para Explain Screen, Ctrl+G para Fix)
# =============================================================================

METIS_INSTALL_DIR="${METIS_INSTALL_DIR:-$HOME/.local/share/metis}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

# 1. Garante que $BIN_DIR está no PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    export PATH="$BIN_DIR:$PATH"
fi

# 2. Registro no Histórico Dedicado de IA (~/.zsh_ai_history)
_metis_record_ai_history() {
    local cmd="$*"
    [[ -z "$cmd" ]] && return 0
    local hist_file="${HOME}/.zsh_ai_history"
    local ts
    ts="$(date +%s)"
    if [[ -f "$hist_file" ]]; then
        local tmp_ai="${hist_file}.tmp"
        local escaped_cmd
        escaped_cmd=$(printf '%s\n' "$cmd" | sed -e 's/[.[^$*+?(){|\\]/\\&/g')
        grep -Ev ";${escaped_cmd}[[:space:]]*$" "$hist_file" > "$tmp_ai" 2>/dev/null && mv "$tmp_ai" "$hist_file"
    fi
    printf ': %s:0;%s\n' "$ts" "$cmd" >> "$hist_file"
}

# 3. Comandos principais de IA

# Pipeline de IA (ia / ai) com suporte a pipes e delegação para ai git
ia() {
    if [[ "$1" == "git" ]]; then
        shift
        git_commit_ai "$@"
        return $?
    fi

    _metis_record_ai_history "ia $*"

    if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/loader.zsh" ]]; then
        zsh -c 'METIS_DIR="$1"; shift; source "$METIS_DIR/zsh/loader.zsh" 2>/dev/null; ia "$@"' _ "$METIS_INSTALL_DIR" "$@"
    else
        "$METIS_INSTALL_DIR/venv/bin/python" "$METIS_INSTALL_DIR/zsh/api_ask.py" "$@"
    fi
}
alias ai="ia"
alias ai-sync="$METIS_INSTALL_DIR/venv/bin/python $METIS_INSTALL_DIR/zsh/manage_models.py sync"

# Manual inteligente (aiman)
aiman() {
    _metis_record_ai_history "aiman $*"

    if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/loader.zsh" ]]; then
        zsh -c 'METIS_DIR="$1"; shift; source "$METIS_DIR/zsh/loader.zsh" 2>/dev/null; aiman "$@"' _ "$METIS_INSTALL_DIR" "$@"
    elif command -v metis >/dev/null 2>&1; then
        metis aiman "$@"
    else
        echo "⚠️  O ZSH é necessário para executar o aiman." >&2
        return 1
    fi
}

# Gerador automático de Commits via IA (gca / git-ai / ai git)
git_commit_ai() {
    if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/loader.zsh" ]]; then
        zsh -c 'METIS_DIR="$1"; shift; source "$METIS_DIR/zsh/loader.zsh" 2>/dev/null; git_commit_ai "$@"' _ "$METIS_INSTALL_DIR" "$@"
    elif command -v metis >/dev/null 2>&1; then
        metis commit "$@"
    else
        echo "⚠️  O ZSH é necessário para executar o git-ai." >&2
        return 1
    fi
}
alias gca="git_commit_ai"
alias git-ai="git_commit_ai"

# Consulta de histórico de IA (iah / ai-history)
iah() {
    local hist_file="${HOME}/.zsh_ai_history"
    if [[ ! -f "$hist_file" ]]; then
        echo "Histórico de IA ainda está vazio."
        return 0
    fi
    if command -v fzf >/dev/null 2>&1; then
        local selected
        selected="$(tac "$hist_file" | sed 's/^: [0-9]*:[0-9]*;//' | awk '!seen[$0]++' | fzf --height 40% --reverse --prompt="🤖 Histórico de IA & Prompts > " --header="Selecione um prompt:")"
        if [[ -n "$selected" ]]; then
            echo "$selected"
        fi
    else
        tail -n 20 "$hist_file" | sed 's/^: [0-9]*:[0-9]*;//'
    fi
}
alias ai-history="iah"

# Consulta de downloads e repositórios (repos / downloads)
downloads-log() {
    local log_file="${HOME}/.zsh_downloads.log"
    if [[ ! -f "$log_file" ]]; then
        echo "Nenhum download ou repositório registrado ainda."
        return 0
    fi
    if command -v fzf >/dev/null 2>&1; then
        local selected
        selected="$(grep -v '^#' "$log_file" | grep -v '^[[:space:]]*$' | tac | fzf --height 40% --reverse --prompt="🌐 Downloads & Repositórios > " --header="Selecione:")"
        if [[ -n "$selected" ]]; then
            echo "$selected" | sed 's/^\[[^]]*\] //'
        fi
    else
        cat "$log_file"
    fi
}
alias repos="downloads-log"
alias downloads="downloads-log"

# Aliases para Explain Screen
alias explain-screen="metis explain"
alias screen-explain="metis explain"
alias explain="metis explain"

# 4. Funções interativas para atalhos do Bash (GNU Readline)
if [[ $- == *i* ]]; then
    # Atalho Alt + E: Explain Screen (captura seleção ativa do mouse ou clipboard)
    _metis_bash_explain_screen() {
        if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/explain_screen.zsh" ]]; then
            zsh "$METIS_INSTALL_DIR/zsh/explain_screen.zsh"
        elif command -v metis >/dev/null 2>&1; then
            metis explain
        fi
    }

    # Atalho Ctrl + G: Fix / Menu Interativo FZF com inserção no prompt do Bash
    _metis_bash_fix_prompt() {
        local cmd_file="${XDG_RUNTIME_DIR:-/tmp}/metis_bash_cmd.$UID"
        rm -f "$cmd_file" 2>/dev/null

        if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/loader.zsh" ]]; then
            METIS_BASH_MODE=1 zsh -c "source '$METIS_INSTALL_DIR/zsh/loader.zsh' 2>/dev/null; inteligencia_prompt"
            if [[ -f "$cmd_file" ]]; then
                local cmd
                cmd="$(cat "$cmd_file" 2>/dev/null)"
                rm -f "$cmd_file" 2>/dev/null
                if [[ -n "$cmd" ]]; then
                    if [[ -n "$READLINE_LINE" && "$READLINE_LINE" != *[[:space:]] ]]; then
                        READLINE_LINE+=' '
                    fi
                    READLINE_LINE+="$cmd"
                    READLINE_POINT=${#READLINE_LINE}
                fi
            fi
        elif command -v metis >/dev/null 2>&1; then
            metis fix
        fi
    }

    # Atalho Alt + H: Busca interativa no histórico de IA e inserção direta no prompt
    _metis_bash_ai_history() {
        local hist_file="${HOME}/.zsh_ai_history"
        [[ ! -f "$hist_file" ]] && return 0
        local selected=""
        if command -v fzf >/dev/null 2>&1; then
            selected="$(tac "$hist_file" | sed 's/^: [0-9]*:[0-9]*;//' | awk '!seen[$0]++' | fzf --height 40% --reverse --prompt="🤖 Histórico de IA & Prompts [Alt+H] > " --header="Selecione um prompt:")"
        fi
        if [[ -n "$selected" ]]; then
            READLINE_LINE="$selected"
            READLINE_POINT=${#READLINE_LINE}
        fi
    }

    # Registro de atalhos no Readline
    bind -x '"\ee": _metis_bash_explain_screen' 2>/dev/null || true
    bind -x '"\eE": _metis_bash_explain_screen' 2>/dev/null || true
    bind -x '"\C-g": _metis_bash_fix_prompt' 2>/dev/null || true
    bind -x '"\C-G": _metis_bash_fix_prompt' 2>/dev/null || true
    bind -x '"\eh": _metis_bash_ai_history' 2>/dev/null || true
    bind -x '"\eH": _metis_bash_ai_history' 2>/dev/null || true
fi
