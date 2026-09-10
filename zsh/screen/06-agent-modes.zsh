#!/usr/bin/env zsh
# =============================================================================
# screen/06-agent-modes.zsh
# Modos de execução do agente: modo assistido padrão e modo /auto autônomo.
# =============================================================================

consultar_agente() {
  local current_context="$1"
  local step=0
  local max_steps=4
  local final_response=""

  local t_start=${EPOCHREALTIME:-$(date +%s 2>/dev/null)}

  while (( step < max_steps )); do
    local raw_response=""

    raw_response="$(chamar_ia "$current_context")"
    local exit_status=$?

    if (( exit_status == 130 )); then
      return 130
    fi

    if [[ -z "$raw_response" ]]; then
      final_response="A IA não retornou resposta."
      break
    fi

    if _parse_tool_call "$raw_response"; then
      local tool_result=""

      tool_result="$(executar_ferramenta "$TOOL_NAME" "$TOOL_PATH" "$TOOL_CONTENT")"
      local tool_status=$?

      current_context="$current_context
[Assistente]: $raw_response
<tool_result>
$tool_result
</tool_result>
[Sistema]: Ação finalizada com código $tool_status. Analise o resultado acima e responda ao usuário ou continue se precisar:"

      (( step++ ))
    else
      if command -v perl >/dev/null 2>&1; then
        final_response="$(print -r -- "$raw_response" | perl -0777 -pe 's/<tool_call[^>]*>.*?<\/tool_call>//gs; s/<tool_result[^>]*>.*?<\/tool_result>//gs' 2>/dev/null)"
      else
        final_response="$raw_response"
      fi

      break
    fi
  done

  if [[ -z "$final_response" ]]; then
    final_response="Limite de passos do agente atingido sem resposta final."
  fi

  local t_end=${EPOCHREALTIME:-$(date +%s 2>/dev/null)}
  LAST_DURATION=$(( t_end - t_start ))

  print -r -- "$final_response"
}

