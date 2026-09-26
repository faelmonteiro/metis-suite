#!/usr/bin/env zsh
# =============================================================================
# client/01-env.zsh
# Parser seguro de arquivos .env, recarga de ambiente e persistência de provedor.
# =============================================================================

_ai_load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0

  if [[ "${AI_ALLOW_INSECURE_ENV:-0}" != "1" ]]; then
    local current_user="${USER:-$(id -un 2>/dev/null)}"
    local file_info
    file_info="$(stat -c '%U %a' "$env_file" 2>/dev/null || stat -f '%Su %Lp' "$env_file" 2>/dev/null)"
    if [[ -n "$file_info" ]]; then
      local file_owner="${file_info%% *}"
      local file_mode="${file_info##* }"
      if [[ "$file_owner" != "$current_user" || ( "$file_mode" != "600" && "$file_mode" != "400" ) ]]; then
        print -r -- "⚠️ Ignorando $env_file por permissões inseguras. Use: chmod 600 $env_file" >&2
        return 0
      fi
    fi
  fi

  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    [[ -z "$line" || "$line" == \#* ]] && continue

    if [[ "$line" =~ ^export[[:space:]]+(.*)$ ]]; then
      line="${match[1]}"
      line="${line#"${line%%[![:space:]]*}"}"
      line="${line%"${line##*[![:space:]]}"}"
    fi

    if [[ "$line" =~ ^([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
      key="${match[1]}"
      val="${match[2]}"

      case "$key" in
        PATH|LD_PRELOAD|LD_LIBRARY_PATH|LD_AUDIT|LD_DEBUG|LD_PROFILE|ZDOTDIR|HOME|SHELL|PYTHONPATH|PYTHONSTARTUP|BASH_ENV|ENV|FPATH|CDPATH)
          continue
          ;;
      esac

      if [[ "$val" =~ ^\"(.*)\"[[:space:]]*(#.*)?$ ]]; then
        val="${match[1]}"
      elif [[ "$val" =~ ^\'(.*)\'[[:space:]]*(#.*)?$ ]]; then
        val="${match[1]}"
      else
        val="${val%%[[:space:]]##*}"
        val="${val#"${val%%[![:space:]]*}"}"
        val="${val%"${val##*[![:space:]]}"}"

        if [[ "$val" =~ ^\"(.*)\"$ ]]; then
          val="${match[1]}"
        elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
          val="${match[1]}"
        fi
      fi

      typeset -gx "$key=$val"
    fi
  done < "$env_file"
}

_ai_reload_all_envs() {
  _ai_load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
}

# Recarrega estado do provedor ativo do arquivo canônico (útil após mudanças no Metis GUI/CLI)
_ai_reload_provider_state() {
  local conf_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
  local last_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.last_provider"
  local theme_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.last_theme"

  [[ -f "$conf_file" ]] && AI_FIX_SELECTED_LABEL="$(_ai_trim "$(cat "$conf_file" 2>/dev/null)")"
  [[ -f "$last_file" ]] && AI_LAST_PROVIDER_NUM="$(_ai_trim "$(cat "$last_file" 2>/dev/null)")"
  [[ -f "$theme_file" ]] && AI_LAST_THEME="$(_ai_trim "$(cat "$theme_file" 2>/dev/null)")"

  # Re-aplica variáveis de ambiente baseadas no provedor salvo
  _ai_reload_all_envs
}

_ai_save_provider_state() {
  local prov="$(_ai_trim "$1")"
  local zsh_ai_dir="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}"
  local file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
  local last_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.last_provider"
  local metis_dir="${METIS_CONFIG_DIR:-$HOME/.config/metis}"

  mkdir -p "${file:h}" 2>/dev/null || return 1
  mkdir -p "$metis_dir" 2>/dev/null

  local default_prov="" label="" num=""

  case "${(U)prov}" in
    OLLAMA|1|LOCAL)
      label="Local: Ollama"
      num="1"
      default_prov="ollama"
      ;;
    G4F|2|WEB)
      label="Web: G4F"
      num="2"
      default_prov="g4f"
      ;;
    GEMINI|3)
      label="API: Gemini"
      num="3"
      default_prov="gemini"
      ;;
    GROQ|4)
      label="API: Groq"
      num="4"
      default_prov="groq"
      ;;
    NVIDIA|5)
      label="API: NVIDIA"
      num="5"
      default_prov="nvidia"
      ;;
    OPENROUTER|6)
      label="API: OpenRouter"
      num="6"
      default_prov="custom:openrouter"
      ;;
    *)
      label="API: $prov"
      num="$prov"
      default_prov="custom:${(L)prov}"
      ;;
  esac

  print -r -- "$label" > "$file"
  print -r -- "$num" > "$last_file" 2>/dev/null
  [[ -d "$zsh_ai_dir" ]] && print -r -- "$label" > "$zsh_ai_dir/.fix_ia_selected" 2>/dev/null
  [[ -d "$zsh_ai_dir" ]] && print -r -- "$num" > "$zsh_ai_dir/.last_provider" 2>/dev/null
  [[ -d "$HOME/.ZSH/ai" ]] && print -r -- "$label" > "$HOME/.ZSH/ai/.fix_ia_selected" 2>/dev/null
  [[ -d "$HOME/.ZSH/ai" ]] && print -r -- "$num" > "$HOME/.ZSH/ai/.last_provider" 2>/dev/null

  # Python save_provider_state already handles this when set_active <provider> <model> is called
  # No need to call Python again - it would incorrectly set DEFAULT_PROVIDER
}
