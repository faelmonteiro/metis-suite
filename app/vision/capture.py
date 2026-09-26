"""
Módulo de Captura e Otimização de Imagem para Wayland / Hyprland e X11.
Realiza capturas ultrarrápidas em memória e otimiza para envio a modelos de visão.
"""

import logging
logger = logging.getLogger(__name__)


import io
import json
import os
import shutil
import subprocess
from typing import Optional
from PIL import Image
from . import config

def is_wayland() -> bool:
    return bool(os.getenv("WAYLAND_DISPLAY") or os.getenv("XDG_SESSION_TYPE") == "wayland")

def get_active_window_geometry() -> Optional[str]:
    """Retorna as coordenadas 'X,Y WxH' da janela ativa no Hyprland."""
    if not shutil.which("hyprctl"):
        return None
    try:
        res = subprocess.run(["hyprctl", "activewindow", "-j"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            at = data.get("at")
            size = data.get("size")
            if at and size and len(at) == 2 and len(size) == 2:
                return f"{at[0]},{at[1]} {size[0]}x{size[1]}"
    except Exception as _silent_e:
        logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
    return None

def capture_screen(mode: str = "fullscreen") -> bytes:
    """
    Captura a tela do sistema.
    Modos suportados:
      - 'fullscreen': Tela inteira
      - 'active_window': Janela atualmente focada (Hyprland)
      - 'region': Seleção manual de retângulo pelo usuário (via slurp)
    Retorna os bytes da imagem comprimida (JPEG).
    """
    cmd = []
    
    if is_wayland():
        if not shutil.which("grim"):
            raise RuntimeError("A ferramenta 'grim' é necessária para capturas no Wayland. Instale com: sudo pacman -S grim")
        
        geom = None
        if mode == "active_window":
            geom = get_active_window_geometry()
        elif mode == "region":
            if not shutil.which("slurp"):
                raise RuntimeError("A ferramenta 'slurp' é necessária para seleção de área. Instale com: sudo pacman -S slurp")
            slurp_res = subprocess.run(["slurp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            region = slurp_res.stdout.strip()
            if not region:
                raise ValueError("Seleção de área cancelada pelo usuário.")
            geom = region
            
        cmd = ["grim"]
        if geom:
            cmd.extend(["-g", geom])
        cmd.extend(["-t", "jpeg", "-q", str(config.IMAGE_JPEG_QUALITY), "-"])
            
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"Falha ao capturar tela com grim: {res.stderr.decode('utf-8', errors='ignore')}")
        raw_bytes = res.stdout

        # grim já entrega JPEG com qualidade desejada - só redimensiona se necessário
        img = Image.open(io.BytesIO(raw_bytes))
        w, h = img.size
        max_dim = config.IMAGE_MAX_DIMENSION
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=config.IMAGE_JPEG_QUALITY, optimize=True)
            raw_bytes = buf.getvalue()
        return raw_bytes

    else:
        # Fallback para X11 com import/scrot ou PIL ImageGrab
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]  # Monitor 0 cobre toda a área de trabalho
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except ImportError:
            from PIL import ImageGrab
            img = ImageGrab.grab()

        # Redimensiona se necessário, senão salva JPEG direto
        w, h = img.size
        max_dim = config.IMAGE_MAX_DIMENSION
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=config.IMAGE_JPEG_QUALITY, optimize=True)
        return buf.getvalue()

def optimize_image_bytes(image_bytes: bytes) -> bytes:
    """Redimensiona para no máximo IMAGE_MAX_DIMENSION mantendo a proporção."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    max_dim = config.IMAGE_MAX_DIMENSION
    
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
    buf = io.BytesIO()
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=config.IMAGE_JPEG_QUALITY, optimize=True)
    return buf.getvalue()

if __name__ == "__main__":
    print("Testando captura de tela...")
    data = capture_screen("fullscreen")
    print(f"Sucesso! Imagem capturada em memória: {len(data) / 1024:.1f} KB")
