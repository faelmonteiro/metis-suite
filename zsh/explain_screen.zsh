#!/usr/bin/env zsh
# =============================================================================
# explain_screen.zsh
# Assistente inteligente de terminal com captura de tela, agente de ferramentas,
# chat contínuo, menus de modelos, modo /auto e integração com Kitty.
# =============================================================================

export ZSH_AI_DIR="${0:A:h}"
[[ ! -d "$ZSH_AI_DIR" || ! -f "$ZSH_AI_DIR/loader.zsh" ]] && ZSH_AI_DIR="$HOME/.local/share/metis/zsh"
export METIS_ROOT="${ZSH_AI_DIR:h}"
export SCREEN_MODULES_DIR="$ZSH_AI_DIR/screen"

# Carregamento sequencial de todos os submódulos
for mod in "$SCREEN_MODULES_DIR"/*.zsh(Nn); do
  if [[ -f "$mod" ]]; then
    source "$mod"
  fi
done

# Garante limpeza de seleção e temporários ao fechar o programa
trap 'limpar_selecao_mouse 2>/dev/null; rm -f /tmp/orig_kitty_id /tmp/orig_kitty_listen /tmp/orig_kitty_pid 2>/dev/null' EXIT INT TERM

# Execução do loop principal
main "$@"
