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

_is_safe_read_cmd() {
  if _has_fn _ai_is_safe_read_cmd; then
    _ai_is_safe_read_cmd "$1"
  else
    return 1
  fi
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

  # Multilinha sempre é tratado como sensível no modo automático.
  if [[ "$cmd" == *$'\n'* ]]; then
    return 0
  fi

  local -a dangerous_patterns=(
    'rm ' $'rm\t' 'rm -' 'mkfs' 'dd ' 'shred' 'chmod -R' 'chmod 777' 'chown -R'
    'kill ' 'kill -9' 'killall' 'pkill' 'reboot' 'shutdown' 'poweroff' 'init 0'
    'git reset --hard' 'git push --force' 'git push -f' 'git clean -f' 'git clean -fd'
    'sudo rm' 'sudo dd' 'sudo mkfs' '> /dev/' 'drop database' 'drop table'

    'find -delete' 'find -exec' '-execdir' '-fprintf' '-fprint'
    'curl' 'wget' 'nc ' 'ncat' 'ssh' 'scp' 'rsync'
    '| sh' '| bash' '| zsh' '|sh' '|bash' '|zsh'
    'bash -c' 'sh -c' 'zsh -c'
    'python -c' 'python3 -c' 'perl -e' 'ruby -e' 'node -e'
    'truncate' 'wipefs' 'fdisk' 'parted' 'umount' 'swapoff'
    'systemctl stop' 'systemctl disable' 'service stop'
    'iptables -F' 'ufw disable'
  )

  local p=""
  for p in "${dangerous_patterns[@]}"; do
    [[ "$cmd" == *"$p"* ]] && return 0
  done

  return 1
}
