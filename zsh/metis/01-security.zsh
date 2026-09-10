#!/usr/bin/env zsh
# =============================================================================
# metis/01-security.zsh
# Checagem de segurança e comandos de risco do copiloto.
# =============================================================================

_metis_is_destructive() {
  local cmd="$1"

  if (( ${+functions[_ai_is_destructive_cmd]} )); then
    _ai_is_destructive_cmd "$cmd"
    return $?
  fi

  # Fallback conservador caso a função externa não exista.
  local risky='(^|[;&|[:space:]])(sudo[[:space:]]+)?(rm[[:space:]]+-[[:alnum:]-]*r|mkfs|dd|shred|fdisk|parted|truncate|chmod[[:space:]]+-R|chown[[:space:]]+-R|curl.*\|[[:space:]]*(sh|bash|zsh)|wget.*\|[[:space:]]*(sh|bash|zsh)|eval|docker[[:space:]]+(rm|rmi|system[[:space:]]+prune)|kubectl[[:space:]]+delete|git[[:space:]]+push.*--force|iptables[[:space:]]+-F|ufw[[:space:]]+disable|drop[[:space:]]+(database|table))'

  [[ "$cmd" =~ $risky ]]
}
