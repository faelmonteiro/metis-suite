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

    for d in app zsh bash bin assets; do
        [ -L "$INSTALL_DIR/$d" ] && rm -f "$INSTALL_DIR/$d"
    done

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

    # 3. Limpeza de atalhos globais de sistema (foco 100% em atalhos de terminal)
    clean_global_desktop_shortcuts() {
        echo -e "  ${CYAN}🧹 Limpando atalhos globais de sistema (mantendo apenas atalhos de terminal)...${NC}"

        # 1. GNOME / Ubuntu / Pop!_OS / Fedora / Debian / Arch GNOME
        python3 -c "
import os, re, subprocess

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

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
" 2>/dev/null || true

        # 2. Cinnamon (Linux Mint)
        python3 -c "
import os, re, subprocess

def run_c(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

cur_raw = run_c('gsettings get org.cinnamon.desktop.keybindings custom-list 2>/dev/null')
if not cur_raw or '@as []' in cur_raw or 'no such schema' in cur_raw.lower():
    cur_raw = run_c('dconf read /org/cinnamon/desktop/keybindings/custom-list 2>/dev/null') or '[]'

items = re.findall(r'[\'\"]([^\'\"]+)[\'\"]', cur_raw)
valid_slots = [s for s in items if re.match(r'^custom\d+$', s)]
keep_slots = []

for s in valid_slots:
    p = f'/org/cinnamon/desktop/keybindings/custom-keybindings/{s}/'
    c = run_c(f'dconf read {p}command 2>/dev/null').strip(\"'\\\"\")
    n = run_c(f'dconf read {p}name 2>/dev/null').strip(\"'\\\"\")
    if 'metis' in c.lower() or 'screenai' in c.lower() or 'metis' in n.lower():
        run_c(f'dconf reset -f {p}')
    else:
        keep_slots.append(s)

if len(keep_slots) != len(valid_slots):
    final_list = '[' + ', '.join([f\"'{s}'\" for s in keep_slots]) + ']'
    run_c(f'gsettings set org.cinnamon.desktop.keybindings custom-list \"{final_list}\" 2>/dev/null')
    run_c(f'dconf write /org/cinnamon/desktop/keybindings/custom-list \"{final_list}\" 2>/dev/null')

run_c('dconf reset -f /org/cinnamon/desktop/keybindings/custom-metis/ 2>/dev/null')
run_c('dconf reset -f /org/cinnamon/desktop/keybindings/custom-screenai/ 2>/dev/null')
run_c('dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/ 2>/dev/null')
run_c('dconf reset -f /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/ 2>/dev/null')
" 2>/dev/null || true

        # 3. KDE Plasma
        local kg_file="$HOME/.config/kglobalshortcutsrc"
        if [ -f "$kg_file" ]; then
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
            qdbus org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.reloadConfig 2>/dev/null || true
            qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || true
        fi

        # 4. XFCE
        if command -v xfconf-query &>/dev/null; then
            xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -r 2>/dev/null || true
            xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>z" -r 2>/dev/null || true
            xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>v" -r 2>/dev/null || true
            xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt>v" -r 2>/dev/null || true
        fi

        # 5. MATE Desktop
        if command -v gsettings &>/dev/null; then
            for i in 1 2 3 4 5; do
                local cmd
                cmd="$(gsettings get org.mate.Marco.keybinding-commands command-$i 2>/dev/null || true)"
                if [[ "$cmd" == *"metis"* || "$cmd" == *"screenai"* ]]; then
                    gsettings reset org.mate.Marco.keybinding-commands command-$i 2>/dev/null || true
                    gsettings reset org.mate.Marco.global-keybindings run-command-$i 2>/dev/null || true
                fi
            done
        fi
        if command -v dconf &>/dev/null; then
            dconf reset -f /org/mate/desktop/keybindings/custom-metis/ 2>/dev/null || true
            dconf reset -f /org/mate/desktop/keybindings/custom-screenai/ 2>/dev/null || true
        fi

        # 6. Window Managers (Hyprland / Sway / i3)
        if [ -f "$HOME/.config/hypr/hyprland.conf" ]; then
            sed -i '/[Mm]etis/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
            sed -i '/screenai/d' "$HOME/.config/hypr/hyprland.conf" 2>/dev/null || true
        fi

        if [ -f "$HOME/.config/sway/config" ]; then
            sed -i '/metis gui/d' "$HOME/.config/sway/config" 2>/dev/null || true
            sed -i '/metis vision/d' "$HOME/.config/sway/config" 2>/dev/null || true
            sed -i '/screenai/d' "$HOME/.config/sway/config" 2>/dev/null || true
        fi

        if [ -f "$HOME/.config/i3/config" ]; then
            sed -i '/metis gui/d' "$HOME/.config/i3/config" 2>/dev/null || true
            sed -i '/metis vision/d' "$HOME/.config/i3/config" 2>/dev/null || true
            sed -i '/screenai/d' "$HOME/.config/i3/config" 2>/dev/null || true
        fi

        # 7. xbindkeys
        if [ -f "$HOME/.xbindkeysrc" ]; then
            sed -i '/# --- \[ Metis AI Suite \] ---/,/metis vision/d' "$HOME/.xbindkeysrc" 2>/dev/null || true
            sed -i '/metis gui/d' "$HOME/.xbindkeysrc" 2>/dev/null || true
            sed -i '/metis vision/d' "$HOME/.xbindkeysrc" 2>/dev/null || true
            command -v pkill &>/dev/null && pkill -HUP xbindkeys 2>/dev/null || true
        fi
    }

    clean_global_desktop_shortcuts

    # 4. Atualização da integração com os terminais (Bash & Kitty ZSH)
    update_terminal_integration() {
        local kitty_conf="$HOME/.config/kitty/kitty.conf"
        if [ -f "$kitty_conf" ] || command -v kitty &>/dev/null; then
            mkdir -p "$HOME/.config/kitty"
            touch "$kitty_conf"
            local zsh_path
            zsh_path="$(which zsh 2>/dev/null || command -v zsh || echo "/usr/bin/zsh")"
            if ! grep -Eq "^[[:space:]]*shell[[:space:]]" "$kitty_conf"; then
                echo "" >> "$kitty_conf"
                echo "# Shell padrão do Kitty com Metis (apenas no Kitty; terminais comuns usam Bash)" >> "$kitty_conf"
                echo "shell $zsh_path" >> "$kitty_conf"
            else
                sed -i "s|^[[:space:]]*shell[[:space:]].*|shell $zsh_path|g" "$kitty_conf" 2>/dev/null || true
            fi

            if ! grep -Eq "^[[:space:]]*copy_on_select[[:space:]]" "$kitty_conf"; then
                echo "" >> "$kitty_conf"
                echo "# Copia automaticamente o texto selecionado com o mouse para a área de transferência" >> "$kitty_conf"
                echo "copy_on_select yes" >> "$kitty_conf"
            fi

            sed -i "/^[[:space:]]*clear_selection_on_clipboard_loss/d" "$kitty_conf" 2>/dev/null || true
            sed -i "s|^[[:space:]]*listen_on.*|listen_on unix:/tmp/mykitty|g" "$kitty_conf" 2>/dev/null || true

            if ! grep -Fq "screen_launcher.zsh" "$kitty_conf" && ! grep -Fq "explain_screen.zsh" "$kitty_conf"; then
                echo "" >> "$kitty_conf"
                echo "# --- [ Metis Explain Screen (Ctrl + Shift + E) ] ---" >> "$kitty_conf"
                echo "allow_remote_control yes" >> "$kitty_conf"
                echo "listen_on unix:/tmp/mykitty" >> "$kitty_conf"
                echo "map ctrl+shift+e pipe @screen_scrollback none /bin/zsh -c \"if [ -f \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\" ]; then zsh \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\"; fi\"" >> "$kitty_conf"
            else
                sed -i "s|.*explain_screen\.zsh.*|map ctrl+shift+e pipe @screen_scrollback none /bin/zsh -c \"if [ -f \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\" ]; then zsh \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\"; fi\"|g" "$kitty_conf" 2>/dev/null || true
                sed -i "s|.*\.ZSH/ai.*screen_launcher\.zsh.*|map ctrl+shift+e pipe @screen_scrollback none /bin/zsh -c \"if [ -f \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\" ]; then zsh \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\"; fi\"|g" "$kitty_conf" 2>/dev/null || true
                if ! grep -Eq "^[[:space:]]*listen_on[[:space:]]" "$kitty_conf"; then
                    echo "listen_on unix:/tmp/mykitty" >> "$kitty_conf"
                fi
            fi

            # Garante loader no ~/.zshrc para o Kitty se zshrc existir
            if [ -f "$HOME/.zshrc" ] && ! grep -Fq "metis/zsh/loader.zsh" "$HOME/.zshrc"; then
                echo "" >> "$HOME/.zshrc"
                echo "# >>> METIS SUITE >>>" >> "$HOME/.zshrc"
                echo "[[ -f \"$INSTALL_DIR/zsh/loader.zsh\" ]] && source \"$INSTALL_DIR/zsh/loader.zsh\"" >> "$HOME/.zshrc"
                echo "# <<< METIS SUITE <<<" >> "$HOME/.zshrc"
            fi
        fi

        # Garante integração no ~/.bashrc
        local bashrc="$HOME/.bashrc"
        if [ -f "$bashrc" ]; then
            sed -i '/# >>> METIS ZSH AUTO-LAUNCH >>>/,/# <<< METIS ZSH AUTO-LAUNCH <<</d' "$bashrc" 2>/dev/null || true
            sed -i '/^[[:space:]]*exec[[:space:]]\+zsh/d' "$bashrc" 2>/dev/null || true
            sed -i '/^[[:space:]]*\[\[.*exec zsh.*\]\]/d' "$bashrc" 2>/dev/null || true
            if ! grep -Fq "metis/bash/loader.bash" "$bashrc"; then
                echo "" >> "$bashrc"
                echo "# >>> METIS SUITE >>>" >> "$bashrc"
                echo "[[ -f \"$INSTALL_DIR/bash/loader.bash\" ]] && source \"$INSTALL_DIR/bash/loader.bash\"" >> "$bashrc"
                echo "# <<< METIS SUITE <<<" >> "$bashrc"
            fi
        fi

        # Restaura shell de login se estiver como ZSH
        local cur_login
        cur_login="$(getent passwd "$USER" 2>/dev/null | cut -d: -f7 || echo "$SHELL")"
        if [[ "$cur_login" == *"zsh"* ]]; then
            local bash_sys
            bash_sys="$(which bash 2>/dev/null || command -v bash || echo "/bin/bash")"
            if [ -x "$bash_sys" ]; then
                sudo -n chsh -s "$bash_sys" "$USER" 2>/dev/null || timeout 3 chsh -s "$bash_sys" "$USER" 2>/dev/null || true
            fi
        fi
    }

    update_terminal_integration
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
echo -e "  ${CYAN}[Alt + E]${NC} Explain Screen no terminal comum"
if [ -f "$HOME/.config/kitty/kitty.conf" ] || command -v kitty &>/dev/null; then
echo -e "  ${CYAN}[Ctrl + Shift + E]${NC} Explain Screen no Kitty"
fi
echo -e "  ${CYAN}[Ctrl + G]${NC} Menu FZF • ${CYAN}[Alt + H]${NC} Histórico • ${CYAN}[metis gui]${NC} GUI • ${CYAN}[metis vision]${NC} Visão"
echo -e "\nℹ️  Suas configurações em ~/.config/metis/ foram mantidas intactas.\n"
