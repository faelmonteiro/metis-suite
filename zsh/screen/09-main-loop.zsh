#!/usr/bin/env zsh
# =============================================================================
# screen/09-main-loop.zsh
# Fluxo central de inicialização, menus FZF, processamento de tela e chat REPL.
# =============================================================================

main() {
  command -v fzf >/dev/null 2>&1 || _die "fzf não encontrado."

  # Suporte a flags na chamada do assistente: -p/--passos <n>, -p<n>, -n/--lines <n>, -<n>
  local cli_steps=""
  local cli_lines=""

  while (( $# > 0 )); do
    case "$1" in
      -p|--passos|--steps)
        shift
        if [[ "$1" == <-> ]]; then
          cli_steps="$1"
          shift
        fi
        ;;
      -p<->)
        cli_steps="${1#-p}"
        shift
        ;;
      -n|--lines)
        shift
        if [[ "$1" == <-> ]]; then
          cli_lines="$1"
          shift
        fi
        ;;
      -n<->)
        cli_lines="${1#-n}"
        shift
        ;;
      -<->)
        cli_lines="${1#-}"
        shift
        ;;
      *)
        shift
        ;;
    esac
  done

  if [[ -n "$cli_steps" ]]; then
    AI_AUTO_MAX_STEPS="$cli_steps"
  fi
  if [[ -n "$cli_lines" ]]; then
    DEFAULT_SCREEN_LINES="$cli_lines"
  fi

  setup_zle

  local busca_principal="" out_principal="" rc=0 menu_principal="" final_query=""
  local modelo_out="" rc2=0 modelo_fzf=""
  local cur_prov="" active_info="" prev_fast="" prev_local="" prev_ext="" prev_help=""
  local -a parts=()

  local FZF_DEFAULT_OPTS=""

  local active_lines="${DEFAULT_SCREEN_LINES:-30}" SCREEN_CONTENT="" clean_final_query=""
  local CONTEXT="" LAST_RESPONSE="" ia_status=0 auto_status=0
  local voltar_menu=0 LAST_SELECTED_CODE=""
  local USER_INPUT="" CLEAN_INPUT=""
  local NOVA_RESPOSTA="" extra_msg="" sync_lines="${DEFAULT_SCREEN_LINES:-30}" LATEST_SCREEN="" TEMP_CONTEXT=""
  local target_idx="" code_to_copy="" code_to_send=""
  local custom_lines="${DEFAULT_SCREEN_LINES:-30}" custom_msg="" custom_screen=""

  while true; do
    if [[ -n "$METIS_KITTY_POPUP" ]]; then
      clear
      _print_header
    fi

    load_env_file "$HOME/Metis/.env"
    load_env_file "$HOME/.ZSH/ai/.env_local"

    cur_prov="$(_get_saved_provider)"
    active_info="$(_get_active_provider_info "$cur_prov")"

    # Cores 100% unificadas com o fundo do terminal
    local fzf_color_theme="bg:-1,preview-bg:-1,bg+:#20212f,fg:#cdd6f4,fg+:#ffffff,hl:#f38ba8,hl+:#f38ba8,info:#585b70,prompt:#f9e2af,pointer:#f38ba8,marker:#a6e3a1,header:#89b4fa,border:#333644,preview-border:#333644"

    local active_model_raw="${active_info#*: }"
    local active_model_display="${active_model_raw##*/}"
    _get_model_specs "$cur_prov" "$active_model_raw"

    _obter_kitty_target

    local mouse_check="$(obter_selecao_mouse)"
    local has_mouse=0
    local mouse_lines=0
    local mouse_snippet=""

    if [[ -n "$mouse_check" ]]; then
      has_mouse=1
      mouse_lines=$(print -r -- "$mouse_check" | wc -l)
      mouse_snippet="$(print -r -- "$mouse_check" | head -n 5)"
    fi

    if (( has_mouse )); then
      prev_fast="\033[1;33m⚡ SELEÇÃO DO MOUSE\033[0m
