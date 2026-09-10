#!/usr/bin/env bash
# =============================================================================
# METIS AI SUITE - UNIVERSAL LINUX INSTALLER
# =============================================================================
set -e

# Paleta Oficial Metis (Truecolor 24-bit)
GOLD='\033[38;2;240;168;93m'
GOLD_BRIGHT='\033[38;2;250;208;148m'
YELLOW='\033[38;2;253;224;71m'
CYAN='\033[38;2;103;232;249m'
CYAN_SOFT='\033[38;2;125;211;252m'
GREEN='\033[38;2;74;222;128m'
RED='\033[38;2;248;113;113m'
GRAY='\033[38;2;148;163;184m'
GRAY_DARK='\033[38;2;100;116;139m'
BORDER='\033[38;2;70;92;122m'
BORDER_SOFT='\033[38;2;46;62;84m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Glifo oficial do Metis (Fonte MetisIcons / PUA Unicode U+E900 / U+E00B)
METIS_GLYPH=$'\ue900'

# Obter ícone inline oficial (metis_emoji_32x32.png) para Kitty ou fallback glifo
obter_icone_metis() {
    local is_kitty=0
    if [[ -n "$KITTY_PID" || -n "$KITTY_WINDOW_ID" || "$TERM" == *"kitty"* ]] && command -v base64 &>/dev/null; then
        is_kitty=1
    fi

    local icon_file="$SCRIPT_DIR/assets/icons/metis_emoji_32x32.png"
    if [ $is_kitty -eq 1 ] && [ -f "$icon_file" ]; then
        local b64
        b64=$(base64 -w 0 "$icon_file" 2>/dev/null || base64 "$icon_file" 2>/dev/null)
        if [ -n "$b64" ]; then
            printf "\x1b_Ga=T,f=100,c=2,r=1;%s\x1b\\ " "$b64"
            return
        fi
    fi
    # Em terminais tradicionais (GNOME, Konsole, Alacritty), usa a Coruja/Glifo de alta compatibilidade
    printf "🦉 "
}

render_metis_header() {
    local icone_render
    icone_render="$(obter_icone_metis)"

    echo -e "${BORDER_SOFT}╭─────────────────────────────────────────────────────────────────────────────────╮${NC}"
    echo -e "${GOLD_BRIGHT}${BOLD}"
    echo "       ███╗   ███╗███████╗████████╗██╗███████╗"
    echo "       ████╗ ████║██╔════╝╚══██╔══╝██║██╔════╝"
    echo "       ██╔████╔██║█████╗     ██║   ██║███████╗"
    echo "       ██║╚██╔╝██║██╔══╝     ██║   ██║╚════██║"
    echo "       ██║ ╚═╝ ██║███████╗   ██║   ██║███████║"
    echo "       ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝╚══════╝"
    echo -e "${NC}"
    echo -e "       ${GOLD}${icone_render}ORÁCULO & COPILOTO AUTÔNOMO DE TERMINAL${NC}"
    echo -e "       ${GRAY}Suíte de Inteligência Artificial para Linux & ZSH${NC}"
    echo -e "${BORDER_SOFT}╰─────────────────────────────────────────────────────────────────────────────────╯${NC}"
}

clear 2>/dev/null || true
render_metis_header

