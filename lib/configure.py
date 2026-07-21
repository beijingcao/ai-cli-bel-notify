#!/usr/bin/env python3
"""Merge and remove the Codex and Claude Code BEL notification settings."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any


CODEX_VALUES = {
    "notifications": '["agent-turn-complete", "approval-requested"]',
    "notification_method": '"bel"',
    "notification_condition": '"always"',
}
MANAGED_CODEX_KEYS = tuple(CODEX_VALUES)
SECTION_RE = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
KEY_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>notifications|notification_method|notification_condition)\s*=\s*(?P<value>.*)$"
)


class ConfigError(RuntimeError):
    pass


def atomic_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else mode
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.chmod(temporary, current_mode)
    os.replace(temporary, path)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc


def load_state(path: Path) -> dict[str, Any]:
    state = load_json(path, {"version": 1, "components": {}})
    if not isinstance(state, dict) or not isinstance(state.get("components"), dict):
        raise ConfigError(f"Invalid installer state in {path}")
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def backup_file(path: Path, install_root: Path, label: str) -> None:
    if not path.exists():
        return
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = install_root / "backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_dir / label)


def find_tui_section(lines: list[str]) -> tuple[int | None, int | None]:
    start = None
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if match and match.group(1).strip() == "tui":
            start = index
            break
    if start is None:
        return None, None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if SECTION_RE.match(lines[index]):
            end = index
            break
    return start, end


def codex_key_locations(
    lines: list[str], start: int, end: int
) -> dict[str, tuple[int, re.Match[str]]]:
    locations: dict[str, tuple[int, re.Match[str]]] = {}
    for index in range(start + 1, end):
        match = KEY_RE.match(lines[index])
        if match and match.group("key") not in locations:
            locations[match.group("key")] = (index, match)
    return locations


def install_codex(config_path: Path, component_state: dict[str, Any] | None) -> dict[str, Any]:
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    had_final_newline = not text or text.endswith("\n")
    lines = text.splitlines()
    start, end = find_tui_section(lines)
    section_existed = start is not None

    if start is None or end is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[tui]")
        start = len(lines) - 1
        end = len(lines)

    locations = codex_key_locations(lines, start, end)
    if component_state and component_state.get("active"):
        original = component_state["original"]
        section_existed = bool(component_state.get("section_existed", True))
    else:
        original = {}
        for key in MANAGED_CODEX_KEYS:
            if key in locations:
                original[key] = {
                    "exists": True,
                    "value": locations[key][1].group("value").strip(),
                }
            else:
                original[key] = {"exists": False}

    for key, value in CODEX_VALUES.items():
        if key in locations:
            index, match = locations[key]
            lines[index] = f'{match.group("indent")}{key} = {value}'

    missing = [key for key in MANAGED_CODEX_KEYS if key not in locations]
    if missing:
        insertion = end
        while insertion > start + 1 and not lines[insertion - 1].strip():
            insertion -= 1
        lines[insertion:insertion] = [f"{key} = {CODEX_VALUES[key]}" for key in missing]

    output = "\n".join(lines)
    if had_final_newline or output:
        output += "\n"
    atomic_write_text(config_path, output)
    return {
        "active": True,
        "config_path": str(config_path),
        "section_existed": section_existed,
        "original": original,
        "expected": CODEX_VALUES,
    }


def uninstall_codex(component_state: dict[str, Any]) -> None:
    config_path = Path(component_state["config_path"])
    if not config_path.exists():
        return
    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start, end = find_tui_section(lines)
    if start is None or end is None:
        return

    locations = codex_key_locations(lines, start, end)
    original = component_state.get("original", {})
    expected = component_state.get("expected", CODEX_VALUES)
    edits: list[tuple[int, str | None]] = []

    for key in MANAGED_CODEX_KEYS:
        location = locations.get(key)
        if not location:
            continue
        index, match = location
        if match.group("value").strip() != expected[key]:
            print(f"Preserved user-modified Codex key: {key}")
            continue
        previous = original.get(key, {"exists": False})
        if previous.get("exists"):
            edits.append(
                (index, f'{match.group("indent")}{key} = {previous["value"]}')
            )
        else:
            edits.append((index, None))

    for index, replacement in sorted(edits, reverse=True):
        if replacement is None:
            del lines[index]
        else:
            lines[index] = replacement

    start, end = find_tui_section(lines)
    if (
        start is not None
        and end is not None
        and not component_state.get("section_existed", True)
        and all(not line.strip() for line in lines[start + 1 : end])
    ):
        del lines[start:end]
        while lines and not lines[-1].strip():
            lines.pop()

    output = "\n".join(lines)
    if output:
        output += "\n"
    atomic_write_text(config_path, output)


def command_hook(command: str) -> dict[str, Any]:
    return {"type": "command", "command": command, "timeout": 5}


def has_command(event_groups: list[Any], command: str) -> bool:
    for group in event_groups:
        if not isinstance(group, dict):
            continue
        for hook in group.get("hooks", []):
            if isinstance(hook, dict) and hook.get("command") == command:
                return True
    return False


def install_claude(settings_path: Path, command: str) -> dict[str, Any]:
    settings = load_json(settings_path, {})
    if not isinstance(settings, dict):
        raise ConfigError(f"Claude settings root must be an object: {settings_path}")
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ConfigError(f"Claude hooks must be an object: {settings_path}")

    stop_groups = hooks.setdefault("Stop", [])
    notification_groups = hooks.setdefault("Notification", [])
    if not isinstance(stop_groups, list) or not isinstance(notification_groups, list):
        raise ConfigError("Claude Stop and Notification hook entries must be arrays")

    if not has_command(stop_groups, command):
        stop_groups.append({"hooks": [command_hook(command)]})
    if not has_command(notification_groups, command):
        notification_groups.append(
            {
                "matcher": "permission_prompt|elicitation_dialog|agent_needs_input",
                "hooks": [command_hook(command)],
            }
        )

    atomic_write_text(settings_path, json.dumps(settings, indent=2) + "\n")
    return {
        "active": True,
        "settings_path": str(settings_path),
        "command": command,
    }


def uninstall_claude(component_state: dict[str, Any]) -> None:
    settings_path = Path(component_state["settings_path"])
    if not settings_path.exists():
        return
    settings = load_json(settings_path, {})
    if not isinstance(settings, dict):
        raise ConfigError(f"Claude settings root must be an object: {settings_path}")
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return

    command = component_state.get("command")
    for event in ("Stop", "Notification"):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        retained_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                retained_groups.append(group)
                continue
            retained_hooks = [
                hook
                for hook in group["hooks"]
                if not (
                    isinstance(hook, dict)
                    and hook.get("type") == "command"
                    and hook.get("command") == command
                )
            ]
            if retained_hooks:
                updated_group = dict(group)
                updated_group["hooks"] = retained_hooks
                retained_groups.append(updated_group)
        if retained_groups:
            hooks[event] = retained_groups
        else:
            hooks.pop(event, None)

    if not hooks:
        settings.pop("hooks", None)
    atomic_write_text(settings_path, json.dumps(settings, indent=2) + "\n")


def selected_components(args: argparse.Namespace) -> list[str]:
    components = []
    if args.codex:
        components.append("codex")
    if args.claude:
        components.append("claude")
    return components or ["codex", "claude"]


def run_install(args: argparse.Namespace, state: dict[str, Any], state_path: Path) -> None:
    install_root = Path(args.install_root).expanduser().resolve()
    components = state["components"]
    home = Path.home()

    for component in selected_components(args):
        if component == "codex":
            config_path = home / ".codex" / "config.toml"
            backup_file(config_path, install_root, "codex-config.toml")
            components["codex"] = install_codex(
                config_path, components.get("codex")
            )
            print(f"Configured Codex: {config_path}")
        else:
            settings_path = home / ".claude" / "settings.json"
            backup_file(settings_path, install_root, "claude-settings.json")
            hook_path = install_root / "bin" / "claude-bel-hook.sh"
            if not hook_path.exists():
                raise ConfigError(f"Claude BEL hook is missing: {hook_path}")
            command = shlex.quote(str(hook_path))
            components["claude"] = install_claude(settings_path, command)
            print(f"Configured Claude Code: {settings_path}")
    save_state(state_path, state)


def run_uninstall(args: argparse.Namespace, state: dict[str, Any], state_path: Path) -> None:
    components = state["components"]
    for component in selected_components(args):
        component_state = components.get(component)
        if not component_state or not component_state.get("active"):
            print(f"No active {component} configuration found")
            continue
        if component == "codex":
            uninstall_codex(component_state)
            print("Removed managed Codex settings")
        else:
            uninstall_claude(component_state)
            print("Removed managed Claude Code hooks")
        components.pop(component, None)

    if components:
        save_state(state_path, state)
    elif state_path.exists():
        state_path.unlink()


def run_status(state: dict[str, Any]) -> None:
    components = state["components"]
    print(
        "Codex BEL notifications: "
        + ("installed" if components.get("codex", {}).get("active") else "not installed")
    )
    print(
        "Claude Code BEL hooks: "
        + ("installed" if components.get("claude", {}).get("active") else "not installed")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "uninstall", "status"))
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--codex", action="store_true")
    parser.add_argument("--claude", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    install_root = Path(args.install_root).expanduser().resolve()
    state_path = install_root / "state.json"
    try:
        state = load_state(state_path)
        if args.action == "install":
            run_install(args, state, state_path)
        elif args.action == "uninstall":
            run_uninstall(args, state, state_path)
        else:
            run_status(state)
    except (ConfigError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
