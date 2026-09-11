#!/usr/bin/env zsh
# =============================================================================
# fix/05-prompt-widget.zsh
# Menu interativo principal FZF (Ctrl+G) e registro de widget ZLE.
# =============================================================================

inteligencia_prompt() {
  setopt LOCAL_OPTIONS TYPESET_SILENT
  trap : INT

  {
    _ai_fix_check_deps || return 0
    _ai_fix_reload_envs

    local -x FZF_DEFAULT_OPTS=""
    local repo_info="" files_preview="" context=""
    local busca="" categoria="" conf_file="${METIS_CONFIG_DIR:-$HOME/.config/metis}/.fix_ia_selected"
    local cr=$'\033[0m' cc=$'\033[1;36m' cy=$'\033[1;33m' cg=$'\033[1;32m' cw=$'\033[1;37m' cdim=$'\033[90m'
    local current_ia_label="" prev_acao="" prev_config="" out_principal="" rc=0
    local busca_principal="" action_principal=""
    local prev_cmd_direto="" prev_me_ensinar="" menu_acao="" out="" rc2=0
    local nova_busca="" action=""
    local prev_cat_local="" prev_cat_web="" prev_cat_api="" menu_categoria_ia="" rc_cat=0
    local prev_api_gem="" prev_api_groq="" prev_api_nvd="" prev_api_or="" menu_api="" rc_api=0
    local current_ia="" use_local=0 use_g4f=0 is_gemini=0 is_groq=0 is_nvidia=0 is_openrouter=0
    local -a main_parts=() action_parts=()

    if command git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      repo_info=" | Repo: Git"
    fi

    files_preview="$(command ls -p 2>/dev/null | grep -v / | head -n 5 | tr '\n' ',' | sed 's/,$//')"
    context="OS: $(uname -s) | Shell: ZSH | Dir: $(pwd)$repo_info | Arquivos Locais: $files_preview"

    zle -I 2>/dev/null || true

    if [[ ! -f "$conf_file" ]]; then
      mkdir -p "${conf_file:h}" 2>/dev/null
      print -r -- "Local: Ollama" > "$conf_file"
    fi

    while true; do
      _ai_fix_reload_envs

      current_ia_label="$(_ai_fix_get_active_ia_label)"

      prev_acao="
${cc}🚀 Executar Ação no Terminal${cr}
────────────────────────────────────────
${cy}💻 1. Comando Direto${cr}
• Gera o comando shell exato para sua dúvida
• Insere diretamente no seu prompt (ZLE)

${cy}📚 2. Me Ensinar${cr}
• Chat didático interativo passo a passo
• Explica flags, parâmetros e boas práticas
"

      prev_config="
${cc}⚙️ Configurações & Modelos de IA${cr}
────────────────────────────────────────
${cg}⭐ Provedor Ativo:${cr} ${cw}$current_ia_label${cr}

${cy}🤖 1. IA Local (Ollama):${cr}
• Modelo: ${cw}${OLLAMA_MODEL:-qwen2.5-coder:7b}${cr} (100% Offline)

${cy}🌍 2. IA Web (G4F):${cr}
• Modelo: ${cw}${G4F_MODEL:-gpt-4o}${cr} (Web Gratuito)

${cy}☁️ 3. APIs Externas:${cr}
• Gemini:     ${cw}${GEMINI_MODEL:-gemini-2.0-flash}${cr}
• Groq:       ${cw}${GROQ_MODEL:-llama-3.3-70b-versatile}${cr}
• NVIDIA:     ${cw}${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}${cr}
• OpenRouter: ${cw}${OPENROUTER_MODEL:-minimax/minimax-m3:free}${cr}
"

      typeset -gx AI_FIX_PREV_ACAO="$prev_acao"
      typeset -gx AI_FIX_PREV_CONFIG="$prev_config"

      out_principal="$(
        printf '🚀 1. Executar Ação\n⚙️ 2. Configurações de IA\n' |
        fzf --height=28% --reverse --border --ansi \
            --header="🏛️  Metis | Digite sua dúvida ou Escolha uma Opção (ESC = Sair):" \
            --prompt="> " \
            --query="$busca" \
            --disabled \
            --no-sort \
            --print-query \
            --preview='case "{}" in *1*) printf "%s\n" "$AI_FIX_PREV_ACAO" ;; *) printf "%s\n" "$AI_FIX_PREV_CONFIG" ;; esac' \
            --preview-window="right:55%:wrap"
      )"
      rc=$?

      if (( rc != 0 )) || [[ -z "$out_principal" ]]; then
        return 0
      fi

      out_principal="${out_principal%$'\n'}"

      main_parts=("${(@f)out_principal}")
      busca_principal="${main_parts[1]}"
      action_principal="${main_parts[-1]}"

      busca="$(_ai_fix_trim "$busca_principal")"
      action_principal="$(_ai_fix_trim "$action_principal")"

      if [[ -z "$action_principal" || "$action_principal" == "$busca" ]]; then
        continue
      fi

      case "$action_principal" in
        "🚀 1."*)
          prev_cmd_direto="
