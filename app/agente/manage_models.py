#!/usr/bin/env python3
"""
CLI simplificado para gerenciar modelos do Metis.
Delegação para agente.models.cli (nova arquitetura centralizada).
"""
import sys
from pathlib import Path

# Adiciona path do Metis principal (resolve symlinks)
metis_root = Path(__file__).resolve().parent.parent
if str(metis_root) not in sys.path:
    sys.path.insert(0, str(metis_root))

# Delegação direta para o novo CLI centralizado
from agente.models.cli import main

if __name__ == "__main__":
    main()