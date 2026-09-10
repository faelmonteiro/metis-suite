#!/usr/bin/env zsh
# =============================================================================
# models/03-add-model.zsh
# Caixa de diálogo FZF para digitação manual e cadastro de novos modelos.
# =============================================================================

_ai_menu_digitar_novo_modelo() {
  setopt LOCAL_OPTIONS TYPESET_SILENT

  local prov_name="$1"
  local prov_info
  prov_info=($(_ai_menu_resolve_provider "$prov_name"))
  local backend_name="${prov_info[1]}"
  local state_name="${prov_info[2]}"
  local novo_id rc_fzf fzf_out
  local -a fzf_parts=()

  _ai_menu_prepare || return 1

  local py_bin="$AI_MENU_PY_BIN"
  local manage_script="$AI_MENU_MANAGE_SCRIPT"

  fzf_out="$(
    printf '↩️  Cancelar / Voltar\n' |
    fzf --height=22% --reverse --border \
      --header="✍️ Digite o ID do modelo para $state_name (ENTER = Salvar / ESC = Cancelar):" \
      --prompt="Modelo > " \
      --print-query
  )"
  rc_fzf=$?

  if (( rc_fzf == 130 || rc_fzf == 2 )) || [[ -z "$fzf_out" ]]; then
    return 1
  fi

  fzf_out="${fzf_out%$'\n'}"
  fzf_parts=("${(@f)fzf_out}")

  novo_id="${fzf_parts[1]}"
  novo_id="$(_ai_trim "$novo_id")"

  if [[ -z "$novo_id" || "$novo_id" == "0" || "$novo_id" == "/voltar" || "$novo_id" == "/v" || "$novo_id" == *"Cancelar / Voltar"* ]]; then
    return 1
  fi

  if [[ "$backend_name" == "OLLAMA" ]]; then
    if ! "$py_bin" "$manage_script" set_active "$backend_name" "$novo_id" 2>/dev/null; then
      printf '\033[31mErro ao definir modelo Ollama ativo.\033[0m\n'
      sleep 1
      return 1
    fi
  else
    if ! "$py_bin" "$manage_script" add "$backend_name" "$novo_id" 2>/dev/null; then
      printf '\033[31mErro ao salvar modelo para %s.\033[0m\n' "$state_name"
      sleep 1
      return 1
    fi

    if ! "$py_bin" "$manage_script" set_active "$backend_name" "$novo_id" 2>/dev/null; then
      printf '\033[31mErro ao salvar/ativar modelo para %s.\033[0m\n' "$state_name"
      sleep 1
      return 1
    fi
  fi

  _ai_reload_all_envs
  _ai_save_provider_state "$state_name"

  printf '\n\033[32m✅ Modelo "%s" salvo e definido como ativo para %s!\033[0m\n' "$novo_id" "$state_name"
  sleep 1
  return 0
}
