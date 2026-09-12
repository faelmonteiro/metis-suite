#!/usr/bin/env bash
# =============================================================================
# METIS AI SUITE - DESINSTALADOR LIMPO
# =============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${RED}${BOLD}"
echo "  __  __      _   _         _    ___ "
echo " |  \/  | ___| |_(_)___    / \  |_ _|"
echo " | |\/| |/ _ \ __| / __|  / _ \  | | "
echo " | |  | |  __/ |_| \__ \ / ___ \ | | "
echo " |_|  |_|\___|\__|_|___//_/   \_\___|"
echo -e "${NC}"
echo -e "${BOLD}Desinstalador do Metis & ZSH AI Suite${NC}"
echo "---------------------------------------------------------"

INSTALL_DIR="$HOME/.local/share/metis"
CONFIG_DIR="$HOME/.config/metis"
BIN_FILE="$HOME/.local/bin/metis"
SCREENAI_BIN="$HOME/.local/bin/screenai"
METIS_VISION_BIN="$HOME/.local/bin/metis-vision"
DESKTOP_FILE="$HOME/.local/share/applications/metis.desktop"
VISION_DESKTOP_FILE="$HOME/.local/share/applications/metis-vision.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/256x256/apps/metis_app_icon.png"
VISION_ICON_FILE="$HOME/.local/share/icons/hicolor/128x128/apps/metis-vision.png"
ZSHRC="$HOME/.zshrc"

# 1. Remover integração do ~/.zshrc e ~/.bashrc
if [ -f "$ZSHRC" ]; then
    echo -e "${YELLOW}🧹 Removendo integração do $ZSHRC...${NC}"
    cp "$ZSHRC" "${ZSHRC}.metis_backup" 2>/dev/null || true
    sed -i '/# >>> METIS SUITE >>>/,/# <<< METIS SUITE <<</d' "$ZSHRC"
    sed -i '/# --- \[ Metis AI Suite \] ---/d' "$ZSHRC"
    sed -i '/metis\/zsh\/loader.zsh/d' "$ZSHRC"
    echo -e "${GREEN}✅ Linhas do Metis removidas do $ZSHRC.${NC}"
fi

BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    echo -e "${YELLOW}🧹 Removendo integração do $BASHRC...${NC}"
    cp "$BASHRC" "${BASHRC}.metis_backup" 2>/dev/null || true
    sed -i '/# >>> METIS SUITE >>>/,/# <<< METIS SUITE <<</d' "$BASHRC"
    sed -i '/# >>> METIS ZSH AUTO-LAUNCH >>>/,/# <<< METIS ZSH AUTO-LAUNCH <<</d' "$BASHRC"
    sed -i '/# --- \[ Metis AI Suite \] ---/d' "$BASHRC"
    sed -i '\|'"$INSTALL_DIR"'|d' "$BASHRC"
    sed -i '/export PATH=".*\.local\/bin:\$PATH"/d' "$BASHRC" 2>/dev/null || true
    echo -e "${GREEN}✅ Linhas do Metis removidas do $BASHRC.${NC}"
fi

# 1.2 Remover integração do Kitty se presente
KITTY_CONF="$HOME/.config/kitty/kitty.conf"
if [ -f "$KITTY_CONF" ] && grep -Fq "explain_screen.zsh" "$KITTY_CONF"; then
    echo -e "${YELLOW}🧹 Removendo atalho do explain_screen em $KITTY_CONF...${NC}"
    cp "$KITTY_CONF" "${KITTY_CONF}.metis_backup" 2>/dev/null || true
    sed -i '/# --- \[ Metis Explain Screen (Ctrl + Shift + E) \] ---/d' "$KITTY_CONF"
    sed -i '/explain_screen\.zsh/d' "$KITTY_CONF"
    echo -e "${GREEN}✅ Atalho do explain_screen removido do Kitty.${NC}"
fi


# 1.5 Remover atalho global do sistema operacional
desktop="${XDG_CURRENT_DESKTOP:-$DESKTOP_SESSION}"
desktop="$(echo "$desktop" | tr '[:upper:]' '[:lower:]')"

if [[ "$desktop" == *"gnome"* || "$desktop" == *"ubuntu"* || "$desktop" == *"pop"* ]] && command -v gsettings &>/dev/null; then
    base_schema="org.gnome.settings-daemon.plugins.media-keys"
    custom_path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-metis/"
    screenai_path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-screenai/"
    current_list=$(gsettings get "$base_schema" custom-keybindings 2>/dev/null || echo "")
    if [[ "$current_list" == *"$custom_path"* || "$current_list" == *"$screenai_path"* ]]; then
        new_list=$(echo "$current_list" | sed "s|'$custom_path', ||; s|, '$custom_path'||; s|'$custom_path'||; s|'$screenai_path', ||; s|, '$screenai_path'||; s|'$screenai_path'||")
        gsettings set "$base_schema" custom-keybindings "$new_list" 2>/dev/null || true
    fi
