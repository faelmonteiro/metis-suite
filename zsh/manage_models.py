#!/usr/bin/env python3
"""
CLI simplificado para gerenciar modelos do Metis.
Delegação para agente.models.cli (nova arquitetura centralizada).
"""
import sys
from pathlib import Path

# Procura caminhos do app Metis
possible_roots = [
    Path(__file__).resolve().parent.parent / "app",
    Path(__file__).resolve().parent.parent,
    Path.home() / ".local" / "share" / "metis" / "app",
    Path.home() / "Metis",
    Path.home() / "metis-suite" / "app",
]

for r in possible_roots:
    if r.exists() and str(r) not in sys.path:
        sys.path.insert(0, str(r))

from agente.models.cli import main

if __name__ == "__main__":
    main()
