# ==============================================================================
# SEPARAÇÃO INTELIGENTE DE HISTÓRICO:
# 1. Comandos Puros -> ~/.zsh_history (Ctrl + R / Seta Cima) [Com desduplicação de portas]
# 2. IA e Prompts -> ~/.zsh_ai_history (Alt + H / iah)
# 3. Git Clones & Downloads Web -> ~/.zsh_downloads.log (comando: repos / downloads)
# 4. Typos, Lixo e Dumps -> DESCARTADOS TOTALMENTE
# ==============================================================================

zmodload zsh/datetime 2>/dev/null || true

AI_HISTFILE="${HOME}/.zsh_ai_history"
DOWNLOADS_LOG="${HOME}/.zsh_downloads.log"

# 1. Função que valida se um comando ou binário realmente existe no sistema
_zsh_validate_cmd_exists() {
  setopt LOCAL_OPTIONS EXTENDED_GLOB
  local cmd="$1"
  local nl=$'\n'
  local clean_cmd="${cmd//(#m)(&&|\|\||\||;)/$nl}"
  local -a segs=("${(@f)clean_cmd}")
  
  local seg
  for seg in "${segs[@]}"; do
    seg="${seg#"${seg%%[![:space:]]*}"}"
    seg="${seg%"${seg##*[![:space:]]}"}"
    [[ -z "$seg" ]] && continue
    
    local words=(${(z)seg})
    local idx=1
    while [[ $idx -le ${#words} && "${words[$idx]}" == *"="* && "${words[$idx]}" != ./* && "${words[$idx]}" != /* ]]; do
      ((idx++))
    done
    [[ $idx -gt ${#words} ]] && continue
    
    local target="${words[$idx]}"
    if [[ "$target" == "sudo" || "$target" == "doas" || "$target" == "time" || "$target" == "nohup" || "$target" == "exec" ]]; then
      ((idx++))
      while [[ $idx -le ${#words} && "${words[$idx]}" == -* ]]; do
        if [[ "${words[$idx]}" == "-u" || "${words[$idx]}" == "-g" ]]; then
          ((idx+=2))
        else
          ((idx++))
        fi
      done
      if [[ $idx -le ${#words} ]]; then
        target="${words[$idx]}"
      fi
    fi
    
    target="${target#\\}"
    [[ -z "$target" ]] && continue
    
    if ! whence "$target" >/dev/null 2>&1 && [[ "$target" != ./* && "$target" != /* && "$target" != ~* ]]; then
      return 1 # Comando inválido / erro de digitação
    fi
  done
  
  return 0
}

# 2. Função para detectar lixo colado, loops grandes, dumps e comandos quebrados (DESCARTA TOTALMENTE)
_zsh_is_absolute_junk() {
  local cmd="$1"
  local first="${cmd%% *}"

  # Comandos sozinhos sem argumentos que travam ou são ruído
  if [[ "$cmd" =~ "^(nano|cat|sudo|npm|node|mpv|sh|zsh|wait|info|icuinfo|cc|ss|dir|p)$" ]]; then
    return 0
  fi

  # Placeholders de documentação
  if [[ "$cmd" =~ "<[a-zA-Z0-9_-]+>" || "$cmd" == "kill -9 pid" || "$cmd" == "kill help" ]]; then
    return 0
  fi

  # Comandos colados quebrados sem operador (ex: mkdir ... cd ... wget ..., sudo ... sudo ...)
  if [[ "$cmd" != *"&&"* && "$cmd" != *"||"* && "$cmd" != *";"* && "$cmd" != *"|"* ]]; then
    if [[ "$cmd" =~ "[[:space:]]+(cd|wget|git clone|export|source|sudo)[[:space:]]+" && "$first" != "export" && "$first" != "alias" && "$first" != "git" ]]; then
      return 0
    fi
  fi

  # Scripts multilinhas, loops ou dumps de projeto colados
  local num_lines=${#${(f)cmd}}
  if [[ $num_lines -gt 2 ]] || \
     [[ "$cmd" =~ '(while[[:space:]]+read|cat[[:space:]]*<<|for[[:space:]]+[a-zA-Z0-9_]+[[:space:]]+in[[:space:]].*;[[:space:]]*do)' ]] || \
     [[ "$cmd" =~ '(>|>>)[[:space:]]*.*(dump|projeto_completo|project_dump|saida\.txt|teste\.txt)' ]]; then
    return 0
  fi

  # Síntese de voz (TTS) ou dumps de texto/logs longos via echo
  if [[ "$cmd" =~ "(^|[[:space:]])(spd-say|piper-tts)($|[[:space:]])" ]]; then
    return 0
  fi
  if [[ "$first" =~ "^(echo|printf|spd-say)$" && (${#cmd} -gt 50 || "$cmd" == *">"*) ]]; then
    return 0
  fi

  # Instalação/remoção em massa de pacotes (4+ pacotes)
  if [[ "$cmd" =~ "(pacman|yay|apt)[[:space:]]" && ${#cmd} -gt 80 ]]; then
    return 0
  fi

  # Chaves de API, tokens e payloads de autorização
  if [[ "$cmd" =~ "(sk-[a-zA-Z0-9_-]{15,}|Authorization:[[:space:]]*Bearer|GEMINI_API_KEY|GROQ_API_KEY|NVIDIA_API_KEY)" ]]; then
    return 0
  fi

  return 1
}

# 3. Função para detectar downloads pontuais da web, git clone e instaladores via curl
_zsh_is_web_download() {
  local cmd="$1"
  if [[ "$cmd" =~ "^(git[[:space:]]+clone|wget)" || \
        "$cmd" =~ "curl[[:space:]].*\|[[:space:]]*(bash|sh|sudo[[:space:]]+bash|sudo[[:space:]]+sh)" || \
        "$cmd" =~ "(pip|npm)[[:space:]]+.*https?://" ]]; then
    return 0
  fi
  return 1
}

# 4. Função para remover variações antigas de comandos que só mudam a porta no HISTFILE
_zsh_dedup_port_variations() {
  local cmd="$1"
  # Verifica se o comando contém porta (--port, -p ou :porta)
  if [[ "$cmd" =~ "(--port[[:space:]]+|-p[[:space:]]+|:)[0-9]{2,5}" ]]; then
    local hfile="${HISTFILE:-${HOME}/.zsh_history}"
    if [[ -f "$hfile" ]]; then
      # Escapa metacaracteres regex antes de substituir a porta por [0-9]+
      local escaped_base=$(print -r -- "$cmd" | sed -E 's/[.[^$*+?(){|\\]/\\&/g' | sed -E 's/(--port[[:space:]]+|-p[[:space:]]+|:)[0-9]{2,5}/\1[0-9]{2,5}/g')
      if grep -Eq ";${escaped_base}$" "$hfile" 2>/dev/null; then
        local tmp="${hfile}.tmp"
        grep -Ev ";${escaped_base}$" "$hfile" > "$tmp" 2>/dev/null && mv "$tmp" "$hfile"
      fi
    fi
  fi
}

# 5. Hook principal que filtra e divide os comandos antes de gravar no histórico
zshaddhistory() {
  setopt LOCAL_OPTIONS EXTENDED_GLOB
  local cmd="$1"
  local single_line="${1%%$'\n'}"
  
  # Ignora comandos vazios
  [[ -z "${cmd// }" ]] && return 1

  # Regra A: Descarta totalmente lixo, comandos colados grudados, dumps e ruídos
  if _zsh_is_absolute_junk "$cmd"; then
    return 1
  fi

  # Regra B: Downloads únicos da internet (git clone, wget, curl ... | bash) -> Salva no REGISTRO DEDICADO
  if _zsh_is_web_download "$cmd"; then
    local clean_dl="${${cmd//$'\n'/ }//[[:space:]]##/ }"
    if [[ ! -f "${DOWNLOADS_LOG}" ]] || ! grep -qF "$clean_dl" "${DOWNLOADS_LOG}" 2>/dev/null; then
      local dt
      if [[ -n "$EPOCHSECONDS" ]]; then
        strftime -s dt "%Y-%m-%d %H:%M:%S" "$EPOCHSECONDS" 2>/dev/null || dt=$(date "+%Y-%m-%d %H:%M:%S")
      else
        dt=$(date "+%Y-%m-%d %H:%M:%S")
      fi
      print -r -- "[${dt}] ${clean_dl}" >> "${DOWNLOADS_LOG}"
    fi
    return 1 # Não salva no .zsh_history
  fi

  # Regra C: Perguntas, ferramentas de IA e prompts limpos -> Salva no HISTÓRICO DE IA
  local is_ai_prompt=0
  if [[ "$single_line" =~ '(^|[[:space:]])(\||\&\&|\;)[[:space:]]*(ia|ai|aiman|explain_screen|opencode|agy|openclaude|copilot|metis|gqwen|g4f)($|[[:space:]])' ]] || \
     [[ "$single_line" =~ '^(ia|ai|aiman|explain_screen|opencode|agy|openclaude|copilot|metis|gqwen|g4f)($|[[:space:]])' ]] || \
     [[ "$single_line" =~ '^(como|qual|quais|porque|pq|onde|quando|quem|quanto|quantos|quero|queria|preciso|ajuda|criar|fazer|comando|descompactar|resetar|renomear)([[:space:]]|$)' ]]; then
    is_ai_prompt=1
  fi

  if [[ $is_ai_prompt -eq 1 ]]; then
    local save_cmd="$cmd"
    if [[ "$save_cmd" =~ "^(opencode|openclaude|agy)[[:space:]]+--port[[:space:]]+[0-9]+$" ]]; then
      save_cmd="${save_cmd%% --port *}"
    fi

    local clean_single="${${save_cmd//$'\n'/ }//[[:space:]]##/ }"
    local ts="${EPOCHSECONDS:-$(date +%s)}"

    # Se já existia antes, remove a ocorrência antiga para atualizar para a posição mais recente (MRU)
    if [[ -f "${AI_HISTFILE}" ]]; then
      local tmp_ai="${AI_HISTFILE}.tmp"
      local escaped_cmd="${clean_single//(#m)[.[^$*+?(){|\\]/\\$MATCH}"
      grep -Ev ";${escaped_cmd}[[:space:]]*$" "${AI_HISTFILE}" > "$tmp_ai" 2>/dev/null && mv "$tmp_ai" "${AI_HISTFILE}"
    fi

    print -r -- ": ${ts}:0;${save_cmd}" >> "${AI_HISTFILE}"
    return 1
  fi

  # Regra D: Validação contra Erros de Digitação (Typos como clar, eixit, lss)
  if ! _zsh_validate_cmd_exists "$cmd"; then
    return 1
  fi

  # Regra E: Desduplicação inteligente de variações de portas no .zsh_history
  _zsh_dedup_port_variations "$cmd"

  # Retorna 0: Comando normal, válido e limpo -> Salva no .zsh_history (Ctrl+R / Seta Cima)
  return 0
}

# 6. Widget interativo para buscar no histórico de IA com FZF (Alt + H)
# Funciona tanto como widget ZLE (Alt+H) quanto como comando no terminal (iah/ai-history)
ai-history-widget() {
  if [[ ! -f "${AI_HISTFILE}" ]]; then
    if [[ -n "$WIDGET" ]]; then
      zle -M "Histórico de IA ainda está vazio."
    else
      print "Histórico de IA ainda está vazio."
    fi
    return
  fi

  local selected
  if command -v fzf >/dev/null 2>&1; then
    selected=$(tac "${AI_HISTFILE}" | sed 's/^: [0-9]*:[0-9]*;//' | awk '!seen[$0]++' | fzf --height 40% --reverse --prompt="🤖 Histórico de IA & Prompts [Alt+H] > " --header="Selecione um prompt:")
  else
    selected=$(tail -n 20 "${AI_HISTFILE}" | sed 's/^: [0-9]*:[0-9]*;//')
  fi

  if [[ -n "$selected" ]]; then
    if [[ -n "$WIDGET" ]]; then
      LBUFFER="$selected"
      zle reset-prompt
    else
      print -z "$selected"
    fi
  fi
}

# 7. Widget interativo para consultar o Registro de Downloads e Repositórios
downloads-log-widget() {
  if [[ ! -f "${DOWNLOADS_LOG}" ]]; then
    echo "Nenhum download ou repositório registrado ainda."
    return
  fi

  if command -v fzf >/dev/null 2>&1; then
    local selected=$(grep -v '^#' "${DOWNLOADS_LOG}" | grep -v '^[[:space:]]*$' | tac | fzf --no-mouse --height 40% --reverse --prompt="🌐 Downloads & Repositórios > " --header="Selecione para colar no terminal:")
    if [[ -n "$selected" ]]; then
      local cmd_to_paste=$(echo "$selected" | sed 's/^\[[^]]*\] //')
      print -z "$cmd_to_paste"
    fi
  else
    cat "${DOWNLOADS_LOG}"
  fi
}

# 8. Registrar o Widget no ZSH e definir os atalhos
zle -N ai-history-widget
bindkey '\eh' ai-history-widget   # Alt + H
bindkey '^[h' ai-history-widget   # Alt + H (escape sequence alternativa)

# 9. Aliases rápidos para o terminal
alias iah='ai-history-widget'
alias ai-history='ai-history-widget'
alias repos='downloads-log-widget'
alias downloads='downloads-log-widget'

# 10. Rastreamento de execução e Exit Code ($?) para o assistente Metis / Screen
autoload -Uz add-zsh-hook 2>/dev/null

typeset -g _METIS_CMD_EXECUTING=0
typeset -g _METIS_LAST_CMD=""

_metis_track_preexec() {
  _METIS_CMD_EXECUTING=1
  _METIS_LAST_CMD="$1"
  local win="${KITTY_WINDOW_ID:-$$}"
  print -r -- "$1" > "/tmp/metis_cmd_${win}" 2>/dev/null
  # Grava ambiente Kitty para Metis Screen
  [[ -n "$KITTY_LISTEN_ON" ]] && print -r -- "$KITTY_LISTEN_ON" > "/tmp/orig_kitty_listen.${UID}" 2>/dev/null
  [[ -n "$KITTY_LISTEN_ON" ]] && print -r -- "$KITTY_LISTEN_ON" > "/tmp/orig_kitty_listen" 2>/dev/null
  [[ -n "$KITTY_WINDOW_ID" ]] && print -r -- "$KITTY_WINDOW_ID" > "/tmp/orig_kitty_id.${UID}" 2>/dev/null
  [[ -n "$KITTY_WINDOW_ID" ]] && print -r -- "$KITTY_WINDOW_ID" > "/tmp/orig_kitty_id" 2>/dev/null
  [[ -n "$KITTY_PID" ]] && print -r -- "$KITTY_PID" > "/tmp/orig_kitty_pid.${UID}" 2>/dev/null
  [[ -n "$KITTY_PID" ]] && print -r -- "$KITTY_PID" > "/tmp/orig_kitty_pid" 2>/dev/null
}

_metis_track_precmd() {
  local exit_code=$?
  # Ignora se o usuário apenas apertou Enter sem rodar comando
  (( _METIS_CMD_EXECUTING == 0 )) && return 0
  _METIS_CMD_EXECUTING=0

  local win="${KITTY_WINDOW_ID:-$$}"
  local cmd="$_METIS_LAST_CMD"
  if [[ -z "$cmd" && -f "/tmp/metis_cmd_${win}" ]]; then
    cmd="$(cat "/tmp/metis_cmd_${win}" 2>/dev/null)"
  fi
  [[ -z "$cmd" ]] && return 0

  {
    print -r -- "CMD: $cmd"
    print -r -- "EXIT_CODE: $exit_code"
    print -r -- "TIME: ${EPOCHSECONDS:-$(date +%s)}"
    print -r -- "WIN: $win"
  } > "/tmp/metis_status_${win}" 2>/dev/null

  cp -f "/tmp/metis_status_${win}" "/tmp/metis_last_status" 2>/dev/null
}

add-zsh-hook preexec _metis_track_preexec
add-zsh-hook precmd _metis_track_precmd