resolver_automatico_no_terminal() {
  local raw_input="$1"

  extrair_linhas_e_query "$raw_input" "$DEFAULT_SCREEN_LINES"

  local auto_lines="$PARSED_LINES"
  local extra_goal="$PARSED_QUERY"

  local max_steps="${AI_AUTO_MAX_STEPS:-6}"
  local step=1
  local nova_tela=""
  local resp=""

  typeset -g AUTO_CANCEL=0
  trap 'AUTO_CANCEL=1' INT

  printf '\n\033[1;35m🚀 [Modo Auto-Resolução (%d linhas)]: Assumindo controle do terminal original...\033[0m\n' "$auto_lines"
  printf '\033[90mOs comandos serão executados diretamente no seu terminal de trabalho.\033[0m\n'
  printf '%s\n' "─────────────────────────────────────────"

  local screen_init
  screen_init="$(recapturar_tela "$auto_lines" 2>/dev/null)"
  [[ -z "$screen_init" ]] && screen_init="$SCREEN_CONTENT"

  local auto_prompt="Você é um Agente Linux autônomo conectado diretamente ao terminal do usuário.
[Terminal do Usuário (últimas $auto_lines linhas)]:
$screen_init

O usuário pediu: ${extra_goal:-Investigar a causa do erro na tela do terminal, aplicar as correções necessárias e resolver o problema.}

DIRETRIZES DE EXECUÇÃO:
1. Para cada ação ou verificação necessária, envie a ferramenta bash:
<tool_call name=\"bash\">
comando_para_executar
</tool_call>

2. O comando será executado diretamente no terminal e você receberá a saída real da tela.
3. Se o pedido contiver múltiplos objetivos (ex: descobrir IP, testar internet, listar portas TCP), você DEVE executar os comandos no terminal para CADA um deles.
4. NUNCA invente, deduza ou simule resultados de comandos que você não executou.
5. Apenas quando TODAS as tarefas pedidas tiverem sido REALMENTE executadas e verificadas no terminal, responda com o relatório final em Markdown no seguinte formato (NUNCA USE TABELAS):

### 🎯 Diagnóstico / Cenário
- Explique de forma clara o que estava acontecendo, a causa raiz ou o que foi investigado.

### ⚡ Comandos Executados e Explicações
**1. \`comando 1\`**
- **O que faz:** Explicação clara e objetiva do objetivo do comando.
- **Resultado obtido:** O que o comando retornou na tela ou alterou no sistema.

**2. \`comando 2\`**
- **O que faz:** Explicação clara do objetivo do comando.
- **Resultado obtido:** O que o comando retornou na tela.

### 🏁 Estado Final / Conclusão
- Resumo final confirmando o sucesso da resolução e o estado atual do sistema.

REGRA IMPORTANTE:
- Ao final do relatório, se houver comandos úteis para o usuário guardar ou rodar, coloque-os dentro de blocos de código com três crases (\`\`\`bash) SEMPRE com comentários inline (# breve explicação) no final de cada linha para que fiquem disponíveis na lista numerada com explicação completa."

  local current_context="[Instrução do Agente]: $auto_prompt"

  while (( step <= max_steps )); do
    if (( AUTO_CANCEL == 1 )); then
      printf '\n\033[33m⚠️ Auto-resolução cancelada pelo usuário (Ctrl+C).\033[0m\n'
      trap ' ' INT
      return 130
    fi

    printf '\033[34m🤖 [Passo %d/%d]: IA planejando próxima ação...\033[0m\n' "$step" "$max_steps"

    resp="$(chamar_ia "$current_context")"
    local ia_status=$?

    if (( ia_status == 130 )) || [[ "$resp" == *"KeyboardInterrupt"* || "$resp" == *"Interrupted"* ]]; then
      printf '\n\033[33m⚠️ Auto-resolução cancelada pelo usuário (Ctrl+C).\033[0m\n'
      trap ' ' INT
      return 130
    fi

    trap 'AUTO_CANCEL=1' INT

    if [[ -z "$resp" ]]; then
      _warn "A IA não retornou resposta."
      break
    fi

    if _parse_tool_call "$resp"; then
      local cmd="$TOOL_CONTENT"
      [[ -z "$cmd" ]] && cmd="$TOOL_PATH"
      cmd="$(_trim "$cmd")"

      if [[ -z "$cmd" ]]; then
        current_context="$current_context
[Assistente]: $resp
<tool_result>
Erro: tool_call sem comando válido.
</tool_result>"
        (( step++ ))
        continue
      fi

      printf '\n\033[36m⚡ [Passo %d/%d - Ação]: \033[1;38;5;214m%s\033[0m\n' "$step" "$max_steps" "$cmd"

      if _is_risky_auto_cmd "$cmd"; then
        _auto_log "SENSÍVEL: $cmd"

        if ! _confirmar_acao "A IA quer executar no seu terminal original: \033[1;33m$cmd\033[0m"; then
          printf '\033[31m✖ Ação cancelada pelo usuário.\033[0m\n'
          _auto_log "NEGADO: $cmd"

          current_context="$current_context
[Assistente]: $resp
<tool_result>
Ação '$cmd' cancelada pelo usuário. Sugira outra abordagem ou finalize.
</tool_result>"

          (( step++ ))
          continue
        fi
      fi

      if [[ "$cmd" == *$'\n'* && "${AI_AUTO_ALLOW_MULTILINE:-0}" != "1" ]]; then
        _auto_log "MULTILINHA: $cmd"
        if ! _confirmar_acao "A IA quer executar no seu terminal original um comando com múltiplas linhas:
\033[1;33m$cmd\033[0m
Deseja continuar mesmo assim?"; then
          printf '\033[31m✖ Ação multilinha cancelada pelo usuário.\033[0m\n'
          _auto_log "NEGADO: $cmd"
          current_context="$current_context
[Assistente]: $resp
<tool_result>
Ação multilinha cancelada pelo usuário. Sugira outra abordagem ou finalize.
</tool_result>"
          (( step++ ))
          continue
        fi
      fi

      printf '\033[32m⌨️  Enviando e executando no seu terminal principal...\033[0m\n'

      if ! AI_AUTO_CONFIRMED=1 enviar_ao_kitty "$cmd" "" 1; then
        _auto_log "FALHA AO ENVIAR: $cmd"

        current_context="$current_context
[Assistente]: $resp
<tool_result>
Erro: não foi possível enviar o comando ao terminal original.
</tool_result>"

        (( step++ ))
        continue
      fi

      _auto_log "EXECUTADO: $cmd"

      sleep "${AI_AUTO_SLEEP:-2}"

      if (( AUTO_CANCEL == 1 )); then
        printf '\n\033[33m⚠️ Auto-resolução cancelada pelo usuário (Ctrl+C).\033[0m\n'
        trap ' ' INT
        return 130
      fi

      nova_tela="$(recapturar_tela 50)"

      if [[ "$nova_tela" == *"$cmd"* ]]; then
        nova_tela="${nova_tela#*"$cmd"}"
      fi

      current_context="$current_context
[Assistente]: $resp
<tool_result>
[Saída do comando '$cmd']:
$nova_tela
</tool_result>
[Sistema]: Analise a saída acima. Se ainda faltam verificações ou comandos para cumprir integralmente o que o usuário pediu, envie a próxima <tool_call name=\"bash\">. NUNCA invente saídas de comandos que não rodaram. Apenas envie o relatório final se TODOS os itens solicitados já foram executados e confirmados:"

      current_context="$(limitar_contexto "$current_context")"

      (( step++ ))
    else
      printf '\n\033[1;32m═════════════════════════════════════════════════════════════\033[0m\n'
      printf '\033[1;32m🎉 PROBLEMA RESOLVIDO / DIAGNÓSTICO FINAL\033[0m\n'
      printf '\033[1;32m═════════════════════════════════════════════════════════════\033[0m\n'

      if command -v perl >/dev/null 2>&1; then
        resp="$(print -r -- "$resp" | perl -0777 -pe 's/<tool_call[^>]*>.*?<\/tool_call>//gs; s/<tool_result[^>]*>.*?<\/tool_result>//gs' 2>/dev/null)"
      fi

      renderizar "$resp"

      LAST_RESPONSE="$resp"

      extrair_blocos "$LAST_RESPONSE"
      exibir_blocos

      printf '%s\n' "─────────────────────────────────────────"

      trap ' ' INT
      return 0
    fi
  done

  if (( step > max_steps )); then
    printf '\n\033[33m⏱️ Limite de ações atingido (%d passos). Gerando relatório final consolidado...\033[0m\n' "$max_steps"
    local final_report_prompt="$current_context
[Sistema]: O limite de passos foi atingido. NÃO envie novas ferramentas ou comandos. Apresente agora o relatório final consolidado com Diagnóstico, Ações Realizadas e Conclusão:"
    resp="$(chamar_ia "$final_report_prompt")"

    if command -v perl >/dev/null 2>&1; then
      resp="$(print -r -- "$resp" | perl -0777 -pe 's/<tool_call[^>]*>.*?<\/tool_call>//gs; s/<tool_result[^>]*>.*?<\/tool_result>//gs' 2>/dev/null)"
    fi

    printf '\n\033[1;32m═════════════════════════════════════════════════════════════\033[0m\n'
    printf '\033[1;32m📋 RELATÓRIO FINAL DA AUTO-RESOLUÇÃO\033[0m\n'
    printf '\033[1;32m═════════════════════════════════════════════════════════════\033[0m\n'

    renderizar "$resp"
    LAST_RESPONSE="$resp"
    extrair_blocos "$LAST_RESPONSE"
    exibir_blocos
    printf '%s\n' "─────────────────────────────────────────"
  elif [[ -n "$resp" ]]; then
    if command -v perl >/dev/null 2>&1; then
      resp="$(print -r -- "$resp" | perl -0777 -pe 's/<tool_call[^>]*>.*?<\/tool_call>//gs; s/<tool_result[^>]*>.*?<\/tool_result>//gs' 2>/dev/null)"
    fi
    renderizar "$resp"
    LAST_RESPONSE="$resp"
    extrair_blocos "$LAST_RESPONSE"
    exibir_blocos
    printf '%s\n' "─────────────────────────────────────────"
  fi

  trap ' ' INT
  return 0
}