# 1. Detecção Automática da Distro e Instalação Completa de Dependências
install_system_deps() {
    echo -e "\n${CYAN}🔍 [1/6] Detectando distribuição e instalando dependências (Terminal + Drivers Gráficos Qt)...${NC}"

    if command -v apt-get &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição baseada em Debian/Ubuntu/Linux Mint detectada (APT).${NC}"
        echo -e "  ${GRAY}Instalando ferramentas essenciais de terminal e Python...${NC}"
        sudo apt-get update
        sudo apt-get install -y python3 python3-venv python3-pip curl git jq xclip fontconfig || {
            echo -e "${RED}  ❌ Falha ao instalar pacotes essenciais. Verifique sua conexão e tente novamente.${NC}"
            exit 1
        }
        echo -e "${GREEN}  ✅ Pacotes essenciais instalados.${NC}"

        # Pacotes opcionais — instala o que conseguir, sem abortar se algum não existir
        echo -e "  ${GRAY}Instalando pacotes opcionais (ZSH, FZF, drivers gráficos Qt)...${NC}"
        for pkg in zsh fzf wl-clipboard libgl1 libegl1 libxkbcommon-x11-0 \
                   libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                   libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
                   libxcb-sync1 libxcb-xfixes0 libxcb-xkb1; do
            sudo apt-get install -y "$pkg" 2>/dev/null || echo -e "  ${GRAY}  ⚠ Pacote '$pkg' não encontrado, pulando (não é crítico).${NC}"
        done
        echo -e "${GREEN}  ✅ Dependências do sistema instaladas com sucesso.${NC}"
    elif command -v dnf &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição baseada em Fedora/RedHat detectada (DNF).${NC}"
        sudo dnf install -y zsh python3 python3-pip fzf curl git jq wl-clipboard xclip fontconfig mesa-libGL mesa-libEGL libxkbcommon-x11 xcb-util-cursor
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v pacman &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição baseada em Arch Linux detectada (Pacman).${NC}"
        sudo pacman -Sy --noconfirm zsh python python-pip fzf curl git jq wl-clipboard xclip fontconfig libglvnd libxkbcommon-x11 xcb-util-cursor
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v zypper &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição openSUSE detectada (Zypper).${NC}"
        sudo zypper install -y zsh python3 python3-pip fzf curl git jq wl-clipboard xclip fontconfig libglvnd libxkbcommon-x11-0 libxcb-cursor0
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v xbps-install &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição Void Linux detectada (XBPS).${NC}"
        sudo xbps-install -Sy zsh python3 python3-pip fzf curl git jq wl-clipboard xclip fontconfig
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v apk &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição Alpine Linux detectada (APK).${NC}"
        sudo apk add zsh python3 py3-pip fzf curl git jq wl-clipboard xclip fontconfig
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    else
        echo -e "${RED}  ❌ Gerenciador de pacotes não identificado automaticamente.${NC}"
        echo "Por favor, instale manualmente: zsh, python3, python3-venv, fzf, curl, git e jq."
        exit 1
    fi
}

install_system_deps

# 2. Definição de diretórios (Padrão XDG)
INSTALL_DIR="$HOME/.local/share/metis"
CONFIG_DIR="$HOME/.config/metis"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
FONTS_DIR="$HOME/.local/share/fonts"

mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APPS_DIR"
mkdir -p "$ICONS_DIR"
mkdir -p "$FONTS_DIR"

# 3. Copiar arquivos da aplicação
echo -e "\n${CYAN}📂 [2/6] Instalando arquivos em ${INSTALL_DIR}...${NC}"
cp -r "$SCRIPT_DIR/app" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/zsh" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/bin" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/update.sh" "$INSTALL_DIR/" 2>/dev/null || true
chmod +x "$INSTALL_DIR/bin/metis" "$INSTALL_DIR/uninstall.sh" "$INSTALL_DIR/update.sh" 2>/dev/null || true
echo -e "${GREEN}  ✅ Arquivos copiados com sucesso.${NC}"

# 4. Configurar ambiente virtual Python isolado
echo -e "\n${CYAN}🐍 [3/6] Configurando ambiente Python isolado (venv)...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet

echo -e "  ${GRAY}Instalando dependências (Core, Terminal e GUI PyQt6)...${NC}"
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet 2>/dev/null || {
    echo -e "  ${YELLOW}⚠️ Executando instalação resiliente por etapas...${NC}"
    "$INSTALL_DIR/venv/bin/pip" install httpx python-dotenv prompt_toolkit fpdf2 pyperclip --quiet || true
    "$INSTALL_DIR/venv/bin/pip" install PyQt6 --quiet || true
    "$INSTALL_DIR/venv/bin/pip" install g4f curl_cffi --quiet 2>/dev/null || true
}

# Verificação do suporte gráfico PyQt6
if "$INSTALL_DIR/venv/bin/python" -c "import PyQt6.QtWidgets" &>/dev/null; then
    echo -e "${GREEN}  ✅ Dependências Python e motor gráfico PyQt6 validados com sucesso.${NC}"
