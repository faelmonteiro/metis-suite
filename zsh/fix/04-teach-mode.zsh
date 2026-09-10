#!/usr/bin/env zsh
# =============================================================================
# fix/04-teach-mode.zsh
# Modo didático interativo "Me Ensinar" com chat contínuo, renderização e notas.
# =============================================================================

_ai_fix_exec_me_ensinar() {
  local context="$1"
  local busca="$2"
  local m_icon="$(_ai_fix_metis_icon)"

  local chat_context="Contexto: $context. Aja como um colega programador experiente batendo papo. Explique o seguinte de forma didática, direta e conversacional: $busca. Estruture sua resposta com subtítulos (usando #) para cada tipo de comando. Sempre que um comando tiver parâmetros ou flags (como -la, -xvf, etc), explique o que cada letra faz de forma rápida usando tópicos (*). REGRA DE OURO: Quando for mostrar o comando exato, isole-o dentro de um bloco markdown com três crases. NUNCA coloque explicações dentro do bloco de código!"
  local full_conversation_notes="# Tutorial: $busca"$'\n'
  full_conversation_notes+="> **Data:** $(date '+%d/%m/%Y %H:%M:%S')"$'\n'

  local resposta="" title="" inside=0 current_block="" line="" fence_re='^[[:space:]]*```'
  local inline="" i=0 preview_line="" user_input="" clean_input=""
  local raw_note_name="" note_name="" notes_dir="" note_file="" idx=0 selected=""
  local insert_rc=0
  local -a blocks=()

  _ai_fix_reload_envs
  zmodload zsh/datetime 2>/dev/null || true

  while true; do
    _ai_fix_reload_envs
    local t_start=${EPOCHREALTIME:-0}
    resposta="$(_ai_fix_query "$chat_context" "Elaborando explicação")"
    local t_end=${EPOCHREALTIME:-0}
    resposta="${resposta//$'\r'/}"

    if [[ -z "$resposta" ]]; then
      printf '\033[33m⚠️ Ação cancelada ou sem resposta da IA.\033[0m\n'
      break
    fi

    local dur_str=""
    if (( t_start > 0 && t_end > 0 )); then
      local dur=$(( t_end - t_start ))
      dur_str="$(printf '⏱️  %.1fs' "$dur")"
    fi

    _ai_fix_reload_envs
    local prov_label="${AI_ACTIVE_LABEL:-IA ativa}"
    title="🏛️  --- TUTORIAL METIS: $prov_label ---"

    full_conversation_notes+="> **Provedor:** $title"$'\n---\n'"$resposta"$'\n'

    # RENDERIZAÇÃO
    printf '\n\033[34m%s\033[0m\n' "$title"

    if (( ${+functions[_ai_render_formatted]} )); then
      _ai_render_formatted "$resposta"
    elif command -v glow >/dev/null 2>&1; then
      print -r -- "$resposta" | glow -
    else
      print -r -- "$resposta"
    fi

    if [[ -n "$dur_str" ]]; then
      printf '\033[34m--------------------------------------------------\033[0m \033[38;2;250;208;148m[%s]\033[0m\n' "$dur_str"
    else
      printf '\033[34m--------------------------------------------------\033[0m\n'
    fi

    # EXTRAÇÃO DE COMANDOS
    blocks=()
    inside=0
    current_block=""

    while IFS= read -r line; do
      if [[ "$line" =~ $fence_re ]]; then
        if (( inside == 1 )); then
          inside=0
          current_block="$(_ai_fix_trim "$current_block")"

          if [[ -n "$current_block" ]]; then
            blocks+=("$current_block")
          fi

          current_block=""
        else
          inside=1
        fi
      else
        if (( inside == 1 )); then
          current_block+="$line"$'\n'
        fi
      fi
    done <<< "$resposta"

    if (( inside == 1 )); then
      current_block="$(_ai_fix_trim "$current_block")"

      if [[ -n "$current_block" ]]; then
        blocks+=("$current_block")
      fi
    fi

    if (( ${#blocks[@]} == 0 )); then
      while IFS= read -r inline; do
        inline="$(_ai_fix_trim "$inline")"
        [[ -n "$inline" ]] && blocks+=("$inline")
      done < <(print -r -- "$resposta" | grep -oE '`[^`]+`' | sed -E 's/^`//; s/`$//')
    fi

    if (( ${#blocks[@]} > 0 )); then
      printf '\n\033[36m✨ Comandos Disponíveis:\033[0m\n'

      for ((i = 1; i <= ${#blocks[@]}; i++)); do
        preview_line="$(print -r -- "${blocks[$i]}" | head -n 1 | cut -c 1-80)"
        preview_line="$(_ai_fix_trim "$preview_line")"

        printf "  \033[1;34m[%d]\033[0m 💻 %s\n" "$i" "$preview_line"
      done

      printf '\n'
    fi

    # LOOP DE CHAT
    while true; do
      if (( ${#blocks[@]} > 0 )); then
        printf '\n\033[90m💬 Digite sua dúvida, [1..%d] para inserir comando, /m (menu), /nota ou /sair:\033[0m\n' "${#blocks[@]}"
      else
        printf '\n\033[90m💬 Digite sua dúvida, /m (menu), /nota ou /sair:\033[0m\n'
      fi

      printf '\033[1;36m❯ \033[0m'
      user_input=""
      if ! read -r user_input </dev/tty; then
        return 0
      fi

      clean_input="$(_ai_fix_trim "$user_input")"

      if [[ -z "$clean_input" || "$clean_input" == "/sair" || "$clean_input" == "/exit" || "$clean_input" == "/q" ]]; then
        return 0
      fi

      if [[ "$clean_input" == "/m" || "$clean_input" == "/menu" ]]; then
        local chat_entries=""
        if (( ${#blocks[@]} > 0 )); then
          for ((i = 1; i <= ${#blocks[@]}; i++)); do
            local prev_line="$(print -r -- "${blocks[$i]}" | head -n 1 | cut -c 1-50)"
            prev_line="$(_ai_fix_trim "$prev_line")"
            chat_entries+="💻 [$i] Inserir no terminal: $prev_line"$'\n'
          done
        fi
        chat_entries+="📝 /nota        Salvar tutorial em ~/Documentos/Notas"$'\n'
        chat_entries+="💡 /ajuda       Exibir guia de atalhos e comandos"$'\n'
        chat_entries+="↩️  /sair        Sair / Finalizar chat"$'\n'

        local chat_fzf_out="$(
          printf '%s' "$chat_entries" |
          fzf --height=30% --reverse --border --ansi \
              --header="🏛️  Metis | Escolha uma ação (ENTER = Confirmar / ESC = Voltar):" \
              --prompt="Ação > "
        )"
        if [[ -n "$chat_fzf_out" ]]; then
          if [[ "$chat_fzf_out" == *"💻 ["* ]]; then
            clean_input="$(print -r -- "$chat_fzf_out" | grep -oE '\[[0-9]+\]' | tr -d '[]')"
          elif [[ "$chat_fzf_out" == *"/nota"* ]]; then
            clean_input="/nota"
          elif [[ "$chat_fzf_out" == *"/ajuda"* ]]; then
            clean_input="/ajuda"
          elif [[ "$chat_fzf_out" == *"Sair"* ]]; then
            return 0
          fi
        else
          continue
        fi
      fi

      if [[ -z "$clean_input" ]]; then
        continue
      fi

      if [[ "$clean_input" == "/ajuda" || "$clean_input" == "/help" || "$clean_input" == "/h" ]]; then
        printf '\n\033[1;36m📖 Guia do Modo Ensinar:\033[0m\n'
        printf '  \033[1;33m• Digitar texto + ENTER:\033[0m Faz perguntas de acompanhamento à IA.\n'
        printf '  \033[1;33m• 1, 2, etc:\033[0m Insere o comando correspondente diretamente no seu prompt.\n'
        printf '  \033[1;33m• /m ou /menu:\033[0m Abre menu interativo FZF de ações.\n'
        printf '  \033[1;33m• /nota [nome]:\033[0m Salva o tutorial completo em ~/Documentos/Notas.\n'
        printf '  \033[1;33m• /sair ou Enter vazio:\033[0m Encerra o chat e retorna ao terminal.\n'
        continue
      fi

      if [[ "$clean_input" == "/nota" || "$clean_input" == "/nota "* || "$clean_input" == "/export" || "$clean_input" == "/export "* ]]; then
        raw_note_name="$(print -r -- "$clean_input" | sed -E 's/^\/(nota|export)[[:space:]]*//')"
        raw_note_name="$(_ai_fix_trim "$raw_note_name")"

        note_name="$(_ai_fix_safe_note_name "$raw_note_name")"
        notes_dir="$HOME/Documentos/Notas"

        if ! mkdir -p "$notes_dir" 2>/dev/null; then
          printf '\033[31mErro: não foi possível criar %s\033[0m\n' "$notes_dir"
          continue
        fi

        note_file="$notes_dir/$note_name"

        if print -r -- "$full_conversation_notes" > "$note_file" 2>/dev/null; then
          printf '\n\033[32m📝 Nota completa salva com sucesso em:\033[0m \033[1;37m%s\033[0m\n' "$note_file"
        else
          printf '\033[31mErro ao salvar nota em %s\033[0m\n' "$note_file"
        fi

        continue
      fi

      if [[ "$clean_input" =~ ^\[?[0-9]+\]?$ ]]; then
        idx="${clean_input//[^0-9]/}"
        idx=$((10#$idx))

        if (( idx >= 1 && idx <= ${#blocks[@]} )); then
          selected="${blocks[$idx]}"

          _ai_fix_insert_command "$selected"
          insert_rc=$?

          if (( insert_rc == 0 )); then
            printf '\033[32m✅ Comando [%d] inserido no seu prompt!\033[0m\n' "$idx"
            sleep 0.8
            return 0
          else
            continue
          fi
        else
          printf '\033[31m⚠️ Comando [%d] não existe.\033[0m\n' "$idx"
          continue
        fi
      fi

      printf '\n%s\033[38;2;250;208;148m[Metis]: \033[0m\033[33mPensando...\033[0m\n' "$m_icon"

      full_conversation_notes+="### Pergunta: $clean_input"$'\n'

      chat_context="$chat_context
[Assistente]: $resposta
[Usuário]: $clean_input"

      if (( ${+functions[_metis_trim_context]} )); then
        chat_context="$(_metis_trim_context "$chat_context" 60000)"
      elif (( ${#chat_context} > 60000 )); then
        chat_context="[Contexto anterior truncado]
$(print -r -- "$chat_context" | tail -c 60000)"
      fi

      break
    done
  done
}
