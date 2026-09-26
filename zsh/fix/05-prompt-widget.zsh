#!/usr/bin/env zsh
# =============================================================================
# fix/05-prompt-widget.zsh
# Menu interativo principal FZF (Ctrl+G) - Gerenciamento de Modelos de IA.
# =============================================================================

inteligencia_prompt() {
  setopt LOCAL_OPTIONS TYPESET_SILENT
  trap : INT

  {
    _ai_fix_check_deps || return 0
    _ai_fix_reload_envs

    local -x FZF_DEFAULT_OPTS=""
    local repo_info="" files_preview="" context=""
    local zsh_ai_dir="${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}"
    [[ ! -d "$zsh_ai_dir" && -d "$HOME/.ZSH/ai" ]] && zsh_ai_dir="$HOME/.ZSH/ai"
    local conf_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
    [[ ! -f "$conf_file" && -f "$zsh_ai_dir/.fix_ia_selected" ]] && conf_file="$zsh_ai_dir/.fix_ia_selected"

    local busca="" categoria=""
    local cr=$'\033[0m' cc=$'\033[1;36m' cy=$'\033[1;33m' cg=$'\033[1;32m' cw=$'\033[1;37m' cdim=$'\033[90m'
    local current_ia_label="" out_principal="" rc=0
    local busca_principal="" action_principal=""
    local prev_cat_local="" prev_cat_web="" prev_cat_api="" menu_categoria_ia="" rc_cat=0
    local prev_api_gem="" prev_api_groq="" prev_api_nvd="" prev_api_or="" menu_api="" rc_api=0
    local current_ia="" use_local=0 use_g4f=0 is_gemini=0 is_groq=0 is_nvidia=0 is_openrouter=0
    local -a main_parts=() action_parts=()

    if command git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      repo_info=" | Repo: Git"
    fi

    files_preview="$(command ls -p 2>/dev/null | grep -v / | head -n 5 | tr '\n' ',' | sed 's/,$//')"
    context="OS: $(uname -s) | Shell: ZSH | Dir: $(pwd)$repo_info | Arquivos: $files_preview"

    zle -I 2>/dev/null || true

    if [[ ! -f "$conf_file" ]]; then
      mkdir -p "${conf_file:h}" 2>/dev/null
      print -r -- "Local: Ollama" > "$conf_file"
    fi

    while true; do
      _ai_fix_reload_envs

      current_ia_label="$(_ai_fix_get_active_ia_label)"

      # Preview unificado com todas as categorias
      prev_cat_local="
${cc}🤖 IA Local (Ollama)${cr}
────────────────────────────────────────
${cg}⭐ Modelo Ativo:${cr} ${OLLAMA_MODEL:-llama3.2:3b}
• 100% offline no hardware local
• Enter para escolher/trocar modelo
"
      prev_cat_web="
${cc}🌍 IA Web (G4F)${cr}
────────────────────────────────────────
${cg}⭐ Modelo Ativo:${cr} ${G4F_MODEL:-gpt-4o}
• Modelos gratuitos via Web
• Enter para escolher ou adicionar modelo
"
      local py_b="$(_ai_fix_get_python)"
      local -a api_menu_lines=()
      local line_item="" api_lines="" api_names_summary=""
      local -a api_names=()
      local manage_script="$zsh_ai_dir/manage_models.py"

      if [[ -n "$py_b" && -f "$manage_script" ]]; then
        while IFS= read -r line_item; do
          [[ -n "$line_item" ]] && api_menu_lines+=("$line_item")
        done < <("$py_b" "$manage_script" api_menu 2>/dev/null)
      fi

      if (( ${#api_menu_lines[@]} > 0 )); then
        for line_item in "${api_menu_lines[@]}"; do
          local disp="${line_item%%|*}"
          local rest="${line_item#*|}"
          local srv_id="${rest%%|*}"
          local srv_model="${rest#*|}"
          local icone="${disp%% *}"
          local nome=""
          if [[ "$srv_id" == "nvidia" ]]; then nome="NVIDIA"
          elif [[ "$srv_id" == "groq" ]]; then nome="Groq"
          elif [[ "$srv_id" == "openrouter" ]]; then nome="OpenRouter"
          elif [[ "$srv_id" == "gemini" ]]; then nome="Gemini"
          else nome="${(C)srv_id}"; fi
          api_names+=("$nome")
          api_lines+="$(printf '%s %-12s %s' "$icone" "${nome}:" "$srv_model")"$'\n'
        done
        api_names_summary="${(j:, :)api_names}"
      fi

      if [[ -z "$api_lines" ]]; then
        api_lines="🟢 NVIDIA:      ${NVIDIA_MODEL:-moonshotai/kimi-k3}"$'\n'"🚀 Groq:        ${GROQ_MODEL:-openai/gpt-oss-120b}"$'\n'
        api_names_summary="NVIDIA, Groq"
      fi

      prev_cat_api="
${cc}☁️ APIs Externas${cr}
────────────────────────────────────────
${cy}Modelos Ativos:${cr}
${api_lines}• Enter para gerenciar provedores
"
      typeset -gx AI_FIX_PREV_CAT_LOCAL="$prev_cat_local"
      typeset -gx AI_FIX_PREV_CAT_WEB="$prev_cat_web"
      typeset -gx AI_FIX_PREV_CAT_API="$prev_cat_api"

      # Menu principal direto com todas as opções
      menu_categoria_ia="$(
        printf '🤖 1. IA Local (Ollama: %s)\n🌍 2. IA Web (G4F: %s)\n☁️ 3. APIs Externas (%s)\n🔄 4. Sincronizar com Metis\n↩️  0. Sair\n' \
          "${OLLAMA_MODEL:-llama3.2:3b}" \
          "${G4F_MODEL:-gpt-4o}" \
          "${api_names_summary:-NVIDIA, Groq, OpenRouter}" |
        fzf --height=25% --reverse --border --ansi --no-mouse \
            --header="🏛️  Metis | Provedor Ativo: ${current_ia_label}  (ESC = Sair)" \
            --prompt="❯ " \
            --query="$busca" \
            --preview='case "{}" in *Local*|*Ollama*) printf "%s\n" "$AI_FIX_PREV_CAT_LOCAL" ;; *Web*|*G4F*) printf "%s\n" "$AI_FIX_PREV_CAT_WEB" ;; *API*|*Externa*) printf "%s\n" "$AI_FIX_PREV_CAT_API" ;; *Sincronizar*) printf "Sincroniza modelos e configurações do Metis para o terminal.\n" ;; *) printf "Sair do menu.\n" ;; esac' \
            --preview-window="right:50%:wrap" \
            --bind 'esc:abort' \
            --color='header:italic:blue,prompt:green,pointer:red,marker:yellow'
      )"
      rc_cat=$?

      if (( rc_cat != 0 )) || [[ -z "$menu_categoria_ia" ]]; then
        return 0
      fi

      case "$menu_categoria_ia" in
        "🤖 1."*)
          _ai_fix_lista_selecao_e_digitacao_ollama
          ;;
        "🌍 2."*)
          _ai_fix_lista_selecao_e_digitacao "G4F"
          ;;
        "☁️ 3."*)
          local fzf_api_entries=""

          for line_item in "${api_menu_lines[@]}"; do
            local display_text="${line_item%%|*}"
            fzf_api_entries+="$display_text"$'\n'
          done
          fzf_api_entries+="🔄 Sincronizar com Metis"$'\n'
          fzf_api_entries+="↩️  0. Voltar"$'\n'

          menu_api="$(
            printf '%s' "$fzf_api_entries" |
            fzf --height=35% --reverse --border --ansi --no-mouse \
                --header="🏛️  Metis | Escolha o Provedor de API:" \
                --prompt="❯ " \
                --color='header:italic:blue,prompt:green,pointer:red,marker:yellow'
          )"
          rc_api=$?

          if (( rc_api != 0 )) || [[ -z "$menu_api" || "$menu_api" == *"Voltar"* ]]; then
            continue
          fi

          if [[ "$menu_api" == *"Sincronizar com Metis"* ]]; then
            clear
            if [[ -n "$py_b" && -f "$manage_script" ]]; then
              "$py_b" "$manage_script" sync
            fi
            _ai_fix_reload_envs
            printf '\n\033[36mPressione ENTER para continuar...\033[0m'
            read -r _ </dev/tty || true
            continue
          fi

          local chosen_prov_id=""
          for line_item in "${api_menu_lines[@]}"; do
            local display_text="${line_item%%|*}"
            if [[ "$menu_api" == "$display_text" ]]; then
              local rest="${line_item#*|}"
              chosen_prov_id="${rest%%|*}"
              break
            fi
          done

          if [[ -z "$chosen_prov_id" ]]; then
            case "$menu_api" in
              *"Gemini"*) chosen_prov_id="Gemini" ;;
              *"Groq"*) chosen_prov_id="Groq" ;;
              *"NVIDIA"*) chosen_prov_id="NVIDIA" ;;
              *"OpenRouter"*) chosen_prov_id="OpenRouter" ;;
              *) continue ;;
            esac
          fi

          _ai_fix_lista_selecao_e_digitacao "$chosen_prov_id"
          ;;
        "🔄 4."*)
          clear
          local py_b="$(_ai_fix_get_python)"
          if [[ -n "$py_b" && -f "$manage_script" ]]; then
            "$py_b" "$manage_script" sync
          fi
          _ai_fix_reload_envs
          printf '\n\033[36mPressione ENTER para continuar...\033[0m'
          read -r _ </dev/tty || true
          ;;
        *)
          return 0
          ;;
      esac
    done
  } always {
    unset AI_FIX_PREV_CAT_LOCAL AI_FIX_PREV_CAT_WEB AI_FIX_PREV_CAT_API 2>/dev/null || true
    trap - INT 2>/dev/null || true
    zle reset-prompt 2>/dev/null || true
  }
}

fix() {
  if [[ -n "$WIDGET" ]]; then
    zle inteligencia_prompt
  else
    inteligencia_prompt
  fi
}

zle -N inteligencia_prompt 2>/dev/null || true
bindkey '^G' inteligencia_prompt 2>/dev/null || true
bindkey '^g' inteligencia_prompt 2>/dev/null || true
