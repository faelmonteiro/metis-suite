#!/usr/bin/env zsh
# =============================================================================
# git-ai.zsh - Gerador Automático de Commits via IA
# Versão corrigida:
# - Valida se está dentro de um repositório Git
# - Usa git diff --no-color
# - Não remove todas as linhas vazias da mensagem
# - Verifica se o git commit realmente funcionou
# - Trata erro da IA com código de retorno
# =============================================================================

source "${ZSH_AI_DIR:-$HOME/.local/share/metis/zsh}/ia_client.zsh" 2>/dev/null || true

if (( ! $+functions[_ai_query] )); then
  return 0 2>/dev/null || exit 0
fi

git_commit_ai() {
  if ! command -v git >/dev/null 2>&1; then
    echo -e "\e[31m⚠️ O comando 'git' não está instalado.\e[0m"
    return 1
  fi

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "\e[31m⚠️ Este diretório não é um repositório Git.\e[0m"
    return 1
  fi

  local diff_data
  diff_data=$(git --no-pager diff --cached --no-color --no-ext-diff 2>/dev/null)

  if [[ -z "$diff_data" ]]; then
    echo -e "\e[33m⚠️ O 'git diff --cached' está vazio. Faça 'git add' nos seus arquivos primeiro!\e[0m"
    return 1
  fi

  local diff_lines
  diff_lines=$(print -r -- "$diff_data" | wc -l)

  if (( diff_lines > 300 )); then
    local stat_summary head_diff
    stat_summary=$(git --no-pager diff --cached --stat --no-color 2>/dev/null | head -n 40)
    head_diff=$(print -r -- "$diff_data" | head -n 250)
    diff_data="[Resumo dos arquivos alterados]:
$stat_summary

[Início do Diff (truncado para performance)]:
$head_diff"
  fi

  local prompt="Gere uma mensagem de commit no formato 'Conventional Commits' para o seguinte diff.

Regras:
1. Comece com o tipo apropriado (feat, fix, refactor, chore, etc).
2. Forneça o título curto na primeira linha.
3. Se necessário, deixe uma linha vazia e adicione detalhes em lista.
4. NUNCA escreva explicações fora da mensagem.
5. Não use cercas de código markdown.

Diff:
$diff_data"

  _ai_get_current_provider_info

  local m_icon="$(_ai_get_metis_icon)"
  if [[ -t 1 ]]; then
    echo -e "${m_icon}\e[38;2;250;208;148m[Metis]:\e[0m \e[34mAnalisando diff e gerando commit via ${AI_ACTIVE_LABEL}...\e[0m"
  fi

  local response rc err_file
  err_file="$(mktemp "${TMPDIR:-/tmp}/ai_git.XXXXXX" 2>/dev/null)" || err_file="${TMPDIR:-/tmp}/ai_git.$$"

  response="$(_ai_query "$prompt" 2>"$err_file")"
  rc=$?

  if (( rc != 0 )); then
    if [[ -s "$err_file" ]]; then
      cat "$err_file" >&2
    else
      echo -e "\e[31m⚠️ Falha ao comunicar com ${AI_ACTIVE_LABEL}.\e[0m" >&2
    fi
    rm -f "$err_file"
    return 1
  fi

  rm -f "$err_file"

  if [[ "$response" == ⚠️* || "$response" == Traceback* || "$response" == Erro* || "$response" == Error* ]]; then
    echo -e "\e[31m⚠️ A IA retornou um erro em vez de mensagem de commit.\e[0m"
    return 1
  fi

  local commit_msg
  commit_msg=$(print -r -- "$response" |
    sed -e 's/^```.*$//' |
    tr -d '\140' |
    awk '{gsub(/\r/,"")} NF {if (seen && blank) print ""; if (!seen) seen=1; blank=0; print; next} {blank=1}')

  if [[ -z "$(_ai_trim "$commit_msg")" ]]; then
    echo -e "\e[31m⚠️ A mensagem final ficou vazia.\e[0m"
    return 1
  fi

  echo -e "\n\e[36mMensagem Sugerida:\e[0m"
  print -r -- "$commit_msg"
  echo -e "\e[36m------------------\e[0m"

  if [[ ! -t 0 ]]; then
    echo -e "\e[33m⚠️ Confirmação interativa requer um terminal.\e[0m"
    return 1
  fi

  local choice
  read "choice?Confirmar este commit? (s/N): "

  if [[ "${choice:l}" == (s|sim|y|yes) ]]; then
    if git commit -m "$commit_msg"; then
      echo -e "\e[32m✅ Commit realizado com sucesso!\e[0m"
    else
      echo -e "\e[31m❌ O comando 'git commit' falhou.\e[0m"
      return 1
    fi
  else
    echo -e "\e[31mCancelado.\e[0m"
  fi
}

alias gca="git_commit_ai"
alias git-ai="git_commit_ai"
