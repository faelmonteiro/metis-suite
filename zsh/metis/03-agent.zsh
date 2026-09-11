#!/usr/bin/env zsh
# =============================================================================
# metis/03-agent.zsh
# Loop autônomo do copiloto Metis, orquestração de comandos e aliases.
# =============================================================================

metis() {
  _metis_require_deps || return 1

  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    printf '\033[33m⚠️  Aviso: Metis está rodando como root. Tenha cuidado.\033[0m\n'
  fi

  local num_lines=30
  local has_line_flag=0
  local max_steps="${METIS_MAX_STEPS:-5}"
  local -a query_words=()

  # Suporte a flags: -p/--passos <n>, -p<n>, -n/--lines <n>, -n<n>, -<n> (ex: -50)
  while (( $# > 0 )); do
    case "$1" in
      -p|--passos|--steps)
        shift
        if [[ "$1" == <-> ]]; then
          max_steps="$1"
          shift
        fi
        ;;
      -p<->)
        max_steps="${1#-p}"
        shift
        ;;
      -n|--lines)
        shift
        if [[ "$1" == <-> ]]; then
          num_lines="$1"
          has_line_flag=1
          shift
        fi
        ;;
      -n<->)
        num_lines="${1#-n}"
        has_line_flag=1
        shift
        ;;
      -<->)
        num_lines="${1#-}"
        has_line_flag=1
        shift
        ;;
      *)
        query_words+=("$1")
        shift
        ;;
    esac
  done

  local query="${(j: :)query_words}"
  local screen_ctx=""

  [[ "$num_lines" == <-> ]] || num_lines=30
  (( num_lines < 1 )) && num_lines=30
  (( num_lines > 500 )) && num_lines=500

  [[ "$max_steps" == <-> ]] || max_steps=5
  (( max_steps < 1 )) && max_steps=1

  query="$(print -r -- "$query" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

  if [[ -z "$query" ]]; then
    local last_cmd=""

    last_cmd="$(fc -ln -1 2>/dev/null | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    screen_ctx="$(_metis_capture_screen "$num_lines")"

    if [[ -n "$screen_ctx" ]]; then
      query="O usuário acabou de executar o comando '$last_cmd' e encontrou um erro. Analise o contexto recente do terminal abaixo ($num_lines linhas) e resolva o problema:
$screen_ctx"
    elif [[ -n "$last_cmd" ]]; then
      query="O último comando executado no terminal foi '$last_cmd'. Investigue o erro e resolva o problema."
    else
      query="Investigue o estado do sistema ou o último erro do terminal e resolva o problema."
    fi
  else
    # Se informou query com flag de linhas, anexa contexto da tela.
    if (( has_line_flag )); then
      screen_ctx="$(_metis_capture_screen "$num_lines")"

      if [[ -n "$screen_ctx" ]]; then
        query="$query
[Contexto da tela do terminal ($num_lines linhas)]:
$screen_ctx"
      fi
    fi
  fi

  _ai_get_current_provider_info

  local icon="$(_ai_get_metis_icon)"
  local active_label="${AI_ACTIVE_LABEL:-IA ativa}"

  printf '\n%s\033[1;38;2;240;195;115m[Metis]: \033[0m\033[90mIniciando copiloto (%d linhas, até %d passos) via %s...\033[0m\n' "$icon" "$num_lines" "$max_steps" "$active_label"

  local system_prompt="Você é a Metis, uma Copiloto Autônoma Linux de alta precisão.

O usuário pediu para resolver o seguinte problema:
$query

DIRETRIZES DE RESPOSTA:
1. Para cada ação ou diagnóstico que você precisar fazer no terminal do usuário, envie EXATAMENTE uma ferramenta no formato:
<tool_call name=\"bash\">
comando_para_executar
</tool_call>

2. REGRAS OBRIGATÓRIAS DE SINTAXE:
- NUNCA use tags adicionais internas como <cmd>, <command> ou blocos de markdown dentro de <tool_call>.
- SEMPRE feche a tag com </tool_call>.
- Não adicione explicações teóricas nem introduções antes ou durante a execução dos comandos.
- Cada comando roda em shell isolado; portanto, use comandos autocontidos.
- Se precisar mudar de diretório, use: cd /caminho && comando.

3. REGRAS DE SEGURANÇA:
- Prefira comandos de diagnóstico antes de comandos de alteração.
- Não execute comandos destrutivos sem necessidade.
- Evite comandos interativos.
- Não tente ler segredos, tokens, chaves privadas ou arquivos sensíveis sem motivo claro.

4. Você receberá o resultado da execução do comando e poderá decidir o próximo passo.

