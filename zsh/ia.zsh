#!/usr/bin/env zsh
# =============================================================================
# ia.zsh - Pipeline de IA com formatação colorida
# Versão corrigida:
# - Limita entrada via pipe
# - Usa código de retorno do _ai_query
# - Não trata qualquer emoji no meio do texto como erro
# - Mantém saída pura quando redirecionada
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || true

if (( ! $+functions[_ai_query] )); then
  return 0 2>/dev/null || exit 0
fi

ia() {
  local query="$*"
  local piped_data=""

  if [[ ! -t 0 ]]; then
    local pipe_limit="${AI_MAX_PIPE_BYTES:-100000}"
    [[ "$pipe_limit" =~ ^[0-9]+$ ]] || pipe_limit=100000

    piped_data="$(head -c "$pipe_limit" 2>/dev/null | tr -d '\000')"

    if (( ${#piped_data} >= pipe_limit )); then
      piped_data="${piped_data}

[Observação: a entrada do pipe pode ter sido truncada por segurança.]"
    fi
  fi

  if [[ -z "$query" && -z "$piped_data" ]]; then
    echo -e "\e[33mUso:\e[0m cat arquivo.txt | ia 'explique isso' \e[90mOU\e[0m ia 'sua pergunta direta'"
    return 1
  fi

  local prompt=""

  if [[ -n "$piped_data" ]]; then
    prompt="Você é um assistente especialista em Linux e terminal.

Analise os seguintes dados fornecidos via pipe pelo usuário:

---
${piped_data}
---

Instrução/Pergunta do usuário: ${query:-Analise a saída acima, explique o que está acontecendo e sugira os comandos necessários para resolver ou prosseguir.}

Regras de formatação:
1. Use títulos em Markdown (#, ##) para organizar a resposta.
2. Use blocos de código markdown (\`\`\`bash) para qualquer comando sugerido.
3. Explique flags e opções usando listas com marcadores (* ou -).
4. Destaque termos e comandos inline com crases (\`comando\`)."
  else
    prompt="${query}"
  fi

  _ai_get_current_provider_info

  if [[ -t 1 ]]; then
    local m_icon="$(_ai_get_metis_icon)"
    echo -e "${m_icon}\e[38;2;250;208;148m[Metis]:\e[0m \e[34mConsultando ${AI_ACTIVE_LABEL}...\e[0m"
  fi

  local response rc err_file
  err_file="$(mktemp "${TMPDIR:-/tmp}/ai_cli.XXXXXX" 2>/dev/null)" || err_file="${TMPDIR:-/tmp}/ai_cli.$$"

  response="$(_ai_query "$prompt" 2>"$err_file")"
  rc=$?

  if (( rc != 0 )); then
    if [[ -s "$err_file" ]]; then
      cat "$err_file" >&2
    else
      echo -e "\e[31m⚠️ Falha ao comunicar com ${AI_ACTIVE_LABEL}.\e[0m" >&2
    fi
    rm -f "$err_file"
    return 1
  fi

  rm -f "$err_file"

  if [[ -z "$(_ai_trim "$response")" ]]; then
    echo -e "\e[31m⚠️ A IA retornou resposta vazia.\e[0m" >&2
    return 1
  fi

  if [[ "$response" == ⚠️* ]]; then
    echo -e "\e[31m${response}\e[0m" >&2
    return 1
  fi

  if [[ -t 1 ]]; then
    echo ""
    _ai_render_formatted "$response"
    echo ""
  else
    print -r -- "$response"
  fi
}

alias ai="ia"
