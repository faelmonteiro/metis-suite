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

# Desativa captura de mouse pelo fzf para permitir seleção livre com o mouse no terminal
if [[ "${FZF_DEFAULT_OPTS:-}" != *"--no-mouse"* ]]; then
    export FZF_DEFAULT_OPTS="--no-mouse ${FZF_DEFAULT_OPTS:-}"
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
        local prov="${DEFAULT_PROVIDER:-groq}"
        "$METIS_INSTALL_DIR/venv/bin/python" "$METIS_INSTALL_DIR/zsh/api_ask.py" "$prov" "$@"
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
        selected="$(tac "$hist_file" | sed 's/^: [0-9]*:[0-9]*;//' | awk '!seen[$0]++' | fzf --no-mouse --height 40% --reverse --prompt="🤖 Histórico de IA & Prompts > " --header="Selecione um prompt:")"
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
        selected="$(grep -v '^#' "$log_file" | grep -v '^[[:space:]]*$' | tac | fzf --no-mouse --height 40% --reverse --prompt="🌐 Downloads & Repositórios > " --header="Selecione:")"
        if [[ -n "$selected" ]]; then
            echo "$selected" | sed 's/^\[[^]]*\] //'
        fi
    else
        cat "$log_file"
    fi
}
alias repos="downloads-log"
alias downloads="downloads-log"

# Habilita expansão de aliases no Bash
shopt -s expand_aliases 2>/dev/null || true

# Função universal do Metis CLI (caso o PATH ainda não tenha sido recarregado)
if ! command -v metis >/dev/null 2>&1; then
    metis() {
        if [[ -x "$METIS_INSTALL_DIR/bin/metis" ]]; then
            "$METIS_INSTALL_DIR/bin/metis" "$@"
        else
            echo "❌ Metis não encontrado em $METIS_INSTALL_DIR/bin/metis" >&2
            return 1
        fi
    }
fi

# Assistente Explain Screen (Terminal Copilot & Screen AI)
explain() {
    if [ "$1" = "screen" ] || [ "$1" = "tela" ]; then
        shift
    fi
    if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/explain_screen.zsh" ]]; then
        zsh "$METIS_INSTALL_DIR/zsh/explain_screen.zsh" "$@"
    elif command -v metis >/dev/null 2>&1; then
        metis explain "$@"
    elif [[ -x "$METIS_INSTALL_DIR/bin/metis" ]]; then
        "$METIS_INSTALL_DIR/bin/metis" explain "$@"
    else
        echo "⚠️  O ZSH é necessário para executar o assistente explain_screen." >&2
        return 1
    fi
}
explain_screen() {
    explain "$@"
}

alias explain-screen="explain"
alias screen-explain="explain"
alias screen="explain"
alias explain_screen="explain_screen"

# Menu Interativo Fix
fix() {
    if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/loader.zsh" ]]; then
        zsh -c "source '$METIS_INSTALL_DIR/zsh/loader.zsh' 2>/dev/null; inteligencia_prompt"
    elif command -v metis >/dev/null 2>&1; then
        metis fix "$@"
    elif [[ -x "$METIS_INSTALL_DIR/bin/metis" ]]; then
        "$METIS_INSTALL_DIR/bin/metis" fix "$@"
    else
        echo "⚠️  O ZSH é necessário para executar o menu fix." >&2
        return 1
    fi
}

