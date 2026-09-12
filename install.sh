#!/usr/bin/env bash
# =============================================================================
# METIS AI SUITE - UNIVERSAL LINUX INSTALLER
# =============================================================================
set -e

# Verificação para evitar execução acidental com sudo direto
if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo -e "\033[31m⚠️  ATENÇÃO: Não execute o instalador completo com 'sudo bash install.sh'.\033[0m"
    echo -e "   O instalador do Metis configura o ambiente local do seu usuário em $HOME."
    echo -e "   Execute simplesmente: \033[1mbash install.sh\033[0m"
    echo -e "   O script solicitará privilégios sudo apenas na etapa de pacotes do sistema."
    exit 1
fi

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
CLEANUP_INSTALL_TMP=0
INSTALL_REPO_TMP=""
KITTY_INSTALADO_AGORA=0
RECUSOU_KITTY_E_ZSH=0

cleanup_installer() {
    local ec=$?
    if [ "$CLEANUP_INSTALL_TMP" -eq 1 ] && [ -n "$INSTALL_REPO_TMP" ] && [ -d "$INSTALL_REPO_TMP" ]; then
        rm -rf "$INSTALL_REPO_TMP"
    fi
    if [ $ec -ne 0 ]; then
        echo -e "\n${RED}❌ A instalação foi interrompida ou encontrou um erro (código $ec).${NC}"
        echo -e "   Recursos temporários foram limpos. Seus arquivos pessoais foram preservados."
    fi
}
trap cleanup_installer EXIT INT TERM

