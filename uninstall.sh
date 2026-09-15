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


# 1.5 Remover atalhos globais do sistema operacional se existirem
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ -S "/run/user/$UID/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$UID/bus"
fi

python3 -c "
import os, re, subprocess

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

# 1. GNOME
base_schema = 'org.gnome.settings-daemon.plugins.media-keys'
base_path = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/'
cur_raw = run_cmd(f'gsettings get {base_schema} custom-keybindings 2>/dev/null')
if not cur_raw or '@as []' in cur_raw or 'no such schema' in cur_raw.lower():
    cur_raw = run_cmd(f'dconf read {base_path} 2>/dev/null') or '[]'

items = re.findall(r'/custom-keybindings/(custom\d+)/', cur_raw)
valid_slots = list(dict.fromkeys(items))
keep_slots = []
for s in valid_slots:
    p = f'{base_path}{s}/'
    c = run_cmd(f'dconf read {p}command 2>/dev/null').strip(\"'\\\"\")
    n = run_cmd(f'dconf read {p}name 2>/dev/null').strip(\"'\\\"\")
    if 'metis' in c.lower() or 'screenai' in c.lower() or 'metis' in n.lower():
        run_cmd(f'dconf reset -f {p}')
    else:
        keep_slots.append(s)

if len(keep_slots) != len(valid_slots):
    final_list = '[' + ', '.join([f\"'{base_path}{s}/'\" for s in keep_slots]) + ']'
    run_cmd(f'gsettings set {base_schema} custom-keybindings \"{final_list}\" 2>/dev/null')
    run_cmd(f'dconf write {base_path} \"{final_list}\" 2>/dev/null')

run_cmd('dconf reset -f /org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-metis/ 2>/dev/null')
run_cmd('dconf reset -f /org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-screenai/ 2>/dev/null')

# 2. Cinnamon
cur_raw_c = run_cmd('gsettings get org.cinnamon.desktop.keybindings custom-list 2>/dev/null')
if not cur_raw_c or '@as []' in cur_raw_c or 'no such schema' in cur_raw_c.lower():
    cur_raw_c = run_cmd('dconf read /org/cinnamon/desktop/keybindings/custom-list 2>/dev/null') or '[]'

items_c = re.findall(r'[\'\"]([^\'\"]+)[\'\"]', cur_raw_c)
valid_slots_c = [s for s in items_c if re.match(r'^custom\d+$', s)]
keep_slots_c = []
for s in valid_slots_c:
    p = f'/org/cinnamon/desktop/keybindings/custom-keybindings/{s}/'
    c = run_cmd(f'dconf read {p}command 2>/dev/null').strip(\"'\\\"\")
    n = run_cmd(f'dconf read {p}name 2>/dev/null').strip(\"'\\\"\")
    if 'metis' in c.lower() or 'screenai' in c.lower() or 'metis' in n.lower():
        run_cmd(f'dconf reset -f {p}')
    else:
        keep_slots_c.append(s)

if len(keep_slots_c) != len(valid_slots_c):
    final_list_c = '[' + ', '.join([f\"'{s}'\" for s in keep_slots_c]) + ']'
    run_cmd(f'gsettings set org.cinnamon.desktop.keybindings custom-list \"{final_list_c}\" 2>/dev/null')
    run_cmd(f'dconf write /org/cinnamon/desktop/keybindings/custom-list \"{final_list_c}\" 2>/dev/null')

run_cmd('dconf reset -f /org/cinnamon/desktop/keybindings/custom-metis/ 2>/dev/null')
run_cmd('dconf reset -f /org/cinnamon/desktop/keybindings/custom-screenai/ 2>/dev/null')
run_cmd('dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/ 2>/dev/null')
run_cmd('dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/ 2>/dev/null')
" 2>/dev/null || true

# KDE
if [ -f "$HOME/.config/kglobalshortcutsrc" ]; then
    python3 -c "
import configparser, os
p = os.path.expanduser('~/.config/kglobalshortcutsrc')
cfg = configparser.ConfigParser(interpolation=None)
try:
    cfg.read(p, encoding='utf-8')
    modified = False
    for sec in list(cfg.sections()):
        if any(k in sec.lower() for k in ['metis', 'screenai']):
            cfg.remove_section(sec)
            modified = True
    if modified:
        with open(p, 'w', encoding='utf-8') as f:
            cfg.write(f)
except Exception:
    pass
" 2>/dev/null || true
fi

# XFCE
if command -v xfconf-query &>/dev/null; then
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -r 2>/dev/null || true
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>z" -r 2>/dev/null || true
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>v" -r 2>/dev/null || true
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt>v" -r 2>/dev/null || true
fi

# Window Managers
[ -f "$HOME/.config/hypr/hyprland.conf" ] && sed -i '/[Mm]etis/d; /screenai/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
[ -f "$HOME/.config/sway/config" ] && sed -i '/[Mm]etis/d; /screenai/d' "$HOME/.config/sway/config" 2>/dev/null || true
[ -f "$HOME/.config/i3/config" ] && sed -i '/[Mm]etis/d; /screenai/d' "$HOME/.config/i3/config" 2>/dev/null || true
[ -f "$HOME/.xbindkeysrc" ] && sed -i '/# --- \[ Metis AI Suite \] ---/,/metis vision/d; /metis gui/d; /metis vision/d' "$HOME/.xbindkeysrc" 2>/dev/null || true

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
