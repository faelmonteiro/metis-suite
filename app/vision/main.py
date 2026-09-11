"""
Ponto de entrada principal do ScreenAI.
Suporta modos interativos (Overlay HUD), headless (Terminal) e atalhos rápidos do sistema.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import config
from capture import capture_screen
from ai_engine import VisionAIEngine

from folder_analyzer import format_folder_context, format_file_context

def parse_args():
    parser = argparse.ArgumentParser(description="ScreenAI • Assistente Visual de Tela com IA")
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Caminho opcional de uma pasta ou arquivo local para analisar"
    )
    parser.add_argument(
        "--mode",
        choices=["fullscreen", "active_window", "region"],
        default="fullscreen",
        help="Modo de captura de tela (padrão: fullscreen)"
    )
    parser.add_argument(
        "--action",
        choices=list(config.QUICK_ACTIONS.keys()),
        default=None,
        help="Executa diretamente uma ação pré-configurada (resumo, explicar, traduzir, extrair)"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Prompt personalizado a ser enviado para a IA"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa em modo linha de comando (sem abrir a interface gráfica)"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Envia a resposta como notificação do desktop (notify-send)"
    )
    parser.add_argument(
        "--provider",
        choices=["nvidia", "gemini", "openrouter", "ollama", "groq"],
        default=None,
        help="Sobrescreve o provedor de IA configurado"
    )
    return parser.parse_args()

def run_headless(args):
    prompt = args.prompt
    if not prompt and args.action:
        prompt = config.QUICK_ACTIONS.get(args.action)
    if not prompt:
        prompt = config.QUICK_ACTIONS["resumo"]

    engine = VisionAIEngine(provider=args.provider)
    chunks = []

    try:
        if args.target:
            target_path = Path(args.target).resolve()
            if target_path.is_dir():
                print(f"📁 Varrendo pasta: {target_path}...")
                context = format_folder_context(target_path)
            elif target_path.is_file():
                print(f"📄 Lendo arquivo: {target_path}...")
                context = format_file_context(target_path)
            else:
                print(f"⚠️ Caminho não encontrado: {args.target}")
                return

            print(f"🧠 Processando via {engine.provider.upper()} ({engine.model})...\n")
            for chunk in engine.analyze_text_stream(prompt, context=context):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print("\n")
        else:
            print(f"📸 Capturando tela (Modo: {args.mode})...")
            img_data = capture_screen(args.mode)
            print(f"🧠 Processando via {engine.provider.upper()} ({engine.model})...\n")
            for chunk in engine.analyze_stream(img_data, prompt):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print("\n")
    except Exception as e:
        print(f"\n⚠️ Erro durante a geração: {e}", file=sys.stderr)
        return

    full_text = "".join(chunks)
    if args.notify and shutil.which("notify-send"):
        icon_path = Path(__file__).parent / "assets" / "icon_128x128.png"
        if not icon_path.exists():
            for fallback in [
                Path(__file__).parent.parent / "assets" / "icons" / "icon_128x128.png",
                Path(__file__).parent.parent.parent / "assets" / "icons" / "icon_128x128.png",
            ]:
                if fallback.exists():
                    icon_path = fallback
                    break
        icon_arg = ["-i", str(icon_path)] if icon_path.exists() else []
        subprocess.run(["notify-send", *icon_arg, "✨ Metis Vision", full_text[:400] + "..."])

def main():
    args = parse_args()
    
    if args.headless or args.notify:
        run_headless(args)
    else:
        # Modo Interface Gráfica Flutuante
        from ui import run_app
        sys.exit(run_app(capture_mode=args.mode, target_path=args.target))

if __name__ == "__main__":
    main()
