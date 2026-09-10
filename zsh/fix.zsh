#!/usr/bin/env zsh
# =============================================================================
# fix.zsh (Versão Modularizada)
# Widget ZLE para gerar comandos, explicações e correções usando IA (Ctrl+G).
# =============================================================================

FIX_MODULES_DIR="${0:A:h}/fix"

# Carregamento sequencial dos submódulos
for mod in "$FIX_MODULES_DIR"/*.zsh(Nn); do
  if [[ -f "$mod" ]]; then
    source "$mod"
  fi
done
