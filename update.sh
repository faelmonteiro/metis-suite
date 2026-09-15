#!/usr/bin/env bash
# =============================================================================
# METIS AI SUITE - ATUALIZADOR AUTOMÁTICO
# =============================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${YELLOW}${BOLD}🔄 Atualizando Metis & ZSH AI Suite...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/metis"
CONFIG_DIR="$HOME/.config/metis"
REPO_URL="https://github.com/faelmonteiro/metis-suite.git"

CLEANUP_TEMP=0
SOURCE_DIR=""

# 1. Identifica a origem das atualizações
if [ -d "$SCRIPT_DIR/.git" ]; then
    echo -e "  ${CYAN}📡 Atualizando repositório Git local em $SCRIPT_DIR...${NC}"
    cd "$SCRIPT_DIR"
    git pull --quiet 2>/dev/null || git pull
    SOURCE_DIR="$SCRIPT_DIR"
elif [ -d "$HOME/metis-suite/.git" ]; then
    echo -e "  ${CYAN}📡 Atualizando repositório Git em $HOME/metis-suite...${NC}"
    cd "$HOME/metis-suite"
    git pull --quiet 2>/dev/null || git pull
    SOURCE_DIR="$HOME/metis-suite"
elif [ -d "$HOME/.metis-suite/.git" ]; then
    echo -e "  ${CYAN}📡 Atualizando repositório Git em $HOME/.metis-suite...${NC}"
    cd "$HOME/.metis-suite"
    git pull --quiet 2>/dev/null || git pull
    SOURCE_DIR="$HOME/.metis-suite"
else
    echo -e "  ${CYAN}📡 Baixando versão mais recente do GitHub...${NC}"
    TEMP_DIR="$(mktemp -d)/metis-suite-update"
    git clone --depth 1 "$REPO_URL" "$TEMP_DIR" --quiet || {
        echo -e "${RED}❌ Falha ao clonar do GitHub. Verifique sua conexão com a internet.${NC}"
        exit 1
    }
    SOURCE_DIR="$TEMP_DIR"
    CLEANUP_TEMP=1
fi