else
    echo -e "${YELLOW}  ⚠️ PyQt6 não pôde ser validado imediatamente.${NC}"
    echo -e "${GRAY}      O modo Terminal funcionará 100%. Se a GUI não abrir, verifique pacotes libgl/libxcb.${NC}"
fi

# 5. Inicializar configurações zeradas (sem expor chaves ou modelos)
echo -e "\n${CYAN}⚙️  [4/6] Configurando preferências em ${CONFIG_DIR}...${NC}"
if [ ! -f "$CONFIG_DIR/config_models.json" ]; then
    cp "$SCRIPT_DIR/config/config_models.default.json" "$CONFIG_DIR/config_models.json"
    echo -e "${GREEN}  📄 Criado:${NC} $CONFIG_DIR/config_models.json ${GRAY}(100% zerado)${NC}"
else
    echo -e "${GRAY}  ℹ️  Configurações de modelos existentes preservadas.${NC}"
fi

if [ ! -f "$CONFIG_DIR/.env" ]; then
    cp "$SCRIPT_DIR/config/.env.example" "$CONFIG_DIR/.env"
    chmod 600 "$CONFIG_DIR/.env"
    echo -e "${GREEN}  🔒 Criado:${NC} $CONFIG_DIR/.env ${GRAY}(permissão restrita 600)${NC}"
else
    echo -e "${GRAY}  ℹ️  Arquivo .env existente preservado.${NC}"
fi

# 6. Criar atalhos executáveis, fontes personalizadas e Desktop Entry
echo -e "\n${CYAN}🚀 [5/6] Registrando lançadores, fontes e ícones no sistema...${NC}"
ln -sf "$INSTALL_DIR/bin/metis" "$BIN_DIR/metis"
ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/metis-vision"
ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/screenai" 

# Instalar Fonte de Glifos do Metis (MetisIcons.ttf)
if [ -f "$SCRIPT_DIR/assets/fonts/MetisIcons.ttf" ]; then
    cp "$SCRIPT_DIR/assets/fonts/MetisIcons.ttf" "$FONTS_DIR/MetisIcons.ttf"
    if command -v fc-cache &>/dev/null; then
        fc-cache -f "$FONTS_DIR" 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✅ Fonte oficial MetisIcons.ttf instalada.${NC}"
fi

# Copiar ícones HD para o tema do sistema
if [ -f "$SCRIPT_DIR/assets/icons/icon_256x256.png" ]; then
    cp "$SCRIPT_DIR/assets/icons/icon_256x256.png" "$ICONS_DIR/metis_app_icon.png"
    cp "$SCRIPT_DIR/assets/icons/icon_256x256.png" "$ICONS_DIR/metis-vision.png"
elif [ -f "$SCRIPT_DIR/app/assets/icons/icon_256x256.png" ]; then
    cp "$SCRIPT_DIR/app/assets/icons/icon_256x256.png" "$ICONS_DIR/metis_app_icon.png"
    cp "$SCRIPT_DIR/app/assets/icons/icon_256x256.png" "$ICONS_DIR/metis-vision.png"
fi

# Registrar .desktop com caminhos absolutos exatos
if [ -f "$SCRIPT_DIR/assets/metis.desktop" ]; then
    cat << DESK_EOF > "$APPS_DIR/metis.desktop"
[Desktop Entry]
Name=Metis AI
Comment=Agente de Inteligência Artificial e Copiloto de Terminal
Exec=$INSTALL_DIR/bin/metis gui
Icon=$INSTALL_DIR/assets/icons/metis_app_icon.png
Path=$INSTALL_DIR/app
Terminal=false
Type=Application
Categories=Utility;Development;
Keywords=ai;assistant;terminal;metis;
DESK_EOF
    chmod +x "$APPS_DIR/metis.desktop"

    cat << VISION_DESK_EOF > "$APPS_DIR/metis-vision.desktop"
