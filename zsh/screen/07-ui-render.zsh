#!/usr/bin/env zsh
# =============================================================================
# screen/07-ui-render.zsh
# Renderização visual, blocos de código, clipboard, ajuda e configuração ZLE.
# =============================================================================

renderizar() {
  local text="$1"

  if [[ -z "$text" ]]; then
    _warn "A IA não retornou resposta."
    return 1
  fi

  local cols=80 width=80
  cols="$(tput cols 2>/dev/null || echo 80)"
  [[ "$cols" =~ ^[0-9]+$ ]] || cols=80

  width=$(( cols - 4 ))
  (( width < 20 )) && width=80

  if command -v glow >/dev/null 2>&1; then
    print -r -- "$text" | glow -w "$width" -
  else
    if command -v perl >/dev/null 2>&1; then
      print -r -- "$text" | fmt -w "$width" -s | perl -pe 's/`([^`]+)`/\e[38;5;214m$1\e[0m/g'
    else
      print -r -- "$text" | fmt -w "$width" -s
    fi
  fi

  if [[ -n "$LAST_DURATION" ]]; then
    printf '\n\033[38;5;240m[⏱️ %.2fs]\033[0m\n' "$LAST_DURATION"
  fi
}

limitar_contexto() {
  local ctx="$1"
  local max_turns="${2:-$MAX_CONTEXT_TURNS}"

  local header=""
  header="$(print -r -- "$ctx" | sed -n '1,/^\[Assistente\]:/{ /^\[Assistente\]:/!p }')"

  local turnos=""
  turnos="$(print -r -- "$ctx" | sed -n '/^\[Assistente\]:/,$p')"

  if [[ -z "$turnos" ]]; then
    print -r -- "$ctx"
    return
  fi

  local n_turnos=0
  n_turnos="$(print -r -- "$turnos" | grep -c '^\[Assistente\]:')"

  if (( n_turnos <= max_turns )); then
    print -r -- "$ctx"
    return
  fi

  local skip=$(( n_turnos - max_turns ))
  local count=0
  local trimmed=""
  local line=""

  while IFS= read -r line; do
    if [[ "$line" == "[Assistente]:"* ]]; then
      (( count++ ))
    fi

    if (( count > skip )); then
      if [[ -n "$trimmed" ]]; then
        trimmed="$trimmed
$line"
      else
        trimmed="$line"
      fi
    fi
  done <<< "$turnos"

  print -r -- "$header
$trimmed"
}

