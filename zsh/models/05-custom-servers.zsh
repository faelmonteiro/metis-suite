#!/usr/bin/env zsh
# =============================================================================
# models/05-custom-servers.zsh
# Menu FZF para exclusão e gerenciamento de servidores e APIs customizadas.
# =============================================================================

_ai_menu_remover_servidor_customizado() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local py_bin manage_script
  local line="" rest="" sid="" display="" fzf_srv_entries="" to_remove="" rc=0 line_srv="" target_id=""
  local -a srv_lines=() selected_servers=() srv_removed=() failed_servers=()
  local ACTION_VOLTAR="↩️  Voltar"

  _ai_menu_prepare || return 1

  py_bin="$AI_MENU_PY_BIN"
  manage_script="$AI_MENU_MANAGE_SCRIPT"

  while IFS= read -r line; do
    line="$(_ai_trim "$line")"
    [[ -n "$line" ]] && srv_lines+=("$line")
  done < <("$py_bin" "$manage_script" api_menu 2>/dev/null)

  for line in "${srv_lines[@]}"; do
    rest="${line#*|}"
    sid="${rest%%|*}"
    display="${line%%|*}"

    sid="$(_ai_trim "$sid")"
    display="$(_ai_trim "$display")"

    if [[ -n "$sid" && "$sid" != "Gemini" && "$sid" != "Groq" && "$sid" != "NVIDIA" && "$sid" != "OLLAMA" && "$sid" != "Ollama" ]]; then
      fzf_srv_entries+="[REM] $display ($sid)"$'\n'
    fi
  done

  if [[ -z "$fzf_srv_entries" ]]; then
    printf '\n\033[33mNenhum servidor customizado cadastrado para remover.\033[0m\n'
    sleep 1
    return 0
  fi

  fzf_srv_entries+="$ACTION_VOLTAR"$'\n'

  to_remove="$(printf '%s' "$fzf_srv_entries" |
    fzf --no-mouse -m --height=38% --reverse --border \
      --header="🗑️ Selecione SERVIDOR(ES) para REMOVER (TAB = Multi-seleção, ENTER = Confirmar):" \
      --prompt="> ")"
  rc=$?

  if (( rc == 130 || rc == 2 )) || [[ -z "$to_remove" ]]; then
    return 0
  fi

  while IFS= read -r line_srv; do
    line_srv="$(_ai_trim "$line_srv")"
    [[ -z "$line_srv" ]] && continue

    if [[ "$line_srv" == "$ACTION_VOLTAR" ]]; then
      return 0
    fi

    if [[ "$line_srv" != *"("*")" ]]; then
      continue
    fi

    target_id="${line_srv##*\(}"
    target_id="${target_id%\)}"
    target_id="$(_ai_trim "$target_id")"

    if [[ -n "$target_id" ]]; then
      selected_servers+=("$target_id")
    fi
  done <<< "$to_remove"

  if (( ${#selected_servers[@]} == 0 )); then
    return 0
  fi

  for target_id in "${selected_servers[@]}"; do
    if "$py_bin" "$manage_script" remove_server "$target_id"; then
      srv_removed+=("$target_id")
    else
      failed_servers+=("$target_id")
    fi
  done

  if (( ${#srv_removed[@]} > 0 )); then
    _ai_reload_all_envs

    printf '\n\033[32m✅ %d servidor(es) removido(s) do menu ZSH!\033[0m\n' "${#srv_removed[@]}"
    sleep 1
  fi

  if (( ${#failed_servers[@]} > 0 )); then
    printf '\n\033[31mErro ao remover %d servidor(es):\033[0m\n' "${#failed_servers[@]}"
    for target_id in "${failed_servers[@]}"; do
      printf '  \033[31m• %s\033[0m\n' "$target_id"
    done
    sleep 1
  fi

  return 0
}
