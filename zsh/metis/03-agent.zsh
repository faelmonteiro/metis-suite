#!/usr/bin/env zsh
# =============================================================================
# metis/03-agent.zsh
# Loop autônomo do copiloto Metis, orquestração de comandos e aliases.
# =============================================================================

# =============================================================================

# Executa um comando, transmite a saída ao terminal e a salva em $tmp_out.
# Devolve, no return, o código de saída REAL do comando.
#
# Existe como função separada por um motivo que só aparece em execução: o
# código de saída precisa ser lido logo após o pipeline e DENTRO do ramo. No
# zsh, quando um `if` termina, `$pipestatus` colapsa para um único elemento
# com o status do próprio `if` — que é 0. Lendo "${pipestatus[@]}" depois do
# `fi`, todo tool_result dizia exit_code="0" mesmo com o comando falhando, e a
# IA recebia "deu certo" para um `ls` em diretório inexistente.
#
# Suporte transparente para sudo: se o comando contiver 'sudo', mantém stdin
# aberto para digitar a senha caso o sudo solicite; caso contrário, fecha o
# stdin (</dev/null) para evitar travamentos de comandos interativos.
_metis_rodar_comando() {
  local cmd="$1" tmp_out="$2" rc
  local -a prefix
  prefix=()

  if command -v timeout >/dev/null 2>&1; then
    prefix=(timeout -s INT "$metis_timeout")
  elif command -v gtimeout >/dev/null 2>&1; then
    prefix=(gtimeout -s INT "$metis_timeout")
  fi

  if [[ "$cmd" == *sudo* ]]; then
    if (( ${#prefix} )); then
      "${prefix[@]}" zsh -c "$cmd" 2>&1 | tee "$tmp_out"
      rc=$pipestatus[1]
    else
      zsh -c "$cmd" 2>&1 | tee "$tmp_out"
      rc=$pipestatus[1]
    fi
  else
    if (( ${#prefix} )); then
      "${prefix[@]}" zsh -c "$cmd" </dev/null 2>&1 | tee "$tmp_out"
      rc=$pipestatus[1]
    else
      zsh -c "$cmd" </dev/null 2>&1 | tee "$tmp_out"
      rc=$pipestatus[1]
    fi
  fi

  [[ "$rc" == <-> ]] || rc=0
  return "$rc"
}

# O passo decide sozinho se precisa de confirmação: METIS_CONFIRM_ALL força
# tudo, e na falta disso basta o comando ser destrutivo.
_metis_precisa_confirmar() {
  [[ "${METIS_CONFIRM_ALL:-0}" == "1" ]] && return 0
  _metis_is_destructive "$1" && return 0
  return 1
}

# Pergunta e lê a confirmação. Devolve 0 só para s/sim/y/yes: qualquer outra
# coisa, Enter incluído, cancela — é a leitura segura para comando de risco.
_metis_confirmar_execucao() {
  printf '\033[33m⚠️  A Metis quer executar um comando de alteração/risco:\033[0m \033[1;38;5;214m%s\033[0m\n' "$1"
  printf '\033[33mConfirmar? (s/N): \033[0m'

  local ans=""
  read -r ans </dev/tty

  case "${ans:l}" in
    s|sim|y|yes) return 0 ;;
    *)           return 1 ;;
  esac
}

# Executa o comando e devolve o código de saída REAL em `return`, deixando a
# saída já resumida e higienizada em $METIS_PASSO_SAIDA.
#
# Duas variáveis em vez de eco porque o comando precisa rodar no shell atual:
# dentro de $( ) o tee da saída do comando deixaria de chegar ao terminal, e o
# 130 do Ctrl+C se perderia.
#
# $METIS_PASSO_ERRO é separado do return de propósito: um comando que termina
# com código 1 é resultado legítimo e entra no contexto da IA, enquanto "não
# consegui nem criar o arquivo temporário" aborta o metis. Colapsar os dois
# num código só deixaria um dos dois sem tratamento.
METIS_PASSO_SAIDA=""
METIS_PASSO_ERRO=0
_metis_executar_passo() {
  local cmd="$1" tmp_out="" cmd_output=""

  METIS_PASSO_ERRO=0
  METIS_PASSO_SAIDA=""

  tmp_out="$(mktemp -t metis.XXXXXX 2>/dev/null || mktemp 2>/dev/null)"

  if [[ -z "$tmp_out" ]]; then
    METIS_PASSO_ERRO=1
    return 1
  fi

  _metis_rodar_comando "$cmd" "$tmp_out"
  local rc=$?

  if (( rc == 130 )); then
    rm -f "$tmp_out" 2>/dev/null
    return 130
  fi

  cmd_output="$(_metis_summarize_output "$tmp_out" 20000)"
  rm -f "$tmp_out" 2>/dev/null

  [[ -z "$cmd_output" ]] && cmd_output="[Comando executado com código $rc sem saída]"

  # Sanitização contra Prompt Injection Indireto em saídas de comandos
  cmd_output="${cmd_output//\<tool_call/<escaped_tool_call}"
  cmd_output="${cmd_output//\<\/tool_call/<\\/escaped_tool_call}"

  METIS_PASSO_SAIDA="$cmd_output"
  return "$rc"
}

# Pergunta se quer mais passos e devolve a quantidade em $METIS_PASSOS_EXTRAS,
# string vazia significando "encerra". Variável em vez de stdout porque o prompt
# é impresso no meio: dentro de $( ) o texto da pergunta seria capturado junto
# com a resposta.
#
# Opções aceitas:
#   - 's' ou 'sim' -> executa padrão de +3 passos
#   - 's -N' ou 's N' (ex: 's -4') -> executa N passos extras
#   - Número direto (ex: '4' ou '-4') -> executa N passos extras
#   - 'n', 'nao', 'no' ou Enter vazio -> encerra
METIS_PASSOS_EXTRAS=""
_metis_perguntar_continuacao() {
  local ans="" raw=""
  setopt localoptions extendedglob

  METIS_PASSOS_EXTRAS=""

  while :; do
    printf '\033[33mDeseja continuar com mais passos? [s/n]: \033[0m'

    if ! read -r ans </dev/tty; then
      ans=""
    fi

    raw="$ans"
    # Remove espaços do início e do fim
    ans="${${ans##[[:space:]]#}%%[[:space:]]#}"

    # Enter vazio encerra
    if [[ -z "$ans" ]]; then
      METIS_PASSOS_EXTRAS=""
      return 0
    fi

    local lower="${ans:l}"

    # 'n' ou variações encerram
    case "$lower" in
      n|nao|não|no|exit|quit|q)
        METIS_PASSOS_EXTRAS=""
        return 0
        ;;
      s|sim|y|yes)
        METIS_PASSOS_EXTRAS=3
        return 0
        ;;
    esac

    # 's -N' ou 's N' (ex: s -4, s-4, s 4, s -p 4, sim -4, y -4)
    if [[ "$lower" =~ "^(s|sim|y|yes)[[:space:]]*-?[[:space:]]*(p[[:space:]]*)?([0-9]+)$" ]]; then
      local n="${match[3]}"
      if [[ -n "$n" ]] && (( n > 0 )); then
        METIS_PASSOS_EXTRAS="$n"
        return 0
      fi
    fi

    # Número direto ou '-N' (ex: 4, 10, -4, -p 4)
    if [[ "$lower" =~ "^-?[[:space:]]*(p[[:space:]]*)?([0-9]+)$" ]]; then
      local n="${match[2]}"
      if [[ -n "$n" ]] && (( n > 0 )); then
        METIS_PASSOS_EXTRAS="$n"
        return 0
      fi
    fi

    printf '\033[33m"%s" não é um número ou opção válida. Digite s (+3), s -N (ex: s -4), número de passos, ou n/Enter para parar.\033[0m\n' "$raw"
    ans=""
  done
}


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

5. REGRA DE PROGRESSO — NUNCA REPITA UM COMANDO:
- Cada tool_result é a resposta do terminal ao ÚLTIMO comando enviado. Depois de lê-lo, avance.
- Está PROIBIDO reenviar um comando idêntico ao que você já enviou: o resultado dele já está no histórico e repetir não traz informação nova.
- Se a saída anterior já responde ao pedido, finalize em vez de mandar outro comando.
- Se ela não bastou, mude de abordagem: outro filtro, outro caminho, outra ferramenta. Não repita o mesmo comando esperando resultado diferente.

6. Quando o problema estiver resolvido e concluído, NÃO envie mais ferramentas. Apenas responda com UMA ÚNICA FRASE direta no formato:
✔ Resolvido: <resumo de uma linha do que foi verificado ou corrigido>"

  local current_context="[Instrução do Agente]: $system_prompt"
  local step=1
  local resp=""
  local metis_timeout="${METIS_TIMEOUT:-120}"

  # Registro da trava de repetição.
  #
  # Fora dos laços de propósito: `local -A x=()` dentro do corpo reatribui a cada
  # volta, e o registro zeraria sozinho — que é justamente o estado que existe
  # para durar a sessão inteira.
  local -A cmd_vistos=()
  local repeticoes=0

  # Laço infinito, e não `while (( continue_loop ))`: a flag nunca mudava de
  # 1, e o laço não é decoração — é ele que recebe as continuações depois de
  # `max_steps` crescer. (Remover este `while` parece limpo e quebra a
  # continuação em silêncio: a execução cai fora da função.)
  #
  # Toda saída é explícita: erro, Ctrl+C, mensagem final e recusa do prompt
  # dão `return`. Chegar ao fim do corpo é o único jeito de continuar.
  while :; do
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
        # Trava de repetição.
        #
        # O modelo reenviando o mesmo comando é a falha mais comum do loop, e era
        # silenciosa: o `ps` saía cinco vezes, devolvia cinco vezes a mesma
        # tabela, e o passo contava como sucesso. Nada no prompt proibia repetir
        # e nada no loop comparava com o que já tinha rodado.
        #
        # Recusado, o comando NÃO é executado — só entra no histórico como
        # tool_result explicando a recusa, para o modelo ter como mudar de
        # abordagem em vez de tomar o silêncio por aprovação.
        #
        # O passo não é contado: só execuções reais consomem teto. Se recusa
        # contasse, um modelo travado em repetição queimaria os 5 passos sem
        # rodar nada.
        #
        # A subscript do array associativo precisa das aspas: em zsh,
        # ${+v[$chave]} sem aspas devolve 0 mesmo com a chave presente — a
        # trava passaria batido exatamente no caso que existe para pegá-la.
        local cmd_norm="$(_metis_norm_cmd "$cmd")"

        if [[ -n "$cmd_norm" ]] && (( ${+cmd_vistos["$cmd_norm"]} )); then
          repeticoes=$(( repeticoes + 1 ))
          printf '\n\033[33m⚠️  Comando repetido, não executado: %s\033[0m\n' "$cmd"

          current_context="$current_context
  [Assistente]: $resp
  <tool_result exit_code=\"0\">
  Comando NÃO executado: idêntico a um que você já enviou, cujo resultado já está no histórico acima. Repetir não traz informação nova. Envie um comando DIFERENTE (outro filtro, outro caminho, outra ferramenta) ou finalize com '✔ Resolvido:'.
  </tool_result>"

          current_context="$(_metis_trim_context "$current_context")"

          # Duas recusas seguidas = modelo travado no laço. Sem este teto o
          # pedido de continuação nunca aparece, porque `step` não avança e
          # `while (( step <= max_steps ))` não tem como sair.
          if (( repeticoes >= 2 )); then
            printf '\n\033[31m❌ A IA repetiu o mesmo comando %d vezes. Encerrando para não entrar em ciclo.\033[0m\n' "$repeticoes"
            printf '\033[90mDica: reformule o pedido com mais contexto, ou troque de provedor em [Ctrl + G] — este é sintoma comum de modelo fraco.\033[0m\n'
            return 1
          fi

          continue
        fi

        repeticoes=0
        [[ -n "$cmd_norm" ]] && cmd_vistos["$cmd_norm"]=1

        printf '\033[1;34m⚡ [Passo %d/%d]:\033[0m \033[36m❯ \033[1;38;5;214m' "$step" "$max_steps"
        _metis_type_live "$cmd" 0.006
        printf '\033[0m'

        if _metis_precisa_confirmar "$cmd" && ! _metis_confirmar_execucao "$cmd"; then
          printf '\033[31m❌ Ação cancelada pelo usuário.\033[0m\n'

          current_context="$current_context
  [Assistente]: $resp
  <tool_result exit_code=\"130\">
  Ação '$cmd' cancelada pelo usuário. Tente outra abordagem segura ou finalize.
  </tool_result>"

          current_context="$(_metis_trim_context "$current_context")"
          (( step++ ))
          continue
        fi

        _metis_executar_passo "$cmd"
        local cmd_code=$?

        if (( METIS_PASSO_ERRO )); then
          printf '\033[31m[Metis] Falha ao criar arquivo temporário.\033[0m\n'
          return 1
        fi

        if (( cmd_code == 130 )); then
          printf '\n\033[33m⚠️ Execução cancelada pelo usuário.\033[0m\n'
          return 130
        fi

        current_context="$current_context
  [Assistente]: $resp
  <tool_result exit_code=\"$cmd_code\">
  $METIS_PASSO_SAIDA
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

    # Pergunta continuação (s = +3, s -N = N passos, n/Enter = encerra).
    _metis_perguntar_continuacao

    if [[ -z "$METIS_PASSOS_EXTRAS" ]]; then
      printf '\033[31m❌ Encerrando.\033[0m\n'
      return 2
    fi

    max_steps=$((max_steps + METIS_PASSOS_EXTRAS))
    printf '\n\033[32m✓ +%d passos (total: %d)\033[0m\n' "$METIS_PASSOS_EXTRAS" "$max_steps"
    # `step` NÃO volta para 1: o contador é a quantidade de passos já
    # executados, e o teto é cumulativo. Zerar aqui fazia a contagem recomeçar
    # a cada número e o laço rodava `max_steps` passos de novo, em vez dos
    # `METIS_PASSOS_EXTRAS` pedidos. Agora ele segue (6/8, 7/8, 8/8) e roda
    # exatamente o que foi pedido.
  done
}

# Aliases de compatibilidade
alias copilot=metis
alias resolve=metis
