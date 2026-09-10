#!/usr/bin/env zsh
# =============================================================================
# models/02-select-ollama.zsh
# Menu interativo FZF para listar modelos locais instalados no Ollama.
# =============================================================================

_ai_menu_selecionar_modelo_ollama() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local py_bin manage_script
  local cur_ollama="" m="" fzf_entries="" prev_ol="" out="" rc=0
  local user_query="" selected_line="" chosen_ol="" clean_query=""
  local -a installed_models=() parts=()

  local backend_name="OLLAMA"
  local state_name="Ollama"

  local ACTION_DIGITAR="✍️  [ Digitar outro modelo Ollama ]"
  local ACTION_VOLTAR="↩️  Voltar"

  _ai_menu_prepare || return 1

  py_bin="$AI_MENU_PY_BIN"
  manage_script="$AI_MENU_MANAGE_SCRIPT"

  while true; do
    _ai_reload_all_envs

    cur_ollama="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
    installed_models=()

    if command -v ollama >/dev/null 2>&1; then
      while IFS= read -r m; do
        m="$(_ai_trim "$m")"
        [[ -n "$m" ]] && installed_models+=("$m")
      done < <(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')
    fi

    if [[ -n "$cur_ollama" ]] && (( ! ${installed_models[(Ie)$cur_ollama]} )); then
      installed_models=("$cur_ollama" "${installed_models[@]}")
    fi

    fzf_entries=""

    for m in "${installed_models[@]}"; do
      if [[ "$m" == "$cur_ollama" ]]; then
        fzf_entries+="⭐ [*] $m (Ativo)"$'\n'
      else
        fzf_entries+="   [ ] $m"$'\n'
      fi
    done

    fzf_entries+="$ACTION_DIGITAR"$'\n'
    fzf_entries+="$ACTION_VOLTAR"$'\n'

    prev_ol="
\033[1;36m🤖 IA Local: Ollama\033[0m
────────────────────────────────────────
\033[1;32m⭐ Modelo Ativo:\033[0m \033[1;37m${cur_ollama}\033[0m
\033[1;33m➕ Para Usar Outro Modelo:\033[0m
• Digite o nome do modelo no campo de busca e aperte Enter.
• Ou selecione: ✍️ [ Digitar outro modelo Ollama ].
\033[1;33m💡 Para Escolher / Ativar:\033[0m
• Navegue até o modelo desejado e aperte ENTER."

    typeset -gx AI_FIX_PREV_OLLAMA="$prev_ol"

    out="$(printf '%s' "$fzf_entries" |
      fzf --height=45% --reverse --border \
        --header="🤖 Modelos Ollama (ENTER = Ativar / Digite o nome do modelo):" \
        --prompt="> " \
        --preview='printf "%b\n" "$AI_FIX_PREV_OLLAMA"' \
        --preview-window="right:55%:wrap" \
        --print-query)"
    rc=$?
    unset AI_FIX_PREV_OLLAMA

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
    elif [[ "$selected_line" == "$ACTION_DIGITAR" ]]; then
      if _ai_menu_digitar_novo_modelo "Ollama"; then
        break
      fi
      continue
    else
      if [[ "$selected_line" != "$user_query" && -n "$selected_line" ]]; then
        chosen_ol="${selected_line#*\]}"
        chosen_ol="$(print -r -- "$chosen_ol" | sed -E 's/[[:space:]]*\(Ativo\)$//')"
        chosen_ol="$(_ai_trim "$chosen_ol")"

        if [[ -n "$chosen_ol" ]]; then
          if "$py_bin" "$manage_script" set_active "$backend_name" "$chosen_ol" 2>/dev/null; then
            _ai_reload_all_envs
            _ai_save_provider_state "$state_name"

            printf '\n\033[32m✅ Modelo Ollama ativo alterado para: %s\033[0m\n' "$chosen_ol"
            sleep 1
            break
          else
            printf '\033[31mErro ao ativar modelo Ollama.\033[0m\n'
            sleep 1
            continue
          fi
        fi
      elif [[ -n "$user_query" ]]; then
        clean_query="$(_ai_trim "$user_query")"

        if [[ -n "$clean_query" ]]; then
          if "$py_bin" "$manage_script" set_active "$backend_name" "$clean_query" 2>/dev/null; then
            _ai_reload_all_envs
            _ai_save_provider_state "$state_name"

            printf '\n\033[32m✅ Modelo Ollama ativo alterado para: %s\033[0m\n' "$clean_query"
            sleep 1
            break
          else
            printf '\033[31mErro ao ativar modelo Ollama.\033[0m\n'
            sleep 1
            continue
          fi
        fi
      fi
    fi
  done
}