${cc}💻 Comando Direto${cr}
────────────────────────────────────────
• Gera o comando shell exato para sua dúvida
• Insere diretamente no seu prompt (ZLE)
"
          prev_me_ensinar="
${cc}📚 Me Ensinar${cr}
────────────────────────────────────────
• Chat didático interativo passo a passo
• Explica flags, parâmetros e boas práticas
"
          typeset -gx AI_FIX_PREV_CMD="$prev_cmd_direto"
          typeset -gx AI_FIX_PREV_ENSINAR="$prev_me_ensinar"

          menu_acao=$'💻 1. Comando Direto\n📚 2. Me Ensinar\n↩️  0. Voltar\n'

          out="$(printf '%s' "$menu_acao" |
            fzf --height=32% --reverse --border --ansi \
                --header="🏛️  Metis | Confirme a dúvida e escolha a ação (Enter):" \
                --prompt="> " \
                --query="$busca" \
                --disabled \
                --no-sort \
                --print-query \
                --preview='case "{}" in *1.*) printf "%s\n" "$AI_FIX_PREV_CMD" ;; *2.*) printf "%s\n" "$AI_FIX_PREV_ENSINAR" ;; *) printf "Voltar\n" ;; esac' \
                --preview-window="right:50%:wrap" \
                --bind 'esc:abort')"
          rc2=$?

          if (( rc2 != 0 )) || [[ -z "$out" ]]; then
            continue
          fi

          out="${out%$'\n'}"

          action_parts=("${(@f)out}")
          nova_busca="${action_parts[1]}"
          action="${action_parts[-1]}"

          busca="$(_ai_fix_trim "$nova_busca")"
          action="$(_ai_fix_trim "$action")"

          if [[ -z "$action" || "$action" == "$busca" ]]; then
            continue
          fi

          case "$action" in
            "💻 1."*)
              categoria="1. Comando Direto"
              ;;
            "📚 2."*)
              categoria="2. Me Ensinar"
              ;;
            *)
              continue
              ;;
          esac

          if [[ -z "$busca" ]]; then
            continue
          fi

          break
          ;;

        "⚙️ 2."*)
          _ai_fix_reload_envs

          prev_cat_local="
${cc}🤖 IA Local (Ollama)${cr}
────────────────────────────────────────
${cg}⭐ Modelo Ativo:${cr} ${OLLAMA_MODEL:-qwen2.5-coder:7b}
• 100% offline no hardware local
• Selecione para escolher ou trocar de modelo
"
          prev_cat_web="
${cc}🌍 IA Web (G4F)${cr}
────────────────────────────────────────
${cg}⭐ Modelo Ativo:${cr} ${G4F_MODEL:-gpt-4o}
• Modelos gratuitos via Web
• Selecione para escolher, adicionar ou remover modelos
"
          prev_cat_api="
