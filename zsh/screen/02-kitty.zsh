#!/usr/bin/env zsh
# =============================================================================
# screen/02-kitty.zsh
# Captura de tela, manipulação de buffer, integração Kitty e envio com digitação.
# =============================================================================

clean_screen_content() {
  local raw="$1"
  local cleaned=""

  if command -v perl >/dev/null 2>&1; then
    cleaned="$(print -r -- "$raw" | perl -pe 's/\e\[[0-9;]*[a-zA-Z]//g; s/\e\][^\a]*(\a|\e\\)//g; s/\e[()][A-Za-z0-9]//g; s/\r//g')"
  else
    cleaned="$(print -r -- "$raw" | sed -E \
      -e 's/\x1b\[[0-9;]*[a-zA-Z]//g' \
      -e 's/\x1b\][^\x07\x1b]*(\x07|\x1b\\)//g' \
      -e 's/\x1b[()][A-Za-z0-9]//g' \
      -e 's/\r//g')"
  fi

  # Remove linhas vazias/espaços do final do grid do terminal
  cleaned="${cleaned%"${cleaned##*[![:space:]]}"}"

  print -r -- "$cleaned"
}

extrair_linhas_e_query() {
  local input="$1"
  local default_lines="$2"
  local parsed_lines="$default_lines"
  local parsed_steps=""
  local -a words=()
  local -a remaining_words=()

  words=(${=input})

  while (( $#words > 0 )); do
    case "$words[1]" in
      -p|--passos|--steps)
        shift words
        if [[ "$words[1]" == <-> ]]; then
          parsed_steps="$words[1]"
          shift words
        fi
        ;;
      -p<->)
        parsed_steps="${words[1]#-p}"
        shift words
        ;;
      -n|--lines)
        shift words
        if [[ "$words[1]" == <-> ]]; then
          parsed_lines="$words[1]"
          shift words
        fi
        ;;
      -n<->)
        parsed_lines="${words[1]#-n}"
        shift words
        ;;
      /s|/sync)
        shift words
        if [[ "$words[1]" == -<-> ]]; then
          parsed_lines="${words[1]#-}"
          shift words
        elif [[ "$words[1]" == <-> ]]; then
          parsed_lines="$words[1]"
          shift words
        fi
        ;;
      -<->)
        parsed_lines="${words[1]#-}"
        shift words
        ;;
      *)
        remaining_words+=("$words[1]")
        shift words
        ;;
    esac
  done

  local clean_msg="${(j: :)remaining_words}"
  clean_msg="$(_trim "$clean_msg")"

  if [[ -n "$parsed_lines" && "$parsed_lines" -lt 1 ]]; then
    parsed_lines=1
  fi

  PARSED_LINES="$parsed_lines"
  PARSED_STEPS="$parsed_steps"
  PARSED_QUERY="$clean_msg"
}

# Limpa a seleção do mouse (Primary buffer, arquivo temporário e seleção interna do Kitty)
limpar_selecao_mouse() {
  rm -f /tmp/qwen_selecao.txt 2>/dev/null
  if command -v wl-copy >/dev/null 2>&1; then
    wl-copy --clear --primary 2>/dev/null || true
  elif command -v xsel >/dev/null 2>&1; then
    xsel -c -p 2>/dev/null || true
  elif command -v xclip >/dev/null 2>&1; then
    xclip -i /dev/null -selection primary 2>/dev/null || true
  fi

  # Limpa o buffer de seleção interno do Kitty para evitar persistência zumbi
  _obter_kitty_target
  if [[ -n "$TARGET_KITTY_SOCK" ]] && command -v kitty >/dev/null 2>&1; then
    if [[ -n "$TARGET_KITTY_WIN" ]]; then
      kitty @ --to "$TARGET_KITTY_SOCK" action --match="id:$TARGET_KITTY_WIN" clear_selection 2>/dev/null || true
    fi
    kitty @ --to "$TARGET_KITTY_SOCK" action --match="all" clear_selection 2>/dev/null || true
  fi
}

