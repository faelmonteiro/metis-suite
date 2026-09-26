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
    for c in python3 curl git jq xclip fc-cache fzf; do
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

        # Pacotes adicionais de terminal e drivers gráficos Qt
        echo -e "  ${GRAY}Instalando pacotes adicionais (FZF, drivers gráficos Qt)...${NC}"
        sudo apt-get install -y -qq fzf wl-clipboard libgl1 libegl1 libxkbcommon-x11-0 \
                   libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                   libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
                   libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 2>/dev/null || true
        echo -e "${GREEN}  ✅ Dependências do sistema instaladas com sucesso.${NC}"
    elif command -v dnf &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição baseada em Fedora/RedHat detectada (DNF).${NC}"
        sudo dnf install -y python3 python3-pip fzf curl git jq wl-clipboard xclip fontconfig mesa-libGL mesa-libEGL libxkbcommon-x11 xcb-util-cursor
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v pacman &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição baseada em Arch Linux detectada (Pacman).${NC}"
        sudo pacman -Sy --noconfirm python python-pip fzf curl git jq wl-clipboard xclip fontconfig libglvnd libxkbcommon-x11 xcb-util-cursor
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v zypper &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição openSUSE detectada (Zypper).${NC}"
        sudo zypper install -y python3 python3-pip fzf curl git jq wl-clipboard xclip fontconfig libglvnd libxkbcommon-x11-0 libxcb-cursor0
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v xbps-install &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição Void Linux detectada (XBPS).${NC}"
        sudo xbps-install -Sy python3 python3-pip fzf curl git jq wl-clipboard xclip fontconfig
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    elif command -v apk &>/dev/null; then
        echo -e "  ${CYAN_SOFT}📦 Distribuição Alpine Linux detectada (APK).${NC}"
        sudo apk add python3 py3-pip fzf curl git jq wl-clipboard xclip fontconfig
        echo -e "${GREEN}  ✅ Dependências instaladas com sucesso.${NC}"
    else
        echo -e "${RED}  ❌ Gerenciador de pacotes não identificado automaticamente.${NC}"
        echo "Por favor, instale manualmente: python3, python3-venv, fzf, curl, git e jq."
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
for d in app zsh bash bin assets; do
    [ -L "$INSTALL_DIR/$d" ] && rm -f "$INSTALL_DIR/$d"
done
rm -rf "$INSTALL_DIR/app/vision/assets" 2>/dev/null || true
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
if [ -f "$CONFIG_DIR/config_models.json" ]; then
    sed -i 's|qwen/qwen3.8-27b|llama-3.3-70b-versatile|g' "$CONFIG_DIR/config_models.json" 2>/dev/null || true
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

# 6. Criar atalhos executáveis, fontes personalizadas e Desktop Entry
echo -e "\n${CYAN}🚀 [5/6] Registrando lançadores, fontes e ícones no sistema...${NC}"
chmod +x "$INSTALL_DIR/bin/metis" "$INSTALL_DIR/app/vision/run.sh" 2>/dev/null || true
ln -sf "$INSTALL_DIR/bin/metis" "$BIN_DIR/metis"
ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/metis-vision"
ln -sf "$INSTALL_DIR/app/vision/run.sh" "$BIN_DIR/screenai"

# Instalar / Vincular Metis Screen (Go nativo)
if [ -f "$SCRIPT_DIR/bin/metis-screen" ]; then
    cp "$SCRIPT_DIR/bin/metis-screen" "$INSTALL_DIR/bin/metis-screen" 2>/dev/null || true
elif [ -f "$HOME/metis-screen/metis-screen" ]; then
    cp "$HOME/metis-screen/metis-screen" "$INSTALL_DIR/bin/metis-screen" 2>/dev/null || true