# Se executado diretamente via curl/pipe ou fora da pasta do repositório
if [ ! -d "$SCRIPT_DIR/app" ] || [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo -e "📡 ${CYAN}Execução direta detectada. Baixando arquivos do Metis AI Suite...${NC}"
    INSTALL_REPO_TMP="$(mktemp -d)/metis-suite-src"
    git clone --depth 1 "https://github.com/faelmonteiro/metis-suite.git" "$INSTALL_REPO_TMP" --quiet || {
        echo -e "${RED}❌ Falha ao clonar repositório. Verifique sua conexão com a internet.${NC}"
        exit 1
    }
    SCRIPT_DIR="$INSTALL_REPO_TMP"
    CLEANUP_INSTALL_TMP=1
fi

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

    # Pré-verificação: se as dependências essenciais já estão instaladas, evita invocar sudo
    local deps_ok=1
    for c in python3 curl git jq xclip fc-cache zsh fzf; do
        if ! command -v "$c" &>/dev/null; then
            deps_ok=0
            break
        fi
    done
    if [ $deps_ok -eq 1 ] && python3 -c "import venv" &>/dev/null; then
        echo -e "${GREEN}  ✅ Todas as dependências essenciais do sistema já estão presentes.${NC}"
        return 0
    fi

    if command -v apt-get &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição baseada em Debian/Ubuntu/Linux Mint detectada (APT).${NC}"
        echo -e "  ${GRAY}Instalando ferramentas essenciais de terminal e Python...${NC}"
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-venv python3-pip curl git jq xclip fontconfig || {
            echo -e "${RED}  ❌ Falha ao instalar pacotes essenciais. Verifique sua conexão e tente novamente.${NC}"
            exit 1
        }
        echo -e "${GREEN}  ✅ Pacotes essenciais instalados.${NC}"

        # Pacotes opcionais em comando único silencioso
        echo -e "  ${GRAY}Instalando pacotes adicionais (ZSH, FZF, drivers gráficos Qt)...${NC}"
        sudo apt-get install -y -qq zsh fzf wl-clipboard libgl1 libegl1 libxkbcommon-x11-0 \
                   libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                   libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
                   libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 2>/dev/null || true
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
cp -r "$SCRIPT_DIR/bash" "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/bin" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/pyproject.toml" "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/update.sh" "$INSTALL_DIR/" 2>/dev/null || true
chmod +x "$INSTALL_DIR/bin/metis" "$INSTALL_DIR/app/vision/run.sh" "$INSTALL_DIR/uninstall.sh" "$INSTALL_DIR/update.sh" "$INSTALL_DIR/bash/loader.bash" "$INSTALL_DIR/zsh/screen_launcher.zsh" "$INSTALL_DIR/zsh/screen/preview_mouse.sh" 2>/dev/null || true
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
"$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR" --no-deps --quiet 2>/dev/null || true

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

# Corrige automaticamente modelos legados inválidos caso existam de instalações prévias
if [ -f "$CONFIG_DIR/config_models.json" ] && grep -Fq "openai/gpt-oss-120b" "$CONFIG_DIR/config_models.json"; then
    sed -i 's|openai/gpt-oss-120b|llama-3.3-70b-versatile|g' "$CONFIG_DIR/config_models.json" 2>/dev/null || true
fi

# 6. Criar atalhos executáveis, fontes personalizadas e Desktop Entry
echo -e "\n${CYAN}🚀 [5/6] Registrando lançadores, fontes e ícones no sistema...${NC}"
chmod +x "$INSTALL_DIR/bin/metis" "$INSTALL_DIR/app/vision/run.sh" 2>/dev/null || true
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
    [ -f "$APPS_DIR/metis-vision.desktop" ] && cp "$APPS_DIR/metis-vision.desktop" "$DESKTOP_DIR/metis-vision.desktop"
    chmod +x "$DESKTOP_DIR/metis.desktop" 2>/dev/null || true
    [ -f "$DESKTOP_DIR/metis-vision.desktop" ] && chmod +x "$DESKTOP_DIR/metis-vision.desktop" 2>/dev/null || true
    if command -v gio &>/dev/null; then
        gio set "$DESKTOP_DIR/metis.desktop" metadata::trusted true 2>/dev/null || true
        [ -f "$DESKTOP_DIR/metis-vision.desktop" ] && gio set "$DESKTOP_DIR/metis-vision.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✅ Ícones oficiais do Metis criados na Área de Trabalho ($DESKTOP_DIR).${NC}"
fi



### 6.5 Configuração Automática dos Atalhos Globais (Super + R e Ctrl + Alt + V)
configure_global_shortcut() {
    echo -e "\n${CYAN}⌨️  [5.5/6] Configuração de atalhos globais [Super + R] e [Ctrl + Alt + V]...${NC}"
    local set_shortcuts="s"
    if [ -t 0 ]; then
        read -t 15 -p "   Deseja configurar os atalhos globais de teclado no sistema? (S/n) [tempo limite 15s]: " set_shortcuts || set_shortcuts="s"
    fi
    case "$set_shortcuts" in
        [nN][aA][oO]|[nN])
            echo -e "${GRAY}  ℹ️  Configuração de atalhos de sistema ignorada a pedido do usuário.${NC}"
            return 0
            ;;
    esac

    local desktop="${XDG_CURRENT_DESKTOP:-$DESKTOP_SESSION}"
    desktop="$(echo "$desktop" | tr '[:upper:]' '[:lower:]')"
    local config_done=0

    # A. GNOME / Ubuntu / Pop!_OS / Fedora
    if [[ "$desktop" == *"gnome"* || "$desktop" == *"ubuntu"* || "$desktop" == *"pop"* ]] && command -v gsettings &>/dev/null; then
        local base_schema="org.gnome.settings-daemon.plugins.media-keys"
        local path_r="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-metis/"
        local path_v="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-screenai/"
        local custom_schema="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
        
        # Super + R (Metis AI)
        gsettings set "${custom_schema}:${path_r}" name "Metis AI" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_r}" command "$INSTALL_DIR/bin/metis gui" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_r}" binding "<Super>r" 2>/dev/null || true
        
        # Ctrl + Alt + V (Metis Vision)
        gsettings set "${custom_schema}:${path_v}" name "Metis Vision" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_v}" command "$INSTALL_DIR/bin/metis vision" 2>/dev/null || true
        gsettings set "${custom_schema}:${path_v}" binding "<Primary><Alt>v" 2>/dev/null || true

        # Anexa aos atalhos existentes sem sobrescrever os atalhos do usuário
        local current_list
        current_list=$(gsettings get "$base_schema" custom-keybindings 2>/dev/null || echo "@as []")
        if [[ "$current_list" == "@as []" || "$current_list" == "[]" || -z "$current_list" ]]; then
            gsettings set "$base_schema" custom-keybindings "['$path_r', '$path_v']" 2>/dev/null || true
        else
            local updated_list="$current_list"
            if [[ "$updated_list" != *"$path_r"* ]]; then
                updated_list="${updated_list%]}, '$path_r']"
            fi
            if [[ "$updated_list" != *"$path_v"* ]]; then
                updated_list="${updated_list%]}, '$path_v']"
            fi
            gsettings set "$base_schema" custom-keybindings "$updated_list" 2>/dev/null || true
        fi
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Ctrl + Alt + V] configurados para GNOME/Ubuntu.${NC}"
        config_done=1
    fi

    # B. Cinnamon / Linux Mint
    if [[ "$desktop" == *"cinnamon"* || "$desktop" == *"x-cinnamon"* ]] && command -v dconf &>/dev/null; then
        # Limpa entrada legada com caminho incorreto se existir
        dconf reset -f /org/cinnamon/desktop/keybindings/custom-screenai/ 2>/dev/null || true

        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/name "'Metis AI'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/command "'$INSTALL_DIR/bin/metis gui'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-metis/binding "['<Super>r', '<Primary><Alt>m']" 2>/dev/null || true

        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/name "'Metis Vision'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/command "'$INSTALL_DIR/bin/metis vision'" 2>/dev/null || true
        dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom-screenai/binding "['<Primary><Alt>v', '<Super>v', '<Super>z']" 2>/dev/null || true

        local cur_list
        cur_list="$(dconf read /org/cinnamon/desktop/keybindings/custom-list 2>/dev/null || echo "[]")"
        [[ -z "$cur_list" ]] && cur_list="[]"
        if [[ "$cur_list" == "[]" || "$cur_list" == "@as []" ]]; then
            dconf write /org/cinnamon/desktop/keybindings/custom-list "['custom-metis', 'custom-screenai']" 2>/dev/null || true
        else
            local upd_list="$cur_list"
            if [[ "$upd_list" != *"custom-metis"* ]]; then
                upd_list="${upd_list%]}, 'custom-metis']"
            fi
            if [[ "$upd_list" != *"custom-screenai"* ]]; then
                upd_list="${upd_list%]}, 'custom-screenai']"
            fi
            dconf write /org/cinnamon/desktop/keybindings/custom-list "$upd_list" 2>/dev/null || true
        fi
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Ctrl + Alt + V] configurados para Linux Mint (Cinnamon).${NC}"
        config_done=1
    fi

    # C. XFCE
    if [[ "$desktop" == *"xfce"* ]] && command -v xfconf-query &>/dev/null; then
        xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -n -t string -s "$INSTALL_DIR/bin/metis gui" 2>/dev/null || \
        xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>r" -s "$INSTALL_DIR/bin/metis gui" 2>/dev/null || true
        
        xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt>v" -n -t string -s "$INSTALL_DIR/bin/metis vision" 2>/dev/null || \
        xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt>v" -s "$INSTALL_DIR/bin/metis vision" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Ctrl + Alt + V] configurados para XFCE.${NC}"
        config_done=1
    fi

    # D. MATE Desktop
    if [[ "$desktop" == *"mate"* ]] && command -v dconf &>/dev/null; then
        dconf write /org/mate/desktop/keybindings/custom-metis/name "'Metis AI'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-metis/action "'$INSTALL_DIR/bin/metis gui'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-metis/binding "'<Mod4>r'" 2>/dev/null || true

        dconf write /org/mate/desktop/keybindings/custom-screenai/name "'Metis Vision'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-screenai/action "'$INSTALL_DIR/bin/metis vision'" 2>/dev/null || true
        dconf write /org/mate/desktop/keybindings/custom-screenai/binding "'<Control><Alt>v'" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Ctrl + Alt + V] configurados para MATE.${NC}"
        config_done=1
    fi

    # E. KDE Plasma
    if [[ "$desktop" == *"kde"* ]]; then
        local kw=""
        command -v kwriteconfig6 &>/dev/null && kw="kwriteconfig6"
        command -v kwriteconfig5 &>/dev/null && kw="kwriteconfig5"
        if [ -n "$kw" ]; then
            $kw --file kglobalshortcutsrc --group "Metis AI" --key "gui" "$INSTALL_DIR/bin/metis gui,none,Metis AI" 2>/dev/null || true
            $kw --file kglobalshortcutsrc --group "Metis Vision" --key "vision" "$INSTALL_DIR/bin/metis vision,Ctrl+Alt+V,Metis Vision" 2>/dev/null || true
            echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Ctrl + Alt + V] registrados para KDE Plasma.${NC}"
            config_done=1
        fi
    fi

    # F. Window Managers (Hyprland / Sway / i3)
    if [ -f "$HOME/.config/hypr/hyprland.conf" ]; then
        if ! grep -Fq "metis vision" "$HOME/.config/hypr/hyprland.conf"; then
            echo "" >> "$HOME/.config/hypr/hyprland.conf"
            echo "bind = \$mainMod, r, exec, [float; size 860 550; center; pin] $INSTALL_DIR/bin/metis gui" >> "$HOME/.config/hypr/hyprland.conf"
            echo "bind = CTRL ALT, v, exec, [float; size 620 390; center; pin] $INSTALL_DIR/bin/metis vision --mode active_window" >> "$HOME/.config/hypr/hyprland.conf"
            echo -e "${GREEN}  ✅ Atalhos [Super + R] e [Ctrl + Alt + V] adicionados ao ~/.config/hypr/hyprland.conf${NC}"
            config_done=1
        fi
    fi

    if [ -f "$HOME/.config/i3/config" ]; then
        if ! grep -Fq "metis vision" "$HOME/.config/i3/config"; then
            echo "" >> "$HOME/.config/i3/config"
            echo "bindsym \$mod+r exec $INSTALL_DIR/bin/metis gui" >> "$HOME/.config/i3/config"
            echo "bindsym Control+Mod1+v exec $INSTALL_DIR/bin/metis vision" >> "$HOME/.config/i3/config"
            echo -e "${GREEN}  ✅ Atalhos adicionados ao ~/.config/i3/config${NC}"
            config_done=1
        fi
    fi

    # G. Terminal Kitty (Experiência Visual Completa)
    local kitty_conf="$HOME/.config/kitty/kitty.conf"

    if ! command -v kitty &>/dev/null && [ ! -f "$kitty_conf" ]; then
        echo ""
        echo -e "${GOLD}✨ Experiência Visual Completa (Terminal Kitty):${NC}"
        echo -e "   O Kitty permite captura de tela 100% automática (sem mouse), digitação autônoma e ícones em alta definição."
        read -t 15 -p "   Deseja instalar o Kitty e configurá-lo integrado com ZSH e Metis? (s/N) [padrão: Não]: " instalar_kitty || instalar_kitty="n"
        case "$instalar_kitty" in
            [sS][iI][mM]|[sS])
                echo -e "  ${GRAY}Instalando terminal Kitty via gerenciador de pacotes...${NC}"
                if command -v apt-get &>/dev/null; then
                    sudo apt-get install -y -qq kitty 2>/dev/null || true
                elif command -v dnf &>/dev/null; then
                    sudo dnf install -y kitty 2>/dev/null || true
                elif command -v pacman &>/dev/null; then
                    sudo pacman -Sy --noconfirm kitty 2>/dev/null || true
                elif command -v zypper &>/dev/null; then
                    sudo zypper install -y kitty 2>/dev/null || true
                elif command -v xbps-install &>/dev/null; then
                    sudo xbps-install -Sy kitty 2>/dev/null || true
                elif command -v apk &>/dev/null; then
                    sudo apk add kitty 2>/dev/null || true
                fi

                if command -v kitty &>/dev/null; then
                    echo -e "${GREEN}  ✅ Terminal Kitty instalado com sucesso!${NC}"
                    KITTY_INSTALADO_AGORA=1
                else
                    echo -e "${YELLOW}  ⚠️ Não foi possível instalar o Kitty automaticamente. Continuando com o terminal atual.${NC}"
                fi
                ;;
            *)
                echo -e "${GRAY}  ℹ️  Continuando com seu terminal e shell padrão.${NC}"
                RECUSOU_KITTY_E_ZSH=1
                ;;
        esac
    fi

    if [ -f "$kitty_conf" ] || command -v kitty &>/dev/null; then
        mkdir -p "$HOME/.config/kitty"
        touch "$kitty_conf"
        local zsh_path
        zsh_path="$(which zsh 2>/dev/null || command -v zsh || echo "/usr/bin/zsh")"

        # Configura o shell do Kitty para abrir diretamente no ZSH
        if ! grep -Eq "^[[:space:]]*shell[[:space:]]" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# Shell padrão do Kitty com Metis" >> "$kitty_conf"
            echo "shell $zsh_path" >> "$kitty_conf"
        fi

        # Habilita cópia automática ao selecionar com o mouse no Kitty
        if ! grep -Eq "^[[:space:]]*copy_on_select[[:space:]]" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# Copia automaticamente o texto selecionado com o mouse para a área de transferência" >> "$kitty_conf"
            echo "copy_on_select yes" >> "$kitty_conf"
        fi

        # Desmarca a seleção no terminal quando a área de transferência for liberada
        if ! grep -Eq "^[[:space:]]*clear_selection_on_clipboard_loss[[:space:]]" "$kitty_conf"; then
            echo "clear_selection_on_clipboard_loss yes" >> "$kitty_conf"
        fi

        if ! grep -Fq "screen_launcher.zsh" "$kitty_conf" && ! grep -Fq "explain_screen.zsh" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# --- [ Metis Explain Screen (Ctrl + Shift + E) ] ---" >> "$kitty_conf"
            echo "allow_remote_control yes" >> "$kitty_conf"
            echo "listen_on unix:\${XDG_RUNTIME_DIR:-/tmp}/kitty_metis_\${UID}.sock" >> "$kitty_conf"
            echo "map ctrl+shift+e pipe @screen_scrollback none /bin/zsh -c \"if [ -f \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\" ]; then zsh \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\"; else zsh \\\"\$HOME/.ZSH/ai/screen_launcher.zsh\\\"; fi\"" >> "$kitty_conf"
            echo -e "${GREEN}  ✅ Atalho [Ctrl + Shift + E] e seleção de mouse integrados ao Kitty (~/.config/kitty/kitty.conf).${NC}"
        else
            sed -i "s|.*explain_screen\.zsh.*|map ctrl+shift+e pipe @screen_scrollback none /bin/zsh -c \"if [ -f \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\" ]; then zsh \\\"\$HOME/.local/share/metis/zsh/screen_launcher.zsh\\\"; else zsh \\\"\$HOME/.ZSH/ai/screen_launcher.zsh\\\"; fi\"|g" "$kitty_conf" 2>/dev/null || true
            echo -e "${GREEN}  ✅ Atalho [Ctrl + Shift + E] do Kitty atualizado para o Metis Screen Launcher.${NC}"
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
    echo "# >>> METIS SUITE >>>" >> "$ZSHRC"
    echo "$LOADER_LINE" >> "$ZSHRC"
    echo "# <<< METIS SUITE <<<" >> "$ZSHRC"
    echo -e "${GREEN}  ✅ Integração completa adicionada ao ~/.zshrc${NC}"