# 2. Atualiza os arquivos instalados
if [ -d "$INSTALL_DIR" ]; then
    echo -e "  ${CYAN}📂 Atualizando arquivos em $INSTALL_DIR...${NC}"

    # Backup preventivo de configurações legadas (caso existam em app/)
    BACKUP_TMP="$(mktemp -d)"
    [ -f "$INSTALL_DIR/app/.env" ] && cp "$INSTALL_DIR/app/.env" "$BACKUP_TMP/.env"
    [ -f "$INSTALL_DIR/app/config_models.json" ] && cp "$INSTALL_DIR/app/config_models.json" "$BACKUP_TMP/config_models.json"

    cp -r "$SOURCE_DIR/app" "$INSTALL_DIR/"
    cp -r "$SOURCE_DIR/zsh" "$INSTALL_DIR/"
    cp -r "$SOURCE_DIR/bash" "$INSTALL_DIR/"
    cp -r "$SOURCE_DIR/bin" "$INSTALL_DIR/"
    cp -r "$SOURCE_DIR/assets" "$INSTALL_DIR/"
    cp "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/"
    cp "$SOURCE_DIR/pyproject.toml" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SOURCE_DIR/update.sh" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SOURCE_DIR/uninstall.sh" "$INSTALL_DIR/" 2>/dev/null || true

    # Restaura configurações legadas se existiam
    [ -f "$BACKUP_TMP/.env" ] && cp "$BACKUP_TMP/.env" "$INSTALL_DIR/app/.env"
    [ -f "$BACKUP_TMP/config_models.json" ] && cp "$BACKUP_TMP/config_models.json" "$INSTALL_DIR/app/config_models.json"
    rm -rf "$BACKUP_TMP"

    # Garante migração para o diretório canônico ~/.config/metis se necessário
    mkdir -p "$CONFIG_DIR"
    if [ ! -f "$CONFIG_DIR/config_models.json" ]; then
        if [ -f "$INSTALL_DIR/app/config_models.json" ]; then
            cp "$INSTALL_DIR/app/config_models.json" "$CONFIG_DIR/config_models.json"
        elif [ -f "$SOURCE_DIR/config/config_models.default.json" ]; then
            cp "$SOURCE_DIR/config/config_models.default.json" "$CONFIG_DIR/config_models.json"
        fi
    fi
    if [ ! -f "$CONFIG_DIR/.env" ]; then
        if [ -f "$INSTALL_DIR/app/.env" ]; then
            cp "$INSTALL_DIR/app/.env" "$CONFIG_DIR/.env"
            chmod 600 "$CONFIG_DIR/.env"
        elif [ -f "$SOURCE_DIR/config/.env.example" ]; then
            cp "$SOURCE_DIR/config/.env.example" "$CONFIG_DIR/.env"
            chmod 600 "$CONFIG_DIR/.env"
        fi
    fi

    # Corrige automaticamente modelos legados inválidos caso ainda constem no config
    if [ -f "$CONFIG_DIR/config_models.json" ] && grep -Fq "openai/gpt-oss-120b" "$CONFIG_DIR/config_models.json"; then
        sed -i 's|openai/gpt-oss-120b|llama-3.3-70b-versatile|g' "$CONFIG_DIR/config_models.json" 2>/dev/null || true
    fi

    # Garante que ENABLE_COMMAND_TOOL esteja habilitado por padrão no .env
    if [ -f "$CONFIG_DIR/.env" ]; then
        if grep -q 'ENABLE_COMMAND_TOOL="0"' "$CONFIG_DIR/.env"; then
            sed -i 's/ENABLE_COMMAND_TOOL="0"/ENABLE_COMMAND_TOOL="1"/g' "$CONFIG_DIR/.env" 2>/dev/null || true
        elif grep -q 'ENABLE_COMMAND_TOOL=0' "$CONFIG_DIR/.env"; then
            sed -i 's/ENABLE_COMMAND_TOOL=0/ENABLE_COMMAND_TOOL=1/g' "$CONFIG_DIR/.env" 2>/dev/null || true
        elif ! grep -q 'ENABLE_COMMAND_TOOL' "$CONFIG_DIR/.env"; then
            echo "ENABLE_COMMAND_TOOL=1" >> "$CONFIG_DIR/.env"
        fi
    fi

    chmod +x "$INSTALL_DIR/bin/metis" "$INSTALL_DIR/app/vision/run.sh" "$INSTALL_DIR/update.sh" "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true

    BIN_DIR="$HOME/.local/bin"
    APPS_DIR="$HOME/.local/share/applications"
    ICONS_DIR="$HOME/.local/share/icons/hicolor"
    mkdir -p "$BIN_DIR" "$APPS_DIR" "$ICONS_DIR/128x128/apps" "$ICONS_DIR/256x256/apps" "$ICONS_DIR/512x512/apps"

    ln -sf "$INSTALL_DIR/bin/metis" "$BIN_DIR/metis"
    ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/metis-vision"
    ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/screenai"

    # Atualiza ícones do sistema
    if [ -f "$INSTALL_DIR/assets/icons/icon_128x128.png" ]; then
        cp "$INSTALL_DIR/assets/icons/icon_128x128.png" "$ICONS_DIR/128x128/apps/metis-vision.png" 2>/dev/null || true
        cp "$INSTALL_DIR/assets/icons/icon_256x256.png" "$ICONS_DIR/256x256/apps/metis-vision.png" 2>/dev/null || true
        cp "$INSTALL_DIR/assets/icons/icon_256x256.png" "$ICONS_DIR/256x256/apps/metis_app_icon.png" 2>/dev/null || true
        command -v gtk-update-icon-cache &>/dev/null && gtk-update-icon-cache -f -t "$ICONS_DIR" 2>/dev/null || true
    fi

    # Atualiza Desktop Entries
    if [ -f "$SOURCE_DIR/assets/metis.desktop" ]; then
        cp "$SOURCE_DIR/assets/metis.desktop" "$APPS_DIR/metis.desktop"
    fi
    if [ -f "$SOURCE_DIR/assets/metis-vision.desktop" ]; then
        cp "$SOURCE_DIR/assets/metis-vision.desktop" "$APPS_DIR/metis-vision.desktop"
    fi
    command -v update-desktop-database &>/dev/null && update-desktop-database "$APPS_DIR" 2>/dev/null || true

    # Atualiza atalho na Área de Trabalho se existir
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "")"
    [ -z "$DESKTOP_DIR" ] && [ -d "$HOME/Desktop" ] && DESKTOP_DIR="$HOME/Desktop"
    [ -z "$DESKTOP_DIR" ] && [ -d "$HOME/Área de trabalho" ] && DESKTOP_DIR="$HOME/Área de trabalho"
    if [ -n "$DESKTOP_DIR" ] && [ -d "$DESKTOP_DIR" ]; then
        if [ -f "$APPS_DIR/metis.desktop" ]; then
            cp "$APPS_DIR/metis.desktop" "$DESKTOP_DIR/metis.desktop" 2>/dev/null || true
            chmod +x "$DESKTOP_DIR/metis.desktop" 2>/dev/null || true
        fi
        if [ -f "$APPS_DIR/metis-vision.desktop" ]; then
            cp "$APPS_DIR/metis-vision.desktop" "$DESKTOP_DIR/metis-vision.desktop" 2>/dev/null || true
            chmod +x "$DESKTOP_DIR/metis-vision.desktop" 2>/dev/null || true
        fi
    fi

    # Atualiza fontes se existirem
    FONTS_DIR="$HOME/.local/share/fonts"
    if [ -f "$SOURCE_DIR/assets/fonts/MetisIcons.ttf" ]; then
        mkdir -p "$FONTS_DIR"
        cp "$SOURCE_DIR/assets/fonts/MetisIcons.ttf" "$FONTS_DIR/MetisIcons.ttf"
        command -v fc-cache &>/dev/null && fc-cache -f "$FONTS_DIR" 2>/dev/null || true
    fi

    # Atualiza dependências Python no venv
    if [ -d "$INSTALL_DIR/venv" ]; then
        echo -e "  ${CYAN}🐍 Atualizando dependências no venv...${NC}"
        "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --upgrade --quiet 2>/dev/null || true
        "$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR" --no-deps --quiet 2>/dev/null || true
    fi

    # Garante acesso ao bus da sessão do usuário mesmo via SSH
    if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ -S "/run/user/$UID/bus" ]; then
        export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$UID/bus"
    fi

    # Atualiza atalhos globais de teclado no Cinnamon / Linux Mint se presente
    if command -v dconf &>/dev/null; then
        dconf reset -f /org/cinnamon/desktop/keybindings/custom-metis/ 2>/dev/null || true
        dconf reset -f /org/cinnamon/desktop/keybindings/custom-screenai/ 2>/dev/null || true
        dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/ 2>/dev/null || true
        dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/ 2>/dev/null || true

        INSTALL_DIR="$INSTALL_DIR" python3 -c "