elif command -v go &>/dev/null; then
    echo -e "  ${CYAN}Compilando Metis Screen (Go)...${NC}"
    SCREEN_SRC="$HOME/metis-screen"
    if [ ! -d "$SCREEN_SRC" ]; then
        SCREEN_SRC="$(mktemp -d)/metis-screen-src"
        git clone --depth 1 "https://github.com/faelmonteiro/metis-terminal-assistent-ia-.git" "$SCREEN_SRC" --quiet 2>/dev/null || true
    fi
    if [ -d "$SCREEN_SRC" ]; then
        (cd "$SCREEN_SRC" && go build -o metis-screen main.go 2>/dev/null && cp metis-screen "$INSTALL_DIR/bin/metis-screen") || true
    fi
fi

if [ -f "$INSTALL_DIR/bin/metis-screen" ]; then
    chmod +x "$INSTALL_DIR/bin/metis-screen"
    ln -sf "$INSTALL_DIR/bin/metis-screen" "$BIN_DIR/metis-screen"
    ln -sf "$INSTALL_DIR/bin/metis-screen" "$BIN_DIR/explain" 2>/dev/null || true
    ln -sf "$INSTALL_DIR/bin/metis-screen" "$BIN_DIR/screen" 2>/dev/null || true
    if [ -w "/usr/local/bin" ]; then
        ln -sf "$INSTALL_DIR/bin/metis-screen" "/usr/local/bin/metis-screen" 2>/dev/null || true
        ln -sf "$INSTALL_DIR/bin/metis-screen" "/usr/local/bin/explain" 2>/dev/null || true
        ln -sf "$INSTALL_DIR/bin/metis-screen" "/usr/local/bin/screen" 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✅ Metis Screen (Go nativo) instalado com sucesso em $BIN_DIR/metis-screen.${NC}"
fi

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



### 6.5 Limpeza de Atalhos Globais de Sistema (Foco 100% em Atalhos de Terminal)
clean_global_desktop_shortcuts() {
    echo -e "\n${CYAN}🧹 [5.5/6] Limpando atalhos globais de sistema (mantendo apenas atalhos de terminal)...${NC}"

    # Garante acesso ao bus da sessão do usuário mesmo via SSH
    if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ -S "/run/user/$UID/bus" ]; then
        export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$UID/bus"
    fi

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

    echo -e "${GREEN}  ✅ Atalhos globais de sistema desativados e limpos com sucesso.${NC}"
}

clean_global_desktop_shortcuts