_is_valid_command_candidate() {
  local str="$1"
  [[ -z "$str" ]] && return 1

  # Remove prompts comuns do início ($ , ❯ , # , > )
  str="${str#[❯$#>] }"
  str="$(_trim "$str")"
  [[ -z "$str" ]] && return 1

  # Ignora linhas decorativas, divisores, markdown
  [[ "$str" =~ ^[-=_*#~]{2,} ]] && return 1
  [[ "$str" =~ ^\[.*\]$ ]] && return 1

  # Ignora IPs, portas, hosts
  [[ "$str" =~ ^(\[[a-fA-F0-9:]+\]|[0-9]{1,3}(\.[0-9]{1,3}){3})(:[0-9]+)?$ ]] && return 1

  # Ignora flags soltas (-t, -l, --help)
  [[ "$str" =~ ^-[a-zA-Z0-9_-]+$ ]] && return 1

  # Ignora nomes de interface comuns soltos sem comando (ex: eth0, wlan0, lo, enp3s0)
  [[ "$str" =~ ^(eth[0-9]+|wlan[0-9]+|lo|enp[0-9a-z]+|wlp[0-9a-z]+)$ ]] && return 1

  # Ignora caminhos simples soltos (ex: /tmp, /etc/hosts, /dev/null) se não for comando
  [[ "$str" =~ ^/[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*$ && ! -x "$str" ]] && return 1

  # Variáveis de ambiente no início (ex: VAR=1 cmd ou NODE_ENV=production app)
  if [[ "$str" =~ ^[a-zA-Z_][a-zA-Z0-9_]*=.* ]]; then
    return 0
  fi

  # Extrai a primeira palavra
  local first_word="${str%%[ =]*}"

  # Se for maiúscula (ex: PING, LISTEN, State, ESTAB, ERROR, INFO), é saída de log, não comando
  [[ "$first_word" =~ ^[A-Z]{2,} ]] && return 1
  [[ "$first_word" =~ ^(State|Status|Total|Error|Warning|Usage|Host|Address|Interface|Active|Device|Recv-Q|Send-Q|Local|Foreign)$ ]] && return 1

  # Se começar com números (ex: 0, 4096, 127.0.0.1)
  [[ "$first_word" =~ ^[0-9] ]] && return 1

  # Palavras de saída de rede / diagnósticos comuns
  case "$first_word" in
    rtt|packets|bytes|round-trip|tcp|udp|raw|unix|netlink)
      return 1
      ;;
  esac

  # Sudo ou env prefix
  if [[ "$first_word" == "sudo" || "$first_word" == "doas" || "$first_word" == "env" ]]; then
    local rest="${str#$first_word }"
    first_word="${rest%%[ =]*}"
  fi

  # Verifica se o primeiro comando realmente existe no sistema ou é comando Unix válido
  if command -v "$first_word" >/dev/null 2>&1 || [[ "$first_word" =~ ^(\./|/) ]]; then
    return 0
  fi

  return 1
}

extrair_blocos() {
  local text="$1"
  CURRENT_CODE_BLOCKS=()

  text="${text//$'\r'/}"

  local inside=0
  local is_output_block=0
  local current_block=""
  local line=""
  local fence_re='^[[:space:]]*```([a-zA-Z0-9_-]*)'

  while IFS= read -r line; do
    if [[ "$line" =~ $fence_re ]]; then
      if (( inside == 1 )); then
        inside=0
        current_block="$(_trim "$current_block")"

        if [[ -n "$current_block" ]] && (( is_output_block == 0 )); then
          local blk_line=""
          while IFS= read -r blk_line; do
            blk_line="${blk_line//\`\`\`/}"
            blk_line="${blk_line//\`/}"
            blk_line="${blk_line#"${blk_line%%[![:space:]]*}"}"
            blk_line="${blk_line%"${blk_line##*[![:space:]]}"}"
            if [[ -n "$blk_line" && "$blk_line" != \#* ]]; then
              local check_candidate="$(_remover_comentarios_linha "$blk_line")"
              if _is_valid_command_candidate "$check_candidate" && (( ${CURRENT_CODE_BLOCKS[(Ie)$blk_line]} == 0 )); then
                CURRENT_CODE_BLOCKS+=("$blk_line")
              fi
            fi
          done <<< "$current_block"
        fi

        current_block=""
        is_output_block=0
      else
        inside=1
        local lang="${match[1]:l}"
        case "$lang" in
          text|txt|log|output|out|stdout|stderr|console|terminal)
            is_output_block=1
            ;;
          *)
            is_output_block=0
            ;;
        esac
      fi
    else
      if (( inside == 1 )); then
        current_block+="$line"$'\n'
      fi
    fi
  done <<< "$text"

  if (( inside == 1 )); then
    current_block="$(_trim "$current_block")"

    if [[ -n "$current_block" ]] && (( is_output_block == 0 )); then
      local blk_line=""
      while IFS= read -r blk_line; do
        blk_line="${blk_line//\`\`\`/}"
        blk_line="${blk_line//\`/}"
        blk_line="${blk_line#"${blk_line%%[![:space:]]*}"}"
        blk_line="${blk_line%"${blk_line##*[![:space:]]}"}"
        if [[ -n "$blk_line" && "$blk_line" != \#* ]]; then
          local check_candidate="$(_remover_comentarios_linha "$blk_line")"
          if _is_valid_command_candidate "$check_candidate" && (( ${CURRENT_CODE_BLOCKS[(Ie)$blk_line]} == 0 )); then
            CURRENT_CODE_BLOCKS+=("$blk_line")
          fi
        fi
      done <<< "$current_block"
    fi
  fi

  if (( ${#CURRENT_CODE_BLOCKS[@]} == 0 )); then
    local inline=""
    local inline_re='`[^`]+`'

    while IFS= read -r inline; do
      inline="${inline//\`\`\`/}"
      inline="${inline//\`/}"
      inline="${inline#"${inline%%[![:space:]]*}"}"
      inline="${inline%"${inline##*[![:space:]]}"}"
      if [[ -n "$inline" && "$inline" != \#* ]]; then
        local check_candidate="$(_remover_comentarios_linha "$inline")"
        if _is_valid_command_candidate "$check_candidate" && (( ${CURRENT_CODE_BLOCKS[(Ie)$inline]} == 0 )); then
          CURRENT_CODE_BLOCKS+=("$inline")
        fi
      fi
    done < <(print -r -- "$text" | grep -oE "$inline_re" | sed -E 's/^`//; s/`$//')
  fi
}

exibir_blocos() {
  if (( ${#CURRENT_CODE_BLOCKS[@]} > 0 )); then
    printf '\n\033[1;36m┌── ✨ Comandos Disponíveis\033[0m\n'

    local cols="${COLUMNS:-80}"
    [[ "$cols" =~ ^[0-9]+$ ]] || cols=80
    local max_len=$(( cols - 14 ))
    (( max_len < 40 )) && max_len=70
    (( max_len > 140 )) && max_len=140

    local i=1 preview_line="" cmd_part="" comment_part=""

    for (( i = 1; i <= ${#CURRENT_CODE_BLOCKS[@]}; i++ )); do
      preview_line="${CURRENT_CODE_BLOCKS[$i]%%$'\n'*}"
      preview_line="${preview_line//\`\`\`/}"
      preview_line="${preview_line//\`/}"
      preview_line="${preview_line#"${preview_line%%[![:space:]]*}"}"
      preview_line="${preview_line%"${preview_line##*[![:space:]]}"}"

      cmd_part="$preview_line"
      comment_part=""

      if [[ "$preview_line" =~ ^([^#]+)[[:space:]]+#+[[:space:]]*(.*)$ ]]; then
        cmd_part="${match[1]}"
        cmd_part="${cmd_part%"${cmd_part##*[![:space:]]}"}"
        comment_part="${match[2]}"
        comment_part="${comment_part#"${comment_part%%[![:space:]]*}"}"
        comment_part="${comment_part%"${comment_part##*[![:space:]]}"}"
      fi

      if (( ${#cmd_part} > max_len )); then
        cmd_part="${cmd_part:0:$(( max_len - 3 ))}..."
      fi

      if [[ -n "$comment_part" ]]; then
        if (( ${#comment_part} > max_len )); then
          comment_part="${comment_part:0:$(( max_len - 3 ))}..."
        fi
        printf '\033[1;36m│\033[0m \033[1;34m[%d]\033[0m 💻 \033[1;37m%s\033[0m\n' "$i" "$cmd_part"
        printf '\033[1;36m│\033[0m     \033[38;5;244m└─▸ %s\033[0m\n' "$comment_part"
      else
        printf '\033[1;36m│\033[0m \033[1;34m[%d]\033[0m 💻 \033[1;37m%s\033[0m\n' "$i" "$cmd_part"
      fi
    done

    printf '\033[1;36m└──\033[0m\n\n'
  fi
}

selecionar_bloco_codigo() {
  if (( ${#CURRENT_CODE_BLOCKS[@]} == 0 )); then
    return 1
  fi

  if (( ${#CURRENT_CODE_BLOCKS[@]} == 1 )); then
    print -r -- "${CURRENT_CODE_BLOCKS[1]}"
    return 0
  fi

  local tmp_menu=""
  tmp_menu="$(mktemp)"

  local i=1
  local b="" preview_line=""

  for b in "${CURRENT_CODE_BLOCKS[@]}"; do
    preview_line="${b%%$'\n'*}"
    preview_line="$(_trim "$preview_line")"
    preview_line="${preview_line:0:60}"

    printf '%d: %s\n' "$i" "$preview_line" >> "$tmp_menu"
    (( i++ ))
  done

  local choice=""
  choice="$(fzf --height=20% --reverse --prompt="Escolha um comando: " < "$tmp_menu" | cut -d':' -f1)"

  rm -f "$tmp_menu"

  if [[ -n "$choice" && "$choice" =~ ^[0-9]+$ ]]; then
    if (( choice >= 1 && choice <= ${#CURRENT_CODE_BLOCKS[@]} )); then
      print -r -- "${CURRENT_CODE_BLOCKS[$choice]}"
      return 0
    fi
  fi

  return 1
}

copiar_codigo() {
  local code="$1"
  local num="$2"

  code="$(_remover_comentarios_comando "$code")"

  if [[ -z "$code" ]]; then
    _warn "Nenhum comando selecionado para copiar."
    return 1
  fi

  if command -v wl-copy >/dev/null 2>&1; then
    print -r -- "$code" | wl-copy
  elif command -v xclip >/dev/null 2>&1; then
    print -r -- "$code" | xclip -selection clipboard
  elif command -v xsel >/dev/null 2>&1; then
    print -r -- "$code" | xsel -b -i
  else
    _warn "Nenhum utilitário de clipboard encontrado (wl-copy, xclip ou xsel)."
    return 1
  fi

  if [[ -n "$num" ]]; then
    printf '\033[32m✅ Comando [%s] copiado para a área de transferência!\033[0m\n' "$num"
  else
    printf '\033[32m✅ Código copiado para a área de transferência!\033[0m\n'
  fi

  local cmd_file="${XDG_RUNTIME_DIR:-/tmp}/metis_bash_cmd.$UID"
  print -r -- "$code" > "$cmd_file" 2>/dev/null || true

  return 0
}

exibir_ajuda() {
  local cols="${COLUMNS:-80}"
  [[ "$cols" =~ ^[0-9]+$ ]] || cols=80
  local w=$(( cols - 4 ))
  (( w < 48 )) && w=48
  (( w > 74 )) && w=74

  local c=$'\033[1;36m'   # Ciano
  local b=$'\033[1;34m'   # Azul
  local g=$'\033[1;32m'   # Verde
  local y=$'\033[1;33m'   # Amarelo
  local m=$'\033[1;35m'   # Magenta
  local w_txt=$'\033[1;37m' # Branco
  local dim=$'\033[90m'   # Cinza escuro
  local r=$'\033[0m'      # Reset

  local sep=""
  local sep_i=0
  for (( sep_i = 0; sep_i < w; sep_i++ )); do
    sep+="─"
  done

  printf "\n"
  printf "${c}╭%s╮${r}\n" "$sep"
  printf "${c}│${r} ${w_txt}📖 GUIA COMPLETO DE COMANDOS & ATALHOS${r}"
  local pad=$(( w - 38 ))
  (( pad > 0 )) && printf "%*s" "$pad" ""
  printf "${c}│${r}\n"
  printf "${c}╰%s╯${r}\n\n" "$sep"

  printf "${m}🤖 AUTOMAÇÃO & DIAGNÓSTICO${r}\n"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/auto [-p N] [obj]" "Resolve erros no terminal (-p passos, ex: /auto -p 10)"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n\n" "/s [-n] [msg]" "Sincroniza a tela atualizada (-n linhas) e envia à IA"

  printf "${b}💻 GESTÃO DE COMANDOS${r}\n"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/e [n]" "Digita o comando [n] no seu prompt (sem Enter)"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "1, 2, 3..." "Seleciona e copia o comando [n] para o clipboard"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n\n" "/c [n]" "Copia o comando [n] para a área de transferência"

  printf "${c}💬 CHAT & CONFIGURAÇÃO${r}\n"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/salvar [nome]" "Salva a resposta/relatório atual em um arquivo .md"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/r" "Regenera a última resposta da IA"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/clear, /l" "Limpa a tela e re-exibe a resposta atual"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/modelos" "Gerencia modelos ativos (trocar, adicionar, remover)"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n" "/menu, /m" "Volta ao menu principal de seleção de IA"
  printf "  ${g}%-18s${r} ${dim}│${r} %s\n\n" "/sair, /q" "Fecha a janela do assistente"

  printf "${y}⌨️  DICAS & ATALHOS DE TECLADO${r}\n"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "Ctrl+Shift+E" "Atalho global no Kitty para abrir o assistente"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "-30 [pergunta]" "Captura as últimas N linhas da tela (ex: -20, -50)"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "Shift + Enter" "Pula linha no texto da sua pergunta"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "Ctrl + Setas" "Navega palavra por palavra na digitação"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "Tab" "Oculta ou exibe o painel lateral de prévia"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "Ctrl + C" "Cancela a geração ou o modo auto com segurança"
  printf "  ${w_txt}%-18s${r} ${dim}│${r} %s\n" "Esc" "Cancela a ação atual ou fecha o assistente"

  printf "\n${dim}%s${r}\n" "$sep"
}

_insert_newline() {
  LBUFFER+=$'\n'
}

_word_wrap_self_insert() {
  local cols="${COLUMNS:-80}"
  (( cols < 20 )) && cols=80

  zle .self-insert

  local NL=$'\n'
  local curr_line=""
  local prev_lines=""
  local prompt_offset=0

  if [[ "$LBUFFER" == *"$NL"* ]]; then
    curr_line="${LBUFFER##*$NL}"
    prev_lines="${LBUFFER%$curr_line}"
    prompt_offset=0
  else
    curr_line="$LBUFFER"
    prev_lines=""
    prompt_offset=3
  fi

  local curr_len=$(( ${#curr_line} + prompt_offset ))

  if (( curr_len >= (cols - 2) )); then
    if [[ "$curr_line" == *" "* ]]; then
      local prefix="${curr_line% *}"
      local last_word="${curr_line##* }"

      if [[ -n "$prefix" && -n "$last_word" ]]; then
        LBUFFER="${prev_lines}${prefix}${NL}${last_word}"
      fi
    fi
  fi
}

setup_zle() {
  setopt prompt_percent prompt_subst multiline 2>/dev/null || true
  bindkey -e 2>/dev/null || true

  bindkey "^[[1;5C" forward-word 2>/dev/null || true
  bindkey "^[[1;5D" backward-word 2>/dev/null || true
  bindkey "^[[1;3C" forward-word 2>/dev/null || true
  bindkey "^[[1;3D" backward-word 2>/dev/null || true
  bindkey "^[f" forward-word 2>/dev/null || true
  bindkey "^[b" backward-word 2>/dev/null || true

  bindkey "^[[A" up-line-or-history 2>/dev/null || true
  bindkey "^[[B" down-line-or-history 2>/dev/null || true
  bindkey "^[OA" up-line-or-history 2>/dev/null || true
  bindkey "^[OB" down-line-or-history 2>/dev/null || true
  bindkey "^[[C" forward-char 2>/dev/null || true
  bindkey "^[[D" backward-char 2>/dev/null || true
  bindkey "^[OC" forward-char 2>/dev/null || true
  bindkey "^[OD" backward-char 2>/dev/null || true
  bindkey "^[[H" beginning-of-line 2>/dev/null || true
  bindkey "^[[F" end-of-line 2>/dev/null || true
  bindkey "^[[1~" beginning-of-line 2>/dev/null || true
  bindkey "^[[4~" end-of-line 2>/dev/null || true
  bindkey "^[[7~" beginning-of-line 2>/dev/null || true
  bindkey "^[[8~" end-of-line 2>/dev/null || true
  bindkey "^A" beginning-of-line 2>/dev/null || true
  bindkey "^E" end-of-line 2>/dev/null || true

  bindkey "^[[3~" delete-char 2>/dev/null || true
  bindkey "^?" backward-delete-char 2>/dev/null || true
  bindkey "^H" backward-delete-char 2>/dev/null || true
  bindkey "^W" backward-kill-word 2>/dev/null || true
  bindkey "^[[3;5~" kill-word 2>/dev/null || true
  bindkey "^U" backward-kill-line 2>/dev/null || true
  bindkey "^K" kill-line 2>/dev/null || true
  bindkey "^L" clear-screen 2>/dev/null || true

  zle -N _insert_newline 2>/dev/null || true

  local mod="" k=""

  for mod in 2 3 4 5 6 7 8 66 67 68 69 70 130 131 132 133 134 194 195 196 197 198; do
    for k in 13 10; do
      bindkey "^[[${k};${mod}u" _insert_newline 2>/dev/null || true
      bindkey "^[[${k};${mod};1u" _insert_newline 2>/dev/null || true
      bindkey "^[[${k};${mod}:1u" _insert_newline 2>/dev/null || true
      bindkey "^[[${k};${mod}:1;1u" _insert_newline 2>/dev/null || true
      bindkey "^[[27;${mod};${k}~" _insert_newline 2>/dev/null || true
    done

    bindkey "^[[13;${mod}~" _insert_newline 2>/dev/null || true
  done

  bindkey "^[^M" _insert_newline 2>/dev/null || true
  bindkey "^[^J" _insert_newline 2>/dev/null || true
  bindkey "^[OM" _insert_newline 2>/dev/null || true
  bindkey "^J" _insert_newline 2>/dev/null || true

  # Word wrap por palavra inteira.
  # Ativado por padrão; pode ser desativado com AI_ASSIST_WORD_WRAP=0.
  if [[ "${AI_ASSIST_WORD_WRAP:-1}" == "1" ]]; then
    zle -N self-insert _word_wrap_self_insert 2>/dev/null || true
  fi
}
