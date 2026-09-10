#!/usr/bin/env zsh
# =============================================================================
# autocomplete.zsh - Sugestão e Autocomplete Inline com IA (Ctrl + X Ctrl + P)
# Versão corrigida:
# - Não insere erro na linha de comando
# - Trata falha do provedor
# - Filtra resposta vazia
# - Remove crases e caracteres de erro
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || true

if (( ! $+functions[_ai_query] )); then
  return 0 2>/dev/null || exit 0
fi

_ai_autocomplete_complete() {
  if [[ -z "$LBUFFER" ]]; then
    return 0
  fi

  _ai_get_current_provider_info

  local prompt="Você é um autocompletador de linha de comando para o Zsh Linux.
O usuário já digitou o seguinte no prompt do terminal:
$LBUFFER

Regras:
1. Retorne APENAS a string de continuação que completa o comando de forma lógica e precisa.
2. NÃO repita a parte que o usuário já digitou.
3. Sem explicações, sem crases de markdown, apenas o texto bruto para concatenar.
4. Se o comando já estiver completo, retorne vazio."

  zle -M "🤖 Sugerindo continuação via ${AI_ACTIVE_LABEL}..."
  zle -R

  local text rc err_file
  err_file="$(mktemp "${TMPDIR:-/tmp}/ai_autocomplete.XXXXXX" 2>/dev/null)" || err_file="${TMPDIR:-/tmp}/ai_autocomplete.$$"

  text="$(_ai_query "$prompt" 20 2>"$err_file")"
  rc=$?

  if (( rc != 0 )); then
    local err_line=""
    if [[ -s "$err_file" ]]; then
      err_line="$(head -n 1 "$err_file")"
      err_line="${err_line//$'\n'/ }"
      err_line="${err_line//$'\r'/ }"
    fi
    rm -f "$err_file"
    if [[ -n "$err_line" ]]; then
      zle -M "❌ Falha na IA: $err_line"
    else
      zle -M "❌ Falha ao consultar ${AI_ACTIVE_LABEL}"
    fi
    return 1
  fi

  rm -f "$err_file"

  if [[ "$text" == ⚠️* || "$text" == Traceback* || "$text" == Erro* || "$text" == Error* || "$text" == Fatal* ]]; then
    zle -M "❌ A IA retornou um erro."
    return 1
  fi

  text="${text//[$'\r'\`]/}"
  local -a lines=("${(@f)text}")
  text=""
  local l
  for l in "${lines[@]}"; do
    l="${l#"${l%%[![:space:]]*}"}"
    l="${l%"${l##*[![:space:]]}"}"
    if [[ -n "$l" ]]; then
      text="$l"
      break
    fi
  done

  if [[ -z "$text" ]]; then
    zle -M "Nenhuma sugestão."
    return 0
  fi

  LBUFFER+="$text"
  zle -M "✅ Completado via ${AI_ACTIVE_LABEL}"
}

if [[ -o interactive ]]; then
  zle -N _ai_autocomplete_complete
  bindkey '^X^P' _ai_autocomplete_complete
fi