${cc}☁️ Provedores de API Externa${cr}
────────────────────────────────────────
${cy}Modelos Ativos:${cr}
✨ Gemini:     ${GEMINI_MODEL:-gemini-2.0-flash}
🚀 Groq:       ${GROQ_MODEL:-llama-3.3-70b-versatile}
🟢 NVIDIA:     ${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}
🪐 OpenRouter: ${OPENROUTER_MODEL:-minimax/minimax-m3:free}
"
          typeset -gx AI_FIX_PREV_CAT_LOCAL="$prev_cat_local"
          typeset -gx AI_FIX_PREV_CAT_WEB="$prev_cat_web"
          typeset -gx AI_FIX_PREV_CAT_API="$prev_cat_api"

          menu_categoria_ia="$(
            printf '🤖 1. IA Local (Ollama: %s)\n🌍 2. IA Web (G4F: %s)\n☁️ 3. API Externa (Gemini, Groq, NVIDIA, OpenRouter)\n🔄 4. Sincronizar com Metis\n🗑️  5. Remover Servidor Customizado\n↩️  0. Voltar\n' \
              "${OLLAMA_MODEL:-qwen2.5-coder:7b}" \
              "${G4F_MODEL:-gpt-4o}" |
            fzf --height=36% --reverse --border --ansi \
                --header="🏛️  Metis | Escolha a Categoria da IA:" \
                --prompt="> " \
                --preview='case "{}" in *Local*|*Ollama*) printf "%s\n" "$AI_FIX_PREV_CAT_LOCAL" ;; *Web*|*G4F*) printf "%s\n" "$AI_FIX_PREV_CAT_WEB" ;; *API*) printf "%s\n" "$AI_FIX_PREV_CAT_API" ;; *Sincronizar*) printf "Sincroniza todos os modelos e configurações adicionados no Metis para o seu terminal.\n" ;; *Remover*) printf "Remove um servidor customizado cadastrado.\n" ;; *) printf "Voltar\n" ;; esac' \
                --preview-window="right:50%:wrap"
          )"
          rc_cat=$?

          if (( rc_cat != 0 )) || [[ -z "$menu_categoria_ia" ]]; then
            continue
          fi

          case "$menu_categoria_ia" in
            "🤖 1."*)
              _ai_fix_lista_selecao_e_digitacao_ollama
              ;;
            "🌍 2."*)
              _ai_fix_lista_selecao_e_digitacao "G4F"
              ;;
            "☁️ 3."*)
              local py_b="$(_ai_fix_get_python)"
              local -a api_menu_lines=()
              local line_item="" fzf_api_entries=""

              if [[ -n "$py_b" ]]; then
                while IFS= read -r line_item; do
                  [[ -n "$line_item" ]] && api_menu_lines+=("$line_item")
                done < <("$py_b" "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py" api_menu 2>/dev/null)
              fi

              for line_item in "${api_menu_lines[@]}"; do
                local display_text="${line_item%%|*}"
                fzf_api_entries+="$display_text"$'\n'
              done
              fzf_api_entries+="🔄 Sincronizar com Metis"$'\n'
              fzf_api_entries+="↩️  0. Voltar"$'\n'

              menu_api="$(
                printf '%s' "$fzf_api_entries" |
                fzf --height=34% --reverse --border --ansi \
                    --header="🏛️  Metis | Escolha o Provedor de API Desejado:" \
                    --prompt="> "
              )"
              rc_api=$?

              if (( rc_api != 0 )) || [[ -z "$menu_api" || "$menu_api" == *"Voltar"* ]]; then
                continue
              fi

              if [[ "$menu_api" == *"Sincronizar com Metis"* ]]; then
                clear
                if [[ -n "$py_b" ]]; then
                  "$py_b" "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py" sync
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
              if [[ -n "$py_b" ]]; then
                "$py_b" "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/manage_models.py" sync
              fi
              _ai_fix_reload_envs
              printf '\n\033[36mPressione ENTER para continuar...\033[0m'
              read -r _ </dev/tty || true
              ;;
            "🗑️"*|"5."*)
              _ai_fix_remover_servidor_customizado
              ;;
            *)
              continue
              ;;
          esac

          continue
          ;;

        *)
          continue
          ;;
      esac
    done

    _ai_fix_reload_envs

    if [[ "$categoria" == "1. Comando Direto" ]]; then
      _ai_fix_exec_comando_direto "$context" "$busca"
    elif [[ "$categoria" == "2. Me Ensinar" ]]; then
      _ai_fix_exec_me_ensinar "$context" "$busca"
    fi
  } always {
    unset AI_FIX_PREV_ACAO AI_FIX_PREV_CONFIG AI_FIX_PREV_CMD \
          AI_FIX_PREV_ENSINAR AI_FIX_PREV_CAT_LOCAL AI_FIX_PREV_CAT_WEB \
          AI_FIX_PREV_CAT_API 2>/dev/null || true
    trap - INT 2>/dev/null || true
    zle reset-prompt 2>/dev/null || true
  }
}

fix() {
  if [[ -n "$WIDGET" ]]; then
    zle inteligencia_prompt
  else
    print "O comando fix é um widget ZLE. Use Ctrl+G no terminal." >&2
    return 1
  fi
}

zle -N inteligencia_prompt 2>/dev/null || true
bindkey '^G' inteligencia_prompt 2>/dev/null || true
bindkey '^g' inteligencia_prompt 2>/dev/null || true