### 6.6 Configuração Opcional do Terminal Kitty & ZSH Isolado
KITTY_ENABLED=0
configure_kitty_terminal() {
    local kitty_conf="$HOME/.config/kitty/kitty.conf"

    if ! command -v kitty &>/dev/null && [ ! -f "$kitty_conf" ]; then
        echo ""
        echo -e "${GOLD}✨ Terminal Kitty (Opcional - Experiência Visual Completa):${NC}"
        echo -e "   O Kitty permite captura de tela 100% automática (sem mouse), digitação autônoma e ícones em alta definição."
        echo -e "   ${GRAY}Nota: Se você optar pelo Kitty, o ZSH será instalado e configurado EXCLUSIVAMENTE dentro dele.${NC}"
        echo -e "   ${GRAY}Seus outros terminais continuarão 100% livres e usando o Bash padrão do sistema.${NC}"
        local instalar_kitty="n"
        if [ -t 0 ]; then
            read -t 20 -p "   Deseja instalar o Kitty e configurá-lo integrado com ZSH e Metis? (s/N) [padrão: Não]: " instalar_kitty || instalar_kitty="n"
        fi
        case "$instalar_kitty" in
            [sS][iI][mM]|[sS])
                echo -e "  ${GRAY}Instalando Kitty e ZSH via gerenciador de pacotes...${NC}"
                if command -v apt-get &>/dev/null; then
                    sudo apt-get install -y -qq kitty zsh 2>/dev/null || true
                elif command -v dnf &>/dev/null; then
                    sudo dnf install -y kitty zsh 2>/dev/null || true
                elif command -v pacman &>/dev/null; then
                    sudo pacman -Sy --noconfirm kitty zsh 2>/dev/null || true
                elif command -v zypper &>/dev/null; then
                    sudo zypper install -y kitty zsh 2>/dev/null || true
                elif command -v xbps-install &>/dev/null; then
                    sudo xbps-install -Sy kitty zsh 2>/dev/null || true
                elif command -v apk &>/dev/null; then
                    sudo apk add kitty zsh 2>/dev/null || true
                fi

                if command -v kitty &>/dev/null; then
                    echo -e "${GREEN}  ✅ Terminal Kitty e ZSH instalados com sucesso!${NC}"
                    KITTY_ENABLED=1
                else
                    echo -e "${YELLOW}  ⚠️ Não foi possível instalar o Kitty automaticamente. Continuando com o terminal padrão.${NC}"
                    KITTY_ENABLED=0
                fi
                ;;
            *)
                echo -e "${GRAY}  ℹ️  Continuando apenas com os terminais padrão do sistema (Bash puro, sem ZSH).${NC}"
                KITTY_ENABLED=0
                ;;
        esac
    elif command -v kitty &>/dev/null || [ -f "$kitty_conf" ]; then
        echo ""
        echo -e "${GOLD}✨ Terminal Kitty detectado no sistema:${NC}"
        echo -e "   Deseja configurar o Kitty integrado com ZSH e Metis?"
        echo -e "   ${GRAY}(O ZSH será configurado apenas no Kitty; seus outros terminais permanecerão no Bash puro)${NC}"
        local configurar_kitty="s"
        if [ -t 0 ]; then
            read -t 15 -p "   Configurar Kitty com ZSH para o Metis? (S/n) [padrão: Sim]: " configurar_kitty || configurar_kitty="s"
        fi
        case "$configurar_kitty" in
            [nN][aA][oO]|[nN])
                echo -e "${GRAY}  ℹ️  Terminal Kitty não será modificado.${NC}"
                KITTY_ENABLED=0
                ;;
            *)
                if ! command -v zsh &>/dev/null; then
                    echo -e "  ${GRAY}Instalando ZSH para o Kitty...${NC}"
                    if command -v apt-get &>/dev/null; then
                        sudo apt-get install -y -qq zsh 2>/dev/null || true
                    elif command -v dnf &>/dev/null; then
                        sudo dnf install -y zsh 2>/dev/null || true
                    elif command -v pacman &>/dev/null; then
                        sudo pacman -Sy --noconfirm zsh 2>/dev/null || true
                    elif command -v zypper &>/dev/null; then
                        sudo zypper install -y zsh 2>/dev/null || true
                    elif command -v xbps-install &>/dev/null; then
                        sudo xbps-install -Sy zsh 2>/dev/null || true
                    elif command -v apk &>/dev/null; then
                        sudo apk add zsh 2>/dev/null || true
                    fi
                fi
                KITTY_ENABLED=1
                ;;
        esac
    fi

    if [ "$KITTY_ENABLED" -eq 1 ]; then
        mkdir -p "$HOME/.config/kitty"
        touch "$kitty_conf"
        local zsh_path
        zsh_path="$(which zsh 2>/dev/null || command -v zsh || echo "/usr/bin/zsh")"

        # Configura o shell do Kitty para abrir diretamente no ZSH
        if ! grep -Eq "^[[:space:]]*shell[[:space:]]" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# Shell padrão do Kitty com Metis (apenas no Kitty; terminais comuns usam Bash)" >> "$kitty_conf"
            echo "shell $zsh_path" >> "$kitty_conf"
        else
            sed -i "s|^[[:space:]]*shell[[:space:]].*|shell $zsh_path|g" "$kitty_conf" 2>/dev/null || true
        fi

        # Habilita cópia automática ao selecionar com o mouse no Kitty
        if ! grep -Eq "^[[:space:]]*copy_on_select[[:space:]]" "$kitty_conf"; then
            echo "" >> "$kitty_conf"
            echo "# Copia automaticamente o texto selecionado com o mouse para a área de transferência" >> "$kitty_conf"
            echo "copy_on_select yes" >> "$kitty_conf"
        fi

        # Higieniza configurações obsoletas ou inválidas no kitty.conf
        sed -i "/^[[:space:]]*clear_selection_on_clipboard_loss/d" "$kitty_conf" 2>/dev/null || true
        sed -i "s|^[[:space:]]*listen_on.*|listen_on unix:/tmp/mykitty|g" "$kitty_conf" 2>/dev/null || true

        sed -i "/.*metis-screen.*/d" "$kitty_conf" 2>/dev/null || true
        sed -i "/.*screen_launcher\.zsh.*/d" "$kitty_conf" 2>/dev/null || true
        sed -i "/.*explain_screen\.zsh.*/d" "$kitty_conf" 2>/dev/null || true
        sed -i "/# --- \[ Metis Explain Screen.*/d" "$kitty_conf" 2>/dev/null || true

        echo "" >> "$kitty_conf"
        echo "# --- [ Metis Explain Screen (Ctrl + Shift + E) - Go Nativo ] ---" >> "$kitty_conf"
        echo "allow_remote_control yes" >> "$kitty_conf"
        echo "listen_on unix:/tmp/mykitty" >> "$kitty_conf"
        echo "map ctrl+shift+e pipe @screen_scrollback none metis-screen" >> "$kitty_conf"
        echo -e "${GREEN}  ✅ Atalho [Ctrl + Shift + E] integrado ao Kitty chamando o Metis Screen (Go nativo).${NC}"
    fi
}

