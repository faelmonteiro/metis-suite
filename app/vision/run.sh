#!/usr/bin/env bash
# ==============================================================================
# Script de execução rápida para o ScreenAI (Atalho no Hyprland / Sistema)
# ==============================================================================

SCRIPT_PATH="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_PATH" ]; do
    DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
    [[ $SCRIPT_PATH != /* ]] && SCRIPT_PATH="$DIR/$SCRIPT_PATH"
done
DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"

if [ -f "$DIR/.venv/bin/python" ]; then
    VENV_PYTHON="$DIR/.venv/bin/python"
elif [ -n "$METIS_INSTALL_DIR" ] && [ -f "$METIS_INSTALL_DIR/venv/bin/python" ]; then
    VENV_PYTHON="$METIS_INSTALL_DIR/venv/bin/python"
elif [ -f "$HOME/.local/share/metis/venv/bin/python" ]; then
    VENV_PYTHON="$HOME/.local/share/metis/venv/bin/python"
elif [ -f "$DIR/../../venv/bin/python" ]; then
    VENV_PYTHON="$DIR/../../venv/bin/python"
elif [ -f "$DIR/../venv/bin/python" ]; then
    VENV_PYTHON="$DIR/../venv/bin/python"
else
    VENV_PYTHON="$DIR/.venv/bin/python"
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Ambiente virtual não encontrado. Criando e instalando dependências..."
    cd "$DIR"
    if command -v uv >/dev/null 2>&1; then
        uv venv .venv
        source .venv/bin/activate
        uv pip install -r requirements.txt
    else
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    fi
fi

# Se não for modo headless, encerra instâncias anteriores para evitar janelas presas
if [[ "$*" != *"--headless"* ]]; then
    pkill -f "$DIR/main.py" 2>/dev/null || true
fi

# Executa o assistente passando todos os argumentos recebidos
exec "$VENV_PYTHON" "$DIR/main.py" "$@"