# 4. Funções interativas para atalhos do Bash (GNU Readline)
if [[ $- == *i* ]]; then
    # Atalho Alt + E: Explain Screen (captura seleção ativa do mouse ou clipboard)
    _metis_bash_explain_screen() {
        local cmd_file="${XDG_RUNTIME_DIR:-/tmp}/metis_bash_cmd.$UID"
        rm -f "$cmd_file" 2>/dev/null
        explain
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
    # Alt+E exclusivo para terminais comuns do sistema (desativado no Kitty)
    if [[ -z "$KITTY_PID" && -z "$KITTY_WINDOW_ID" && "$TERM" != *"kitty"* ]]; then
        bind -x '"\ee": _metis_bash_explain_screen' 2>/dev/null || true
        bind -x '"\eE": _metis_bash_explain_screen' 2>/dev/null || true
    fi
    bind -x '"\C-g": _metis_bash_fix_prompt' 2>/dev/null || true
    bind -x '"\C-G": _metis_bash_fix_prompt' 2>/dev/null || true
    bind -x '"\eh": _metis_bash_ai_history' 2>/dev/null || true
    bind -x '"\eH": _metis_bash_ai_history' 2>/dev/null || true

    # 5. Interceptador inteligente de comandos desconhecidos / linguagem natural
    command_not_found_handle() {
        [[ $- != *i* ]] && return 127
        [[ -t 0 && -t 1 ]] || {
            printf "%s: comando não encontrado\n" "$1" >&2
            return 127
        }

        local full_cmd="$*"
        [[ -z "$full_cmd" ]] && return 127

        [[ "$full_cmd" =~ ^[/~] ]] && {
            printf "%s: comando não encontrado\n" "$1" >&2
            return 127
        }
        [[ "$full_cmd" =~ ^\./ ]] && {
            printf "%s: comando não encontrado\n" "$1" >&2
            return 127
        }
        [[ "$full_cmd" =~ ^\.\./ ]] && {
            printf "%s: comando não encontrado\n" "$1" >&2
            return 127
        }

        if command -v zsh >/dev/null 2>&1 && [[ -f "$METIS_INSTALL_DIR/zsh/loader.zsh" ]]; then
            printf '\n\033[33m⚡ Analisando comando/pedido:\033[0m \033[1;37m%s\033[0m\n' "$full_cmd"
            printf '🤖 \033[38;2;250;208;148m[Metis]:\033[0m \033[34mConsultando IA...\033[0m\n'

            local result
            result="$(zsh -c '
                source "'"$METIS_INSTALL_DIR"'/zsh/loader.zsh" 2>/dev/null
                ai_fix_command "$@"
            ' _ "$full_cmd" 2>/dev/null)"

            if [[ -z "$result" ]]; then
                if [ -x /usr/lib/command-not-found ]; then
                    /usr/lib/command-not-found -- "$1"
                    return $?
                fi
                printf "%s: comando não encontrado\n" "$1" >&2
                return 127
            fi

            local -a options=()
            local line
            local num_re='^[0-9]+[.)][[:space:]]*(.*)$'
            while IFS= read -r line || [[ -n "$line" ]]; do
                line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^`//' -e 's/`$//' -e 's/^\$ //' -e 's/^# //')"
                [[ -z "$line" ]] && continue
                if [[ "$line" =~ $num_re ]]; then
                    local opt_cmd="${BASH_REMATCH[1]}"
                    opt_cmd="$(echo "$opt_cmd" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^`//' -e 's/`$//')"
                    [[ -n "$opt_cmd" ]] && options+=("$opt_cmd")
                else
                    options+=("$line")
                fi
            done <<< "$result"

            local total=${#options[@]}
            if (( total == 0 )); then
                if [ -x /usr/lib/command-not-found ]; then
                    /usr/lib/command-not-found -- "$1"
                    return $?
                fi
                printf "%s: comando não encontrado\n" "$1" >&2
                return 127
            fi

            printf '\n'
            if (( total == 1 )); then
                local single_cmd="${options[0]}"
                printf '\033[38;5;214m  ➤ %s\033[0m\n\n' "$single_cmd"

                local choice=""
                read -r -p "Executar este comando agora? (S/n) [S=executa, n=histórico]: " choice </dev/tty || return 127
                choice="$(echo "$choice" | tr '[:upper:]' '[:lower:]' | xargs)"
                history -s "$single_cmd" 2>/dev/null || true

                if [[ -z "$choice" || "$choice" == "s" || "$choice" == "sim" || "$choice" == "y" || "$choice" == "yes" ]]; then
                    printf '\033[32m▶ Executando:\033[0m %s\n' "$single_cmd"
                    eval "$single_cmd"
                    return $?
                else
                    printf '\033[36mℹ️  Comando salvo no histórico! Pressione ↑ (Seta para cima) para editar no terminal.\033[0m\n'
                    return 0
                fi
            fi

            local i
            for (( i = 0; i < total; i++ )); do
                printf '\033[38;5;42m  [%d]\033[0m \033[38;5;214m%s\033[0m\n' "$((i+1))" "${options[i]}"
            done
            printf '\n'

            local opt=""
            read -r -p "Escolha o número (1-$total) para executar, ou Enter para cancelar: " opt </dev/tty || return 127
            opt="$(echo "$opt" | xargs)"

            if [[ "$opt" =~ ^[0-9]+$ ]] && (( opt >= 1 && opt <= total )); then
                local chosen="${options[opt-1]}"
                history -s "$chosen" 2>/dev/null || true
                printf '\033[32m▶ Executando:\033[0m %s\n' "$chosen"
                eval "$chosen"
                return $?
            fi

            printf '\033[31mCancelado.\033[0m\n'
            return 127
        else
            if [ -x /usr/lib/command-not-found ]; then
                /usr/lib/command-not-found -- "$1"
                return $?
            fi
            printf "%s: comando não encontrado\n" "$1" >&2
            return 127
        fi
    }

    # 6. Rastreamento do último comando e Exit Code ($?) no Bash
    _metis_bash_track_precmd() {
        local last_exit="$?"
        local last_cmd
        last_cmd="$(history 1 2>/dev/null | sed -e 's/^[[:space:]]*[0-9]*[[:space:]]*//')"
        if [[ -n "$last_cmd" && "$last_cmd" != "explain"* && "$last_cmd" != "fix"* && "$last_cmd" != "_metis_"* ]]; then
            {
                printf 'CMD: %s\n' "$last_cmd"
                printf 'EXIT_CODE: %s\n' "$last_exit"
                printf 'TIME: %s\n' "$(date +%s)"
                printf 'WIN: %s\n' "$$"
            } > "/tmp/metis_status_$$" 2>/dev/null
            cp -f "/tmp/metis_status_$$" "/tmp/metis_last_status" 2>/dev/null
        fi
    }

    if [[ "$PROMPT_COMMAND" != *"_metis_bash_track_precmd"* ]]; then
        if [[ -n "$PROMPT_COMMAND" ]]; then
            PROMPT_COMMAND="_metis_bash_track_precmd; $PROMPT_COMMAND"
        else
            PROMPT_COMMAND="_metis_bash_track_precmd"
        fi
    fi
fi
