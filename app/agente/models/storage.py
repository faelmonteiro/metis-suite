"""
Armazenamento atômico para config_models.json.
Single source of truth: ~/.config/metis/config_models.json
"""
import copy as _copy
import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.getenv("METIS_CONFIG_DIR", Path.home() / ".config" / "metis"))
CONFIG_FILE = CONFIG_DIR / "config_models.json"

# Serializa leitura-modificação-escrita do config_models.json entre threads.
_config_lock = threading.RLock()
# Cache de leitura, invalidado por mtime do arquivo (evita re-parses em cada request).
_config_cache: Optional[Tuple[Optional[int], Dict[str, Any]]] = None


def _legacy_config_paths() -> List[Path]:
    """Caminhos de cópias legadas do config dentro do repositório."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return [
        repo_root / "vision" / "config_models.json",
        repo_root / "config_models.json",
    ]


def purge_model_from_legacy_files(model_id: str) -> int:
    """
    Remove `model_id` de todas as cópias legadas do config ao apagar um modelo,
    para que exclusões sejam definitivas e não deixem sobras em outros arquivos.

    Só age quando o config em uso é o padrão de produção (~/.config/metis);
    em execuções isoladas (METIS_CONFIG_DIR alternativo) não toca arquivos reais.
    """
    if CONFIG_FILE.parent != Path.home() / ".config" / "metis":
        return 0

    if not model_id:
        return 0
    needle = model_id.strip().lower()

    changed_total = 0
    for path in _legacy_config_paths():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        changed = False

        # builtin_models
        bmodels = data.get("builtin_models")
        if isinstance(bmodels, dict):
            for key in list(bmodels.keys()):
                new_list = [m for m in bmodels[key] if str(m).strip().lower() != needle]
                if len(new_list) != len(bmodels[key]):
                    bmodels[key] = new_list
                    changed = True

        # custom_servers
        for srv in data.get("custom_servers", []):
            mods = srv.get("modelos", [])
            new_mods = [m for m in mods if str(m).strip().lower() != needle]
            if len(new_mods) != len(mods):
                srv["modelos"] = new_mods
                changed = True
            if str(srv.get("modelo_atual", "")).strip().lower() == needle:
                srv["modelo_atual"] = new_mods[0] if new_mods else ""
                changed = True

        # removed_models (legado v1): limpa a mesma referência
        rm = data.get("removed_models")
        if isinstance(rm, dict):
            for key in list(rm.keys()):
                nrm = [m for m in rm[key] if str(m).strip().lower() != needle]
                if len(nrm) != len(rm[key]):
                    rm[key] = nrm
                    changed = True
                if not rm[key]:
                    del rm[key]
                    changed = True

        if changed:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
            changed_total += 1

    return changed_total

DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": 2,
    "builtin_models": {},
    "custom_servers": [],
    "preferences": {
        "active_model": "",
        "active_models": {},
        "theme_id": "metis_oracle",
        "font_size": "medium",
        "font_family": "default",
        "window_opacity": 95,
        "neon_glow": True,
        "copy_btn": True,
    },
    "removed_servers": [],
}


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Carrega configuração do arquivo canônico.

    Faz cache do resultado e invalida por mtime: chamadas repetidas entre
    escritas não re-leem/parseiam o arquivo. Use `force_reload=True` para
    ignorar o cache. Retorna config padrão se o arquivo não existir;
    se estiver corrompido, registra um warning (em vez de falhar em silêncio).
    """
    _ensure_config_dir()

    global _config_cache
    with _config_lock:
        if not CONFIG_FILE.exists():
            _config_cache = None
            return dict(DEFAULT_CONFIG)

        try:
            mtime = CONFIG_FILE.stat().st_mtime_ns
        except OSError:
            mtime = None

        if not force_reload and _config_cache is not None and _config_cache[0] == mtime:
            return _copy.deepcopy(_config_cache[1])

        try:
            content = CONFIG_FILE.read_text(encoding="utf-8")
            data = json.loads(content)

            # Migra schema v1 -> v2 se necessário
            if data.get("schema_version", 1) < 2:
                data = _migrate_v1_to_v2(data)

            result = _merge_with_defaults(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("config_models.json ilegível (%s); usando defaults", exc)
            return dict(DEFAULT_CONFIG)

        _config_cache = (mtime, result)
        return _copy.deepcopy(result)


def save_config(data: Dict[str, Any]) -> None:
    """
    Salva configuração com escrita atômica (tempfile + os.replace).
    Thread-safe (lock de escrita) e resistente a falhas de energia.
    Exceções de I/O NÃO são engolidas: propagam para o chamador.
    """
    _ensure_config_dir()

    # Garante schema_version
    data["schema_version"] = 2

    content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)

    with _config_lock:
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=str(CONFIG_DIR))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(CONFIG_FILE))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
            raise

    global _config_cache
    with _config_lock:
        try:
            _config_cache = (CONFIG_FILE.stat().st_mtime_ns, _copy.deepcopy(data))
        except OSError:
            _config_cache = None


def _migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migra config v1 (sem schema_version ou v1) para v2."""
    migrated = dict(DEFAULT_CONFIG)

    # Preserva builtin_models
    if "builtin_models" in data:
        migrated["builtin_models"] = data["builtin_models"]

    # Preserva custom_servers
    if "custom_servers" in data:
        migrated["custom_servers"] = data["custom_servers"]

    # Preserva preferences
    if "preferences" in data:
        migrated["preferences"].update(data["preferences"])

    # Preserva removed_servers (não removed_models - que é dict provider->models)
    removed_servers = data.get("removed_servers") or []
    migrated["removed_servers"] = [str(s).strip().lower() for s in removed_servers]

    return migrated


def _merge_with_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """Garante que todas as chaves padrão existam no dict carregado."""
    result = dict(DEFAULT_CONFIG)
    result.update(data)

    # Deep merge para dicts aninhados
    if "preferences" in data:
        result["preferences"].update(data["preferences"])

    return result