configure_kitty_terminal

# 7. Integrar aos shells (BASH e ZSH condicional ao Kitty)
echo -e "\n${CYAN}⚡ [6/6] Configurando integração de terminal...${NC}"

# A. Integração no ~/.zshrc (SOMENTE se Kitty estiver configurado com ZSH)
if [ "$KITTY_ENABLED" -eq 1 ]; then
    ZSHRC="$HOME/.zshrc"
    touch "$ZSHRC"
    sed -i '/# >>> METIS SUITE >>>/,/# <<< METIS SUITE <<</d' "$ZSHRC" 2>/dev/null || true
    cat << ZSHRC_EOF >> "$ZSHRC"

# >>> METIS SUITE >>>
# Se executado em terminal comum (fora do Kitty), redireciona imediatamente para o Bash
if [[ -z "\$KITTY_PID" && -z "\$KITTY_WINDOW_ID" && "\$TERM" != *"kitty"* && -o interactive ]]; then
    exec bash
fi
[[ -f "$INSTALL_DIR/zsh/loader.zsh" ]] && source "$INSTALL_DIR/zsh/loader.zsh"
# <<< METIS SUITE <<<
ZSHRC_EOF
    echo -e "${GREEN}  ✅ Integração do ZSH vinculada ao ~/.zshrc (para o Kitty).${NC}"
else
    # Remove qualquer integração residual do Metis no ~/.zshrc se Kitty não foi escolhido
    if [ -f "$HOME/.zshrc" ]; then
        sed -i '/# >>> METIS SUITE >>>/,/# <<< METIS SUITE <<</d' "$HOME/.zshrc" 2>/dev/null || true
        sed -i '/metis\/zsh\/loader\.zsh/d' "$HOME/.zshrc" 2>/dev/null || true
    fi
fi

# B. Integração no ~/.bashrc (UNIVERSAL para terminais do sistema)
BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    sed -i '/export PATH=".*\.local\/bin:\$PATH"/d' "$BASHRC" 2>/dev/null || true
    sed -i '/# >>> METIS SUITE >>>/,/# <<< METIS SUITE <<</d' "$BASHRC" 2>/dev/null || true
    sed -i '/# --- \[ Metis AI Suite \] ---/,/alias ai-sync=/d' "$BASHRC" 2>/dev/null || true

    BASH_LOADER_LINE="[[ -f \"$INSTALL_DIR/bash/loader.bash\" ]] && source \"$INSTALL_DIR/bash/loader.bash\""
    echo "" >> "$BASHRC"
    echo "# >>> METIS SUITE >>>" >> "$BASHRC"
    echo "$BASH_LOADER_LINE" >> "$BASHRC"
    echo "# <<< METIS SUITE <<<" >> "$BASHRC"
    echo -e "${GREEN}  ✅ Integração do Bash (Alt+E, Ctrl+G, Alt+H, metis) configurada no ~/.bashrc${NC}"