import os, sys, re, subprocess

def run_c(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

install_dir = os.environ.get('INSTALL_DIR', os.path.expanduser('~/.local/share/metis'))
cmd_gui = f'{install_dir}/bin/metis gui'
cmd_vis = f'{install_dir}/bin/metis vision'

cur_raw = run_c('gsettings get org.cinnamon.desktop.keybindings custom-list 2>/dev/null')
if not cur_raw or '@as []' in cur_raw or 'no such schema' in cur_raw.lower():
    cur_raw = run_c('dconf read /org/cinnamon/desktop/keybindings/custom-list 2>/dev/null') or '[]'

items = re.findall(r'[\'\"]([^\'\"]+)[\'\"]', cur_raw)
valid_slots = [s for s in items if re.match(r'^custom\d+$', s)]

slot_gui = None
slot_vis = None

for s in valid_slots:
    c = run_c(f'dconf read /org/cinnamon/desktop/keybindings/custom-keybindings/{s}/command 2>/dev/null').strip(\"'\\\"\")
    n = run_c(f'dconf read /org/cinnamon/desktop/keybindings/custom-keybindings/{s}/name 2>/dev/null').strip(\"'\\\"\")
    if 'metis gui' in c or n == 'Metis AI':
        slot_gui = s
    elif 'metis vision' in c or 'screenai' in c or n == 'Metis Vision':
        slot_vis = s

def alloc_slot():
    idx = 0
    while f'custom{idx}' in valid_slots or f'custom{idx}' == slot_gui or f'custom{idx}' == slot_vis:
        idx += 1
    new_s = f'custom{idx}'
    valid_slots.append(new_s)
    return new_s

if not slot_gui:
    slot_gui = alloc_slot()
if not slot_vis:
    slot_vis = alloc_slot()

if slot_gui not in valid_slots:
    valid_slots.append(slot_gui)
if slot_vis not in valid_slots:
    valid_slots.append(slot_vis)

path_gui = f'/org/cinnamon/desktop/keybindings/custom-keybindings/{slot_gui}/'
run_c(f\"gsettings set org.cinnamon.desktop.keybindings.custom-keybinding:{path_gui} name 'Metis AI' 2>/dev/null\")
run_c(f\"gsettings set org.cinnamon.desktop.keybindings.custom-keybinding:{path_gui} command '{cmd_gui}' 2>/dev/null\")
run_c(f\"gsettings set org.cinnamon.desktop.keybindings.custom-keybinding:{path_gui} binding \\\"['<Super>r', '<Primary><Alt>m']\\\" 2>/dev/null\")
run_c(f\"dconf write {path_gui}name \\\"'Metis AI'\\\" 2>/dev/null\")
run_c(f\"dconf write {path_gui}command \\\"'{cmd_gui}'\\\" 2>/dev/null\")
run_c(f\"dconf write {path_gui}binding \\\"['<Super>r', '<Primary><Alt>m']\\\" 2>/dev/null\")

path_vis = f'/org/cinnamon/desktop/keybindings/custom-keybindings/{slot_vis}/'
run_c(f\"gsettings set org.cinnamon.desktop.keybindings.custom-keybinding:{path_vis} name 'Metis Vision' 2>/dev/null\")
run_c(f\"gsettings set org.cinnamon.desktop.keybindings.custom-keybinding:{path_vis} command '{cmd_vis}' 2>/dev/null\")
run_c(f\"gsettings set org.cinnamon.desktop.keybindings.custom-keybinding:{path_vis} binding \\\"['<Primary><Alt>v', '<Super>v']\\\" 2>/dev/null\")
run_c(f\"dconf write {path_vis}name \\\"'Metis Vision'\\\" 2>/dev/null\")
run_c(f\"dconf write {path_vis}command \\\"'{cmd_vis}'\\\" 2>/dev/null\")
run_c(f\"dconf write {path_vis}binding \\\"['<Primary><Alt>v', '<Super>v']\\\" 2>/dev/null\")

final_list = '[' + ', '.join([f\"'{s}'\" for s in sorted(list(set(valid_slots)), key=lambda x: int(x.replace('custom', '')))]) + ']'
run_c(f\"gsettings set org.cinnamon.desktop.keybindings custom-list \\\"{final_list}\\\" 2>/dev/null\")
run_c(f\"dconf write /org/cinnamon/desktop/keybindings/custom-list \\\"{final_list}\\\" 2>/dev/null\")
" 2>/dev/null || true
    fi

    # Garante que kitty.conf use ZSH se kitty existir
    local kitty_conf="$HOME/.config/kitty/kitty.conf"
    if [ -f "$kitty_conf" ]; then
        local zsh_path
        zsh_path="$(which zsh 2>/dev/null || command -v zsh || echo "/usr/bin/zsh")"
        if ! grep -Eq "^[[:space:]]*shell[[:space:]]" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# Shell padrão do Kitty com Metis (apenas no Kitty; terminais comuns usam Bash)" >> "$kitty_conf"
            echo "shell $zsh_path" >> "$kitty_conf"
        else
            sed -i "s|^[[:space:]]*shell[[:space:]].*|shell $zsh_path|g" "$kitty_conf" 2>/dev/null || true
        fi
    fi
else
    echo -e "${RED}❌ Instalação do Metis não encontrada em $INSTALL_DIR.${NC}"
    echo "Por favor, instale o Metis executando: bash install.sh"
    exit 1
fi

# Limpeza se usou diretório temporário
if [ "$CLEANUP_TEMP" -eq 1 ] && [ -n "$SOURCE_DIR" ]; then
    rm -rf "$SOURCE_DIR"
fi

echo -e "\n${GREEN}${BOLD}✅ Metis AI Suite atualizado com sucesso!${NC}"
echo -e "ℹ️  Suas configurações em ~/.config/metis/ foram mantidas intactas.\n"
