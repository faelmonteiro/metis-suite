#!/usr/bin/env zsh
# =============================================================================
# models/04-remove-model.zsh
# Menu FZF multi-seleção para remover modelos salvos dos provedores.
# =============================================================================

_ai_menu_remover_modelo_salvo() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local prov_name="$1"
  local prov_info
  prov_info=($(_ai_menu_resolve_provider "$prov_name"))
  local backend_name="${prov_info[1]}"
  local state_name="${prov_info[2]}"
  local cur_model="" m fzf_entries="" to_remove="" rc=0 m_clean="" first_remaining="" line_rem=""
  local -a model_lines=() selected_removals=() removed_items=() failed_items=()
  local ACTION_VOLTAR="↩️  Voltar"

  _ai_menu_prepare || return 1

  local py_bin="$AI_MENU_PY_BIN"
  local manage_script="$AI_MENU_MANAGE_SCRIPT"

  _ai_reload_all_envs

  cur_model="$(_ai_menu_get_default_model "$backend_name")"

  while IFS= read -r m; do
    m="$(_ai_trim "$m")"
    [[ -n "$m" ]] && model_lines+=("$m")
  done < <("$py_bin" "$manage_script" list "$backend_name" 2>/dev/null)

  if (( ${#model_lines[@]} == 0 )); then
    printf '\n\033[33mNenhum modelo salvo para %s.\033[0m\n' "$state_name"
    sleep 1
    return 0
  fi

  if (( ${#model_lines[@]} == 1 )); then
    printf '\n\033[33m⚠️ A lista possui apenas 1 modelo salvo. Não é possível remover o único modelo.\033[0m\n'
    sleep 1
    return 0
  fi

  for m in "${model_lines[@]}"; do
    fzf_entries+="[REM] $m"$'\n'
  done
  fzf_entries+="$ACTION_VOLTAR"$'\n'

  to_remove="$(printf '%s' "$fzf_entries" |
    fzf --no-mouse -m --height=40% --reverse --border \
      --header="🗑️ Selecione modelo(s) para REMOVER (TAB = Multi-seleção, ENTER = Confirmar):" \
      --prompt="> ")"
  rc=$?

  if (( rc == 130 || rc == 2 )) || [[ -z "$to_remove" ]]; then
    return 0
  fi

  while IFS= read -r line_rem; do
    line_rem="$(_ai_trim "$line_rem")"
    [[ -z "$line_rem" ]] && continue

    if [[ "$line_rem" == "$ACTION_VOLTAR" ]]; then
      return 0
    fi

    m_clean="${line_rem#\[REM\]}"
    m_clean="$(_ai_trim "$m_clean")"
    [[ -n "$m_clean" ]] && selected_removals+=("$m_clean")
  done <<< "$to_remove"

  if (( ${#selected_removals[@]} == 0 )); then
    return 0
  fi

  if (( ${#selected_removals[@]} >= ${#model_lines[@]} )); then
    printf '\n\033[33m⚠️ Não é possível remover todos os modelos salvos de %s.\033[0m\n' "$state_name"
    sleep 1
    return 0
  fi

  for m_clean in "${selected_removals[@]}"; do
    if "$py_bin" "$manage_script" remove "$backend_name" "$m_clean" 2>/dev/null; then
      removed_items+=("$m_clean")
    else
      failed_items+=("$m_clean")
    fi
  done

  if (( ${#removed_items[@]} > 0 )); then
    if [[ -n "$cur_model" ]] && (( ${removed_items[(Ie)$cur_model]} > 0 )); then
      first_remaining=""

      while IFS= read -r m; do
        m="$(_ai_trim "$m")"
        if [[ -n "$m" ]]; then
          first_remaining="$m"
          break
        fi
      done < <("$py_bin" "$manage_script" list "$backend_name" 2>/dev/null)

      if [[ -n "$first_remaining" ]]; then
        if "$py_bin" "$manage_script" set_active "$backend_name" "$first_remaining" 2>/dev/null; then
          _ai_save_provider_state "$state_name"
        fi
      fi
    fi

    _ai_reload_all_envs

    printf '\n\033[32m🗑️ %d modelo(s) removido(s) de %s com sucesso!\033[0m\n' "${#removed_items[@]}" "$state_name"
    for m in "${removed_items[@]}"; do
      printf '  \033[31m• %s\033[0m\n' "$m"
    done
    sleep 1
  fi

  if (( ${#failed_items[@]} > 0 )); then
    printf '\n\033[31mErro ao remover %d modelo(s):\033[0m\n' "${#failed_items[@]}"
    for m in "${failed_items[@]}"; do
      printf '  \033[31m• %s\033[0m\n' "$m"
    done
    sleep 1
  fi

  return 0
}