else
    echo -e "${GRAY}  ℹ️  Integração já presente no ~/.zshrc${NC}"
fi

# B. Integração no ~/.bashrc (para funcionar no Bash padrão do Mint/Ubuntu/Debian)
BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    # Limpa linhas antigas soltas de PATH e blocos anteriores do Metis
    sed -i '/export PATH=".*\.local\/bin:\$PATH"/d' "$BASHRC" 2>/dev/null || true
    sed -i '/# >>> METIS SUITE >>>/,/# <<< METIS SUITE <<</d' "$BASHRC" 2>/dev/null || true
    sed -i '/# --- \[ Metis AI Suite \] ---/,/alias ai-sync=/d' "$BASHRC" 2>/dev/null || true

    BASH_LOADER_LINE="[[ -f \"$INSTALL_DIR/bash/loader.bash\" ]] && source \"$INSTALL_DIR/bash/loader.bash\""
    echo "" >> "$BASHRC"
    echo "# >>> METIS SUITE >>>" >> "$BASHRC"
    echo "$BASH_LOADER_LINE" >> "$BASHRC"
    echo "# <<< METIS SUITE <<<" >> "$BASHRC"
    echo -e "${GREEN}  ✅ Integração universal (Alt+E, Ctrl+G, comandos IA) adicionada ao ~/.bashrc${NC}"
