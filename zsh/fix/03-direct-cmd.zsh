#!/usr/bin/env zsh
# =============================================================================
# fix/03-direct-cmd.zsh
# Geração direta de comandos e inserção inteligente no prompt (ZLE).
# =============================================================================

_ai_fix_exec_comando_direto() {
  local context="$1"
  local busca="$2"

  local ai_prompt="Contexto: $context. Retorne o comando para: $busca. Envie o comando dentro de um bloco de código markdown (com três crases). Sem explicações adicionais."
  local resposta=""

  resposta="$(_ai_fix_query "$ai_prompt" "Gerando comando")"
  resposta="${resposta//$'\r'/}"

  if [[ -z "$resposta" ]]; then
    printf '\033[33m⚠️ Ação cancelada ou sem resposta da IA.\033[0m\n'
    return 0
  fi

  local cmd="$(_ai_fix_clean_command "$resposta")"

  if [[ -z "$cmd" ]]; then
    printf '\033[33m⚠️ A IA não retornou um comando válido.\033[0m\n'
    _ai_fix_pause
    return 0
  fi

  _ai_fix_insert_command "$cmd"
}
