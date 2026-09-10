#!/usr/bin/env zsh
# =============================================================================
# screen/05-agent-tools.zsh
# Execução e controle de ferramentas do agente (bash, arquivos, listagem).
# =============================================================================

executar_ferramenta() {
  local tool_name="$1"
  local tool_path="$2"
  local tool_content="$3"

  local result=""
  local tool_exit_code=0

  tool_path="${tool_path/#\~/$HOME}"

  case "$tool_name" in
    bash|exec|run_command|sh)
      local cmd="$tool_content"
      [[ -z "$cmd" ]] && cmd="$tool_path"
      cmd="$(_trim "$cmd")"

      if [[ -z "$cmd" ]]; then
        print -r -- "Erro: nenhum comando válido fornecido pela IA."
        return 1
      fi

      local auto_read="${AI_AGENT_AUTO_READ:-1}"

      if [[ "$auto_read" == "1" ]] && _is_safe_read_cmd "$cmd"; then
        printf '\033[36m🔍 [Agente Inspecionando]: \033[1;38;5;214m%s\033[0m\n' "$cmd" >&2
        local tmp_cmd_out=""
        tmp_cmd_out="$(mktemp)"
        if command -v timeout >/dev/null 2>&1; then
          timeout 15 zsh -c "$cmd" >"$tmp_cmd_out" 2>&1
          tool_exit_code=$?
        else
          zsh -c "$cmd" >"$tmp_cmd_out" 2>&1
          tool_exit_code=$?
        fi
        result="$(head -n 120 "$tmp_cmd_out" 2>/dev/null)"
        rm -f "$tmp_cmd_out" 2>/dev/null
      else
        if ! _confirmar_acao "A IA quer inserir no seu terminal original: \033[1;38;5;214m$cmd\033[0m"; then
          print -r -- "Ação negada pelo usuário para inserir o comando '$cmd'."
          return 0
        fi

        printf '\033[36m⚡ [Agente inserindo no terminal original]: \033[1;38;5;214m%s\033[0m\n' "$cmd" >&2

        if enviar_ao_kitty "$cmd"; then
          result="Comando inserido no terminal original sem executar. Revise, execute manualmente e use /s para sincronizar após executar."
        else
          result="Erro: não foi possível inserir o comando no terminal original."
          tool_exit_code=1
        fi
      fi
      ;;

    read_file|cat|ler_arquivo)
      local filepath="$tool_path"

      if [[ -z "$filepath" ]]; then
        filepath="${tool_content%%$'\n'*}"
      fi

      filepath="$(_trim "${filepath/#\~/$HOME}")"

      printf '\033[36m🔍 [Agente Lendo Arquivo]: \033[1;37m%s\033[0m\n' "$filepath" >&2

      if _is_sensitive_path "$filepath"; then
        if ! _confirmar_acao "A IA quer ler um arquivo potencialmente sensível: \033[1;37m$filepath\033[0m"; then
          print -r -- "Ação negada pelo usuário para ler '$filepath'."
          return 0
        fi
      fi

      if [[ -f "$filepath" ]]; then
        result="$(head -n 250 "$filepath" 2>&1)"
      else
        result="Erro: Arquivo '$filepath' não encontrado."
        tool_exit_code=1
      fi
      ;;

    write_file|create_file|salvar_arquivo)
      local filepath="$tool_path"
      local content="$tool_content"

      if [[ -z "$filepath" ]]; then
        filepath="${tool_content%%$'\n'*}"
        content="${tool_content#*$'\n'}"
      fi

      filepath="$(_trim "${filepath/#\~/$HOME}")"

      local dirpath=""
      dirpath="$(dirname "$filepath")"

      local resolved_path="$(_resolve_path "$filepath")"

      if _is_sensitive_path "$resolved_path" && [[ "${AI_AGENT_ALLOW_DANGEROUS_PATHS:-0}" != "1" ]]; then
        result="Erro: Caminho sensível bloqueado para escrita: '$resolved_path'. Defina AI_AGENT_ALLOW_DANGEROUS_PATHS=1 somente se souber o que está fazendo."
        tool_exit_code=1
        print -r -- "$result"
        return "$tool_exit_code"
      fi

      local acao_msg="criar o arquivo: \033[1;37m$filepath\033[0m"

      if [[ -f "$filepath" ]]; then
        acao_msg="modificar o arquivo existente: \033[1;37m$filepath\033[0m"
      fi

      if ! _confirmar_acao "A IA quer $acao_msg"; then
        print -r -- "Ação negada pelo usuário para gravar no arquivo '$filepath'."
        return 0
      fi

      printf '\033[36m💾 [Agente Gravando Arquivo]: \033[1;37m%s\033[0m\n' "$filepath" >&2

      mkdir -p "$dirpath" 2>/dev/null

      local write_ok=0

      if [[ "$filepath" == *.pdf ]]; then
        local tmp_txt=""
        tmp_txt="$(mktemp --suffix=.txt 2>/dev/null || mktemp /tmp/pdf_src.XXXXXX)"

        print -r -- "$content" > "$tmp_txt"

        if command -v libreoffice >/dev/null 2>&1; then
          libreoffice --headless --convert-to pdf "$tmp_txt" --outdir "$dirpath" >/dev/null 2>&1

          local gen_pdf="${tmp_txt%.*}.pdf"

          if [[ -f "$gen_pdf" ]]; then
            mv "$gen_pdf" "$filepath" 2>/dev/null
            write_ok=1
          fi
        elif command -v pandoc >/dev/null 2>&1 && command -v pdflatex >/dev/null 2>&1; then
          pandoc "$tmp_txt" -o "$filepath" >/dev/null 2>&1 && write_ok=1
        fi

        rm -f "$tmp_txt" 2>/dev/null

        if (( write_ok == 0 )); then
          local txt_fallback="${filepath%.pdf}.txt"

          print -r -- "$content" > "$txt_fallback" 2>/dev/null

          if [[ -f "$txt_fallback" ]]; then
            filepath="$txt_fallback"
            write_ok=1
          fi
        fi
      else
        if print -r -- "$content" > "$filepath" 2>/dev/null; then
          write_ok=1
        fi
      fi

      if (( write_ok == 1 )) && [[ -f "$filepath" ]]; then
        if [[ "$filepath" == *.sh || "$filepath" == *.zsh || "$content" == \#\!* ]]; then
          chmod +x "$filepath" 2>/dev/null
        fi

        local size_bytes=""
        size_bytes="$(_trim "$(wc -c < "$filepath" 2>/dev/null)")"

        printf '\033[32m✅ [Arquivo Salvo com Sucesso]: %s (%s bytes)\033[0m\n' "$filepath" "$size_bytes" >&2

        result="Arquivo '$filepath' salvo com sucesso ($size_bytes bytes)."
      else
        result="Erro: Falha ao gravar no caminho '$filepath'."
        tool_exit_code=1
      fi
      ;;

    append_file|adicionar_ao_arquivo)
      local filepath="$tool_path"
      local content="$tool_content"

      if [[ -z "$filepath" ]]; then
        filepath="${tool_content%%$'\n'*}"
        content="${tool_content#*$'\n'}"
      fi

      filepath="$(_trim "${filepath/#\~/$HOME}")"

      local resolved_path="$(_resolve_path "$filepath")"

      if _is_sensitive_path "$resolved_path" && [[ "${AI_AGENT_ALLOW_DANGEROUS_PATHS:-0}" != "1" ]]; then
        result="Erro: Caminho sensível bloqueado para append: '$resolved_path'. Defina AI_AGENT_ALLOW_DANGEROUS_PATHS=1 somente se souber o que está fazendo."
        tool_exit_code=1
        print -r -- "$result"
        return "$tool_exit_code"
      fi

      if ! _confirmar_acao "A IA quer adicionar linhas ao arquivo: \033[1;37m$filepath\033[0m"; then
        print -r -- "Ação negada pelo usuário para adicionar conteúdo em '$filepath'."
        return 0
      fi

      printf '\033[36m➕ [Agente Adicionando ao Arquivo]: \033[1;37m%s\033[0m\n' "$filepath" >&2

      mkdir -p "$(dirname "$filepath")" 2>/dev/null

      if print -r -- "$content" >> "$filepath" 2>/dev/null && [[ -f "$filepath" ]]; then
        local size_bytes=""
        size_bytes="$(_trim "$(wc -c < "$filepath" 2>/dev/null)")"

        printf '\033[32m✅ [Conteúdo Adicionado]: %s (%s bytes total)\033[0m\n' "$filepath" "$size_bytes" >&2

        result="Conteúdo anexado ao final de '$filepath' com sucesso."
      else
        result="Erro: Falha ao anexar no arquivo '$filepath'."
        tool_exit_code=1
      fi
      ;;

    list_dir|ls|listar_pasta)
      local dirpath="$tool_path"

      if [[ -z "$dirpath" ]]; then
        dirpath="${tool_content%%$'\n'*}"
      fi

      [[ -z "$dirpath" ]] && dirpath="."
      dirpath="$(_trim "${dirpath/#\~/$HOME}")"

      printf '\033[36m📂 [Agente Listando Pasta]: \033[1;37m%s\033[0m\n' "$dirpath" >&2

      if [[ -d "$dirpath" ]]; then
        if command -v eza >/dev/null 2>&1; then
          result="$(eza -la --group-directories-first --no-quotes --time-style=relative "$dirpath" 2>&1 | head -n 100)"
        elif command -v tree >/dev/null 2>&1; then
          result="$(tree -L 2 --dirsfirst "$dirpath" 2>&1 | head -n 100)"
        else
          result="$(ls -lah "$dirpath" 2>&1 | head -n 100)"
        fi
      else
        result="Erro: Diretório '$dirpath' não encontrado."
        tool_exit_code=1
      fi
      ;;

    *)
      result="Erro: Ferramenta '$tool_name' não reconhecida."
      tool_exit_code=1
      ;;
  esac

  print -r -- "$result"
  return "$tool_exit_code"
}
