from agente import config

__all__ = [
    "RESET", "BOLD", "DIM", "ITALIC", "UNDERLINE",
    "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE", "GRAY",
    "METIS_GOLD", "METIS_GOLD_BRIGHT", "METIS_GOLD_MUTED", "METIS_AMBER",
    "METIS_CYAN", "METIS_CYAN_SOFT", "METIS_BLUE", "METIS_GREEN", "METIS_RED",
    "METIS_WHITE", "METIS_GRAY", "METIS_GRAY_LIGHT", "METIS_GRAY_DARK",
    "METIS_BORDER", "METIS_BORDER_BRIGHT", "METIS_BG_CARD",
]

if config.NO_COLOR:
    RESET = ""
    BOLD = ""
    DIM = ""
    ITALIC = ""
    UNDERLINE = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    GRAY = ""
    METIS_GOLD = ""
    METIS_GOLD_BRIGHT = ""
    METIS_GOLD_MUTED = ""
    METIS_AMBER = ""
    METIS_CYAN = ""
    METIS_CYAN_SOFT = ""
    METIS_BLUE = ""
    METIS_GREEN = ""
    METIS_RED = ""
    METIS_WHITE = ""
    METIS_GRAY = ""
    METIS_GRAY_LIGHT = ""
    METIS_GRAY_DARK = ""
    METIS_BORDER = ""
    METIS_BORDER_BRIGHT = ""
    METIS_BG_CARD = ""
else:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    # Cores Clássicas ANSI
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Paleta Premium: Ouro & Navy/Slate (Metis Oracle Theme)
    METIS_GOLD = "\033[38;2;240;168;93m"         # #f0a85d (Dourado clássico)
    METIS_GOLD_BRIGHT = "\033[38;2;250;208;148m"  # #fad094 (Dourado luminoso)
    METIS_GOLD_MUTED = "\033[38;2;190;135;80m"    # #be8750 (Dourado suave)
    METIS_AMBER = "\033[38;2;245;158;11m"         # #f59e0b (Âmbar)

    METIS_CYAN = "\033[38;2;103;232;249m"         # #67e8f9 (Ciano oráculo)
    METIS_CYAN_SOFT = "\033[38;2;125;211;252m"    # #7dd3fc (Azul celeste)
    METIS_BLUE = "\033[38;2;56;189;248m"          # #38bdf8 (Azul neon)

    METIS_GREEN = "\033[38;2;74;222;128m"         # #4ade80 (Verde online)
    METIS_RED = "\033[38;2;248;113;113m"          # #f87171 (Vermelho coral aviso)
    METIS_WHITE = "\033[38;2;248;250;252m"        # #f8fafc (Branco gelo)

    METIS_GRAY = "\033[38;2;148;163;184m"         # #94a3b8 (Slate texto suave)
    METIS_GRAY_LIGHT = "\033[38;2;203;213;225m"   # #cbd5e1 (Slate claro)
    METIS_GRAY_DARK = "\033[38;2;100;116;139m"    # #64748b (Slate escuro)

    METIS_BORDER = "\033[38;2;46;62;84m"          # #2e3e54 (Borda elegante)
    METIS_BORDER_BRIGHT = "\033[38;2;70;92;122m"  # #465c7a (Borda destacada)
    METIS_BG_CARD = "\033[48;2;20;30;46m"         # #141e2e (Fundo de destaque)
