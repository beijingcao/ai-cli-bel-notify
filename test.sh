#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
INSTALL_ROOT=${AI_CLI_BEL_HOME:-"$HOME/.local/share/ai-cli-bel-notify"}
PYTHON_BIN=${PYTHON_BIN:-python3}

if [ "${1:-}" != "--bell-only" ]; then
    if [ -f "$SCRIPT_DIR/lib/configure.py" ]; then
        "$PYTHON_BIN" "$SCRIPT_DIR/lib/configure.py" status --install-root "$INSTALL_ROOT"
    elif [ -f "$INSTALL_ROOT/lib/configure.py" ]; then
        "$PYTHON_BIN" "$INSTALL_ROOT/lib/configure.py" status --install-root "$INSTALL_ROOT"
    else
        printf 'Notification helper is not installed.\n' >&2
        exit 1
    fi
fi

printf '\007'
printf 'BEL sent. If no sound was heard, enable audible bell in the terminal settings.\n'
