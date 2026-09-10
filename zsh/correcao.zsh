#!/usr/bin/env zsh
# correcao.zsh - Auto-correção e interpretação inteligente de comandos/linguagem natural
# Conectado à IA ativa selecionada no Ctrl+G (Ollama, Gemini, Groq, NVIDIA ou G4F)
# Para funcionar, este arquivo deve ser carregado com source no shell atual.

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || true

_ai_fix_ready() {
  command -v _ai_query >/dev/null 2>&1 || return 1
  command -v _ai_get_current_provider_info >/dev/null 2>&1 || return 1
  command -v _ai_get_metis_icon >/dev/null 2>&1 || return 1
}

_ai_fix_normalize_command() {
  local s="$1"
  local tick=$'\x60'

  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"

  if (( ${#s} >= 2 )) && [[ "$s" == ${tick}*${tick} ]]; then
    s="${s#$tick}"
    s="${s%$tick}"
  fi

  if [[ "$s" == '$ '* ]]; then
    s="${s:2}"
  elif [[ "$s" == '# '* ]]; then
    s="${s:2}"
  fi

  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"

  print -r -- "$s"
}

_ai_fix_fill_command() {
  local cmd="$1"

  if [[ -n "$KITTY_WINDOW_ID" ]] && command -v kitty >/dev/null 2>&1; then
    kitty @ send-text --match="id:${KITTY_WINDOW_ID}" -- "$cmd" 2>/dev/null || print -z -- "$cmd"
  else
    print -z -- "$cmd"
  fi
}

ai_fix_command() {
  _ai_fix_ready || return 1

  local input="$*"
  local prompt="Você é um assistente de terminal Linux.
O usuário digitou o seguinte texto na linha de comando do ZSH:
<<<${input}>>>
Isso pode ser:
1. Um comando com erro de digitação (ex: 'gti status' -> 'git status', 'doker ps' -> 'docker ps').
2. Uma instrução ou pergunta em linguagem natural (ex: 'comando para renomear pastas', 'como descompactar arquivo tar', 'matar processo porta 8080').
SUA TAREFA:
- Gere os comandos shell Linux correspondentes e funcionais para o que o usuário quer fazer.
- Se houver mais de uma forma ou variação comum, liste até 5 opções relevantes (uma por linha) no formato:
1. comando_exemplo_1
2. comando_exemplo_2
- NUNCA escreva introduções, explicações ou texto adicional. Responda apenas com os comandos limpos."

  local response
  if ! response="$(_ai_query "$prompt" 2>/dev/null)"; then
    return 1
  fi

  [[ -z "$response" ]] && return 1

  local -a res_lines=("${(@f)response}")
  local l out=""
  for l in "${res_lines[@]}"; do
    l="${l//$'\r'/}"
    [[ "$l" == *'```'* ]] && continue
    l="${l#"${l%%[![:space:]]*}"}"
    l="${l%"${l##*[![:space:]]}"}"
    [[ -z "$l" ]] && continue
    if [[ -n "$out" ]]; then
      out+=$'\n'"$l"
    else
      out="$l"
    fi
  done
  print -r -- "$out"
}

command_not_found_handler() {
  [[ -o interactive ]] || return 127
  [[ -t 0 && -t 1 ]] || return 127
  _ai_fix_ready || return 127

  local full_cmd="$*"
  [[ -z "$full_cmd" ]] && return 127

  # Ignora caminhos absolutos, home e caminhos relativos óbvios
  [[ "$full_cmd" =~ ^[/~] ]] && return 127
  [[ "$full_cmd" =~ ^\./ ]] && return 127
  [[ "$full_cmd" =~ ^\.\./ ]] && return 127

  _ai_get_current_provider_info >/dev/null 2>&1 || true

  local m_icon
  m_icon="$(_ai_get_metis_icon 2>/dev/null)" || m_icon=""
  m_icon="$(_ai_trim "$m_icon")"
  [[ -z "$m_icon" ]] && m_icon="🤖"

  printf '%s %s\n' $'\e[33m⚡ Analisando comando/pedido:\e[0m' $'\e[1;37m'"$full_cmd"$'\e[0m'
  printf '%s %s\n' "$m_icon" $'\e[38;2;250;208;148m[Metis]:\e[0m \e[34mConsultando '"${AI_ACTIVE_LABEL:-IA}"$'\e[0m...'

  local result
  result="$(ai_fix_command "$full_cmd")" || return 127
  [[ -z "$result" ]] && return 127

  local -a numbered_options=()
  local -a plain_options=()
  local -a options=()
  local line="" opt_cmd="" i=0 total=0 choice="" opt="" opt_num=0 chosen="" single_cmd=""
  local num_re='^[0-9]+[.)][[:space:]]*(.*)$'

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="$(_ai_fix_normalize_command "$line")"
    [[ -z "$line" ]] && continue

    if [[ "$line" =~ $num_re ]]; then
      opt_cmd="$(_ai_fix_normalize_command "${match[1]}")"
      [[ -n "$opt_cmd" ]] && numbered_options+=("$opt_cmd")
    else
      plain_options+=("$line")
    fi
  done <<< "$result"

  if (( ${#numbered_options[@]} > 0 )); then
    options=("${numbered_options[@]}")
  else
    options=("${plain_options[@]}")
  fi

  if (( ${#options[@]} > 5 )); then
    options=("${(@)options[1,5]}")
  fi

  total=${#options[@]}
  (( total == 0 )) && return 127

  printf '\n'

  if (( total == 1 )); then
    single_cmd="${options[1]}"
    printf '%s\n' $'\e[38;5;214m  ➤ '"$single_cmd"$'\e[0m'

    if ! read -r "choice?Preencher comando no terminal? (S/n): "; then
      return 127
    fi

    choice="$(_ai_trim "$choice")"
    if [[ -z "$choice" || "${choice:l}" == [sy] || "${choice:l}" == "sim" || "${choice:l}" == "yes" ]]; then
      _ai_fix_fill_command "$single_cmd"
      return 0
    fi

    printf '%s\n' $'\e[31mCancelado.\e[0m'
    return 127
  fi

  for (( i = 1; i <= total; i++ )); do
    printf '%s%s%s %s%s%s\n' \
      $'\e[38;5;42m  [' "$i" $']\e[0m' \
      $'\e[38;5;214m' "${options[$i]}" $'\e[0m'
  done

  printf '\n'

  if ! read -r "opt?Escolha o número (1-$total) para preencher no terminal, ou Enter para cancelar: "; then
    return 127
  fi

  opt="$(_ai_trim "$opt")"

  if [[ "$opt" =~ ^[0-9]+$ ]]; then
    opt_num=$((10#$opt))

    if (( opt_num >= 1 && opt_num <= total )); then
      chosen="${options[$opt_num]}"

      if [[ -n "$chosen" ]]; then
        _ai_fix_fill_command "$chosen"
        return 0
      fi
    fi
  fi

  printf '%s\n' $'\e[31mOpção inválida. Cancelado.\e[0m'
  return 127
}
