"""
Módulo de Análise e Varredura de Pastas e Arquivos Locais.
Gera árvore de diretórios inteligente, lê arquivos-chave (README, configs) e prepara contexto para a IA.
"""

import logging
logger = logging.getLogger(__name__)


import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from . import config

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".cache",
    ".idea", ".vscode", "dist", "build", ".next", ".nuxt", "target", ".antigravity"
}

KEY_FILES = {
    "readme.md", "readme.txt", "readme", "package.json", "pyproject.toml",
    "cargo.toml", "go.mod", "requirements.txt", "dockerfile", "docker-compose.yml",
    "makefile", "gemfile", "composer.json"
}

def generate_folder_tree(dir_path: Path, max_depth: int = 3, max_entries: int = 80) -> Tuple[str, Dict[str, str], int]:
    """
    Gera uma representação textual da árvore de diretórios e extrai o conteúdo de arquivos-chave.
    """
    dir_path = dir_path.resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"O caminho '{dir_path}' não é um diretório válido.")

    lines: List[str] = [f"📁 {dir_path.name}/"]
    key_contents: Dict[str, str] = {}
    total_files = 0
    total_dirs = 0
    entry_count = 0

    def walk(current_dir: Path, prefix: str = "", depth: int = 0):
        nonlocal entry_count, total_files, total_dirs
        if depth > max_depth or entry_count >= max_entries:
            return

        try:
            items = sorted(list(current_dir.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}└── [Permissão negada]")
            return

        filtered_items = [item for item in items if item.name not in IGNORE_DIRS]

        for i, item in enumerate(filtered_items):
            if entry_count >= max_entries:
                lines.append(f"{prefix}└── ... (mais itens omitidos)")
                break

            entry_count += 1
            is_last = (i == len(filtered_items) - 1)
            connector = "└── " if is_last else "├── "
            new_prefix = prefix + ("    " if is_last else "│   ")

            if item.is_dir():
                total_dirs += 1
                lines.append(f"{prefix}{connector}📁 {item.name}/")
                walk(item, new_prefix, depth + 1)
            else:
                total_files += 1
                try:
                    size_kb = item.stat().st_size / 1024
                    size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
                except (OSError, PermissionError):
                    size_str = "? KB"
                lines.append(f"{prefix}{connector}📄 {item.name} ({size_str})")

                # Se for arquivo-chave, lê prévia do conteúdo
                if item.name.lower() in KEY_FILES and len(key_contents) < 4:
                    try:
                        with open(item, encoding="utf-8", errors="ignore") as f:
                            content = f.read(2500)
                        key_contents[item.name] = content
                    except Exception as _silent_e:
                        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

    walk(dir_path)
    tree_str = "\n".join(lines)
    return tree_str, key_contents, total_files

def format_folder_context(dir_path: Path) -> str:
    """Monta um prompt detalhado com a estrutura da pasta e arquivos-chave."""
    try:
        from agente.utils import caminho_leitura_seguro
        dir_path = caminho_leitura_seguro(str(dir_path), permitir_diretorio=True)
    except Exception as e:
        return f"Acesso negado para leitura do diretório: {str(e)}"

    tree_str, key_contents, total_files = generate_folder_tree(dir_path)
    
    context = [
        f"=== ANÁLISE DE DIRETÓRIO: {dir_path.resolve()} ===",
        f"Estrutura da pasta:\n```\n{tree_str}\n```",
    ]

    if key_contents:
        context.append("\n=== CONTEÚDO DOS ARQUIVOS-CHAVE ENCONTRADOS ===")
        for filename, content in key_contents.items():
            context.append(f"\n--- {filename} ---\n```\n{content}\n```")

    return "\n".join(context)

def format_file_context(file_path: Path, max_chars: int = 40000) -> str:
    """Lê e formata o conteúdo de um arquivo individual com validação de segurança."""
    try:
        from agente.utils import caminho_leitura_seguro
        file_path = caminho_leitura_seguro(str(file_path))
    except Exception as e:
        return f"Acesso negado para leitura do arquivo: {str(e)}"

    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"O caminho '{file_path}' não é um arquivo válido.")

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        is_truncated = len(content) > max_chars
        content_preview = content[:max_chars]
        
        res = [
            f"=== ARQUIVO: {file_path.name} (Caminho: {file_path}) ===",
            f"Tamanho total: {file_path.stat().st_size / 1024:.1f} KB",
            "Conteúdo:\n```",
            content_preview,
            "```"
        ]
        if is_truncated:
            res.append(f"\n*(Nota: O arquivo foi truncado aos primeiros {max_chars} caracteres)*")
        return "\n".join(res)
    except Exception as e:
        return f"Erro ao ler arquivo {file_path.name}: {str(e)}"

