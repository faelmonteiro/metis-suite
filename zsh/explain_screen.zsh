#!/usr/bin/env zsh
# =============================================================================
# explain_screen.zsh
# Assistente inteligente de terminal com captura de tela, agente de ferramentas,
# chat contínuo, menus de modelos, modo /auto e integração com Kitty.
# =============================================================================

SCREEN_MODULES_DIR="${0:A:h}/screen"

# Carregamento sequencial de todos os submódulos
for mod in "$SCREEN_MODULES_DIR"/*.zsh(Nn); do
  if [[ -f "$mod" ]]; then
    source "$mod"
  fi
done

# Execução do loop principal
main "$@"
