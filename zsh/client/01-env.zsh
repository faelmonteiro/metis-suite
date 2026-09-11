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
  [[ -f "$HOME/Metis/.env" ]] && _ai_load_env_file "$HOME/Metis/.env"
  [[ -n "$ZSH_AI_DIR" && -f "${ZSH_AI_DIR:h}/.env" ]] && _ai_load_env_file "${ZSH_AI_DIR:h}/.env"
  _ai_load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
}

_ai_save_provider_state() {
  local prov="$(_ai_trim "$1")"
  local file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
  local last_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.last_provider"

  mkdir -p "${file:h}" 2>/dev/null || return 1

  local default_prov=""

  case "${(U)prov}" in
    OLLAMA|1|LOCAL)
      print -r -- "Local: Ollama" > "$file"
      print -r -- "1" > "$last_file" 2>/dev/null
      default_prov="ollama"
      ;;
    G4F|2|WEB)
      print -r -- "Web: G4F" > "$file"
      print -r -- "2" > "$last_file" 2>/dev/null
      default_prov="g4f"
      ;;
    GEMINI|3)
      print -r -- "API: Gemini" > "$file"
      print -r -- "3" > "$last_file" 2>/dev/null
      default_prov="gemini"
      ;;
    GROQ|4)
      print -r -- "API: Groq" > "$file"
      print -r -- "4" > "$last_file" 2>/dev/null
      default_prov="groq"
      ;;
    NVIDIA|5)
      print -r -- "API: NVIDIA" > "$file"
      print -r -- "5" > "$last_file" 2>/dev/null
      default_prov="nvidia"
      ;;
    OPENROUTER|6)
      print -r -- "API: OpenRouter" > "$file"
      print -r -- "6" > "$last_file" 2>/dev/null
      default_prov="custom:openrouter"
      ;;
    *)
      print -r -- "API: $prov" > "$file"
      print -r -- "$prov" > "$last_file" 2>/dev/null
      default_prov="custom:${(L)prov}"
      ;;
  esac

  local py_b="$(_ai_get_python 2>/dev/null)"
  if [[ -n "$py_b" && -n "$default_prov" ]]; then
    "$py_b" "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py" set_active "DEFAULT_PROVIDER" "$default_prov" 2>/dev/null || true
  fi
}
