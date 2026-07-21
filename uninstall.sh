#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
INSTALL_ROOT=${AI_CLI_BEL_HOME:-"$HOME/.local/share/ai-cli-bel-notify"}
PYTHON_BIN=${PYTHON_BIN:-python3}

usage() {
    cat <<'EOF'
Usage: ./uninstall.sh [--all|--codex|--claude]

  --all      Remove Codex and Claude Code notification configuration (default)
  --codex    Remove Codex configuration only
  --claude   Remove Claude Code hooks only
  --help     Show this help
EOF
}

want_codex=0
want_claude=0
explicit_component=0

for arg in "$@"; do
    case "$arg" in
        --all)
            want_codex=1
            want_claude=1
            explicit_component=1
            ;;
        --codex)
            want_codex=1
            explicit_component=1
            ;;
        --claude)
            want_claude=1
            explicit_component=1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$arg" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ "$explicit_component" -eq 0 ]; then
    want_codex=1
    want_claude=1
fi

case "$INSTALL_ROOT" in
    ""|/|"$HOME")
        printf 'Refusing unsafe install directory: %s\n' "$INSTALL_ROOT" >&2
        exit 1
        ;;
esac

if [ -f "$SCRIPT_DIR/lib/configure.py" ]; then
    CONFIGURE="$SCRIPT_DIR/lib/configure.py"
elif [ -f "$INSTALL_ROOT/lib/configure.py" ]; then
    CONFIGURE="$INSTALL_ROOT/lib/configure.py"
else
    printf 'Cannot find configure.py. Nothing was changed.\n' >&2
    exit 1
fi

if [ "$want_codex" -eq 1 ] && [ "$want_claude" -eq 1 ]; then
    "$PYTHON_BIN" "$CONFIGURE" uninstall --install-root "$INSTALL_ROOT" --codex --claude
elif [ "$want_codex" -eq 1 ]; then
    "$PYTHON_BIN" "$CONFIGURE" uninstall --install-root "$INSTALL_ROOT" --codex
else
    "$PYTHON_BIN" "$CONFIGURE" uninstall --install-root "$INSTALL_ROOT" --claude
fi

if [ "$want_claude" -eq 1 ]; then
    rm -f "$INSTALL_ROOT/bin/claude-bel-hook.sh"
fi

if [ "$want_codex" -eq 1 ] && [ "$want_claude" -eq 1 ]; then
    rm -f "$INSTALL_ROOT/lib/configure.py" "$INSTALL_ROOT/uninstall.sh" "$INSTALL_ROOT/test.sh" "$INSTALL_ROOT/README.md"
    rmdir "$INSTALL_ROOT/bin" "$INSTALL_ROOT/lib" "$INSTALL_ROOT" 2>/dev/null || true
fi

printf 'Uninstall complete. Configuration backups, if present, remain in %s/backups\n' "$INSTALL_ROOT"