def get_active_window_cwd() -> Optional[Path]:
    """
    Descobre o diretório de trabalho (CWD) da janela ativa no Hyprland
    (ex: terminal focado, gerenciador de arquivos, etc.).
    """
    import subprocess
    import json
    try:
        res = subprocess.run(["hyprctl", "activewindow", "-j"], stdout=subprocess.PIPE, text=True, timeout=0.4)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            pid = data.get("pid")
            if pid:
                pids_to_check = [pid]
                try:
                    children_res = subprocess.run(["pgrep", "-P", str(pid)], stdout=subprocess.PIPE, text=True, timeout=0.3)
                    if children_res.returncode == 0:
                        for c_pid in children_res.stdout.splitlines():
                            if c_pid.strip():
                                pids_to_check.insert(0, int(c_pid.strip()))
                except Exception as _silent_e:
                    logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)

                for p in pids_to_check:
                    try:
                        cwd_link = os.readlink(f"/proc/{p}/cwd")
                        if os.path.exists(cwd_link):
                            return Path(cwd_link)
                    except Exception as _silent_e:
                        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
    return None

def detect_and_attach_local_files(prompt: str, extra_cwd: Optional[Path] = None) -> Tuple[Optional[str], list[Path]]:
    """
    Detecta menções a arquivos ou pastas no prompt do usuário:
    1. Ignora se o prompt for uma ação rápida de tela (QUICK_ACTIONS) ou se referir explicitamente à tela.
    2. Caminhos explícitos (~/..., /..., ./..., ou com extensões de arquivo válidas).
    3. Menções explícitas a arquivos ou pastas com palavras-chave ("arquivo X", "pasta Y").
    """
    if not prompt:
        return None, []

    prompt_lower = prompt.lower().strip()

    # Se for uma ação rápida de análise de tela, não anexa pastas locais
    if any(prompt.strip() == qa.strip() for qa in config.QUICK_ACTIONS.values()):
        return None, []

    if any(kw in prompt_lower for kw in ["nesta tela", "desta tela", "na tela", "da tela", "no print", "do print", "da captura", "na captura"]):
        return None, []

    import re
    attached_contexts = []
    found_paths = []
    
    # 1. Correspondências diretas por regex de caminhos e arquivos com extensão
    pattern = r"(?:(?:~|\/|\.\/|\.\.\/)[^\s\'\"`\(\)\[\]\{\},;]+|[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9_\-]+)"
    for m in re.findall(pattern, prompt):
        m_clean = m.strip("`'\"()[]{}.,;")
        if m_clean.lower() in [".", "..", "/", "~", "...", "py", "sh", "conf", "json", "md", "txt", "ia", "pdf", "csv", "png", "jpg", "jpeg", "webp"]:
            continue
        try:
            p = Path(m_clean).expanduser()
            if not p.is_absolute():
                candidates = [
                    (extra_cwd / p) if extra_cwd else None,
                    Path.cwd() / p,
                    Path.home() / p,
                    Path.home() / "Downloads" / "Telegram Desktop" / p,
                    Path.home() / "Downloads" / p,
                    Path.home() / "Documents" / p,
                    Path.home() / "Desktop" / p,
                    Path.home() / "Metis" / p,
                    Path.home() / ".config" / p,
                ]
                found = next((c for c in candidates if c and c.exists()), None)
                if found:
                    p = found

            if p.exists() and p not in found_paths:
                try:
                    from agente.utils import caminho_leitura_seguro
                    p_seguro = caminho_leitura_seguro(str(p), permitir_diretorio=True)
                except Exception:
                    continue

                if p_seguro.is_file():
                    content = format_file_context(p_seguro)
                    if not content.startswith("Acesso negado"):
                        attached_contexts.append(content)
                        found_paths.append(p_seguro)
                elif p_seguro.is_dir():
                    content = format_folder_context(p_seguro)
                    if not content.startswith("Acesso negado"):
                        attached_contexts.append(content)
                        found_paths.append(p_seguro)
        except Exception:
            continue

    # 2. Se o usuário explicitamente pediu para analisar/ler uma pasta ou arquivo pelo nome
    if not attached_contexts:
        indicadores = ["arquivo", "pasta", "diretorio", "diretório", "documento", "script", "planilha"]
        tem_indicador = any(ind in prompt_lower for ind in indicadores)
        
        if tem_indicador:
            stop_words = {
                "podia", "pode", "resumir", "resumo", "o", "que", "estava", "esta", "dentro", "do",
                "da", "de", "no", "na", "arquivo", "arquivos", "pasta", "pastas", "leia", "veja", "analise", "conteudo",
                "sobre", "qual", "quais", "e", "um", "uma", "me", "diga", "explique", "fale", "mostre",
                "tem", "la", "aqui", "por", "favor", "ia", "você", "voce", "texto", "textos", "tela", "telas",
                "codigo", "código", "imagem", "imagens", "print", "janela", "erro", "erros", "traduzir",
                "extrair", "transcreva", "importante", "contido", "comentarios", "adicionais"
            }
            
            words = [w.strip(".,;:?!\"'`()[]{}") for w in prompt_lower.split() if w.strip(".,;:?!\"'`()[]{}") not in stop_words and len(w) > 2]
            
            phrases = []
            for length in range(min(3, len(words)), 0, -1):
                for i in range(len(words) - length + 1):
                    phrase = " ".join(words[i:i+length])
                    if phrase not in phrases and len(phrase) >= 3:
                        phrases.append(phrase)

            search_dirs = [
                extra_cwd,
                Path.home() / "Downloads" / "Telegram Desktop",
                Path.home() / "Downloads",
                Path.home() / "Documents",
                Path.home() / "Desktop",
                Path.home() / "Metis",
                Path.home() / ".config",
                Path.cwd(),
                Path.home()
            ]

            found_target = None
            for base_dir in search_dirs:
                if not base_dir or not base_dir.exists():
                    continue
                base_path = base_dir.resolve()
                
                try:
                    candidates = [f for f in base_path.iterdir() if not f.name.startswith(".")]
                except Exception:
                    continue

                for phrase in phrases:
                    phrase_norm = phrase.replace("_", " ").replace("-", " ").strip()
                    if not phrase_norm or len(phrase_norm) < 3:
                        continue
                    for cand in candidates:
                        cand_stem = cand.stem.replace("_", " ").replace("-", " ").strip().lower()
                        cand_full = cand.name.replace("_", " ").replace("-", " ").strip().lower()
                        
                        # Correspondência exata de nome ou stem
                        if phrase_norm == cand_stem or phrase_norm == cand_full:
                            found_target = cand
                            break
                    if found_target:
                        break
                if found_target:
                    break

            if found_target and found_target.exists():
                if found_target.is_file():
                    content = format_file_context(found_target)
                    attached_contexts.append(content)
                    found_paths.append(found_target)
                elif found_target.is_dir():
                    content = format_folder_context(found_target)
                    attached_contexts.append(content)
                    found_paths.append(found_target)

    if attached_contexts:
        return "\n\n".join(attached_contexts), found_paths
    return None, []

def detect_save_target_path(prompt: str, extra_cwd: Optional[Path] = None) -> Optional[Path]:
    """
    Detecta se o usuário pediu para salvar a resposta em um arquivo específico.
    Exemplos:
      - "salve em ~/resumo.md"
      - "salve no arquivo ./output.txt"
      - "salvar em /tmp/notas.txt"
      - "salve como relatorio.md"
    """
    import re
    patterns = [
        r"salv(?:ar|e|ando)\s+(?:em|no\s+arquivo|na|no|como)\s+([~/\.a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9_\-]+)",
        r"salv(?:ar|e|ando)\s+(?:em|no\s+arquivo|na|no|como)\s+([~/\.][^\s]+)",
        r"save\s+(?:to|in|as)\s+([~/\.a-zA-Z0-9_\-\./\\]+)",
    ]
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            raw_path = m.group(1).strip("`'\",;:")
            try:
                p = Path(raw_path).expanduser()
                if not p.is_absolute():
                    base = extra_cwd or Path.cwd()
                    p = (base / raw_path).resolve()
                return p
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
    return None

if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(format_folder_context(target))
