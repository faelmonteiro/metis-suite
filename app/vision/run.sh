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
PROJECT_ROOT="$(cd -P "$DIR/.." && pwd)"
VENV_PYTHON="$DIR/.venv/bin/python"

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

# ==============================================================================
# Controle de instância única (PID file)
# ==============================================================================
# Substitui o antigo `pkill -f "vision.main"`. O pkill trata o padrão como
# REGEX, e o "." funciona como curinga: "vision.main" também casava com
# "vision/main" — encerrava o editor/terminal com vision/main.py aberto.
# Aqui o encerramento é por PID e o argv é conferido token a token.
PIDFILE="${TMPDIR:-/tmp}/metis_vision.pid"

# Verdadeiro apenas se $1 for um processo python realmente executando
# "-m vision.main" (comparação exata, sem regex e sem curinga).
_pid_e_vision() {
    local pid="$1"
    [ -n "$pid" ] && [ -d "/proc/$pid" ] && [ -r "/proc/$pid/cmdline" ] || return 1
    tr '\0' '\n' < "/proc/$pid/cmdline" 2>/dev/null | grep -qxF -- "-m" || return 1
    tr '\0' '\n' < "/proc/$pid/cmdline" 2>/dev/null | grep -qxF "vision.main" || return 1
    return 0
}

_encerrar_vision_anterior() {
    local pid alvo=""

    # 1) Instância registrada no PID file
    if [ -f "$PIDFILE" ]; then
        pid="$(tr -cd '0-9' < "$PIDFILE" 2>/dev/null)"
        if _pid_e_vision "$pid"; then
            alvo="$pid"
        fi
        rm -f "$PIDFILE"
    fi

    # 2) Fallback: varre /proc por instâncias do Vision sem PID file
    #    (iniciadas por uma versão anterior deste script).
    if [ -z "$alvo" ]; then
        for d in /proc/[0-9]*; do
            pid="${d#/proc/}"
            [ "$pid" = "$$" ] && continue
            if _pid_e_vision "$pid"; then
                alvo="$alvo $pid"
            fi
        done
    fi

    [ -z "$alvo" ] && return 0

    for pid in $alvo; do
        kill -TERM "$pid" 2>/dev/null || true
    done

    # Aguarda até 3s pelo encerramento amigável antes de forçar
    local i vivo
    for i in $(seq 1 15); do
        vivo=""
        for pid in $alvo; do
            if _pid_e_vision "$pid"; then
                vivo="$vivo $pid"
            fi
        done
        [ -z "$vivo" ] && return 0
        sleep 0.2
    done

    for pid in $alvo; do
        if _pid_e_vision "$pid"; then
            kill -KILL "$pid" 2>/dev/null || true
        fi
    done
}

# Se não for modo headless, encerra instâncias anteriores para evitar janelas presas
if [[ "$*" != *"--headless"* ]]; then
    _encerrar_vision_anterior
fi

# Registra o PID antes do exec: o shell é substituído pelo python, que
# herda o mesmo PID. Um PID file obsoleto é descartado pela checagem de
# vivacidade acima, então não é preciso trap de limpeza.
echo $$ > "$PIDFILE"

# Executa o assistente como pacote a partir da raiz do Metis, passando todos os argumentos
cd "$PROJECT_ROOT"
exec "$VENV_PYTHON" -m vision.main "$@"