fi

if [[ "$desktop" == *"cinnamon"* || "$desktop" == *"x-cinnamon"* ]] && command -v dconf &>/dev/null; then
    dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/ 2>/dev/null || true
    dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/ 2>/dev/null || true
    dconf reset -f /org/cinnamon/desktop/keybindings/custom-screenai/ 2>/dev/null || true
    list=$(dconf read /org/cinnamon/desktop/keybindings/custom-list 2>/dev/null || echo "")
    if [[ "$list" == *"custom-metis"* || "$list" == *"custom-screenai"* ]]; then
        new_l=$(echo "$list" | sed "s/'custom-metis', //; s/, 'custom-metis'//; s/'custom-metis'//; s/'custom-screenai', //; s/, 'custom-screenai'//; s/'custom-screenai'//")
        dconf write /org/cinnamon/desktop/keybindings/custom-list "$new_l" 2>/dev/null || true
    fi
fi

if [[ "$desktop" == *"xfce"* ]] && command -v xfconf-query &>/dev/null; then
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -r 2>/dev/null || true
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>z" -r 2>/dev/null || true
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt>v" -r 2>/dev/null || true
fi

if [ -f "$HOME/.config/hypr/hyprland.conf" ]; then
    sed -i '/Metis AI GUI Shortcut/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
    sed -i '/bind.*metis gui/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
    sed -i '/bind.*screenai/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
    sed -i '/bind.*metis vision/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
fi

if [ -f "$HOME/.config/i3/config" ]; then
    sed -i '/bindsym.*metis gui/d' "$HOME/.config/i3/config" 2>/dev/null || true
    sed -i '/bindsym.*screenai/d' "$HOME/.config/i3/config" 2>/dev/null || true
    sed -i '/bindsym.*metis vision/d' "$HOME/.config/i3/config" 2>/dev/null || true
fi

# 2. Remover arquivos da aplicação e venv
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}📂 Removendo arquivos de $INSTALL_DIR...${NC}"
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✅ Diretório de instalação removido.${NC}"
fi

# 3. Remover executável do PATH e Desktop Entry
[ -f "$BIN_FILE" ] && rm -f "$BIN_FILE"
[ -f "$SCREENAI_BIN" ] && rm -f "$SCREENAI_BIN"
[ -f "$METIS_VISION_BIN" ] && rm -f "$METIS_VISION_BIN"
[ -f "$DESKTOP_FILE" ] && rm -f "$DESKTOP_FILE"
[ -f "$VISION_DESKTOP_FILE" ] && rm -f "$VISION_DESKTOP_FILE"

# Remover da Área de Trabalho se existir
for d in "$HOME/Desktop" "$HOME/Área de trabalho" "$(xdg-user-dir DESKTOP 2>/dev/null)"; do
    [ -f "$d/metis.desktop" ] && rm -f "$d/metis.desktop"
    [ -f "$d/metis-vision.desktop" ] && rm -f "$d/metis-vision.desktop"
done

[ -f "$ICON_FILE" ] && rm -f "$ICON_FILE"
[ -f "$VISION_ICON_FILE" ] && rm -f "$VISION_ICON_FILE"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

if [ -f "$HOME/.local/share/fonts/MetisIcons.ttf" ]; then
    rm -f "$HOME/.local/share/fonts/MetisIcons.ttf"
    command -v fc-cache &>/dev/null && fc-cache -f "$HOME/.local/share/fonts" 2>/dev/null || true
fi

# 4. Perguntar sobre configurações e chaves de API
if [ -d "$CONFIG_DIR" ]; then
    echo ""
    read -p "❓ Deseja também apagar suas chaves e configurações em $CONFIG_DIR? (s/N): " resposta
    case "$resposta" in
        [sS][iI][mM]|[sS])
            echo -e "${YELLOW}🗑️  Apagando pasta de configurações...${NC}"
            rm -rf "$CONFIG_DIR"
            echo -e "${GREEN}✅ Configurações removidas.${NC}"
            ;;
        *)
            echo -e "${GREEN}ℹ️  Configurações preservadas em $CONFIG_DIR.${NC}"
            ;;
    esac
fi

echo -e "\n${GREEN}${BOLD}✅ Metis AI Suite foi desinstalado com sucesso do seu sistema!${NC}"
echo "Para aplicar a remoção no terminal atual, reinicie o terminal ou rode: exec zsh"
