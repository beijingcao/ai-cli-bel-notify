#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
INSTALL_ROOT=${AI_CLI_BEL_HOME:-"$HOME/.local/share/ai-cli-bel-notify"}
PYTHON_BIN=${PYTHON_BIN:-python3}

usage() {
    cat <<'EOF'
Usage: ./install.sh [--all|--codex|--claude] [--test]

  --all      Configure Codex and Claude Code (default)
  --codex    Configure Codex only
  --claude   Configure Claude Code only
  --test     Send one BEL after installation
  --help     Show this help
EOF
}

want_codex=0
want_claude=0
explicit_component=0
run_test=0

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
        --test)
            run_test=1
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

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    printf 'Python 3 is required. Set PYTHON_BIN if it is installed under another name.\n' >&2
    exit 1
fi

case "$INSTALL_ROOT" in
    ""|/|"$HOME")
        printf 'Refusing unsafe install directory: %s\n' "$INSTALL_ROOT" >&2
        exit 1
        ;;
esac

mkdir -p "$INSTALL_ROOT/bin" "$INSTALL_ROOT/lib"
cp "$SCRIPT_DIR/bin/claude-bel-hook.sh" "$INSTALL_ROOT/bin/claude-bel-hook.sh"
cp "$SCRIPT_DIR/lib/configure.py" "$INSTALL_ROOT/lib/configure.py"
cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_ROOT/uninstall.sh"
cp "$SCRIPT_DIR/test.sh" "$INSTALL_ROOT/test.sh"
cp "$SCRIPT_DIR/README.md" "$INSTALL_ROOT/README.md"
chmod 755 "$INSTALL_ROOT/bin/claude-bel-hook.sh" "$INSTALL_ROOT/uninstall.sh" "$INSTALL_ROOT/test.sh"

if [ "$want_codex" -eq 1 ] && [ "$want_claude" -eq 1 ]; then
    "$PYTHON_BIN" "$INSTALL_ROOT/lib/configure.py" install --install-root "$INSTALL_ROOT" --codex --claude
elif [ "$want_codex" -eq 1 ]; then
    "$PYTHON_BIN" "$INSTALL_ROOT/lib/configure.py" install --install-root "$INSTALL_ROOT" --codex
else
    "$PYTHON_BIN" "$INSTALL_ROOT/lib/configure.py" install --install-root "$INSTALL_ROOT" --claude
fi

printf 'Installed support files in %s\n' "$INSTALL_ROOT"

if [ "$run_test" -eq 1 ]; then
    "$INSTALL_ROOT/test.sh" --bell-only
fi
