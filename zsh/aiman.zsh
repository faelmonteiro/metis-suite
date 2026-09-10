#!/usr/bin/env zsh
# =============================================================================
# aiman.zsh - O Man Page do Futuro
# Conectado à IA ativa selecionada no Ctrl+G (Ollama, Gemini, Groq, NVIDIA ou G4F)
#
# Uso:
#   aiman <comando>
#   Exemplos:
#     aiman tar
#     aiman git commit
#     aiman ffmpeg
# =============================================================================

unalias aiman 2>/dev/null || true

ZSH_AI_DIR="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}"
if [[ ! -f "$ZSH_AI_DIR/ia_client.zsh" ]]; then
    print "\e[31m⚠️ Erro: Arquivo $ZSH_AI_DIR/ia_client.zsh não encontrado.\e[0m" >&2
    return 1 2>/dev/null || exit 1
fi
source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || true

aiman() {
    local cmd="$*"
    if [[ -z "$cmd" ]]; then
        print "Uso: aiman <comando>"
        print "Exemplo: aiman tar -xvf"
        return 1
    fi

    local safe_cmd="${cmd//\'/\\\'}"

    local prompt="Explique de forma resumida e didática para que serve o comando Linux '$safe_cmd'.
Forneça os 3 a 5 exemplos práticos mais comuns de uso desse comando.
Use formatação Markdown clara (títulos e blocos de código)."

    if (( ${+functions[_ai_get_current_provider_info]} )); then
        _ai_get_current_provider_info
    fi

    local m_icon="🏛️ "
    if (( ${+functions[_ai_get_metis_icon]} )); then
        m_icon="$(_ai_get_metis_icon)"
    fi

    local prov_label="${AI_ACTIVE_LABEL:-IA Ativa}"
    printf '\n%s\e[38;2;250;208;148m[Metis]:\e[0m \e[33mGerando manual de \e[1;37m%s\e[0m \e[33mvia %s...\e[0m\n' "$m_icon" "$cmd" "$prov_label"

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
    printf '\n%s\e[32m================ MANUAL EXPRESSO: %s (%s) ================\e[0m\n\n' "$m_icon" "$cmd" "$prov_label"

    if command -v glow >/dev/null 2>&1; then
        print -r -- "$text" | glow -
    else
        print -r -- "$text"
    fi

    if [[ -n "$dur_str" ]]; then
        printf '\n\e[32m=========================================================\e[0m \e[38;2;250;208;148m[%s]\e[0m\n\n' "$dur_str"
    else
        print "\n\e[32m=========================================================\e[0m\n"
    fi
}
