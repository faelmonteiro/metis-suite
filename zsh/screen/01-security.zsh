#!/usr/bin/env zsh
# =============================================================================
# screen/01-security.zsh
# Checagens de segurança, caminhos sensíveis, comandos de risco e confirmações.
# =============================================================================

_is_sensitive_path() {
  local p="$1"
  [[ -z "$p" ]] && return 1

  if _has_fn _ai_is_sensitive_path; then
    _ai_is_sensitive_path "$p"
    return $?
  fi

  local rp="$(_resolve_path "$p")"

  [[ "$rp" == /etc/* || \
     "$rp" == /boot/* || \
     "$rp" == /sys/* || \
     "$rp" == /proc/* || \
     "$rp" == /dev/* || \
     "$rp" == /usr/* || \
     "$rp" == /bin/* || \
     "$rp" == /sbin/* || \
     "$rp" == /lib/* || \
     "$rp" == /root/* || \
     "$rp" == "$HOME"/.ssh/* || \
     "$rp" == "$HOME"/.gnupg/* || \
     "$rp" == "$HOME"/.aws/* || \
     "$rp" == "$HOME"/.config/claude/* || \
     "$rp" == "$HOME"/.ZSH/ai/.env* || \
     "$rp" == "$HOME"/Metis/.env* ]] && return 0

  return 1
}

_confirmar_acao() {
  local prompt_msg="$1"
  local ans=""

  printf '\n\033[33m⚠️  %b\033[0m\n' "$prompt_msg" >&2
  printf '\033[33mDeseja permitir? (s/N): \033[0m' >&2

  if read -r ans </dev/tty; then
    case "${ans:l}" in
      s|sim|y|yes)
        return 0
        ;;
      *)
        printf '\033[31m❌ Ação negada pelo usuário.\033[0m\n' >&2
        return 1
        ;;
    esac
  fi

  return 1
}

_confirmar_acao_formatada() {
  local cmd="$1"
  local motivo="${2:-Comando potencialmente sensível}"
  local ans=""

  printf '\n\033[1;33m⚠️  Confirmação [%s]\033[0m\n' "$motivo" >&2
  printf '  \033[1;37m$\033[0m \033[1;38;5;214m%s\033[0m\n' "$cmd" >&2
  printf '\033[1;33mPermitir execução no terminal? (s/N): \033[0m' >&2

  if read -r ans </dev/tty; then
    case "${ans:l}" in
      s|sim|y|yes)
        return 0
        ;;
      *)
        printf '\033[31m✖ Ação cancelada pelo usuário.\033[0m\n' >&2
        return 1
        ;;
    esac
  fi

  return 1
}

_is_safe_read_cmd() {
  local cmd="$1"
  [[ -z "$cmd" ]] && return 1

  if _has_fn _ai_is_safe_read_cmd && _ai_is_safe_read_cmd "$cmd"; then
    return 0
  fi

  # Remove comentários inline (# ...)
  cmd="${cmd%%#*}"
  cmd="$(_trim "$cmd")"
  [[ -z "$cmd" ]] && return 1

  # Multilinha não é safe read
  local non_empty_lines=0
  non_empty_lines=$(print -r -- "$cmd" | grep -c .)
  (( non_empty_lines > 1 )) && return 1

  # Operadores perigosos
  local -a forbidden=(';' '&&' '||' '$(' '`' '&' 'sudo')
  local fb=""
  for fb in "${forbidden[@]}"; do
    [[ "$cmd" == *"$fb"* ]] && return 1
  done

  # Redirecionamento: só permite /dev/null ou 2>&1
  if [[ "$cmd" == *'>'* ]]; then
    local without_devnull="${cmd//>\/dev\/null/}"
    without_devnull="${without_devnull//2>&1/}"
    without_devnull="${without_devnull//2>\/dev\/null/}"
    if [[ "$without_devnull" == *'>'* ]]; then
      return 1
    fi
  fi

  # Arquivos sensíveis
  local -a sensitive=('.ssh' '.aws' '.gnupg' '.env' 'shadow' 'sudoers' '/root')
  local s=""
  for s in "${sensitive[@]}"; do
    [[ "$cmd" == *"$s"* ]] && return 1
  done

  # Validação por pipeline
  local -a segments
  segments=("${(@s:|:)cmd}")

  set -o noglob
  local seg=""
  for seg in "${segments[@]}"; do
    seg="$(_trim "$seg")"
    [[ -z "$seg" ]] && { set +o noglob; return 1; }

    local -a words
    words=(${=seg})
    local bin="${words[1]:t}"

    case "$bin" in
      ss|netstat|ip|ifconfig|ping|traceroute|host|dig|nslookup|route|\
      ps|pgrep|pidof|uptime|whoami|id|uname|hostname|\
      df|du|free|lsblk|lscpu|lshw|lspci|lsusb|inxi|\
      dmesg|journalctl|which|whereis|type|file|stat|\
      cat|head|tail|grep|egrep|fgrep|awk|cut|wc|sort|uniq|tr|sed|column|echo|printf|ls)
        ;;
      systemctl)
        local subcmd="${words[2]:-}"
        case "$subcmd" in
          status|is-active|is-enabled|is-failed|list-units|list-unit-files) ;;
          *) set +o noglob; return 1 ;;
        esac
        ;;
      find)
        [[ "$seg" == *"-delete"* || "$seg" == *"-exec"* ]] && { set +o noglob; return 1; }
        ;;
      *)
        set +o noglob
        return 1
        ;;
    esac
  done
  set +o noglob

  return 0
}

_is_destructive_cmd() {
  if _has_fn _ai_destructive_cmd; then
    _ai_destructive_cmd "$1"
  elif _has_fn _ai_is_destructive_cmd; then
    _ai_is_destructive_cmd "$1"
  else
    return 0
  fi
}

_is_risky_auto_cmd() {
  local cmd="$1"
  [[ -z "$cmd" ]] && return 1

  # Multilinha real (mais de 1 linha com texto)
  local non_empty_lines=0
  non_empty_lines=$(print -r -- "$cmd" | grep -c .)
  if (( non_empty_lines > 1 )); then
    return 0
  fi

  # Teste seguro de conectividade via curl sem escrita em disco
  if [[ "$cmd" == *"curl -o /dev/null"* || "$cmd" == *"curl -sS -o /dev/null"* || "$cmd" == *"curl -s -o /dev/null"* || "$cmd" =~ ^[[:space:]]*curl[[:space:]]+(-I|-sI|--head) ]]; then
    if [[ "$cmd" == *'|'*'sh'* || "$cmd" == *'|'*'bash'* || "$cmd" == *'|'*'zsh'* ]]; then
      return 0
    fi
    return 1
  fi

  local -a dangerous_patterns=(
    'rm ' $'rm\t' 'rm -' 'mkfs' 'dd ' 'shred' 'chmod -R' 'chmod 777' 'chown -R'
    'kill ' 'kill -9' 'killall' 'pkill' 'reboot' 'shutdown' 'poweroff' 'init 0'
    'git reset --hard' 'git push --force' 'git push -f' 'git clean -f' 'git clean -fd'
    'sudo rm' 'sudo dd' 'sudo mkfs' '> /dev/' 'drop database' 'drop table'

    'find -delete' 'find -exec' '-execdir' '-fprintf' '-fprint'
    'nc ' 'ncat ' 'ssh ' 'scp ' 'rsync '
    '| sh' '| bash' '| zsh' '|sh' '|bash' '|zsh'
    'bash -c' 'sh -c' 'zsh -c'
    'python -c' 'python3 -c' 'perl -e' 'ruby -e' 'node -e'
    'truncate' 'wipefs' 'fdisk' 'parted' 'umount' 'swapoff'
    'systemctl stop' 'systemctl disable' 'service stop'
    'iptables -F' 'ufw disable'
    'curl -O' 'curl -o ' 'curl -d ' 'curl --data' 'curl -X POST' 'curl -X PUT' 'curl -X DELETE'
    'wget -O' 'wget -qO'
  )

  local p=""
  for p in "${dangerous_patterns[@]}"; do
    [[ "$cmd" == *"$p"* ]] && return 0
  done

  return 1
}
