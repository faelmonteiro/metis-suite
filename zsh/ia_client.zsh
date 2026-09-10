#!/usr/bin/env zsh
# =============================================================================
# ia_client.zsh (Versão Modularizada)
# Motor Central Unificado de IA para o Terminal ZSH.
# =============================================================================

CLIENT_MODULES_DIR="${0:A:h}/client"

# Carregamento sequencial dos submódulos
for mod in "$CLIENT_MODULES_DIR"/*.zsh(Nn); do
  if [[ -f "$mod" ]]; then
    source "$mod"
  fi
done
