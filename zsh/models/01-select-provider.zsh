#!/usr/bin/env zsh
# =============================================================================
# models/01-select-provider.zsh
# Menu interativo FZF para selecionar, listar e alternar modelos de APIs e Web.
# =============================================================================

_ai_menu_selecionar_modelo() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local prov_name="$1"
  local prov_info
  prov_info=($(_ai_menu_resolve_provider "$prov_name"))
  local backend_name="${prov_info[1]}"
  local state_name="${prov_info[2]}"
  local py_bin manage_script
  local cur_model="" m fzf_entries="" prev_lista="" out="" rc=0
  local user_query="" selected_line="" chosen_model="" clean_query=""
  local -a model_lines=() parts=()

  local ACTION_NOVO="✍️  [ Digitar novo modelo manualmente ]"
  local ACTION_REMOVER="🗑️  [ Remover modelo salvo da lista ]"
  local ACTION_SYNC="🔄  [ Sincronizar com Metis ]"
  local ACTION_VOLTAR="↩️  Voltar"

  _ai_menu_prepare || return 1

  py_bin="$AI_MENU_PY_BIN"
  manage_script="$AI_MENU_MANAGE_SCRIPT"

  while true; do
    _ai_reload_all_envs

    cur_model="$(_ai_menu_get_default_model "$backend_name")"

    model_lines=()

    while IFS= read -r m; do
      m="$(_ai_trim "$m")"
      [[ -n "$m" ]] && model_lines+=("$m")
    done < <("$py_bin" "$manage_script" list "$backend_name" 2>/dev/null)

    if [[ -n "$cur_model" ]] && (( ! ${model_lines[(Ie)$cur_model]} )); then
      if (( ${#model_lines[@]} > 0 )); then
        cur_model="${model_lines[1]}"
        "$py_bin" "$manage_script" set_active "$backend_name" "$cur_model" 2>/dev/null
        _ai_reload_all_envs
      fi
    fi

    fzf_entries=""

    for m in "${model_lines[@]}"; do
      if [[ "$m" == "$cur_model" ]]; then
        fzf_entries+="⭐ [*] $m (Ativo)"$'\n'
      else
        fzf_entries+="   [ ] $m"$'\n'
      fi
    done

    fzf_entries+="$ACTION_NOVO"$'\n'
    fzf_entries+="$ACTION_REMOVER"$'\n'
    fzf_entries+="$ACTION_SYNC"$'\n'
    fzf_entries+="$ACTION_VOLTAR"$'\n'

    prev_lista="
\033[1;36m⭐ Provedor: ${state_name}\033[0m
────────────────────────────────────────
\033[1;32m⭐ Modelo Ativo:\033[0m \033[1;37m${cur_model}\033[0m
\033[1;33m➕ Para Adicionar um Novo Modelo:\033[0m
• Digite o nome/ID do modelo no campo de busca e aperte Enter.
• Ou selecione: ✍️ [ Digitar novo modelo manualmente ].
\033[1;33m🗑️ Para Remover um Modelo:\033[0m
• Selecione: 🗑️ [ Remover modelo salvo da lista ].
\033[1;33m🔄 Para Sincronizar:\033[0m
• Selecione: 🔄 [ Sincronizar com Metis ].
\033[1;33m💡 Para Escolher / Ativar um Modelo:\033[0m
• Navegue até o modelo desejado e aperte ENTER."

    typeset -gx AI_FIX_PREV_LISTA="$prev_lista"

    out="$(printf '%s' "$fzf_entries" |
      fzf --height=45% --reverse --border \
        --header="⚙️ Modelos $state_name (ENTER = Ativar / Digite um novo modelo):" \
        --prompt="> " \
        --preview='printf "%b\n" "$AI_FIX_PREV_LISTA"' \
        --preview-window="right:55%:wrap" \
        --print-query)"
    rc=$?
    unset AI_FIX_PREV_LISTA

    if (( rc == 130 || rc == 2 )) || [[ -z "$out" ]]; then
      break
    fi

    out="${out%$'\n'}"
    parts=("${(@f)out}")

    user_query="${parts[1]}"
    selected_line="${parts[-1]}"

    user_query="$(_ai_trim "$user_query")"
    selected_line="$(_ai_trim "$selected_line")"

    if [[ -z "$selected_line" || "$selected_line" == "$ACTION_VOLTAR" || "$user_query" == "$ACTION_VOLTAR" || "$user_query" == "/voltar" || "$user_query" == "/v" || "$user_query" == "0" ]]; then
      break
    elif [[ "$selected_line" == "$ACTION_NOVO" ]]; then
      if _ai_menu_digitar_novo_modelo "$prov_name"; then
        break
      fi
      continue
    elif [[ "$selected_line" == "$ACTION_REMOVER" ]]; then
      _ai_menu_remover_modelo_salvo "$prov_name"
      continue
    elif [[ "$selected_line" == "$ACTION_SYNC" ]]; then
      clear

      if ! "$py_bin" "$manage_script" sync; then
        printf '\n\033[31mErro ao sincronizar com Metis.\033[0m\n'
        sleep 1
      fi

      _ai_reload_all_envs

      printf '\n\033[36mPressione ENTER para continuar (ou aguarde 3s)...\033[0m'
      stty sane 2>/dev/null
      read -t 3 -k 1 _ </dev/tty 2>/dev/null || read -t 3 -r _ </dev/tty 2>/dev/null || true
      continue
    else
      if [[ "$selected_line" != "$user_query" && -n "$selected_line" ]]; then
        chosen_model="${selected_line#*\]}"
        chosen_model="$(print -r -- "$chosen_model" | sed -E 's/[[:space:]]*\(Ativo\)$//')"
        chosen_model="$(_ai_trim "$chosen_model")"

        if [[ -n "$chosen_model" ]]; then
          if "$py_bin" "$manage_script" set_active "$backend_name" "$chosen_model" 2>/dev/null; then
            _ai_reload_all_envs
            _ai_save_provider_state "$state_name"

            printf '\n\033[32m✅ %s ativado com modelo: %s\033[0m\n' "$state_name" "$chosen_model"
            sleep 1
            break
          else
            printf '\033[31mErro ao ativar modelo %s.\033[0m\n' "$chosen_model"
            sleep 1
            continue
          fi
        fi
      elif [[ -n "$user_query" ]]; then
        clean_query="$(_ai_trim "$user_query")"

        if [[ -n "$clean_query" ]]; then
          if [[ "$backend_name" == "OLLAMA" ]]; then
            if ! "$py_bin" "$manage_script" set_active "$backend_name" "$clean_query" 2>/dev/null; then
              printf '\033[31mErro ao ativar modelo Ollama.\033[0m\n'
              sleep 1
              continue
            fi
          else
            if ! "$py_bin" "$manage_script" add "$backend_name" "$clean_query" 2>/dev/null; then
              printf '\033[31mErro ao adicionar modelo %s para %s.\033[0m\n' "$clean_query" "$state_name"
              sleep 1
              continue
            fi

            if ! "$py_bin" "$manage_script" set_active "$backend_name" "$clean_query" 2>/dev/null; then
              printf '\033[31mErro ao ativar modelo %s.\033[0m\n' "$clean_query"
              sleep 1
              continue
            fi
          fi

          _ai_reload_all_envs
          _ai_save_provider_state "$state_name"

          printf '\n\033[32m✅ Novo modelo "%s" salvo e ativado para %s!\033[0m\n' "$clean_query" "$state_name"
          sleep 1
          break
        fi
      fi
    fi
  done
}