[Desktop Entry]
Name=Metis Vision
Comment=Assistente Visual de Tela e Análise Multimodal com IA
Exec=$INSTALL_DIR/app/vision/run.sh
Icon=$INSTALL_DIR/assets/icons/icon_256x256.png
Path=$INSTALL_DIR/app/vision
Terminal=false
Type=Application
Categories=Utility;Development;Graphics;
Keywords=ai;vision;screen;metis;screenshot;ocr;
StartupWMClass=metis-vision
VISION_DESK_EOF
    chmod +x "$APPS_DIR/metis-vision.desktop"

    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$APPS_DIR" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✅ Aplicativos registrados no menu do sistema (GNOME/KDE/Rofi/Wofi).${NC}"
fi

# Copiar atalho para a Área de Trabalho (Desktop) em qualquer idioma do Linux
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "")"
if [ -z "$DESKTOP_DIR" ] || [ ! -d "$DESKTOP_DIR" ]; then
    if [ -d "$HOME/Área de trabalho" ]; then
        DESKTOP_DIR="$HOME/Área de trabalho"
    elif [ -d "$HOME/Desktop" ]; then
        DESKTOP_DIR="$HOME/Desktop"
    fi
fi

if [ -n "$DESKTOP_DIR" ] && [ -d "$DESKTOP_DIR" ]; then
    cp "$APPS_DIR/metis.desktop" "$DESKTOP_DIR/metis.desktop"
    chmod +x "$DESKTOP_DIR/metis.desktop"
    if command -v gio &>/dev/null; then
        gio set "$DESKTOP_DIR/metis.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✅ Ícone oficial do Metis criado na Área de Trabalho ($DESKTOP_DIR).${NC}"
fi



