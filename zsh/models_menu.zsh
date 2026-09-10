#!/usr/bin/env zsh
# =============================================================================
# models_menu.zsh (Versão Modularizada)
# Menus FZF Compartilhados de Gerenciamento de Modelos e Provedores.
# =============================================================================

MODELS_MODULES_DIR="${0:A:h}/models"

# Carregamento sequencial dos submódulos
for mod in "$MODELS_MODULES_DIR"/*.zsh(Nn); do
  if [[ -f "$mod" ]]; then
    source "$mod"
  fi
done
