#!/usr/bin/env zsh
# =============================================================================
# screen/06-agent-modes.zsh
# Modos de execução do agente: modo assistido padrão e modo /auto autônomo.
# =============================================================================

consultar_agente() {
  local current_context="$1"
  local step=0
  local max_steps="${PARSED_STEPS:-${AI_AGENT_MAX_STEPS:-${AI_AUTO_MAX_STEPS:-6}}}"
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

  extrair_linhas_e_query "$raw_input" "${DEFAULT_SCREEN_LINES:-30}"

  local auto_lines="${PARSED_LINES:-30}"
  [[ "$auto_lines" =~ ^[0-9]+$ ]] || auto_lines=30
  (( auto_lines < 1 )) && auto_lines=30
  local extra_goal="$PARSED_QUERY"

  local max_steps="${PARSED_STEPS:-${AI_AUTO_MAX_STEPS:-6}}"
  local step=1
  local nova_tela=""
  local resp=""

  local screen_init=""
  local label_fonte="Terminal do Usuário (últimas $auto_lines linhas)"

  if [[ "$MODO_CAPTURA" == "mouse" && -n "$SCREEN_CONTENT" ]]; then
    screen_init="$SCREEN_CONTENT"
    label_fonte="Seleção Ativa do Mouse no Terminal"
  else
    screen_init="$(recapturar_tela "$auto_lines" 2>/dev/null)"
    [[ -z "$screen_init" ]] && screen_init="$SCREEN_CONTENT"
  fi

  local real_lines=0
  if [[ -n "$screen_init" ]]; then
    real_lines=$(print -r -- "$screen_init" | wc -l)
    real_lines="${real_lines##* }"
  fi
  (( real_lines == 0 )) && real_lines="$auto_lines"

  printf '\n\033[1;35m🚀 Modo Auto-Resolução (%d linhas • até %d passos)\033[0m\n' "$real_lines" "$max_steps"
  printf '\033[90mControle autônomo conectado ao terminal de trabalho.\033[0m\n'
  printf '%s\n' "──────────────────────────────────────────────────────────"

  obter_status_ultimo_comando "${TARGET_KITTY_WIN:-}"
  local last_cmd_header=""
  if [[ -n "$LAST_CMD_NAME" ]]; then
    local status_label="0 (Sucesso)"
    [[ "$LAST_CMD_EXIT" != "0" ]] && status_label="$LAST_CMD_EXIT (Falha / Erro)"
    last_cmd_header="
[Último Comando Executado no Terminal]: $LAST_CMD_NAME
[Código de Retorno / Exit Code]: $status_label"
  fi

  local prev_diag_header=""
  if [[ -n "$LAST_RESPONSE" ]]; then
    prev_diag_header="
[Diagnóstico Inicial Identificado]:
$LAST_RESPONSE
"
  fi

  local auto_prompt="Você é um Agente Linux autônomo conectado diretamente ao terminal do usuário.${last_cmd_header}${prev_diag_header}
[${label_fonte}]:
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
      trap '_metis_exit_handler' INT TERM 2>/dev/null || trap - INT TERM
      return 130
    fi

    printf '\n\033[1;34m🤖 [Passo %d/%d]\033[0m \033[90mPlanejando próxima ação...\033[0m\n' "$step" "$max_steps"

    resp="$(chamar_ia "$current_context")"
    local ia_status=$?

    if (( ia_status == 130 )) || [[ "$resp" == *"KeyboardInterrupt"* || "$resp" == *"Interrupted"* ]]; then
      printf '\n\033[33m⚠️ Auto-resolução cancelada pelo usuário (Ctrl+C).\033[0m\n'
      trap '_metis_exit_handler' INT TERM 2>/dev/null || trap - INT TERM
      return 130
    fi

    trap 'AUTO_CANCEL=1' INT

    if [[ -z "$resp" ]]; then
      _warn "A IA não retornou resposta."
      break
    fi

    if _parse_tool_call "$resp"; then
      local t_name="${(L)TOOL_NAME:-bash}"

      # Se for uma ferramenta de leitura/escrita de arquivo ou listagem de pastas, executa diretamente
      if [[ "$t_name" != "bash" && "$t_name" != "exec" && "$t_name" != "sh" && "$t_name" != "run_command" ]]; then
        local tool_res=""
        local tool_code=0
        tool_res="$(executar_ferramenta "$TOOL_NAME" "$TOOL_PATH" "$TOOL_CONTENT")"
        tool_code=$?

        current_context="$current_context
[Assistente]: $resp
<tool_result>
$tool_res
</tool_result>
[Sistema]: Ação finalizada com código $tool_code. Analise o resultado acima e responda com o relatório final ou continue se ainda faltarem passos:"
        current_context="$(limitar_contexto "$current_context")"
        (( step++ ))
        continue
      fi

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

      printf '\033[1;36m⚡ [Passo %d/%d - Ação]:\033[0m\n  \033[1;38;5;214m$ %s\033[0m\n' "$step" "$max_steps" "$cmd"

      local precisa_confirmar=0
      local motivo_confirmacao=""

      if _is_risky_auto_cmd "$cmd"; then
        precisa_confirmar=1
        motivo_confirmacao="Comando potencialmente sensível"
      elif [[ "$cmd" == *$'\n'* && "${AI_AUTO_ALLOW_MULTILINE:-0}" != "1" ]]; then
        local n_linhas_cmd=0
        n_linhas_cmd=$(print -r -- "$cmd" | grep -c .)
        if (( n_linhas_cmd > 1 )); then
          precisa_confirmar=1
          motivo_confirmacao="Comando multilinha"
        fi
      fi

      if (( precisa_confirmar )); then
        _auto_log "CONFIRMAR: $cmd ($motivo_confirmacao)"

        if ! _confirmar_acao_formatada "$cmd" "$motivo_confirmacao"; then
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

      _obter_kitty_target
      local status_info=""

      # Se estiver no modo Kitty Popup com socket remoto válido, envia para a janela de origem
      if [[ -n "$METIS_KITTY_POPUP" && -n "$TARGET_KITTY_SOCK" ]]; then
        local win_target="${TARGET_KITTY_WIN:-}"
        [[ -n "$win_target" ]] && rm -f "/tmp/metis_status_${win_target}" 2>/dev/null
        rm -f "/tmp/metis_last_status" 2>/dev/null

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

        local waited=0
        local max_wait="${AI_AUTO_TIMEOUT:-12}"
        local check_status_file="/tmp/metis_last_status"
        [[ -n "$win_target" ]] && check_status_file="/tmp/metis_status_${win_target}"

        while (( waited < max_wait * 10 )); do
          if (( AUTO_CANCEL == 1 )); then
            break
          fi
          if [[ -f "$check_status_file" ]]; then
            sleep 0.15
            break
          fi
          sleep 0.1
          (( waited++ ))
        done

        if [[ ! -f "$check_status_file" ]]; then
          sleep "${AI_AUTO_SLEEP:-1.5}"
        fi

        if (( AUTO_CANCEL == 1 )); then
          printf '\n\033[33m⚠️ Auto-resolução cancelada pelo usuário (Ctrl+C).\033[0m\n'
          trap '_metis_exit_handler' INT TERM 2>/dev/null || trap - INT TERM
          return 130
        fi

        nova_tela="$(recapturar_tela "${DEFAULT_SCREEN_LINES:-30}")"

        if [[ "$nova_tela" == *"$cmd"* ]]; then
          nova_tela="${nova_tela#*"$cmd"}"
        fi

        obter_status_ultimo_comando "$win_target"

        if [[ -n "$LAST_CMD_EXIT" ]]; then
          if [[ "$LAST_CMD_EXIT" == "0" ]]; then
            status_info="[Status de Retorno / Exit Code]: 0 (Sucesso / OK)"
            printf '\033[32m✔ Executado no terminal (Sucesso)\033[0m\n'
          else
            status_info="[Status de Retorno / Exit Code]: $LAST_CMD_EXIT (Erro / Falha)"
            printf '\033[33m⚠ Executado no terminal (Exit: %s)\033[0m\n' "$LAST_CMD_EXIT"
          fi
        else
          printf '\033[32m✔ Executado no terminal\033[0m\n'
        fi
      else
        # Modo Terminal Direto (execução inline no terminal atual)
        printf '\n\033[1;33m▶ Executando:\033[0m \033[1;37m%s\033[0m\n' "$cmd"
        local tmp_cmd_out=""
        tmp_cmd_out="$(mktemp)"
        local cmd_exit_code=0

        if command -v timeout >/dev/null 2>&1; then
          timeout 30 zsh -c "$cmd" >"$tmp_cmd_out" 2>&1
          cmd_exit_code=$?
        else
          zsh -c "$cmd" >"$tmp_cmd_out" 2>&1
          cmd_exit_code=$?
        fi

        local cmd_output="$(cat "$tmp_cmd_out" 2>/dev/null)"
        rm -f "$tmp_cmd_out" 2>/dev/null

        if [[ -n "$cmd_output" ]]; then
          printf '%s\n' "$cmd_output" | head -n 30
          local total_l=$(print -r -- "$cmd_output" | wc -l)
          total_l="${total_l##* }"
          (( total_l > 30 )) && printf '\033[90m[... +%d linhas de saída omitidas ...]\033[0m\n' "$(( total_l - 30 ))"
        else
          printf '\033[90m(Comando executado sem retorno de texto)\033[0m\n'
        fi

        if (( cmd_exit_code == 0 )); then
          printf '\033[32m✔ Sucesso (Exit: 0)\033[0m\n'
          status_info="[Status de Retorno / Exit Code]: 0 (Sucesso / OK)"
        else
          printf '\033[31m⚠ Falha na execução (Exit: %d)\033[0m\n' "$cmd_exit_code"
          status_info="[Status de Retorno / Exit Code]: $cmd_exit_code (Erro / Falha)"
        fi
        nova_tela="$cmd_output"
        _auto_log "EXECUTADO LOCAL: $cmd (Exit: $cmd_exit_code)"
      fi

      current_context="$current_context
[Assistente]: $resp
<tool_result>
[Comando executado]: $cmd
${status_info}
[Saída capturada do terminal]:
${nova_tela:-(Sem saída de texto adicional)}
</tool_result>
[Sistema]: Analise o status de retorno e a saída acima. Se o comando resolveu o erro com sucesso ou se ainda faltam verificações ou comandos para cumprir integralmente o que o usuário pediu, envie a próxima <tool_call name=\"bash\">. NUNCA invente saídas de comandos que não rodaram. Apenas envie o relatório final se TODOS os itens solicitados já foram executados e confirmados:"

      current_context="$(limitar_contexto "$current_context")"

      (( step++ ))
    else
      printf '\n\033[1;32m═════════════════════════════════════════════════════════════\033[0m\n'
      printf '\033[1;32m🎉 PROBLEMA RESOLVIDO / DIAGNÓSTICO FINAL\033[0m\n'
      printf '\033[1;32m═════════════════════════════════════════════════════════════\033[0m\n'

      if command -v perl >/dev/null 2>&1; then
        resp="$(print -r -- "$resp" | perl -0777 -pe 's/<tool_call[^>]*>.*?<\/tool_call>//gs; s/<function[^>]*>.*?<\/function>//gs; s/<tool_result[^>]*>.*?<\/tool_result>//gs; s/<\/?(parameter|function|tool_call)[^>]*>//gi' 2>/dev/null)"
      fi

      renderizar "$resp"

      LAST_RESPONSE="$resp"

      extrair_blocos "$LAST_RESPONSE"
      exibir_blocos

      printf '%s\n' "─────────────────────────────────────────"

      trap '_metis_exit_handler' INT TERM 2>/dev/null || trap - INT TERM
      return 0
    fi
  done

  if (( step > max_steps )); then
    printf '\n\033[33m⏱️ Limite de ações atingido (%d passos). Gerando relatório final consolidado...\033[0m\n' "$max_steps"
    local final_report_prompt="$current_context
[Sistema]: O limite de passos foi atingido. NÃO envie novas ferramentas ou comandos. Apresente agora o relatório final consolidado com Diagnóstico, Ações Realizadas e Conclusão:"
    resp="$(chamar_ia "$final_report_prompt")"

    if command -v perl >/dev/null 2>&1; then
      resp="$(print -r -- "$resp" | perl -0777 -pe 's/<tool_call[^>]*>.*?<\/tool_call>//gs; s/<function[^>]*>.*?<\/function>//gs; s/<tool_result[^>]*>.*?<\/tool_result>//gs; s/<\/?(parameter|function|tool_call)[^>]*>//gi' 2>/dev/null)"
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

  trap '_metis_exit_handler' INT TERM 2>/dev/null || trap - INT TERM
  return 0
}