# 6.5 Configuração Automática dos Atalhos Globais (Super + R e Super + Z)
configure_global_shortcut() {
    echo -e "\n${CYAN}⌨️  [5.5/6] Configurando atalhos globais [Super + R] e [Super + Z] no sistema...${NC}"
    local desktop="${XDG_CURRENT_DESKTOP:-$DESKTOP_SESSION}"
    desktop="$(echo "$desktop" | tr '[:upper:]' '[:lower:]')"
    local config_done=0

    # A. GNOME / Ubuntu / Pop!_OS / Fedora
    if [[ "$desktop" == *"gnome"* || "$desktop" == *"ubuntu"* || "$desktop" == *"pop"* ]] && command -v gsettings &>/dev/null; then
        local base_schema="org.gnome.settings-daemon.plugins.media-keys"
        local path_r="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-metis/"
        local path_z="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-screenai/"
        local custom_schema="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
        
        # Super + R
        gsettings set "${custom_schema}:${path_r}" name "Metis AI" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_r}" command "$INSTALL_DIR/bin/metis gui" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_r}" binding "<Super>r" 2>/dev/null || true
        
        # Super + Z
        gsettings set "${custom_schema}:${path_z}" name "ScreenAI" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_z}" command "$BIN_DIR/screenai" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_z}" binding "<Super>z" 2>/dev/null || true

        # Anexa aos atalhos existentes sem sobrescrever os atalhos do usuário
        local current_list
        current_list=$(gsettings get "$base_schema" custom-keybindings 2>/dev/null || echo "@as []")
        if [[ "$current_list" == "@as []" || "$current_list" == "[]" || -z "$current_list" ]]; then
            gsettings set "$base_schema" custom-keybindings "['$path_r', '$path_z']" 2>/dev/null || true
        else
            local updated_list="$current_list"
            if [[ "$updated_list" != *"$path_r"* ]]; then
                updated_list="${updated_list%]}, '$path_r']"
            fi
            if [[ "$updated_list" != *"$path_z"* ]]; then
                updated_list="${updated_list%]}, '$path_z']"
            fi
            gsettings set "$base_schema" custom-keybindings "$updated_list" 2>/dev/null || true
        fi
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Super + Z] configurados para GNOME/Ubuntu.${NC}"
        config_done=1
    fi

    # B. Cinnamon / Linux Mint
    if [[ "$desktop" == *"cinnamon"* || "$desktop" == *"x-cinnamon"* ]] && command -v dconf &>/dev/null; then
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/name "'Metis AI'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/command "'$INSTALL_DIR/bin/metis gui'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/binding "['<Super>r']" 2>/dev/null || true

        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/name "'ScreenAI'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/command "'$BIN_DIR/screenai'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/binding "['<Super>z']" 2>/dev/null || true

        dconf write /org/cinnamon/desktop/keybindings/custom-list "['custom-metis', 'custom-screenai']" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Super + Z] configurados para Linux Mint (Cinnamon).${NC}"
        config_done=1
    fi

    # C. XFCE
    if [[ "$desktop" == *"xfce"* ]] && command -v xfconf-query &>/dev/null; then
        xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -n -t string -s "$INSTALL_DIR/bin/metis gui" 2>/dev/null ||         xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -s "$INSTALL_DIR/bin/metis gui" 2>/dev/null || true
        
        xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>z" -n -t string -s "$BIN_DIR/screenai" 2>/dev/null ||         xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>z" -s "$BIN_DIR/screenai" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Super + Z] configurados para XFCE.${NC}"
        config_done=1
    fi

    # D. MATE Desktop
    if [[ "$desktop" == *"mate"* ]] && command -v dconf &>/dev/null; then
        dconf write /org/mate/desktop/keybindings/custom-metis/name "'Metis AI'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-metis/action "'$INSTALL_DIR/bin/metis gui'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-metis/binding "'<Mod4>r'" 2>/dev/null || true

        dconf write /org/mate/desktop/keybindings/custom-screenai/name "'ScreenAI'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-screenai/action "'$BIN_DIR/screenai'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-screenai/binding "'<Mod4>z'" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Super + Z] configurados para MATE.${NC}"
        config_done=1
    fi

    # E. KDE Plasma
    if [[ "$desktop" == *"kde"* ]]; then
        local kw=""
        command -v kwriteconfig6 &>/dev/null && kw="kwriteconfig6"
        command -v kwriteconfig5 &>/dev/null && kw="kwriteconfig5"
        if [ -n "$kw" ]; then
            $kw --file kglobalshortcutsrc --group "Metis AI" --key "gui" "$INSTALL_DIR/bin/metis gui,none,Metis AI" 2>/dev/null || true
            $kw --file kglobalshortcutsrc --group "ScreenAI" --key "vision" "$BIN_DIR/screenai,none,ScreenAI" 2>/dev/null || true
            echo -e "${GREEN}  ✅ Atalhos registrados para KDE Plasma.${NC}"
            config_done=1
        fi
    fi

    # F. Window Managers (Hyprland / Sway / i3)
    if [ -f "$HOME/.config/hypr/hyprland.conf" ]; then
        if ! grep -Fq "metis gui" "$HOME/.config/hypr/hyprland.conf"; then
            echo "" >> "$HOME/.config/hypr/hyprland.conf"
            echo "bind = \$mainMod, r, exec, [float; size 860 550; center; pin] $INSTALL_DIR/bin/metis gui" >> "$HOME/.config/hypr/hyprland.conf"
            echo "bind = \$mainMod, z, exec, [float; size 620 390; center; pin] $BIN_DIR/screenai --mode active_window" >> "$HOME/.config/hypr/hyprland.conf"
            echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Super + Z] adicionados ao ~/.config/hypr/hyprland.conf${NC}"
            config_done=1
        fi
    fi

    if [ -f "$HOME/.config/i3/config" ]; then
        if ! grep -Fq "metis gui" "$HOME/.config/i3/config"; then
            echo "" >> "$HOME/.config/i3/config"
            echo "bindsym \$mod+r exec $INSTALL_DIR/bin/metis gui" >> "$HOME/.config/i3/config"
            echo "bindsym \$mod+z exec $BIN_DIR/screenai" >> "$HOME/.config/i3/config"
            echo -e "${GREEN}  ✅ Atalhos adicionados ao ~/.config/i3/config${NC}"
            config_done=1
        fi
    fi

    # G. Terminal Kitty (Ctrl + Shift + E -> Explain Screen)
    local kitty_conf="$HOME/.config/kitty/kitty.conf"
    if [ -f "$kitty_conf" ] || command -v kitty &>/dev/null; then
        mkdir -p "$HOME/.config/kitty"
        touch "$kitty_conf"
        if ! grep -Fq "explain_screen.zsh" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# --- [ Metis Explain Screen (Ctrl + Shift + E) ] ---" >> "$kitty_conf"
            echo "allow_remote_control yes" >> "$kitty_conf"
            echo "listen_on unix:/tmp/mykitty" >> "$kitty_conf"
            echo "map ctrl+shift+e pipe @screen_scrollback none /bin/zsh -c \"cat > /tmp/qwen_tela.txt && echo \\\"\\\$KITTY_WINDOW_ID\\\" > /tmp/orig_kitty_id && echo \\\"\\\$KITTY_LISTEN_ON\\\" > /tmp/orig_kitty_listen && kitty --class kitty-screen-assistant --config NONE -o confirm_os_window_close=0 -o \\\"map shift+enter send_text all \\\\x1b\\\\r\\\" -o \\\"map ctrl+enter send_text all \\\\x1b\\\\r\\\" zsh -c \\\"\\\$HOME/.local/share/metis/zsh/explain_screen.zsh\\\"\"" >> "$kitty_conf"
            echo -e "${GREEN}  ✅ Atalho [Ctrl + Shift + E] do explain_screen integrado ao Kitty (~/.config/kitty/kitty.conf).${NC}"
        else
            sed -i "s|\$HOME/\.ZSH/ai/explain_screen\.zsh|\$HOME/\.local/share/metis/zsh/explain_screen\.zsh|g" "$kitty_conf" 2>/dev/null || true
            sed -i "s|~/\.ZSH/ai/explain_screen\.zsh|\$HOME/\.local/share/metis/zsh/explain_screen\.zsh|g" "$kitty_conf" 2>/dev/null || true
            echo -e "${GREEN}  ✅ Atalho [Ctrl + Shift + E] do Kitty atualizado para o Metis.${NC}"
        fi
        config_done=1
    fi

    if [ $config_done -eq 0 ]; then
        echo -e "${GRAY}  ℹ️  Mapeamento de atalhos concluído ou ambiente requer configuração manual.${NC}"
    fi
}

