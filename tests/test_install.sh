#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(CDPATH= cd -P "$(dirname "$0")/.." && pwd)
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

export HOME="$TEST_ROOT/home"
export AI_CLI_BEL_HOME="$TEST_ROOT/install"
mkdir -p "$HOME/.codex" "$HOME/.claude"

cat >"$HOME/.codex/config.toml" <<'EOF'
model = "gpt-5"

[tui]
notification_method = "osc9"
show_tooltips = true

[features]
example = true
EOF

cat >"$HOME/.claude/settings.json" <<'EOF'
{
  "permissions": {"defaultMode": "acceptEdits"},
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "/usr/local/bin/existing-hook"}
        ]
      }
    ]
  }
}
EOF

"$PROJECT_DIR/install.sh" --all
"$PROJECT_DIR/install.sh" --all

python3 - <<'PY'
import json
import os
from pathlib import Path

home = Path(os.environ["HOME"])
install_root = Path(os.environ["AI_CLI_BEL_HOME"])
codex = (home / ".codex/config.toml").read_text()
assert 'notifications = ["agent-turn-complete", "approval-requested"]' in codex
assert 'notification_method = "bel"' in codex
assert 'notification_condition = "always"' in codex
assert "show_tooltips = true" in codex
assert '[features]\nexample = true' in codex

settings = json.loads((home / ".claude/settings.json").read_text())
assert settings["permissions"]["defaultMode"] == "acceptEdits"

command = str(install_root / "bin/claude-bel-hook.sh")
all_hooks = []
for event in ("Stop", "Notification"):
    for group in settings["hooks"][event]:
        all_hooks.extend(group.get("hooks", []))

assert sum(h.get("command") == command for h in all_hooks) == 2
assert any(h.get("command") == "/usr/local/bin/existing-hook" for h in all_hooks)

state = json.loads((install_root / "state.json").read_text())
assert state["components"]["codex"]["active"]
assert state["components"]["claude"]["active"]
PY

hook_output=$(printf '{}\n' | "$AI_CLI_BEL_HOME/bin/claude-bel-hook.sh")
HOOK_OUTPUT="$hook_output" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["HOOK_OUTPUT"])
assert payload == {"terminalSequence": "\a"}
PY

python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["HOME"]) / ".codex/config.toml"
text = path.read_text()
path.write_text(text.replace('notification_condition = "always"', 'notification_condition = "inactive"'))
PY

"$PROJECT_DIR/uninstall.sh" --all

python3 - <<'PY'
import json
import os
from pathlib import Path

home = Path(os.environ["HOME"])
codex = (home / ".codex/config.toml").read_text()
assert 'notification_method = "osc9"' in codex
assert "notifications =" not in codex
assert 'notification_condition = "inactive"' in codex
assert "show_tooltips = true" in codex

settings = json.loads((home / ".claude/settings.json").read_text())
stop_hooks = settings["hooks"]["Stop"][0]["hooks"]
assert stop_hooks == [{"type": "command", "command": "/usr/local/bin/existing-hook"}]
assert "Notification" not in settings["hooks"]
PY

printf 'All install, idempotency, hook, and uninstall tests passed.\n'