fi

# C. Checagem do Shell Padrão do Usuário
CURRENT_SHELL="$(basename "$SHELL")"
if [ "$CURRENT_SHELL" != "zsh" ] && command -v zsh &>/dev/null; then
    zsh_bin="$(which zsh 2>/dev/null || command -v zsh)"
    trocar_shell="n"

    if [ "$KITTY_INSTALADO_AGORA" -eq 1 ]; then
        echo ""
        echo -e "${GREEN}⚡ Terminal Kitty integrado com ZSH! Vinculando ZSH como padrão...${NC}"
        trocar_shell="s"
    elif [ "$RECUSOU_KITTY_E_ZSH" -eq 1 ]; then
        # O usuário já optou por manter o ambiente atual, não perguntamos de novo
        trocar_shell="n"
    else
        echo ""
        echo -e "${GOLD}💡 Dica de Shell:${NC} O seu shell padrão atual é o ${CYAN}${CURRENT_SHELL}${NC}."
        echo -e "   O Metis agora funciona perfeitamente no ${CYAN}${CURRENT_SHELL}${NC} com os atalhos [Alt + E] e [Ctrl + G]."
        echo -e "   (O ZSH é opcional, caso queira recursos adicionais como autocompletar inline com Ctrl+X Ctrl+P)."
        read -t 15 -p "   Deseja que seus novos terminais abram automaticamente em ZSH? (s/N) [padrão: Não]: " trocar_shell || trocar_shell="n"
    fi

    case "$trocar_shell" in
        [sS][iI][mM]|[sS])
            # 1. Garante que o ZSH está registrado em /etc/shells
            if [ -f "/etc/shells" ] && ! grep -Fxq "$zsh_bin" /etc/shells 2>/dev/null; then
                sudo sh -c "echo '$zsh_bin' >> /etc/shells" 2>/dev/null || true
            fi

            # 2. Registra a troca no sistema operacional
            if command -v usermod &>/dev/null; then
                sudo usermod -s "$zsh_bin" "$USER" 2>/dev/null || true
            fi
            if command -v chsh &>/dev/null; then
                chsh -s "$zsh_bin" 2>/dev/null || true
            fi

            # 3. Transição Imediata: ativação automática ao abrir novo terminal
            # Evita ter que reiniciar ou fazer logout da interface gráfica
            if [ -f "$BASHRC" ]; then
                if ! grep -Fq "METIS ZSH AUTO-LAUNCH" "$BASHRC"; then
                    echo "" >> "$BASHRC"
                    echo "# >>> METIS ZSH AUTO-LAUNCH >>>" >> "$BASHRC"
                    echo "if [ -t 1 ] && [ -x \"$zsh_bin\" ] && [ -z \"\$METIS_NO_AUTO_ZSH\" ]; then" >> "$BASHRC"
                    echo "    export SHELL=\"$zsh_bin\"" >> "$BASHRC"
                    echo "    exec \"$zsh_bin\"" >> "$BASHRC"
                    echo "fi" >> "$BASHRC"
                    echo "# <<< METIS ZSH AUTO-LAUNCH <<<" >> "$BASHRC"
                fi
            fi

            echo -e "${GREEN}  ✅ ZSH ativado com sucesso! Qualquer novo terminal abrirá direto no ZSH.${NC}"
            ;;
        *)
            echo -e "${GRAY}  ℹ️  Mantendo $CURRENT_SHELL como seu shell padrão. A integração foi configurada no ~/.bashrc com sucesso!${NC}"
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
echo -e "${BORDER}│${NC}  ${GOLD}${BOLD}Comandos e Atalhos Prontos no Terminal (ZSH & BASH):${NC}"
echo -e "${BORDER}│${NC}    ${CYAN}[Alt + E]${NC}           Explain Screen (analisa texto selecionado com mouse ou erro)"
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + G]${NC}          Menu interativo FZF (Perguntas, notas e modelos)"
echo -e "${BORDER}│${NC}    ${CYAN}[Alt + H]${NC}           Histórico de prompts de IA"
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + X Ctrl + P]${NC} Autocomplete inteligente no prompt (ZSH)"
echo -e "${BORDER}│${NC}    ${CYAN}[metis]${NC}             Copiloto de diagnóstico e resolução de erros"
echo -e "${BORDER}│${NC}    ${CYAN}[metis explain]${NC}     Executa o explain screen diretamente pelo terminal"
echo -e "${BORDER}│${NC}    ${CYAN}[metis update]${NC}      Atualiza o Metis para a versão mais recente"
echo -e "${BORDER}│${NC}    ${CYAN}[Super + R]${NC}         Abre a interface visual do Metis de qualquer lugar"
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + Alt + V]${NC}    Abre o Metis Vision (Análise visual de tela/OCR) de qualquer lugar"
echo -e "${BORDER}│${NC}    ${CYAN}[metis gui]${NC}         Comando para abrir a interface gráfica via terminal"
echo -e "${BORDER}│${NC}    ${CYAN}[metis vision]${NC}      Comando para abrir o assistente visual via terminal"
echo -e "${BORDER}│${NC}    ${CYAN}[ia <pergunta>]${NC}     Consulta rápida com suporte a pipes"
echo -e "${BORDER}│${NC}    ${CYAN}[gca]${NC}               Gerador automático de commits Git"
echo -e "${BORDER}│${NC}"
echo -e "${BORDER}│${NC}  ${GRAY_DARK}🔧 Configurações:${NC} Adicione suas chaves de API em ${GOLD}~/.config/metis/.env${NC}"
echo -e "${GOLD_BRIGHT}${BOLD}╰─────────────────────────────────────────────────────────────────────────────────╯${NC}"

# Limpeza de diretório temporário se foi criado na instalação via curl
if [ "$CLEANUP_INSTALL_TMP" -eq 1 ] && [ -n "$SCRIPT_DIR" ]; then
    rm -rf "$SCRIPT_DIR"
fi

if [ -n "$ZSH_VERSION" ]; then
    echo -e "\n${CYAN_SOFT}✨ Recarregando a sessão ZSH para ativar os atalhos agora...${NC}\n"
    exec zsh
elif [ -n "$BASH_VERSION" ]; then
    echo -e "\n${CYAN_SOFT}✨ Instalação pronta! Para ativar os atalhos no Bash agora, execute: ${GOLD}source ~/.bashrc${NC}\n"
else
    echo -e "\n${CYAN_SOFT}💡 Abra um novo terminal para começar a usar o Metis.${NC}\n"
fi