────────────────────────
• \033[1;37mIA Ativa:\033[0m $active_model_display
• \033[1;37mAção:\033[0m Analisar texto selecionado no terminal
• \033[1;37mLinhas:\033[0m $mouse_lines
• \033[1;37mLatência média:\033[0m $MODEL_SPEC_LATENCY
• \033[1;37mContexto:\033[0m $MODEL_SPEC_CONTEXT

\033[1;36mTrecho marcado com o mouse:\033[0m
$mouse_snippet
"
    else
      prev_fast="\033[1;33m⚡ SELEÇÃO DO MOUSE\033[0m
────────────────────────
• \033[1;37mIA Ativa:\033[0m $active_model_display
• \033[1;37mAção:\033[0m Analisar texto selecionado no terminal
• \033[1;37mStatus:\033[0m \033[1;33mNenhuma seleção ativa detectada\033[0m
• \033[1;37mLatência média:\033[0m $MODEL_SPEC_LATENCY
• \033[1;37mContexto:\033[0m $MODEL_SPEC_CONTEXT

\033[1;30m(Dica: Selecione com o mouse no terminal antes de abrir,\nou confirme aqui para analisar a saída recente do terminal)\033[0m
"
    fi

    prev_screen="\033[1;33m🖥️ SAÍDA DO TERMINAL\033[0m
────────────────────────
• \033[1;37mIA Ativa:\033[0m $active_model_display
• \033[1;37mAção:\033[0m Capturar saída recente do terminal ($DEFAULT_SCREEN_LINES linhas)
• \033[1;37mLatência média:\033[0m $MODEL_SPEC_LATENCY
• \033[1;37mContexto:\033[0m $MODEL_SPEC_CONTEXT
"

    main_menu_items="$(printf '🖥️ 1. Enviar Saída do Terminal\n⚡ 2. Enviar Seleção do Mouse\n🤖 3. IA Local e Web\n✨ 4. API Externa\n📖 5. Ajuda & Atalhos\n🚪 0. Sair do Assistente\n')"

    _get_model_specs "2" "${OLLAMA_MODEL:-llama3.2:3b}"
    local o_lat="$MODEL_SPEC_LATENCY"
    local o_ctx="$MODEL_SPEC_CONTEXT"

    prev_local="\033[1;36m🤖 IA LOCAL E WEB\033[0m
──────────────────
• \033[1;37mLocal:\033[0m ${OLLAMA_MODEL:-llama3.2:3b} (Offline)
• \033[1;37mLatência Local:\033[0m $o_lat
• \033[1;37mContexto Local:\033[0m $o_ctx
• \033[1;37mWeb G4F:\033[0m ${G4F_MODEL:-gpt-4o}
"

    _get_model_specs "4" "${GROQ_MODEL:-openai/gpt-oss-120b}"
    local g_lat="$MODEL_SPEC_LATENCY"
    local g_ctx="$MODEL_SPEC_CONTEXT"

    prev_ext="\033[1;35m✨ APIS EXTERNAS & SERVIDORES\033[0m
─────────────────────────────
• \033[1;37mGroq:\033[0m ${GROQ_MODEL:-openai/gpt-oss-120b}
• \033[1;37mGemini:\033[0m ${GEMINI_MODEL:-gemini-2.0-flash}
• \033[1;37mNVIDIA:\033[0m ${NVIDIA_MODEL:-meta/llama-3.2-11b-vision-instruct}
• \033[1;37mOpenRouter:\033[0m ${OPENROUTER_MODEL:-liquid/lfm-2.5-2.6b:free}
"

    prev_help="\033[1;32m📖 GUIA COMPLETO & ATALHOS\033[0m
────────────────────────────
• \033[1;37mEsc / Ctrl + C\033[0m    Sai do assistente e volta ao terminal
• \033[1;37mEnter (vazio)\033[0m    Sai do assistente (no chat)
• \033[1;37mq / /sair\033[0m         Sai do assistente e volta ao terminal
• \033[1;37mCtrl + Shift + E\033[0m   Abre este assistente no Kitty (ou Alt+E)
• \033[1;37mTab\033[0m                Alterna painel lateral (on/off)
• \033[1;37mCtrl + R\033[0m           Atualiza seleção do mouse em tempo real

\033[1;36mComandos no Prompt:\033[0m
• \033[1;33m/auto\033[0m   Resolve erro de forma autônoma
• \033[1;33m/s\033[0m      Recaptura terminal e sincroniza
• \033[1;33m/e [n]\033[0m  Insere comando [n] no seu terminal
• \033[1;33m1, 2..\033[0m  Copia comando [n] para área de transf.
• \033[1;33m/m\033[0m      Volta ao menu principal
• \033[1;33m/q\033[0m      Fecha o assistente
"

    trap 'limpar_selecao_mouse 2>/dev/null; rm -f /tmp/orig_kitty_id /tmp/orig_kitty_listen /tmp/orig_kitty_pid 2>/dev/null' EXIT INT TERM

    local preview_mouse_script="${SCREEN_MODULES_DIR:-$HOME/.local/share/metis/zsh/screen}/preview_mouse.sh"
    [[ -f "$preview_mouse_script" ]] || preview_mouse_script="$HOME/.local/share/metis/zsh/screen/preview_mouse.sh"

    local -x PREV_ACTIVE_MODEL="$active_model_display"
    local -x PREV_MODEL_LAT="$MODEL_SPEC_LATENCY"
    local -x PREV_MODEL_CTX="$MODEL_SPEC_CONTEXT"
    local -x TARGET_KITTY_SOCK="$TARGET_KITTY_SOCK"
    local -x TARGET_KITTY_WIN="$TARGET_KITTY_WIN"

    local -x PREV_SCREEN="$prev_screen"
    local -x PREV_LOCAL="$prev_local"
    local -x PREV_EXT="$prev_ext"
    local -x PREV_HELP="$prev_help"

    local fzf_nav_footer=$'\n↑/↓ navegar  •  Enter confirmar  •  Esc sair  •  Ctrl+R atualiza seleção\nTab alterna painel'

    local -a fzf_footer_args=()
    local fzf_header_text=$'💬 Digite sua dúvida ou Enter:\n\n'
    if fzf --help 2>&1 | grep -q -- '--footer'; then
      fzf_footer_args=(--footer="$fzf_nav_footer")
    else
      fzf_header_text=$'💬 Digite sua dúvida ou Enter [↑/↓ navegar • Enter confirma • Esc sair • Tab painel]:\n\n'
    fi

    out_principal="$(
      printf '%s\n' "$main_menu_items" |
      fzf --height=40% --reverse \
          --no-mouse \
          --border=rounded \
          --pointer='▌' \
          --ansi \
          --color="$fzf_color_theme" \
          --header="$fzf_header_text" \
          --prompt="> " \
          --query="$busca_principal" \
          --disabled \
          --no-sort \
          --print-query \
          --preview='case "{}" in *Saída*|*Terminal*|*Tela*|*1.*) printf "%b\n" "$PREV_SCREEN" ;; *Seleção*|*2.*) "'"$preview_mouse_script"'" ;; *Local*|*3.*) printf "%b\n" "$PREV_LOCAL" ;; *API*|*Externa*|*4.*) printf "%b\n" "$PREV_EXT" ;; *Ajuda*|*Atalhos*|*Help*|*5.*) printf "%b\n" "$PREV_HELP" ;; *) printf "%b\n" "$PREV_HELP" ;; esac' \
          --preview-window="right:48%:wrap:border-rounded" \
          --bind 'tab:toggle-preview' \
          --bind 'focus:refresh-preview' \
          --bind 'ctrl-r:refresh-preview' \
          "${fzf_footer_args[@]}"
    )"
    rc=$?

    if (( rc != 0 )) || [[ -z "$out_principal" ]]; then
      limpar_selecao_mouse 2>/dev/null
      rm -f /tmp/orig_kitty_id /tmp/orig_kitty_listen /tmp/orig_kitty_pid 2>/dev/null
      exit 0
    fi

    out_principal="${out_principal%$'\n'}"
    parts=("${(@f)out_principal}")

    busca_principal="$(_trim "${parts[1]}")"
    menu_principal="$(_trim "${parts[-1]}")"

    if [[ -z "$menu_principal" || "$menu_principal" == "$busca_principal" ]]; then
      continue
    fi

    final_query="$busca_principal"

    # Atualiza a detecção de mouse no momento da confirmação (após o usuário selecionar na tela)
    local live_mouse="$(obter_selecao_mouse)"
    local has_mouse_live=0
    [[ -n "$live_mouse" ]] && has_mouse_live=1

    case "$menu_principal" in
      *"Sair"*|"🚪 0."*|"0."*|"0"|"q"|"/q"|"/sair"|"sair"|"exit"|"/exit")
        limpar_selecao_mouse 2>/dev/null
        rm -f /tmp/orig_kitty_id /tmp/orig_kitty_listen /tmp/orig_kitty_pid 2>/dev/null
        exit 0
        ;;

      *"Seleção"*|"⚡ 2."*|"2."*)
        PROVIDER="$cur_prov"
        MODO_CAPTURA="mouse"
        ;;

      *"Saída"*|*"Terminal"*|*"Tela Inteira"*|"🖥️ 1."*|"🖥️  1."*|"1."*)
        PROVIDER="$cur_prov"
        if (( has_mouse_live )) && [[ -n "$busca_principal" ]]; then
          MODO_CAPTURA="mouse"
        else
          MODO_CAPTURA="tela"
        fi
        ;;

      *"Local"*|"🤖 2."*|"🤖 3."*)
        if [[ -n "$METIS_KITTY_POPUP" ]]; then
          clear
          _print_header
        fi

        if (( has_mouse_live )); then
          MODO_CAPTURA="mouse"
        else
          MODO_CAPTURA="tela"
        fi

        modelo_out="$(
          printf '🌍 1. Web G4F (%s)\n🤖 2. Qwen (Local: %s)\n↩️  0. Voltar\n' \
            "${G4F_MODEL:-gpt-4o}" \
            "${OLLAMA_MODEL:-llama3.2:3b}" |
          fzf --height=28% --reverse \
              --no-mouse \
              --border=rounded \
              --pointer='▌' \
              --color="$fzf_color_theme" \
              --header="🤖 Escolha a IA Local/Web (ENTER = Enviar / ESC = Voltar):" \
              --prompt="> " \
              --query="$busca_principal" \
              --disabled \
              --no-sort \
              --print-query
        )"
        rc2=$?

        if (( rc2 != 0 )) || [[ -z "$modelo_out" ]]; then
          continue
        fi

        modelo_out="${modelo_out%$'\n'}"
        parts=("${(@f)modelo_out}")

        busca_principal="$(_trim "${parts[1]}")"
        final_query="$busca_principal"
        modelo_fzf="$(_trim "${parts[-1]}")"

        if [[ -z "$modelo_fzf" || "$modelo_fzf" == *"Voltar"* ]]; then
          continue
        fi

        case "$modelo_fzf" in
          "🌍 1."*)
            if ! menu_provedor_api "G4F" "🌍"; then
              continue
            fi
            PROVIDER=1
            ;;
          "🤖 2."*)
            if ! menu_provedor_ollama; then
              continue
            fi
            PROVIDER=2
            ;;
          *)
            continue
            ;;
        esac

        _save_active_provider "$PROVIDER"
        ;;

      *"API Externa"*|"✨ 3."*|"✨ 4."*|"3."*|"4."*)
        if [[ -n "$METIS_KITTY_POPUP" ]]; then
          clear
          _print_header
        fi

        if (( has_mouse_live )); then
          MODO_CAPTURA="mouse"
        else
          MODO_CAPTURA="tela"
        fi

        local -a api_menu_lines=()
        local line_item=""
        local fzf_api_entries=""

        while IFS= read -r line_item; do
          [[ -n "$line_item" ]] && api_menu_lines+=("$line_item")
        done < <("$PYTHON_BIN" "$(_get_manage_models_script)" api_menu 2>/dev/null)

        for line_item in "${api_menu_lines[@]}"; do
          local display_text="${line_item%%|*}"
          fzf_api_entries+="$display_text"$'\n'
        done
        fzf_api_entries+="🔄 Sincronizar com Metis"$'\n'
        fzf_api_entries+="↩️  0. Voltar"$'\n'

        modelo_out="$(
          printf '%s' "$fzf_api_entries" |
          fzf --height=34% --reverse \
              --no-mouse \
              --border=rounded \
              --pointer='▌' \
              --color="$fzf_color_theme" \
              --header="🤖 Escolha a API / Servidor Customizado (ENTER = Confirmar / ESC = Voltar):" \
              --prompt="> " \
              --query="$busca_principal" \
              --disabled \
              --no-sort \
              --print-query
        )"
        rc2=$?

        if (( rc2 != 0 )) || [[ -z "$modelo_out" ]]; then
          continue
        fi

        modelo_out="${modelo_out%$'\n'}"
        parts=("${(@f)modelo_out}")

        busca_principal="$(_trim "${parts[1]}")"
        final_query="$busca_principal"
        modelo_fzf="$(_trim "${parts[-1]}")"

        if [[ -z "$modelo_fzf" || "$modelo_fzf" == *"Voltar"* ]]; then
          continue
        fi

        if [[ "$modelo_fzf" == *"Sincronizar com Metis"* ]]; then
          if [[ -n "$METIS_KITTY_POPUP" ]]; then
            clear
            _print_header
          else
            printf '\n'
          fi
          "$PYTHON_BIN" "$(_get_manage_models_script)" sync
          load_env_file "$HOME/Metis/.env"
          load_env_file "$HOME/.ZSH/ai/.env_local"
          load_env_file "${METIS_CONFIG_DIR:-$HOME/.config/metis}/.env"
          printf '\n\033[32m✅ Sincronização concluída com sucesso!\033[0m\n'
          printf '\033[36mPressione ENTER para continuar (ou aguarde 3s)...\033[0m\n'
          stty sane 2>/dev/null
          read -t 3 -r _ </dev/tty 2>/dev/null || true
          exit 0
        fi

        local chosen_prov_id=""
        for line_item in "${api_menu_lines[@]}"; do
          local display_text="${line_item%%|*}"
          if [[ "$modelo_fzf" == "$display_text"* ]]; then
            local rest="${line_item#*|}"
            chosen_prov_id="${rest%%|*}"
            break
          fi
        done

        if [[ -z "$chosen_prov_id" ]]; then
          case "$modelo_fzf" in
            *"Gemini"*) chosen_prov_id="Gemini" ;;
            *"Groq"*) chosen_prov_id="Groq" ;;
            *"NVIDIA"*) chosen_prov_id="NVIDIA" ;;
            *"OpenRouter"*) chosen_prov_id="OpenRouter" ;;
            *) continue ;;
          esac
        fi

        local icon="🌐"
        [[ "$chosen_prov_id" == "Gemini" ]] && icon="✨"
        [[ "$chosen_prov_id" == "Groq" ]] && icon="🚀"
        [[ "$chosen_prov_id" == "NVIDIA" ]] && icon="🟢"
        [[ "$chosen_prov_id" == "OpenRouter" || "$chosen_prov_id" == "openrouter" ]] && icon="🪐"

        if ! menu_provedor_api "$chosen_prov_id" "$icon"; then
          continue
        fi

        case "$chosen_prov_id" in
          Gemini) PROVIDER=3 ;;
          Groq) PROVIDER=4 ;;
          NVIDIA) PROVIDER=5 ;;
          OpenRouter|openrouter) PROVIDER=6 ;;
          *) PROVIDER="$chosen_prov_id" ;;
        esac

        _save_active_provider "$PROVIDER"
        ;;

      *"Ajuda"*|*"Help"*|*"Atalhos"*|"📖 5."*|"5."*)
        if [[ -n "$METIS_KITTY_POPUP" ]]; then
          clear
          _print_header
        else
          printf '\n'
        fi
        exibir_ajuda
        printf '\n\033[1;36mPressione ENTER para voltar ao menu (ou aguarde 3s)...\033[0m'
        stty sane 2>/dev/null
        read -t 3 -r _ </dev/tty 2>/dev/null || true
        continue
        ;;

      *)
        continue
        ;;
    esac

    extrair_linhas_e_query "$final_query" "${DEFAULT_SCREEN_LINES:-30}"

    active_lines="${PARSED_LINES:-30}"
    [[ "$active_lines" =~ ^[0-9]+$ ]] || active_lines=30
    (( active_lines < 1 )) && active_lines=30
    final_query="$PARSED_QUERY"

    obter_conteudo_tela "$active_lines" >/dev/null 2>&1

    if [[ -n "$METIS_KITTY_POPUP" ]]; then
      clear
      _print_header
    else
      printf '\n'
      _print_header
    fi

    local is_auto_cmd=0
    [[ "$final_query" =~ ^/(auto|resolver|fix|corrigir) ]] && is_auto_cmd=1

    if (( ! is_auto_cmd )); then
      if [[ "$MODO_CAPTURA" == "mouse" && "$TIPO_FONTE_CAPTURA" == "mouse" ]]; then
        local n_captured_lines=$(print -r -- "$SCREEN_CONTENT" | wc -l)
        n_captured_lines="${n_captured_lines##* }"
        printf '\n\033[1;32m📋 Analisando Seleção do Mouse (%d linhas)\033[0m\n' "$n_captured_lines"
        printf '\033[90mFoco direcionado exclusivamente ao trecho selecionado.\033[0m\n'
        printf '%s\n' "──────────────────────────────────────────────────────────"
        limpar_selecao_mouse 2>/dev/null
      elif [[ "$MODO_CAPTURA" == "mouse" && "$TIPO_FONTE_CAPTURA" != "mouse" && -n "$SCREEN_CONTENT" ]]; then
        local n_captured_lines=$(print -r -- "$SCREEN_CONTENT" | wc -l)
        n_captured_lines="${n_captured_lines##* }"
        printf '\n\033[1;33m💡 Nenhuma seleção detectada • Usando Terminal (%d linhas)\033[0m\n' "$n_captured_lines"
        printf '\033[90mBuffer de tela capturado para diagnóstico.\033[0m\n'
        printf '%s\n' "──────────────────────────────────────────────────────────"
      elif [[ -n "$SCREEN_CONTENT" ]]; then
        local n_captured_lines=$(print -r -- "$SCREEN_CONTENT" | wc -l)
        n_captured_lines="${n_captured_lines##* }"
        printf '\n\033[1;33m🖥️ Analisando Saída do Terminal (%d linhas)\033[0m\n' "$n_captured_lines"
        printf '\033[90mBuffer de tela capturado para diagnóstico.\033[0m\n'
        printf '%s\n' "──────────────────────────────────────────────────────────"
      else
        printf '\n\033[1;36m💬 Modo Consulta Direta\033[0m\n'
        printf '\033[90mNenhum texto selecionado ou capturado do terminal.\033[0m\n'
        printf '%s\n' "──────────────────────────────────────────────────────────"
      fi
    fi

    local SYSTEM_PROMPT='Você é um assistente de terminal e agente Linux especialista.
Seu objetivo é ajudar o usuário analisando saídas de terminal, explicando erros, sugerindo comandos e executando tarefas no computador quando solicitado.
FERRAMENTAS DISPONÍVEIS:
1. Executar comandos bash ou listar arquivos:
<tool_call name="bash">
ls -la ~/Documentos
</tool_call>
2. Ler o conteúdo de um arquivo:
<tool_call name="read_file" path="/caminho/do/arquivo">
</tool_call>
3. Criar ou salvar/sobrescrever um arquivo completo:
<tool_call name="write_file" path="/caminho/do/arquivo">
Conteúdo completo que deseja gravar no arquivo
</tool_call>
4. Adicionar linhas ao final de um arquivo existente (append):
<tool_call name="append_file" path="/caminho/do/arquivo">
Linhas para adicionar ao final
</tool_call>
COMO NAVEGAR E MODIFICAR ARQUIVOS:
- Para ver o que tem numa pasta: use list_dir ou bash com ls -la <pasta> ou tree.
- Para editar/modificar um arquivo existente: primeiro use read_file para ler o conteúdo atual, aplique a alteração necessária e use write_file com a versão atualizada completa.
- Para acrescentar linhas ao final (ex: adicionar alias no .zshrc): use append_file.
FORMATO DE LISTAGEM DE PASTAS:
- Ao listar diretórios ou pastas para o usuário, organize o resultado com ícones e tópicos limpos:
  - 📁 **Pastas / Subdiretórios** primeiro
  - 📄 **Arquivos** com seus respectivos tipos e extensões (ex: 🐍 `.py`, 📜 `.sh`, 📦 `.zip`/`.tar`, 🖼️ imagens, 📝 `.md`/`.txt`)
  - Mostre os tamanhos e datas quando relevante de forma legível.
  - Finalize com um resumo claro (ex: `📊 Total: X pastas, Y arquivos`).
FORMATO DE EXPLICAÇÃO DE COMANDOS (NUNCA USE TABELAS):
- NUNCA use tabelas Markdown (| coluna | coluna |), pois em janelas de terminal as colunas ficam espremidas em poucas letras e quebram palavras de forma ilegível.
- Ao sugerir comandos e explicá-los, estruture SEMPRE no formato de tópicos limpos e espaçados (Cards):

### 🎯 Diagnóstico / Cenário
(Explicação clara e didática do cenário ou erro identificado)

### 🛠️ Comandos Sugeridos e Explicação
**1. `comando 1`**
- **O que faz:** (Explicação clara e objetiva do que o comando executa)
- **Por que usar:** (Por que é recomendado no caso do usuário)

**2. `comando 2`**
- **O que faz:** (Explicação clara e objetiva)
- **Por que usar:** (Finalidade no caso do usuário)

### 💡 Dicas e Próximos Passos
* 🔌 **Verificação Física / Hardware:** (Se o link não subir, teste cabo/porta ou hardware)
* 🌐 **Teste de Conectividade:** (Comando para testar ping/conectividade em sua própria linha):
  `ping -c 4 1.1.1.1`
* 🔄 **Persistência na Inicialização:** (Comando para salvar a configuração de forma permanente):
  `nmcli connection add type ethernet ifname <interface> autoconnect yes`
* 📋 **Logs e Depuração:** (Comando para verificar logs detalhados do serviço caso falhe):
  `journalctl -u NetworkManager -b -e`

REGRAS:
- Quando o usuário pedir para verificar pastas, inspecionar arquivos, criar ou modificar arquivos, use SEMPRE as ferramentas apropriadas.
- OBRIGATÓRIO: SEMPRE explique cada comando sugerido detalhadamente (o que ele faz, seus parâmetros e por que é usado no caso do usuário).
- REGRA OBRIGATÓRIA DE COMENTÁRIOS: Em TODOS os comandos que você sugerir em blocos de código bash ou comandos soltos, você DEVE SEMPRE incluir um comentário `# o que o comando faz` ao final de cada linha (exemplo: `df -h / # verifica espaço livre no disco raiz`, `journalctl -p err -b # lista erros do boot atual`, `sudo pacman -Syu # atualiza todos os pacotes do sistema`). NUNCA omita o comentário explicativo # ao lado de nenhum comando.
- Em Dicas e Próximos Passos, coloque cada comando de teste/configuração em sua própria linha destacada com crases para facilitar a leitura e seleção.
- Seja sempre direto, claro, visualmente organizado e muito didático. Sem introduções prolixas.'

    clean_final_query="$(_trim "$final_query")"

    obter_status_ultimo_comando "$TARGET_KITTY_WIN"
    local last_cmd_ctx=""
    if [[ -n "$LAST_CMD_NAME" ]]; then
      local now_ts="${EPOCHSECONDS:-$(date +%s)}"
      if [[ -z "$LAST_CMD_TIME" ]] || (( now_ts - LAST_CMD_TIME <= 600 )); then
        local status_desc="0 (Sucesso)"
        [[ "$LAST_CMD_EXIT" != "0" ]] && status_desc="$LAST_CMD_EXIT (Falha / Erro)"
        last_cmd_ctx="
[Último Comando Executado no Terminal]: $LAST_CMD_NAME
[Código de Retorno / Exit Code]: $status_desc"
      fi
    fi

    if [[ -n "$clean_final_query" ]]; then
      if [[ -n "$SCREEN_CONTENT" ]]; then
        CONTEXT="[Instruções]: $SYSTEM_PROMPT${last_cmd_ctx}
[Terminal do Usuário / Seleção do Mouse]:
$SCREEN_CONTENT
[Pergunta/Pedido do Usuário]: $final_query"
      else
        CONTEXT="[Instruções]: $SYSTEM_PROMPT${last_cmd_ctx}
[Pergunta/Pedido do Usuário]: $final_query"
      fi
    else
      if [[ -z "$SCREEN_CONTENT" ]]; then
        CONTEXT="[Instruções]: $SYSTEM_PROMPT${last_cmd_ctx}
[Instrução]: O usuário abriu o assistente sem texto capturado ou selecionado. Apresente-se brevemente como assistente Metis e explique de forma amigável como você pode ajudar (selecione erros no terminal com o mouse ou digite sua dúvida diretamente)."
      else
        CONTEXT="[Instruções]: $SYSTEM_PROMPT${last_cmd_ctx}
[Terminal do Usuário / Seleção do Mouse]:
$SCREEN_CONTENT
[Instrução]: Analise o terminal do usuário ou seleção do mouse acima. Explique o erro ou situação encontrada de forma didática e forneça os comandos para solucionar."
      fi
    fi

    if [[ "$clean_final_query" =~ ^/(auto|resolver|fix|corrigir) ]]; then
      extra_msg="$(print -r -- "$clean_final_query" | sed -E 's#^/(auto|resolver|fix|corrigir)[[:space:]]*##')"

      resolver_automatico_no_terminal "$extra_msg"
      auto_status=$?

      if (( auto_status == 130 )); then
        continue
      fi
    else
      LAST_RESPONSE="$(consultar_agente "$CONTEXT")"
      ia_status=$?

      if (( ia_status == 130 )) || [[ -z "$LAST_RESPONSE" || "$LAST_RESPONSE" == *"KeyboardInterrupt"* || "$LAST_RESPONSE" == *"Interrupted"* ]]; then
        printf '\n\033[33m⚠️  Operação interrompida. Voltando ao menu...\033[0m\n'
        sleep 1
        continue
      fi

      renderizar "$LAST_RESPONSE"
      extrair_blocos "$LAST_RESPONSE"
      exibir_blocos
    fi

    printf '%s\n' "─────────────────────────────────────────"

    voltar_menu=0
    LAST_SELECTED_CODE=""

    while true; do
      printf '\033[90m[/e 1] Executar no terminal  •  [!cmd] Rodar comando  •  [/sh] Shell  •  [Ctrl+C / Esc / q] Sair\033[0m\n'
      printf '\033[32mDigite sua pergunta ou comando:\033[0m\n'

      USER_INPUT=""

      if ! vared -c -p '%B%F{blue} ❯ %f%b' USER_INPUT 2>/dev/null; then
        _metis_exit_handler
      fi

      if [[ -z "$USER_INPUT" ]]; then
        _metis_exit_handler
      fi

      CLEAN_INPUT="$(_trim "$USER_INPUT")"

      if [[ "$CLEAN_INPUT" =~ ^[0-9]+$ ]]; then
        target_idx=$((10#$CLEAN_INPUT))

        if (( target_idx >= 1 && target_idx <= ${#CURRENT_CODE_BLOCKS[@]} )); then
          LAST_SELECTED_CODE="${CURRENT_CODE_BLOCKS[$target_idx]}"
          copiar_codigo "$LAST_SELECTED_CODE" "$target_idx"
          printf '\033[90m(Digite /e para enviar este comando ao terminal original)\033[0m\n'
        else
          _warn "Número inválido: o comando [$target_idx] não existe."
        fi

        continue
      fi

      case "$CLEAN_INPUT" in
        /auto|/auto\ *|/resolver|/resolver\ *|/fix|/fix\ *|/corrigir|/corrigir\ *)
          extra_msg="$(print -r -- "$USER_INPUT" | sed -E 's#^/(auto|resolver|fix|corrigir)[[:space:]]*##')"

          resolver_automatico_no_terminal "$extra_msg"
          auto_status=$?

          if (( auto_status == 130 )); then
            continue
          fi

          if [[ -n "$LAST_RESPONSE" ]]; then
            CONTEXT="$(limitar_contexto "$CONTEXT
[Assistente]: $LAST_RESPONSE")"
          fi

          continue
          ;;

        /menu|/m|/voltar|/v)
          voltar_menu=1
          break
          ;;

        /sair|/q|/exit|/quit|exit|quit|sair|q)
          limpar_selecao_mouse 2>/dev/null
          rm -f /tmp/orig_kitty_id /tmp/orig_kitty_listen /tmp/orig_kitty_pid 2>/dev/null
          exit 0
          ;;

        /modelos|/modelos\ *|/models|/models\ *|/config_model|/config_model\ *|/mod|/mod\ *|/provedor|/provedor\ *|/provider|/provider\ *|/modelo|/modelo\ *|/ia|/ia\ *)
          local mod_arg="$(print -r -- "$USER_INPUT" | sed -E 's#^/(modelos|models|config_model|mod|provedor|provider|modelo|ia)[[:space:]]*##')"
          trocar_modelo_sessao "$mod_arg"
          if [[ -n "$METIS_KITTY_POPUP" ]]; then
            clear
            _print_header
          else
            printf '\n'
          fi
          renderizar "$LAST_RESPONSE"
          exibir_blocos
          printf '%s\n' "─────────────────────────────────────────"
          local cur_prov_info="$(_get_active_provider_info "$PROVIDER")"
          printf '\033[1;32m⭐ IA Ativa na Sessão: %s\033[0m\n\n' "$cur_prov_info"
          continue
          ;;

        /ajuda|/help|/h)
          exibir_ajuda
          if (( $? == 200 )); then
            voltar_menu=1
            break
          fi
          continue
          ;;

        /clear|/limpar|/l)
          clear
          _print_header

          renderizar "$LAST_RESPONSE"
          exibir_blocos

          printf '%s\n' "─────────────────────────────────────────"
          continue
          ;;

        /salvar|/salvar\ *|/save|/save\ *|/relatorio|/relatorio\ *|/report|/report\ *)
          local save_path="$(print -r -- "$USER_INPUT" | sed -E 's#^/(salvar|save|relatorio|report)[[:space:]]*##')"
          save_path="$(_trim "$save_path")"

          if [[ -z "$save_path" ]]; then
            save_path="$HOME/Downloads/relatorio_$(date +%Y%m%d_%H%M%S).md"
          else
            save_path="${save_path/#\~/$HOME}"
            [[ "$save_path" != *.* ]] && save_path="${save_path}.md"
          fi

          mkdir -p "$(dirname "$save_path")" 2>/dev/null

          if [[ -n "$LAST_RESPONSE" ]]; then
            print -r -- "$LAST_RESPONSE" > "$save_path" 2>/dev/null
            printf '\n\033[32m✅ Relatório salvo com sucesso em: \033[1;37m%s\033[0m\n' "$save_path"
          else
            _warn "Nenhuma resposta recente para salvar."
          fi
          continue
          ;;

        /retry|/r)
          printf '\n\033[33m→ Regenerando resposta...\033[0m\n'

          NOVA_RESPOSTA="$(consultar_agente "$CONTEXT")"
          ia_status=$?

          if (( ia_status == 130 )) || [[ "$NOVA_RESPOSTA" == *"KeyboardInterrupt"* || "$NOVA_RESPOSTA" == *"Interrupted"* ]]; then
            printf '\n\033[33m⚠️  Geração cancelada pelo usuário (Ctrl+C).\033[0m\n'
            continue
          fi

          if [[ -n "$NOVA_RESPOSTA" ]]; then
            LAST_RESPONSE="$NOVA_RESPOSTA"

            renderizar "$LAST_RESPONSE"
            extrair_blocos "$LAST_RESPONSE"
            exibir_blocos

            LAST_SELECTED_CODE=""

            printf '%s\n' "─────────────────────────────────────────"
          else
            _warn "A IA não retornou resposta."
          fi

          continue
          ;;

        /mouse|/mouse\ *|/selecao|/selecao\ *)
          extra_msg="$(print -r -- "$USER_INPUT" | sed -E 's#^/(mouse|selecao)[[:space:]]*##')"
          extra_msg="$(_trim "$extra_msg")"

          local new_mouse="$(obter_selecao_mouse)"
          if [[ -z "$new_mouse" ]]; then
            _warn "Nenhuma seleção ativa do mouse encontrada no momento."
            continue
          fi

          local mouse_n=$(print -r -- "$new_mouse" | wc -l)
          printf '\n\033[32m📋 Nova seleção do mouse capturada (%d linhas)!\033[0m\n' "$mouse_n"

          if [[ -z "$extra_msg" ]]; then
            extra_msg="Analise o trecho selecionado com o mouse acima e me ajude a resolver:"
          fi

          TEMP_CONTEXT="$CONTEXT
[Assistente]: $LAST_RESPONSE
[Trecho Selecionado com o Mouse ($mouse_n linhas)]:
$new_mouse
[Usuário]: $extra_msg"

          NOVA_RESPOSTA="$(consultar_agente "$TEMP_CONTEXT")"
          ia_status=$?

          if (( ia_status == 130 )) || [[ "$NOVA_RESPOSTA" == *"KeyboardInterrupt"* || "$NOVA_RESPOSTA" == *"Interrupted"* ]]; then
            printf '\n\033[33m⚠️  Geração cancelada pelo usuário (Ctrl+C).\033[0m\n'
            continue
          fi

          if [[ -z "$NOVA_RESPOSTA" ]]; then
            _warn "A IA não retornou resposta."
            continue
          fi

          CONTEXT="$(limitar_contexto "$TEMP_CONTEXT")"
          LAST_RESPONSE="$NOVA_RESPOSTA"

          renderizar "$LAST_RESPONSE"
          extrair_blocos "$LAST_RESPONSE"
          exibir_blocos

          LAST_SELECTED_CODE=""
          printf '%s\n' "─────────────────────────────────────────"
          continue
          ;;

        /clip|/clip\ *)
          extra_msg="$(print -r -- "$USER_INPUT" | sed -E 's#^/(clip)[[:space:]]*##')"
          extra_msg="$(_trim "$extra_msg")"

          local new_clip="$(obter_clipboard)"
          if [[ -z "$new_clip" ]]; then
            _warn "Área de transferência (clipboard) está vazia."
            continue
          fi

          local clip_n=$(print -r -- "$new_clip" | wc -l)
          printf '\n\033[32m📋 Conteúdo do clipboard capturado (%d linhas)!\033[0m\n' "$clip_n"

          if [[ -z "$extra_msg" ]]; then
            extra_msg="Analise o texto copiado acima:"
          fi

          TEMP_CONTEXT="$CONTEXT
[Assistente]: $LAST_RESPONSE
[Texto Copiado do Clipboard ($clip_n linhas)]:
$new_clip
[Usuário]: $extra_msg"

          NOVA_RESPOSTA="$(consultar_agente "$TEMP_CONTEXT")"
          ia_status=$?

          if (( ia_status == 130 )) || [[ "$NOVA_RESPOSTA" == *"KeyboardInterrupt"* || "$NOVA_RESPOSTA" == *"Interrupted"* ]]; then
            printf '\n\033[33m⚠️  Geração cancelada pelo usuário (Ctrl+C).\033[0m\n'
            continue
          fi

          if [[ -z "$NOVA_RESPOSTA" ]]; then
            _warn "A IA não retornou resposta."
            continue
          fi

          CONTEXT="$(limitar_contexto "$TEMP_CONTEXT")"
          LAST_RESPONSE="$NOVA_RESPOSTA"

          renderizar "$LAST_RESPONSE"
          extrair_blocos "$LAST_RESPONSE"
          exibir_blocos

          LAST_SELECTED_CODE=""
          printf '%s\n' "─────────────────────────────────────────"
          continue
          ;;

        /sync|/sync\ *|/s|/s\ *|/tela|/tela\ *|/atualizar|/atualizar\ *|/screen|/screen\ *|/update|/update\ *)
          extra_msg="$(print -r -- "$USER_INPUT" | sed -E 's#^/(sync|s|tela|atualizar|screen|update)[[:space:]]*##')"

          extrair_linhas_e_query "$extra_msg" "${DEFAULT_SCREEN_LINES:-30}"

          sync_lines="${PARSED_LINES:-30}"
          [[ "$sync_lines" =~ ^[0-9]+$ ]] || sync_lines=30
          (( sync_lines < 1 )) && sync_lines=30
          extra_msg="$PARSED_QUERY"

          if [[ -z "$extra_msg" ]]; then
            extra_msg="Executei o comando (ou fiz alterações no terminal), mas encontrei um erro ou resultado inesperado. Analise a tela atualizada acima e me diga o que fazer:"
          fi

          printf '\n\033[36m🔄 Recapturando tela (%d linhas) do terminal original...\033[0m\n' "$sync_lines"

          LATEST_SCREEN="$(recapturar_tela "$sync_lines")"

          if [[ -z "$LATEST_SCREEN" ]]; then
            _warn "Não foi possível sincronizar o terminal original."
            continue
          fi

          obter_status_ultimo_comando "$TARGET_KITTY_WIN"
          local sync_status_ctx=""
          if [[ -n "$LAST_CMD_NAME" ]]; then
            local status_desc="0 (Sucesso)"
            [[ "$LAST_CMD_EXIT" != "0" ]] && status_desc="$LAST_CMD_EXIT (Falha / Erro)"
            sync_status_ctx="
[Último Comando Executado no Terminal]: $LAST_CMD_NAME
[Código de Retorno / Exit Code]: $status_desc"
          fi

          TEMP_CONTEXT="$CONTEXT
[Assistente]: $LAST_RESPONSE
[Terminal Atualizado do Usuário (últimas $sync_lines linhas)]:
$LATEST_SCREEN${sync_status_ctx}
[Usuário]: $extra_msg"

          NOVA_RESPOSTA="$(consultar_agente "$TEMP_CONTEXT")"
          ia_status=$?

          if (( ia_status == 130 )) || [[ "$NOVA_RESPOSTA" == *"KeyboardInterrupt"* || "$NOVA_RESPOSTA" == *"Interrupted"* ]]; then
            printf '\n\033[33m⚠️  Geração cancelada pelo usuário (Ctrl+C).\033[0m\n'
            continue
          fi

          if [[ -z "$NOVA_RESPOSTA" ]]; then
            _warn "A IA não retornou resposta."
            continue
          fi

          CONTEXT="$(limitar_contexto "$TEMP_CONTEXT")"
          LAST_RESPONSE="$NOVA_RESPOSTA"

          renderizar "$LAST_RESPONSE"
          extrair_blocos "$LAST_RESPONSE"
          exibir_blocos

          LAST_SELECTED_CODE=""

          printf '%s\n' "─────────────────────────────────────────"

          continue
          ;;

        /copy|/copy\ *|/c|/c\ *)
          target_idx="$(print -r -- "$CLEAN_INPUT" | grep -oE '[0-9]+' | head -n 1)"
          code_to_copy=""

          if [[ -n "$target_idx" && "$target_idx" -ge 1 && "$target_idx" -le ${#CURRENT_CODE_BLOCKS[@]} ]]; then
            code_to_copy="${CURRENT_CODE_BLOCKS[$target_idx]}"
            LAST_SELECTED_CODE="$code_to_copy"
            copiar_codigo "$code_to_copy" "$target_idx"
          elif [[ -n "$LAST_SELECTED_CODE" ]]; then
            copiar_codigo "$LAST_SELECTED_CODE"
          else
            code_to_copy="$(selecionar_bloco_codigo)"

            if [[ -n "$code_to_copy" ]]; then
              LAST_SELECTED_CODE="$code_to_copy"
              copiar_codigo "$code_to_copy"
            fi
          fi

          continue
          ;;

        /sh|/bash|/terminal)
          printf '\n\033[1;36m🐚 Abrindo shell interativo no terminal...\033[0m\n'
          printf '\033[90m(Execute os comandos que desejar e digite \033[1;33mexit\033[90m para retornar ao Metis)\033[0m\n\n'
          "${SHELL:-/bin/bash}"
          printf '\n\033[32m↩️  De volta ao assistente Metis!\033[0m\n'
          printf '\033[90m(Dica: Use /s para sincronizar a tela do que você acabou de rodar, ou continue a conversa)\033[0m\n\n'
          continue
          ;;

        \!*)
          local direct_run="${USER_INPUT#\!}"
          direct_run="$(_trim "$direct_run")"
          if [[ -n "$direct_run" ]]; then
            printf '\n\033[1;36m▶ Executando no terminal:\033[0m\n  \033[1;38;5;214m$ %s\033[0m\n' "$direct_run"
            printf '%s\n' "──────────────────────────────────────────────────────────"
            local tmp_run_out="$(mktemp)"
            local run_code=0
            eval "$direct_run" 2>&1 | tee "$tmp_run_out"
            run_code=${pipestatus[1]}
            printf '%s\n' "──────────────────────────────────────────────────────────"
            if (( run_code == 0 )); then
              printf '\033[32m✔ Concluído com sucesso (Exit: 0)\033[0m\n\n'
            else
              printf '\033[31m✖ Finalizado com erro (Exit: %d)\033[0m\n\n' "$run_code"
            fi
            local run_text="$(cat "$tmp_run_out" 2>/dev/null)"
            rm -f "$tmp_run_out" 2>/dev/null
            CONTEXT="$(limitar_contexto "$CONTEXT
[Comando executado no terminal]: $direct_run
[Código de saída]: $run_code
[Saída no terminal]:
${run_text:-(Sem saída)}")"
          fi
          continue
          ;;

        /exec|/exec\ *|/e|/e\ *|/run|/run\ *|/r|/r\ *)
          local cmd_arg="$(print -r -- "$USER_INPUT" | sed -E 's#^/(exec|e|run|r)[[:space:]]*##')"
          cmd_arg="$(_trim "$cmd_arg")"
          target_idx=""
          code_to_send=""

          if [[ "$cmd_arg" =~ ^[0-9]+$ ]]; then
            target_idx=$((10#$cmd_arg))
          else
            target_idx="$(print -r -- "$CLEAN_INPUT" | grep -oE '[0-9]+' | head -n 1)"
          fi

          if [[ -n "$target_idx" && "$target_idx" -ge 1 && "$target_idx" -le ${#CURRENT_CODE_BLOCKS[@]} ]]; then
            code_to_send="${CURRENT_CODE_BLOCKS[$target_idx]}"
          elif [[ -n "$cmd_arg" && "$cmd_arg" != <-> ]]; then
            code_to_send="$cmd_arg"
          elif [[ -n "$LAST_SELECTED_CODE" ]]; then
            code_to_send="$LAST_SELECTED_CODE"
          else
            code_to_send="$(selecionar_bloco_codigo)"
          fi

          if [[ -n "$code_to_send" ]]; then
            LAST_SELECTED_CODE="$code_to_send"
            _obter_kitty_target

            if [[ -n "$METIS_KITTY_POPUP" && -n "$TARGET_KITTY_SOCK" ]]; then
              enviar_ao_kitty "$code_to_send" "$target_idx" 1
              printf '\033[32m🚀 Comando enviado para o terminal Kitty!\033[0m\n'
            else
              printf '\n\033[1;36m▶ Executando no terminal:\033[0m\n  \033[1;38;5;214m$ %s\033[0m\n' "$code_to_send"
              printf '%s\n' "──────────────────────────────────────────────────────────"
              local tmp_e_out="$(mktemp)"
              local e_code=0
              eval "$code_to_send" 2>&1 | tee "$tmp_e_out"
              e_code=${pipestatus[1]}
              printf '%s\n' "──────────────────────────────────────────────────────────"
              if (( e_code == 0 )); then
                printf '\033[32m✔ Concluído com sucesso (Exit: 0)\033[0m\n\n'
              else
                printf '\033[31m✖ Finalizado com erro (Exit: %d)\033[0m\n\n' "$e_code"
              fi
              local e_text="$(cat "$tmp_e_out" 2>/dev/null)"
              rm -f "$tmp_e_out" 2>/dev/null
              CONTEXT="$(limitar_contexto "$CONTEXT
[Comando executado no terminal]: $code_to_send
[Código de saída]: $e_code
[Saída no terminal]:
${e_text:-(Sem saída)}")"
              copiar_codigo "$code_to_send" "" >/dev/null 2>&1 || true
            fi
          fi

          continue
          ;;

        *)
          printf '\n'

          extrair_linhas_e_query "$USER_INPUT" ""

          if [[ -n "$PARSED_LINES" && "$PARSED_LINES" =~ ^[0-9]+$ && "$PARSED_LINES" -gt 0 ]]; then
            custom_lines="$PARSED_LINES"
            custom_msg="$PARSED_QUERY"

            [[ -z "$custom_msg" ]] && custom_msg="Analise a tela com as $custom_lines linhas capturadas:"

            printf '\033[36m🔄 Recapturando tela (%d linhas) do terminal original...\033[0m\n' "$custom_lines"

            custom_screen="$(recapturar_tela "$custom_lines")"

            TEMP_CONTEXT="$CONTEXT
[Assistente]: $LAST_RESPONSE
[Terminal Atualizado do Usuário (últimas $custom_lines linhas)]:
$custom_screen
[Usuário]: $custom_msg"
          else
            TEMP_CONTEXT="$CONTEXT
[Assistente]: $LAST_RESPONSE
[Usuário]: $USER_INPUT"
          fi

          NOVA_RESPOSTA="$(consultar_agente "$TEMP_CONTEXT")"
          ia_status=$?

          if (( ia_status == 130 )) || [[ "$NOVA_RESPOSTA" == *"KeyboardInterrupt"* || "$NOVA_RESPOSTA" == *"Interrupted"* ]]; then
            printf '\n\033[33m⚠️  Geração cancelada pelo usuário (Ctrl+C).\033[0m\n'
            continue
          fi

          if [[ -z "$NOVA_RESPOSTA" ]]; then
            _warn "A IA não retornou resposta."
            continue
          fi

          CONTEXT="$(limitar_contexto "$TEMP_CONTEXT")"
          LAST_RESPONSE="$NOVA_RESPOSTA"

          renderizar "$LAST_RESPONSE"
          extrair_blocos "$LAST_RESPONSE"
          exibir_blocos

          LAST_SELECTED_CODE=""

          printf '%s\n' "─────────────────────────────────────────"
          ;;
      esac
    done

    if (( voltar_menu == 1 )); then
      continue
    fi

    break
  done
}