fi

# C. Isolamento Total de Shell: Garante que NENHUM terminal comum execute ZSH
# 1. Remove qualquer auto-launch de ZSH no ~/.bashrc
if [ -f "$BASHRC" ]; then
    sed -i '/# >>> METIS ZSH AUTO-LAUNCH >>>/,/# <<< METIS ZSH AUTO-LAUNCH <<</d' "$BASHRC" 2>/dev/null || true
    sed -i '/^[[:space:]]*exec[[:space:]]\+zsh/d' "$BASHRC" 2>/dev/null || true
    sed -i '/^[[:space:]]*\[\[.*exec zsh.*\]\]/d' "$BASHRC" 2>/dev/null || true
fi

# 2. Restaura o shell de login do usuário para Bash se tiver sido alterado para ZSH
CURRENT_LOGIN_SHELL="$(getent passwd "$USER" 2>/dev/null | cut -d: -f7 || echo "$SHELL")"
if [[ "$CURRENT_LOGIN_SHELL" == *"zsh"* ]]; then
    BASH_SYS_PATH="$(which bash 2>/dev/null || command -v bash || echo "/bin/bash")"
    if [ -x "$BASH_SYS_PATH" ]; then
        sudo -n chsh -s "$BASH_SYS_PATH" "$USER" 2>/dev/null || timeout 5 chsh -s "$BASH_SYS_PATH" "$USER" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Shell padrão do usuário configurado para o Bash (${BASH_SYS_PATH}).${NC}"
    fi
fi

CURRENT_SHELL="$(basename "${CURRENT_LOGIN_SHELL:-$SHELL}")"
if [ "$KITTY_ENABLED" -eq 1 ]; then
    echo -e "${GREEN}  ✅ O ZSH foi vinculado exclusivamente ao terminal Kitty (~/.config/kitty/kitty.conf).${NC}"
    echo -e "${GRAY}  ℹ️  Seus outros terminais permanecem 100% livres no Bash padrão.${NC}"
else
    echo -e "${GRAY}  ℹ️  Terminais do sistema operando 100% em Bash puro (sem ZSH).${NC}"
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
echo -e "${BORDER}│${NC}  ${GOLD}${BOLD}Atalhos do Terminal:${NC}"
echo -e "${BORDER}│${NC}    ${CYAN}[Alt + E]${NC}           Explain Screen no terminal comum (analisa seleção do mouse ou erro)"
if [ "$KITTY_ENABLED" -eq 1 ]; then
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + Shift + E]${NC}  Explain Screen no Kitty (captura scrollback completa)"
fi
echo -e "${BORDER}│${NC}    ${CYAN}[Ctrl + G]${NC}          Menu interativo FZF (Perguntas, notas e modelos)"
echo -e "${BORDER}│${NC}    ${CYAN}[Alt + H]${NC}           Histórico de prompts de IA"
echo -e "${BORDER}│${NC}"
echo -e "${BORDER}│${NC}  ${GOLD}${BOLD}Comandos Disponíveis:${NC}"
echo -e "${BORDER}│${NC}    ${CYAN}[metis]${NC}             Copiloto de terminal, diagnóstico e resolução de erros"
echo -e "${BORDER}│${NC}    ${CYAN}[metis gui]${NC}         Abre a interface gráfica moderna (GUI flutuante)"
echo -e "${BORDER}│${NC}    ${CYAN}[metis vision]${NC}      Abre o assistente visual de tela e OCR"
echo -e "${BORDER}│${NC}    ${CYAN}[metis explain]${NC}     Executa a análise de tela pelo terminal"
echo -e "${BORDER}│${NC}    ${CYAN}[metis update]${NC}      Atualiza o Metis para a versão mais recente"
echo -e "${BORDER}│${NC}    ${CYAN}[ia <pergunta>]${NC}     Consulta rápida de IA com suporte a pipes"
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
