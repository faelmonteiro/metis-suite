#!/usr/bin/env zsh
# =============================================================================
# aith.zsh - Modo "Ensine-me" Direto (AI Teach)
# Conectado à IA ativa selecionada no Ctrl+G (Ollama, Gemini, Groq, NVIDIA ou G4F)
#
# Uso:
#   aith <tópico>
#   Exemplos:
#     aith tar
#     aith "git rebase interativo"
#     aith "docker compose vs docker stack"
# =============================================================================

unalias aith 2>/dev/null || true

if [[ ! -f ${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh ]]; then
    print "\e[31m⚠️ Erro: Arquivo ${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh não encontrado.\e[0m" >&2
    return 1 2>/dev/null || exit 1
fi
source ${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh 2>/dev/null || true

_aith_trim() {
    local s="${1:-}"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    print -r -- "$s"
}

_aith_safe_note_name() {
    local name="${1:-tutorial}"
    name="${name//[^a-zA-Z0-9._-]/_}"
    [[ "$name" == *.* ]] || name="${name}.md"
    print -r -- "$name"
}

_aith_extract_code_blocks() {
    local text="$1"
    local -a blocks=()
    local inside=0
    local current_block=""
    local line=""
    local fence_re='^[[:space:]]*```'

    while IFS= read -r line; do
        if [[ "$line" =~ $fence_re ]]; then
            if (( inside == 1 )); then
                inside=0
                current_block="$(_aith_trim "$current_block")"
                if [[ -n "$current_block" ]]; then
                    blocks+=("$current_block")
                fi
                current_block=""
            else
                inside=1
            fi
        else
            if (( inside == 1 )); then
                current_block+="$line"$'\n'
            fi
        fi
    done <<< "$text"

    if (( inside == 1 )); then
        current_block="$(_aith_trim "$current_block")"
        if [[ -n "$current_block" ]]; then
            blocks+=("$current_block")
        fi
    fi

    # Fallback: inline code blocks
    if (( ${#blocks[@]} == 0 )); then
        local inline=""
        while IFS= read -r inline; do
            inline="$(_aith_trim "$inline")"
            [[ -n "$inline" ]] && blocks+=("$inline")
        done < <(print -r -- "$text" | grep -oE '`[^`]+`' | sed -E 's/^`//; s/`$//')
    fi

    print -r -- "${(pj:\x1f:)blocks}"
}

aith() {
    local topic="$*"
    if [[ -z "$topic" ]]; then
        print "Uso: aith <tópico>"
        print "Exemplo: aith tar -xvf"
        print "Exemplo: aith \"git rebase interativo\""
        return 1
    fi

    local safe_topic="${topic//\'/\\\'}"

    local prompt="Aja como um colega programador experiente batendo papo. Explique o seguinte de forma didática, direta e conversacional: $safe_topic. 
Estruture sua resposta com subtítulos (usando #) para cada tipo de comando. 
Sempre que um comando tiver parâmetros ou flags (como -la, -xvf, etc), explique o que cada letra faz de forma rápida usando tópicos (*). 
REGRA DE OURO: Quando for mostrar o comando exato, isole-o dentro de um bloco markdown com três crases. NUNCA coloque explicações dentro do bloco de código!"

    if (( ${+functions[_ai_get_current_provider_info]} )); then
        _ai_get_current_provider_info
    fi

    local m_icon="🏛️ "
    if (( ${+functions[_ai_get_metis_icon]} )); then
        m_icon="$(_ai_get_metis_icon)"
    fi

    local prov_label="${AI_ACTIVE_LABEL:-IA Ativa}"
    printf '\n%s\e[38;2;250;208;148m[Metis]:\e[0m \e[33mIniciando modo Ensino para \e[1;37m%s\e[0m \e[33mvia %s...\e[0m\n' "$m_icon" "$topic" "$prov_label"

    zmodload zsh/datetime 2>/dev/null || true
    local t_start=${EPOCHREALTIME:-0}

    local text=""
    if (( ${+functions[_ai_query]} )); then
        text="$(_ai_query "$prompt")"
    else
        print "\e[31m⚠️ Função _ai_query não encontrada em ia_client.zsh.\e[0m" >&2
        return 1
    fi
    local query_status=$?
    local t_end=${EPOCHREALTIME:-0}

    # Tratamento de cancelamento com Ctrl+C
    if (( query_status == 130 )) || [[ "$text" == *"KeyboardInterrupt"* ]]; then
        print "\n\e[33m⚠️ Operação cancelada.\e[0m"
        return 130
    fi

    local dur_str=""
    if (( t_start > 0 && t_end > 0 )); then
        local dur=$(( t_end - t_start ))
        dur_str="$(printf '⏱️  %.1fs' "$dur")"
    fi

    local m_icon="$(_ai_get_metis_icon)"
    printf '\n%s\e[32m================ MODO ENSINO: %s (%s) ================\e[0m\n\n' "$m_icon" "$topic" "$prov_label"

    if (( ${+functions[_ai_render_formatted]} )); then
        _ai_render_formatted "$text"
    elif command -v glow >/dev/null 2>&1; then
        print -r -- "$text" | glow -
    else
        print -r -- "$text"
    fi

    if [[ -n "$dur_str" ]]; then
        printf '\n\e[32m=========================================================\e[0m \e[38;2;250;208;148m[%s]\e[0m\n\n' "$dur_str"
    else
        print "\n\e[32m=========================================================\e[0m\n"
    fi

    # EXTRAÇÃO DE COMANDOS
    local blocks_str="$(_aith_extract_code_blocks "$text")"
    local -a blocks=("${(@ps:\x1f:)blocks_str}")

    if (( ${#blocks[@]} > 0 )); then
        printf '\n\e[36m✨ Comandos Disponíveis:\e[0m\n'
        for ((i = 1; i <= ${#blocks[@]}; i++)); do
            local preview_line="$(print -r -- "${blocks[$i]}" | head -n 1 | cut -c 1-80)"
            preview_line="$(_aith_trim "$preview_line")"
            printf "  \e[1;34m[%d]\e[0m 💻 %s\n" "$i" "$preview_line"
        done
        printf '\n'
    fi

    # LOOP INTERATIVO
    local full_notes="# Tutorial: $topic"$'\n'
    full_notes+="> **Data:** $(date '+%d/%m/%Y %H:%M:%S')"$'\n'
    full_notes+="> **Provedor:** $prov_label"$'\n---\n'"$text"$'\n'

    while true; do
        if (( ${#blocks[@]} > 0 )); then
            printf '\n\e[90m💬 Digite sua dúvida, [1..%d] para inserir comando, /m (menu), /nota ou /sair:\e[0m\n' "${#blocks[@]}"
        else
            printf '\n\e[90m💬 Digite sua dúvida, /m (menu), /nota ou /sair:\e[0m\n'
        fi

        printf '\e[1;36m❯ \e[0m'
        local user_input=""
        if ! read -r user_input </dev/tty; then
            return 0
        fi

        local clean_input="$(_aith_trim "$user_input")"

        if [[ -z "$clean_input" || "$clean_input" == "/sair" || "$clean_input" == "/exit" || "$clean_input" == "/q" ]]; then
            return 0
        fi

        if [[ "$clean_input" == "/m" || "$clean_input" == "/menu" ]]; then
            local chat_entries=""
            if (( ${#blocks[@]} > 0 )); then
                for ((i = 1; i <= ${#blocks[@]}; i++)); do
                    local prev_line="$(print -r -- "${blocks[$i]}" | head -n 1 | cut -c 1-50)"
                    prev_line="$(_aith_trim "$prev_line")"
                    chat_entries+="💻 [$i] Inserir no terminal: $prev_line"$'\n'
                done
            fi
            chat_entries+="📝 /nota        Salvar tutorial em ~/Documentos/Notas"$'\n'
            chat_entries+="💡 /ajuda       Exibir guia de atalhos e comandos"$'\n'
            chat_entries+="↩️  /sair        Sair / Finalizar chat"$'\n'

            local chat_fzf_out="$(
                printf '%s' "$chat_entries" |
                fzf --height=30% --reverse --border --ansi \
                    --header="🏛️  Metis | Escolha uma ação (ENTER = Confirmar / ESC = Voltar):" \
                    --prompt="Ação > "
            )"
            if [[ -n "$chat_fzf_out" ]]; then
                if [[ "$chat_fzf_out" == *"💻 ["* ]]; then
                    clean_input="$(print -r -- "$chat_fzf_out" | grep -oE '\[[0-9]+\]' | tr -d '[]')"
                elif [[ "$chat_fzf_out" == *"/nota"* ]]; then
                    clean_input="/nota"
                elif [[ "$chat_fzf_out" == *"/ajuda"* ]]; then
                    clean_input="/ajuda"
                elif [[ "$chat_fzf_out" == *"Sair"* ]]; then
                    return 0
                fi
            else
                continue
            fi
        fi

        if [[ -z "$clean_input" ]]; then
            continue
        fi

        if [[ "$clean_input" == "/ajuda" || "$clean_input" == "/help" || "$clean_input" == "/h" ]]; then
            printf '\n\e[1;36m📖 Guia do Modo Ensino:\e[0m\n'
            printf '  \e[1;33m• Digitar texto + ENTER:\e[0m Faz perguntas de acompanhamento à IA.\n'
            printf '  \e[1;33m• 1, 2, etc:\e[0m Insere o comando correspondente diretamente no seu prompt.\n'
            printf '  \e[1;33m• /m ou /menu:\e[0m Abre menu interativo FZF de ações.\n'
            printf '  \e[1;33m• /nota [nome]:\e[0m Salva o tutorial completo em ~/Documentos/Notas.\n'
            printf '  \e[1;33m• /sair ou Enter vazio:\e[0m Encerra o chat e retorna ao terminal.\n'
            continue
        fi

        if [[ "$clean_input" == "/nota" || "$clean_input" == "/nota "* || "$clean_input" == "/export" || "$clean_input" == "/export "* ]]; then
            local raw_note_name="$(print -r -- "$clean_input" | sed -E 's/^\/(nota|export)[[:space:]]*//')"
            raw_note_name="$(_aith_trim "$raw_note_name")"

            local note_name="$(_aith_safe_note_name "$raw_note_name")"
            local notes_dir="$HOME/Documentos/Notas"

            if ! mkdir -p "$notes_dir" 2>/dev/null; then
                printf '\e[31mErro: não foi possível criar %s\e[0m\n' "$notes_dir"
                continue
            fi

            local note_file="$notes_dir/$note_name"

            if print -r -- "$full_notes" > "$note_file" 2>/dev/null; then
                printf '\n\e[32m📝 Nota completa salva com sucesso em:\e[0m \e[1;37m%s\e[0m\n' "$note_file"
            else
                printf '\e[31mErro ao salvar nota em %s\e[0m\n' "$note_file"
            fi
            continue
        fi

        if [[ "$clean_input" =~ ^\[?[0-9]+\]?$ ]]; then
            local idx="${clean_input//[^0-9]/}"
            idx=$((10#$idx))

            if (( idx >= 1 && idx <= ${#blocks[@]} )); then
                local selected="${blocks[$idx]}"

                print -z "$selected"
                printf '\e[32m✅ Comando [%d] inserido no seu prompt!\e[0m\n' "$idx"
                sleep 0.5
                return 0
            else
                printf '\e[31m⚠️ Comando [%d] não existe.\e[0m\n' "$idx"
                continue
            fi
        fi

        # Pergunta de acompanhamento - faz nova query
        printf '\n%s\e[38;2;250;208;148m[Metis]: \e[0m\e[33mPensando...\e[0m\n' "$m_icon"

        full_notes+="### Pergunta: $clean_input"$'\n'

        local followup_prompt="$text
[Usuário]: $clean_input
Continue a explicação didática baseada na pergunta acima. Mantenha o mesmo formato: subtítulos, explicação de flags, blocos de código isolados."

        local t_start2=${EPOCHREALTIME:-0}
        local followup_text="$(_ai_query "$followup_prompt")"
        local t_end2=${EPOCHREALTIME:-0}

        if [[ -z "$followup_text" ]]; then
            printf '\e[33m⚠️ Sem resposta da IA.\e[0m\n'
            continue
        fi

        local dur_str2=""
        if (( t_start2 > 0 && t_end2 > 0 )); then
            local dur2=$(( t_end2 - t_start2 ))
            dur_str2="$(printf '⏱️  %.1fs' "$dur2")"
        fi

        text="$followup_text"
        full_notes+="$text"$'\n'

        # Re-render
        printf '\n\e[34m🏛️  --- CONTINUAÇÃO: %s ---\e[0m\n' "$prov_label"
        if (( ${+functions[_ai_render_formatted]} )); then
            _ai_render_formatted "$text"
        elif command -v glow >/dev/null 2>&1; then
            print -r -- "$text" | glow -
        else
            print -r -- "$text"
        fi

        if [[ -n "$dur_str2" ]]; then
            printf '\e[34m--------------------------------------------------\e[0m \e[38;2;250;208;148m[%s]\e[0m\n' "$dur_str2"
        else
            printf '\e[34m--------------------------------------------------\e[0m\n'
        fi

        # Re-extract blocks
        blocks_str="$(_aith_extract_code_blocks "$text")"
        blocks=("${(@ps:\x1f:)blocks_str}")

        if (( ${#blocks[@]} > 0 )); then
            printf '\n\e[36m✨ Comandos Disponíveis:\e[0m\n'
            for ((i = 1; i <= ${#blocks[@]}; i++)); do
                local preview_line="$(print -r -- "${blocks[$i]}" | head -n 1 | cut -c 1-80)"
                preview_line="$(_aith_trim "$preview_line")"
                printf "  \e[1;34m[%d]\e[0m 💻 %s\n" "$i" "$preview_line"
            done
            printf '\n'
        fi
    done
}