5. Quando o problema estiver resolvido e concluído, NÃO envie mais ferramentas. Apenas responda com UMA ÚNICA FRASE direta no formato:
✔ Resolvido: <resumo de uma linha do que foi verificado ou corrigido>"

  local current_context="[Instrução do Agente]: $system_prompt"
  local step=1
  local resp=""
  local metis_timeout="${METIS_TIMEOUT:-120}"

  while (( step <= max_steps )); do
    resp="$(_ai_query "$current_context" 360)"
    local status_query=$?

    if (( status_query == 130 )) || [[ "$resp" == *"KeyboardInterrupt"* ]]; then
      printf '\n\033[33m⚠️ Operação cancelada pelo usuário (Ctrl+C).\033[0m\n'
      return 130
    fi

    if (( status_query != 0 )) || [[ -z "$resp" ]]; then
      if [[ -n "$resp" ]]; then
        printf '\n\033[31m%s\033[0m\n' "$resp"
      else
        printf '\n\033[31m⚠️ Falha ao obter resposta de %s. Verifique conexão, credenciais ou provedor ativo.\033[0m\n' "$active_label"
      fi
      return 1
    fi

    local cmd="$(_metis_extract_cmd "$resp")"

    if [[ -n "$cmd" ]]; then
      printf '\033[1;34m⚡ [Passo %d/%d]:\033[0m \033[36m❯ \033[1;38;5;214m' "$step" "$max_steps"
      _metis_type_live "$cmd" 0.006
      printf '\033[0m'

      local should_confirm=0

      if [[ "${METIS_CONFIRM_ALL:-0}" == "1" ]]; then
        should_confirm=1
      elif _metis_is_destructive "$cmd"; then
        should_confirm=1
      fi

      if (( should_confirm )); then
        printf '\033[33m⚠️  A Metis quer executar um comando de alteração/risco:\033[0m \033[1;38;5;214m%s\033[0m\n' "$cmd"
        printf '\033[33mDeseja confirmar a execução? (s/N): \033[0m'

        local ans=""
        read -r ans </dev/tty

        case "${ans:l}" in
          s|sim|y|yes) ;;
          *)
            printf '\033[31m❌ Ação cancelada pelo usuário.\033[0m\n'

            current_context="$current_context
[Assistente]: $resp
<tool_result exit_code=\"130\">
Ação '$cmd' cancelada pelo usuário. Tente outra abordagem segura ou finalize.
</tool_result>"

            current_context="$(_metis_trim_context "$current_context")"
            (( step++ ))
            continue
            ;;
        esac
      fi

      local tmp_out=""
      tmp_out="$(mktemp -t metis.XXXXXX 2>/dev/null || mktemp 2>/dev/null)"

      if [[ -z "$tmp_out" ]]; then
        printf '\033[31m[Metis] Falha ao criar arquivo temporário.\033[0m\n'
        return 1
      fi

      local -a run_prefix
      run_prefix=()

      if command -v timeout >/dev/null 2>&1; then
        run_prefix=(timeout -s INT "$metis_timeout")
      elif command -v gtimeout >/dev/null 2>&1; then
        run_prefix=(gtimeout -s INT "$metis_timeout")
      fi

      # Suporte transparente para sudo: se o comando contiver 'sudo', mantém
      # stdin aberto para digitar a senha caso o sudo solicite; caso contrário,
      # fecha o stdin (</dev/null) para evitar travamentos de comandos interativos.
      if [[ "$cmd" == *sudo* ]]; then
        if (( ${#run_prefix} )); then
          "${run_prefix[@]}" zsh -c "$cmd" 2>&1 | tee "$tmp_out"
        else
          zsh -c "$cmd" 2>&1 | tee "$tmp_out"
        fi
      else
        if (( ${#run_prefix} )); then
          "${run_prefix[@]}" zsh -c "$cmd" </dev/null 2>&1 | tee "$tmp_out"
        else
          zsh -c "$cmd" </dev/null 2>&1 | tee "$tmp_out"
        fi
      fi

      local -a _ps=("${pipestatus[@]}")
      local cmd_code="${_ps[1]:-$?}"

      if (( cmd_code == 130 )); then
        rm -f "$tmp_out" 2>/dev/null
        printf '\n\033[33m⚠️ Execução cancelada pelo usuário.\033[0m\n'
        return 130
      fi

      local cmd_output=""
      cmd_output="$(_metis_summarize_output "$tmp_out" 20000)"
      rm -f "$tmp_out" 2>/dev/null

      [[ -z "$cmd_output" ]] && cmd_output="[Comando executado com código $cmd_code sem saída]"

      # Sanitização contra Prompt Injection Indireto em saídas de comandos
      cmd_output="${cmd_output//\<tool_call/<escaped_tool_call}"
      cmd_output="${cmd_output//\<\/tool_call/<\\/escaped_tool_call}"

      current_context="$current_context
[Assistente]: $resp
<tool_result exit_code=\"$cmd_code\">
$cmd_output
</tool_result>"

      current_context="$(_metis_trim_context "$current_context")"
      (( step++ ))
    else
      local final_msg="$(_metis_clean_final_msg "$resp")"

      if [[ -z "$final_msg" ]]; then
        printf '\n\033[33m⚠️ A IA respondeu sem comando executável e sem mensagem final clara.\033[0m\n'
        return 1
      fi

      printf '\n\033[1;32m%s\033[0m\n' "$final_msg"
      return 0
    fi
  done

  printf '\n\033[33m⚠️ Limite de %d passos atingido sem conclusão final.\033[0m\n' "$max_steps"

  if [[ -n "$resp" ]]; then
    local final_msg="$(_metis_clean_final_msg "$resp")"
    if [[ -n "$final_msg" ]]; then
      printf '\033[90mÚltima resposta limpa:\033[0m\n\033[1;32m%s\033[0m\n' "$final_msg"
    fi
  fi

  return 2
}

# Aliases de compatibilidade
alias copilot=metis
alias resolve=metis
