"""Módulo principal do agente Llama + SearXNG.

readline/histórico do terminal é carregado e configurado em agente/completer
(configurar_readline, chamado por main). Imports duplicados aqui seriam
redundantes e silenciados como "unused" — mantemos a responsabilidade única lá.
"""
import logging
logger = logging.getLogger(__name__)