# Captura especificamente a seleção ativa do mouse (Primary selection no Wayland / X11 ou Kitty)
obter_selecao_mouse() {
  local sel=""

  # 1. Wayland: Primary Selection em tempo real (seleção ativa do mouse)
  if command -v wl-paste >/dev/null 2>&1; then
    sel="$(wl-paste --primary --no-newline 2>/dev/null)"
  fi

  # 2. Se vazio, tenta obter diretamente do Kitty via Remote Control na janela de origem
  if [[ -z "$sel" ]]; then
    _obter_kitty_target
    if command -v kitty >/dev/null 2>&1 && [[ -n "$TARGET_KITTY_SOCK" ]]; then
      if [[ -n "$TARGET_KITTY_WIN" ]]; then
        sel="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=selection --match="id:$TARGET_KITTY_WIN" 2>/dev/null)"
      fi
      [[ -z "$sel" ]] && sel="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=selection 2>/dev/null)"
    fi
  fi

  # 3. X11 Primary Selection fallback
  if [[ -z "$sel" ]] && command -v xclip >/dev/null 2>&1; then
    sel="$(xclip -o -selection primary 2>/dev/null)"
  elif [[ -z "$sel" ]] && command -v xsel >/dev/null 2>&1; then
    sel="$(xsel -o -p 2>/dev/null)"
  fi

  # 4. Fallback imediato gravado pelo launcher (apenas se recente <= 3s)
  if [[ -z "$sel" ]] && [[ -f "/tmp/qwen_selecao.txt" && -s "/tmp/qwen_selecao.txt" && ! -L "/tmp/qwen_selecao.txt" ]]; then
    local now=$(date +%s)
    local mtime=$(date -r "/tmp/qwen_selecao.txt" +%s 2>/dev/null || stat -c %Y "/tmp/qwen_selecao.txt" 2>/dev/null || echo 0)
    if (( now - mtime <= 3 )); then
      sel="$(cat "/tmp/qwen_selecao.txt" 2>/dev/null)"
    else
      rm -f /tmp/qwen_selecao.txt 2>/dev/null
    fi
  fi

  local clean_sel="$(_trim "$sel")"
  if [[ -n "$clean_sel" ]]; then
    print -r -- "$clean_sel" > /tmp/qwen_selecao.txt 2>/dev/null
    clean_screen_content "$clean_sel"
  else
    rm -f /tmp/qwen_selecao.txt 2>/dev/null
    return 1
  fi
}

# Captura especificamente o conteúdo da área de transferência (Clipboard)
obter_clipboard() {
  local clip=""
  if command -v wl-paste >/dev/null 2>&1; then
    clip="$(wl-paste --no-newline 2>/dev/null)"
  elif command -v xclip >/dev/null 2>&1; then
    clip="$(xclip -o -selection clipboard 2>/dev/null)"
  elif command -v xsel >/dev/null 2>&1; then
    clip="$(xsel -o -b 2>/dev/null)"
  fi

  local clean_clip="$(_trim "$clip")"
  if [[ -n "$clean_clip" ]]; then
    clean_screen_content "$clip"
  fi
}