configure_global_shortcut

# 7. Integrar aos shells (ZSH e BASH)
echo -e "\n${CYAN}⚡ [6/6] Configurando integração de terminal (ZSH & BASH)...${NC}"

# A. Integração no ~/.zshrc (se zsh estiver instalado)
ZSHRC="$HOME/.zshrc"
LOADER_LINE="[[ -f \"$INSTALL_DIR/zsh/loader.zsh\" ]] && source \"$INSTALL_DIR/zsh/loader.zsh\""

touch "$ZSHRC"
if ! grep -Fq "metis/zsh/loader.zsh" "$ZSHRC"; then
    echo "" >> "$ZSHRC"
    echo "# --- [ Metis AI Suite ] ---" >> "$ZSHRC"
    echo "$LOADER_LINE" >> "$ZSHRC"
    echo -e "${GREEN}  ✅ Integração completa adicionada ao ~/.zshrc${NC}"
else
    echo -e "${GRAY}  ℹ️  Integração já presente no ~/.zshrc${NC}"
fi

# B. Integração no ~/.bashrc (para funcionar mesmo no Bash padrão do Mint/Ubuntu)
BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    if ! grep -Fq "# --- [ Metis AI Suite ] ---" "$BASHRC"; then
        echo "" >> "$BASHRC"
        echo "# --- [ Metis AI Suite ] ---" >> "$BASHRC"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$BASHRC"
        echo "alias ia=\"$INSTALL_DIR/venv/bin/python $INSTALL_DIR/zsh/api_ask.py\"" >> "$BASHRC"
        echo "alias ai=\"ia\"" >> "$BASHRC"
        echo "alias ai-sync=\"$INSTALL_DIR/venv/bin/python $INSTALL_DIR/zsh/manage_models.py sync\"" >> "$BASHRC"
        echo -e "${GREEN}  ✅ Comandos 'metis', 'ia' e 'ai' integrados ao ~/.bashrc${NC}"
    fi
fi

