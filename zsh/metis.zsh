#!/usr/bin/env zsh
# =============================================================================
# metis.zsh (Versão Modularizada)
# O Copiloto Autônomo de Terminal.
# =============================================================================

METIS_MODULES_DIR="${0:A:h}/metis"

# Carregamento sequencial dos submódulos
for mod in "$METIS_MODULES_DIR"/*.zsh(Nn); do
  if [[ -f "$mod" ]]; then
    source "$mod"
  fi
done