# Captura a tela e histórico recente do Kitty / terminal
obter_tela_terminal() {
  local n_lines="${1:-${DEFAULT_SCREEN_LINES:-30}}"
  [[ "$n_lines" =~ ^[0-9]+$ ]] || n_lines=30
  (( n_lines < 1 )) && n_lines=30
  local raw=""

  # 1. Tenta capturar do socket ativo do Kitty
  _obter_kitty_target
  if command -v kitty >/dev/null 2>&1 && [[ -n "$TARGET_KITTY_SOCK" ]]; then
    raw="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=screen --match="id:$TARGET_KITTY_WIN" 2>/dev/null)"
    [[ -z "$raw" ]] && raw="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=screen 2>/dev/null)"
  fi

  # 2. Arquivos gravados pelo atalho ou pipe do Kitty
  if [[ -z "$raw" && -f "$FILE" && -s "$FILE" ]]; then
    raw="$(cat "$FILE" 2>/dev/null)"
  elif [[ -z "$raw" && -f "/tmp/qwen_tela.txt" && -s "/tmp/qwen_tela.txt" && ! -L "/tmp/qwen_tela.txt" ]]; then
    raw="$(cat "/tmp/qwen_tela.txt" 2>/dev/null)"
  fi

  local cleaned="$(clean_screen_content "$raw")"
  if [[ -n "$cleaned" ]]; then
    local -a lines=("${(@f)cleaned}")
    if (( ${#lines[@]} > n_lines )); then
      lines=("${(@)lines[-$n_lines,-1]}")
    fi
    print -r -- "${(F)lines}"
  fi
}

obter_conteudo_tela() {
  local n_lines="${1:-${DEFAULT_SCREEN_LINES:-30}}"
  [[ "$n_lines" =~ ^[0-9]+$ ]] || n_lines=30
  (( n_lines < 1 )) && n_lines=30

  # Se o modo foi explicitamente definido como 'mouse'
  if [[ "$MODO_CAPTURA" == "mouse" ]]; then
    local sel="$(obter_selecao_mouse)"
    if [[ -n "$sel" ]]; then
      TIPO_FONTE_CAPTURA="mouse"
      SCREEN_CONTENT="$sel"
      print -r -- "$sel"
      return 0
    fi
    # Fallback suave para saída do terminal quando mouse foi escolhido sem seleção prévia
    local tela="$(obter_tela_terminal "$n_lines")"
    if [[ -n "$tela" ]]; then
      TIPO_FONTE_CAPTURA="tela"
      SCREEN_CONTENT="$tela"
      print -r -- "$tela"
      return 0
    fi
  fi

  # Se o modo foi explicitamente definido como 'tela'
  if [[ "$MODO_CAPTURA" == "tela" ]]; then
    local tela="$(obter_tela_terminal "$n_lines")"
    if [[ -n "$tela" ]]; then
      TIPO_FONTE_CAPTURA="tela"
      SCREEN_CONTENT="$tela"
      print -r -- "$tela"
      return 0
    fi
  fi

  # Modo Padrão / Automático:
  # 1. Se houver seleção ativa no mouse, ela tem prioridade total!
  local sel="$(obter_selecao_mouse)"
  if [[ -n "$sel" ]]; then
    TIPO_FONTE_CAPTURA="mouse"
    SCREEN_CONTENT="$sel"
    print -r -- "$sel"
    return 0
  fi

  # 2. Caso contrário, captura as últimas linhas da tela do terminal
  local tela="$(obter_tela_terminal "$n_lines")"
  if [[ -n "$tela" ]]; then
    TIPO_FONTE_CAPTURA="tela"
    SCREEN_CONTENT="$tela"
    print -r -- "$tela"
    return 0
  fi

  # 3. Fallback: Clipboard regular
  local clip="$(obter_clipboard)"
  if [[ -n "$clip" ]]; then
    TIPO_FONTE_CAPTURA="clipboard"
    SCREEN_CONTENT="$clip"
    print -r -- "$clip"
    return 0
  fi

  TIPO_FONTE_CAPTURA="vazio"
  SCREEN_CONTENT=""
  return 1
}

_obter_kitty_target() {
  local listen_sock=""

  if [[ -f "/tmp/orig_kitty_listen" && ! -L "/tmp/orig_kitty_listen" ]]; then
    listen_sock="$(_trim "$(cat /tmp/orig_kitty_listen 2>/dev/null)")"
  fi
  [[ -z "$listen_sock" && -n "$KITTY_LISTEN_ON" ]] && listen_sock="$KITTY_LISTEN_ON"

  # Se o socket salvo não responde mais (terminal foi fechado), limpa
  if [[ -n "$listen_sock" ]] && command -v kitty >/dev/null 2>&1; then
    if ! kitty @ --to "$listen_sock" ls >/dev/null 2>&1; then
      listen_sock=""
    fi
  fi

  if [[ -z "$listen_sock" ]]; then
    # Se houver Hyprland ativo, tenta obter o PID da janela focada antes da abertura
    if command -v hyprctl >/dev/null 2>&1; then
      local active_pid="$(hyprctl activewindow -j 2>/dev/null | jq -r '.pid // empty' 2>/dev/null)"
      if [[ -n "$active_pid" && -S "/tmp/mykitty-$active_pid" ]]; then
        if kitty @ --to "unix:/tmp/mykitty-$active_pid" ls >/dev/null 2>&1; then
          listen_sock="unix:/tmp/mykitty-$active_pid"
        fi
      fi
    fi

    # Fallback: candidatos ordenados por modificação mais recente (evita sockets zumbis antigos)
    if [[ -z "$listen_sock" ]]; then
      local -a sock_candidates
      sock_candidates=(${(f)"$(ls -1t /tmp/mykitty* 2>/dev/null)"})
      for s in "${sock_candidates[@]}"; do
        s="$(_trim "$s")"
        [[ -S "$s" ]] || continue
        if kitty @ --to "unix:$s" ls >/dev/null 2>&1; then
          listen_sock="unix:$s"
          break
        fi
      done
    fi
  fi

  local target_win=""
  if [[ -f "/tmp/orig_kitty_id" && ! -L "/tmp/orig_kitty_id" ]]; then
    target_win="$(_trim "$(cat /tmp/orig_kitty_id 2>/dev/null)")"
  fi

  if [[ -n "$listen_sock" ]] && command -v kitty >/dev/null 2>&1; then
    local win_exists=0
    if [[ -n "$target_win" ]]; then
      if kitty @ --to "$listen_sock" ls 2>/dev/null | grep -q "\"id\": $target_win\b"; then
        win_exists=1
      fi
    fi

    if (( win_exists == 0 )); then
      if command -v jq >/dev/null 2>&1; then
        target_win="$(kitty @ --to "$listen_sock" ls 2>/dev/null | jq -r '.[0].tabs[] | select(.is_active == true) | .windows[] | select(.is_active == true) | .id' 2>/dev/null | head -n 1)"
        [[ -z "$target_win" ]] && target_win="$(kitty @ --to "$listen_sock" ls 2>/dev/null | jq -r '.[0].tabs[0].windows[0].id // empty' 2>/dev/null)"
      fi

      if [[ -z "$target_win" ]]; then
        target_win="$(kitty @ --to "$listen_sock" ls 2>/dev/null | grep -oE '"id": [0-9]+' | head -n 1 | awk '{print $2}')"
      fi
    fi
  fi

  [[ -z "$target_win" ]] && target_win="1"

  TARGET_KITTY_SOCK="$listen_sock"
  TARGET_KITTY_WIN="$target_win"
}

recapturar_tela() {
  local n_lines="${1:-${DEFAULT_SCREEN_LINES:-30}}"
  [[ "$n_lines" =~ ^[0-9]+$ ]] || n_lines=30
  (( n_lines < 1 )) && n_lines=30
  obter_tela_terminal "$n_lines"
}

# Obtém o comando e código de saída real ($?) rastreado pelo ZSH
obter_status_ultimo_comando() {
  local target_win="${1:-${TARGET_KITTY_WIN:-}}"
  local status_file=""

  if [[ -n "$target_win" && -f "/tmp/metis_status_${target_win}" ]]; then
    status_file="/tmp/metis_status_${target_win}"
  elif [[ -f "/tmp/metis_last_status" ]]; then
    status_file="/tmp/metis_last_status"
  fi

  LAST_CMD_NAME=""
  LAST_CMD_EXIT=""
  LAST_CMD_TIME=""

  if [[ -n "$status_file" && -r "$status_file" ]]; then
    local val=""
    while IFS= read -r line; do
      case "$line" in
        CMD:*)
          val="${line#CMD:}"
          val="${val#"${val%%[![:space:]]*}"}"
          LAST_CMD_NAME="${val%"${val##*[![:space:]]}"}"
          ;;
        EXIT_CODE:*)
          val="${line#EXIT_CODE:}"
          val="${val#"${val%%[![:space:]]*}"}"
          LAST_CMD_EXIT="${val%"${val##*[![:space:]]}"}"
          ;;
        TIME:*)
          val="${line#TIME:}"
          val="${val#"${val%%[![:space:]]*}"}"
          LAST_CMD_TIME="${val%"${val##*[![:space:]]}"}"
          ;;
      esac
    done < "$status_file"
  fi
}

_should_type_effect() {
  local code="$1"
  local auto_enter="${2:-0}"

  [[ "$auto_enter" == "1" ]] && return 1
  [[ "${AI_ASSIST_TYPE_EFFECT:-1}" == "1" ]] || return 1
  [[ "$code" == *$'\n'* ]] && return 1

  local cols="${COLUMNS:-80}"
  [[ "$cols" =~ ^[0-9]+$ ]] || cols=80

  local max=$(( cols - 12 ))
  (( max < 20 )) && max=68
  (( max > 120 )) && max=120

  (( ${#code} <= max ))
}

enviar_ao_kitty() {
  local code="$1"
  local num="$2"
  local auto_enter="${3:-0}"

  # Remove comentários (# ...) preservando strings, aspas e parâmetros
  code="$(_remover_comentarios_comando "$code")"

  if [[ -z "$code" ]]; then
    _warn "Nenhum comando selecionado para enviar."
    return 1
  fi

  # Resolve o terminal de origem (socket e id da janela) ANTES de checar
  _obter_kitty_target

  if ! command -v kitty >/dev/null 2>&1 || [[ -z "$TARGET_KITTY_SOCK" ]]; then
    if _has_fn copiar_codigo; then
      copiar_codigo "$code" "$num"
    else
      [[ -n "$code" ]] && print -r -- "$code" | (wl-copy 2>/dev/null || xclip -selection clipboard 2>/dev/null || true)
    fi
    printf '\033[36m💡 Comando copiado para a área de transferência! Cole com Ctrl+Shift+V no seu terminal.\033[0m\n'
    return 0
  fi

  if [[ "$auto_enter" == 1 ]]; then
    if [[ "${AI_AUTO_CONFIRMED:-0}" != "1" ]]; then
      if _is_risky_auto_cmd "$code"; then
        if ! _confirmar_acao "Atenção: este comando pode ser sensível ou alterar o sistema:
\033[1;31m$code\033[0m
Deseja realmente enviar ao terminal?"; then
          printf '\033[33mEnvio cancelado pelo usuário.\033[0m\n'
          return 1
        fi
      fi

      if [[ "$code" == *$'\n'* && "${AI_AUTO_ALLOW_MULTILINE:-0}" != "1" ]]; then
        if ! _confirmar_acao "O comando possui múltiplas linhas e pode ser executado linha a linha no modo automático:
\033[1;33m$code\033[0m
Deseja continuar mesmo assim?"; then
          printf '\033[33mEnvio multilinha cancelado pelo usuário.\033[0m\n'
          return 1
        fi
      fi
    fi
  else
    if _is_destructive_cmd "$code"; then
      if ! _confirmar_acao "Atenção: este comando pode ser destrutivo ou alterar o sistema:
\033[1;31m$code\033[0m
Deseja realmente enviar ao terminal?"; then
        printf '\033[33mEnvio cancelado pelo usuário.\033[0m\n'
        return 1
      fi
    fi

    if [[ "$code" == *$'\n'* ]]; then
      if ! _confirmar_acao "O comando possui múltiplas linhas e pode ser executado parcialmente ao ser inserido no terminal:
\033[1;33m$code\033[0m
Deseja continuar mesmo assim?"; then
        printf '\033[33mEnvio multilinha cancelado pelo usuário.\033[0m\n'
        return 1
      fi
    fi
  fi

  code="${code%"${code##*[![:space:]]}"}"

  local sent=1

  if _should_type_effect "$code" "$auto_enter" && _python_ok "$PYTHON_BIN"; then
    "${PYTHON_BIN:-python3}" -c '
import subprocess, time, sys

sock, win, cmd = sys.argv[1], sys.argv[2], sys.argv[3]
auto_enter = int(sys.argv[4]) if len(sys.argv) > 4 else 0
speed = 0.012

match_arg = [f"--match=id:{win}"] if win else []
failed = False

for ch in cmd:
    res = subprocess.run(["kitty", "@", "--to", sock, "send-text"] + match_arg + [ch], capture_output=True)
    if res.returncode != 0:
        res2 = subprocess.run(["kitty", "@", "--to", sock, "send-text", ch], capture_output=True)
        if res2.returncode != 0:
            failed = True
            break
    time.sleep(speed)

if not failed and auto_enter == 1:
    time.sleep(0.15)
    subprocess.run(["kitty", "@", "--to", sock, "send-text"] + match_arg + ["\r"], capture_output=True)

sys.exit(1 if failed else 0)
' "$TARGET_KITTY_SOCK" "$TARGET_KITTY_WIN" "$code" "$auto_enter" 2>/dev/null

    sent=$?
  fi

  if (( sent != 0 )); then
    if [[ -n "$TARGET_KITTY_WIN" ]] && kitty @ --to "$TARGET_KITTY_SOCK" send-text --match="id:$TARGET_KITTY_WIN" "$code" 2>/dev/null; then
      sent=0
    elif kitty @ --to "$TARGET_KITTY_SOCK" send-text "$code" 2>/dev/null; then
      sent=0
    fi

    if (( sent == 0 )) && [[ "$auto_enter" == 1 ]]; then
      sleep 0.15
      if [[ -n "$TARGET_KITTY_WIN" ]]; then
        kitty @ --to "$TARGET_KITTY_SOCK" send-text --match="id:$TARGET_KITTY_WIN" $'\r' 2>/dev/null ||
          kitty @ --to "$TARGET_KITTY_SOCK" send-text $'\r' 2>/dev/null
      else
        kitty @ --to "$TARGET_KITTY_SOCK" send-text $'\r' 2>/dev/null
      fi
    fi
  fi

  if (( sent == 0 )); then
    if [[ "$auto_enter" == 1 ]]; then
      if [[ -n "$num" ]]; then
        printf '\033[32m🚀 Comando [%s] executado no terminal original!\033[0m\n' "$num"
      else
        printf '\033[32m🚀 Comando executado no terminal original!\033[0m\n'
      fi
    else
      if [[ -n "$num" ]]; then
        printf '\033[32m✍️  Comando [%s] inserido no terminal!\033[0m\n' "$num"
      else
        printf '\033[32m✍️  Comando inserido no terminal!\033[0m\n'
      fi
    fi

    return 0
  fi

  _warn "Falha ao comunicar com o socket do Kitty ($TARGET_KITTY_SOCK)."
  return 1
}
