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
  local clean_msg="$input"

  input="${input#"${input%%[![:space:]]*}"}"

  if [[ "$input" =~ ^-([0-9]+)([[:space:]]+(.*)|$) ]]; then
    parsed_lines="${match[1]}"
    clean_msg="${match[3]}"
  elif [[ "$input" =~ ^-[nN][[:space:]]*([0-9]+)([[:space:]]+(.*)|$) ]]; then
    parsed_lines="${match[1]}"
    clean_msg="${match[3]}"
  fi

  clean_msg="$(_trim "$clean_msg")"

  if [[ -n "$parsed_lines" && "$parsed_lines" -lt 1 ]]; then
    parsed_lines=1
  fi

  PARSED_LINES="$parsed_lines"
  PARSED_QUERY="$clean_msg"
}

obter_conteudo_tela() {
  local n_lines="${1:-$DEFAULT_SCREEN_LINES}"
  local raw=""

  if [[ -f "$FILE" && -s "$FILE" ]]; then
    raw="$(cat "$FILE" 2>/dev/null)"
  elif [[ -f "/tmp/qwen_tela.txt" && -s "/tmp/qwen_tela.txt" && ! -L "/tmp/qwen_tela.txt" ]]; then
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

_obter_kitty_target() {
  local listen_sock=""

  if [[ -f "/tmp/orig_kitty_listen" && ! -L "/tmp/orig_kitty_listen" ]]; then
    listen_sock="$(_trim "$(cat /tmp/orig_kitty_listen 2>/dev/null)")"
  fi
  [[ -z "$listen_sock" && -n "$KITTY_LISTEN_ON" ]] && listen_sock="$KITTY_LISTEN_ON"

  # Se o socket salvo não responde mais (terminal foi fechado), busca o socket ativo mais recente
  if [[ -n "$listen_sock" ]] && command -v kitty >/dev/null 2>&1; then
    if ! kitty @ --to "$listen_sock" ls >/dev/null 2>&1; then
      listen_sock=""
    fi
  fi

  if [[ -z "$listen_sock" ]]; then
    local -a sock_candidates
    sock_candidates=(/tmp/mykitty*(N))
    for s in "${sock_candidates[@]}"; do
      [[ -S "$s" ]] || continue
      if kitty @ --to "unix:$s" ls >/dev/null 2>&1; then
        listen_sock="unix:$s"
        break
      fi
    done
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
        target_win="$(kitty @ --to "$listen_sock" ls 2>/dev/null | jq -r '.[0].tabs[0].windows[0].id // empty' 2>/dev/null)"
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
  local n_lines="${1:-$DEFAULT_SCREEN_LINES}"
  local nova_tela=""

  _obter_kitty_target

  if command -v kitty >/dev/null 2>&1 && [[ -n "$TARGET_KITTY_SOCK" ]]; then
    nova_tela="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=screen --match="id:$TARGET_KITTY_WIN" 2>/dev/null)"

    if [[ -z "$nova_tela" ]]; then
      nova_tela="$(kitty @ --to "$TARGET_KITTY_SOCK" get-text --extent=screen 2>/dev/null)"
    fi
  fi

  if [[ -z "$nova_tela" && -f "$FILE" ]]; then
    nova_tela="$(cat "$FILE" 2>/dev/null)"
  elif [[ -z "$nova_tela" && -f "/tmp/qwen_tela.txt" && ! -L "/tmp/qwen_tela.txt" ]]; then
    nova_tela="$(cat "/tmp/qwen_tela.txt" 2>/dev/null)"
  fi

  if [[ -z "$nova_tela" ]]; then
    _warn "Não foi possível capturar a tela do terminal original."
    return 1
  fi

  local cleaned="$(clean_screen_content "$nova_tela")"
  if [[ -n "$cleaned" ]]; then
    local -a lines=("${(@f)cleaned}")
    if (( ${#lines[@]} > n_lines )); then
      lines=("${(@)lines[-$n_lines,-1]}")
    fi
    print -r -- "${(F)lines}"
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

  if ! command -v kitty >/dev/null 2>&1; then
    _warn "Comando 'kitty' não encontrado."
    return 1
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

  _obter_kitty_target

  if [[ -z "$TARGET_KITTY_SOCK" ]]; then
    _warn "Nenhum socket do Kitty encontrado."
    return 1
  fi

  local sent=1

  if _should_type_effect "$code" "$auto_enter" && _python_ok "$PYTHON_BIN"; then
    "${PYTHON_BIN:-python3}" -c '
import subprocess, time, sys

sock, win, cmd = sys.argv[1], sys.argv[2], sys.argv[3]
auto_enter = int(sys.argv[4]) if len(sys.argv) > 4 else 0
speed = 0.012

for ch in cmd:
    subprocess.run(["kitty", "@", "--to", sock, "send-text", f"--match=id:{win}", ch], capture_output=True)
    time.sleep(speed)

if auto_enter == 1:
    time.sleep(0.15)
    subprocess.run(["kitty", "@", "--to", sock, "send-text", f"--match=id:{win}", "\r"], capture_output=True)
' "$TARGET_KITTY_SOCK" "$TARGET_KITTY_WIN" "$code" "$auto_enter" 2>/dev/null

    sent=$?

    if (( sent != 0 )); then
      if kitty @ --to "$TARGET_KITTY_SOCK" send-text --match="id:$TARGET_KITTY_WIN" "$code" 2>/dev/null ||
         kitty @ --to "$TARGET_KITTY_SOCK" send-text "$code" 2>/dev/null; then
        if [[ "$auto_enter" == 1 ]]; then
          sleep 0.15
          kitty @ --to "$TARGET_KITTY_SOCK" send-text --match="id:$TARGET_KITTY_WIN" $'\r' 2>/dev/null ||
            kitty @ --to "$TARGET_KITTY_SOCK" send-text $'\r' 2>/dev/null
        fi
        sent=0
      else
        sent=1
      fi
    fi
  else
    if kitty @ --to "$TARGET_KITTY_SOCK" send-text --match="id:$TARGET_KITTY_WIN" "$code" 2>/dev/null ||
       kitty @ --to "$TARGET_KITTY_SOCK" send-text "$code" 2>/dev/null; then
      if [[ "$auto_enter" == 1 ]]; then
        sleep 0.15
        kitty @ --to "$TARGET_KITTY_SOCK" send-text --match="id:$TARGET_KITTY_WIN" $'\r' 2>/dev/null ||
          kitty @ --to "$TARGET_KITTY_SOCK" send-text $'\r' 2>/dev/null
      fi
      sent=0
    else
      sent=1
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
