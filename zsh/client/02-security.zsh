#!/usr/bin/env zsh
# =============================================================================
# client/02-security.zsh
# Análise de caminhos protegidos, comandos destrutivos e comandos seguros de leitura.
# =============================================================================

_ai_is_sensitive_path() {
  local p="$1"
  [[ -z "$p" ]] && return 1

  case "$p" in
    "$HOME/.ssh"*|"$HOME/.aws"*|"$HOME/.gnupg"*|"$HOME/.env"*|"$HOME/.config/gcloud"*|"$HOME/.kube/config"*|"$HOME/.docker/config.json"*|"$HOME/.netrc"|"$HOME/.git-credentials"*|"$HOME/.bash_history"|"$HOME/.zsh_history"|/etc/shadow|/etc/sudoers|/etc/sudoers.d*|/root/*)
      return 0
      ;;
  esac

  return 1
}

_ai_is_destructive_cmd() {
  local cmd="$1"
  [[ -z "$cmd" ]] && return 1

  local -a dangerous_patterns
  dangerous_patterns=(
    'rm ' $'rm\t' 'rm -' 'rmdir ' 'mkfs' 'dd ' 'shred' 'chmod -R' 'chmod 777' 'chown -R'
    'kill ' 'kill -9' 'killall' 'pkill' 'reboot' 'shutdown' 'poweroff' 'init 0'
    'git reset --hard' 'git push --force' 'git push -f' 'git push --force-with-lease'
    'git clean -f' 'git clean -fd'
    'sudo rm' 'sudo dd' 'sudo mkfs' '> /dev/' 'drop database' 'drop table'
    'truncate' 'wipefs' 'fdisk' 'parted' 'swapoff' 'umount'
    'iptables -F' 'ufw disable' 'systemctl stop' 'systemctl disable'
  )

  local p
  for p in "${dangerous_patterns[@]}"; do
    [[ "$cmd" == *"$p"* ]] && return 0
  done

  return 1
}

_ai_is_safe_read_cmd() {
  local cmd="$1"
  [[ -z "$cmd" ]] && return 1

  if [[ "$cmd" == *$'\n'* || "$cmd" == *$'\r'* ]]; then
    return 1
  fi

  if [[ "$cmd" == *".."* ]]; then
    return 1
  fi

  local -a bad_ops
  bad_ops=('|' ';' '&' '>' '<' '$(' '`' '&&' '||')

  local op
  for op in "${bad_ops[@]}"; do
    [[ "$cmd" == *"$op"* ]] && return 1
  done

  local -a sensitive
  sensitive=(
    '.ssh' '.aws' '.gnupg' '.env' 'id_rsa' 'credentials'
    'shadow' 'sudoers' '.netrc' '.kube/config' '.docker/config'
    '/root' '.git-credentials' '.bash_history' '.zsh_history'
    '.python_history' '.npmrc' '.pypirc'
  )

  local s
  for s in "${sensitive[@]}"; do
    [[ "$cmd" == *"$s"* ]] && return 1
  done

  local -a words
  words=(${=cmd})

  local first_word="${words[1]}"

  # Se for caminho absoluto ou relativo, rejeita se não estiver em diretórios confiáveis
  if [[ "$first_word" == /* ]]; then
    if [[ "$first_word" != /bin/* && "$first_word" != /usr/bin/* && "$first_word" != /usr/local/bin/* ]]; then
      return 1
    fi
  elif [[ "$first_word" == ./* || "$first_word" == ../* ]]; then
    return 1
  fi

  local first="${first_word:t}"

  case "$first" in
    ls|eza|lsd|cat|head|tail|grep|rg|find|pwd|date|whoami|tree|which|file|wc|du|df|uname|stat)
      if [[ "$first" == "find" ]]; then
        [[ "$cmd" == *"-delete"* || "$cmd" == *"-exec"* || "$cmd" == *"-execdir"* || "$cmd" == *"-ok"* || "$cmd" == *"-fprint"* || "$cmd" == *"-fprintf"* || "$cmd" == *"-fls"* ]] && return 1
      fi
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}