# C. Checagem do Shell Padrão do Usuário
CURRENT_SHELL="$(basename "$SHELL")"
if [ "$CURRENT_SHELL" != "zsh" ] && command -v zsh &>/dev/null; then
    echo ""
    echo -e "${GOLD}💡 Dica de Shell:${NC} O seu shell padrão atual é o ${CYAN}${CURRENT_SHELL}${NC}."
    echo -e "   Para aproveitar todos os atalhos visuais e autocompletar avançado no terminal, o ZSH é recomendado."
    read -t 10 -p "   Deseja definir o ZSH como seu shell padrão agora? (s/N) [tempo limite 10s]: " trocar_shell || trocar_shell="n"
    case "$trocar_shell" in
        [sS][iI][mM]|[sS])
            if command -v chsh &>/dev/null; then
                chsh -s "$(which zsh)" 2>/dev/null || true
                echo -e "${GREEN}  ✅ Shell padrão alterado para ZSH! (Terá efeito no próximo login).${NC}"
            fi
            ;;
        *)
            echo -e "${GRAY}  ℹ️  Mantendo $CURRENT_SHELL como padrão. Os comandos principais funcionam normalmente em ambos.${NC}"
            ;;
    esac
fi

# Verificação de status de serviços
echo -e "\n${BORDER}╭─ Status de Serviços ────────────────────────────────────────────────────────────╮${NC}"
if command -v ollama &>/dev/null; then
    echo -e "${BORDER}│${NC}  ${GREEN}●${NC} Ollama Local:        ${GREEN}Detectado e pronto${NC}"
else
    echo -e "${BORDER}│${NC}  ${GRAY}○${NC} Ollama Local:        ${GRAY}Não detectado (opcional para modelos locais)${NC}"
fi

if command -v docker &>/dev/null; then
    echo -e "${BORDER}│${NC}  ${GREEN}●${NC} Docker / SearXNG:    ${GREEN}Detectado e pronto${NC}"
else
    echo -e "${BORDER}│${NC}  ${GRAY}○${NC} Docker / SearXNG:    ${GRAY}Não detectado (opcional para busca web)${NC}"
fi
echo -e "${BORDER}╰─────────────────────────────────────────────────────────────────────────────────╯${NC}"

# Painel Final de Sucesso
echo -e "\n${GOLD_BRIGHT}${BOLD}╭─────────────────────────────────────────────────────────────────────────────────╮${NC}"
echo -e "${GOLD_BRIGHT}${BOLD}│       🎉 INSTALAÇÃO DO METIS AI SUITE CONCLUÍDA COM SUCESSO!                    │${NC}"
echo -e "${BORDER}├─────────────────────────────────────────────────────────────────────────────────┤${NC}"
echo -e "${BORDER}│${NC}  ${GOLD}${BOLD}Comandos e Atalhos Prontos no Terminal ZSH:${NC}"
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + G]${NC}          Menu interativo FZF (Perguntas, notas e modelos)"
echo -e "${BORDER}│${NC}    ${CYAN}[Alt + H]${NC}           Histórico de prompts de IA"
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + X Ctrl + P]${NC} Autocomplete inteligente no prompt"
echo -e "${BORDER}│${NC}    ${CYAN}[metis]${NC}             Copiloto de diagnóstico e resolução de erros"
echo -e "${BORDER}│${NC}    ${CYAN}[Super + R]${NC}         Abre a interface visual do Metis de qualquer lugar"
echo -e "${BORDER}│${NC}    ${CYAN}[metis gui]${NC}         Comando para abrir a interface gráfica via terminal"
echo -e "${BORDER}│${NC}    ${CYAN}[ia <pergunta>]${NC}     Consulta rápida com suporte a pipes"
echo -e "${BORDER}│${NC}    ${CYAN}[gca]${NC}               Gerador automático de commits Git"
echo -e "${BORDER}│${NC}"
echo -e "${BORDER}│${NC}  ${GRAY_DARK}🔧 Configurações:${NC} Adicione suas chaves de API em ${GOLD}~/.config/metis/.env${NC}"
echo -e "${GOLD_BRIGHT}${BOLD}╰─────────────────────────────────────────────────────────────────────────────────╯${NC}"

if [ -n "$ZSH_VERSION" ]; then
    echo -e "\n${CYAN_SOFT}✨ Recarregando a sessão ZSH para ativar os atalhos agora...${NC}\n"
    exec zsh
else
    echo -e "\n${CYAN_SOFT}💡 Abra um novo terminal ou inicie o zsh para começar.${NC}\n"
fi
