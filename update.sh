#!/usr/bin/env bash
# =============================================================================
# METIS AI SUITE - ATUALIZADOR AUTOMÁTICO
# =============================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${YELLOW}${BOLD}🔄 Atualizando Metis & ZSH AI Suite...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/metis"

# Se estiver em repositório Git, puxa as novidades
if [ -d "$SCRIPT_DIR/.git" ]; then
    echo "📡 Baixando atualizações do Git..."
    cd "$SCRIPT_DIR"
    git pull --quiet
fi

# Atualiza os arquivos instalados
if [ -d "$INSTALL_DIR" ]; then
    echo "📂 Atualizando arquivos em $INSTALL_DIR..."
    cp -r "$SCRIPT_DIR/app" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/zsh" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/bin" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
    
    BIN_DIR="$HOME/.local/bin"
    APPS_DIR="$HOME/.local/share/applications"
    ICONS_DIR="$HOME/.local/share/icons/hicolor"
    mkdir -p "$BIN_DIR" "$APPS_DIR" "$ICONS_DIR/128x128/apps" "$ICONS_DIR/256x256/apps" "$ICONS_DIR/512x512/apps"

    ln -sf "$INSTALL_DIR/bin/metis" "$BIN_DIR/metis"
    ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/metis-vision"
    ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/screenai"

    # Atualiza ícones do sistema
    if [ -f "$INSTALL_DIR/assets/icons/icon_128x128.png" ]; then
        cp "$INSTALL_DIR/assets/icons/icon_128x128.png" "$ICONS_DIR/128x128/apps/metis-vision.png"
        cp "$INSTALL_DIR/assets/icons/icon_256x256.png" "$ICONS_DIR/256x256/apps/metis-vision.png" 2>/dev/null || true
        cp "$INSTALL_DIR/assets/icons/icon_256x256.png" "$ICONS_DIR/256x256/apps/metis_app_icon.png" 2>/dev/null || true
        command -v gtk-update-icon-cache &>/dev/null && gtk-update-icon-cache -f -t "$ICONS_DIR" 2>/dev/null || true
    fi

    # Atualiza Desktop Entries
    if [ -f "$SCRIPT_DIR/assets/metis.desktop" ]; then
        cp "$SCRIPT_DIR/assets/metis.desktop" "$APPS_DIR/metis.desktop"
    fi
    if [ -f "$SCRIPT_DIR/assets/metis-vision.desktop" ]; then
        cp "$SCRIPT_DIR/assets/metis-vision.desktop" "$APPS_DIR/metis-vision.desktop"
    fi
    command -v update-desktop-database &>/dev/null && update-desktop-database "$APPS_DIR" 2>/dev/null || true

    echo "🐍 Atualizando dependências no venv..."
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --upgrade --quiet
fi

echo -e "\n${GREEN}${BOLD}✅ Metis AI Suite atualizado com sucesso!${NC}"
echo "ℹ️ Suas configurações em ~/.config/metis/ foram mantidas intactas."
