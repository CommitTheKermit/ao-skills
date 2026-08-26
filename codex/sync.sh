#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_skills="$repo_root/codex/skills"
source_commands="$repo_root/codex/commands"
source_hooks="$repo_root/codex/hooks"
agent_skills="$HOME/.agents/skills"
codex_commands="$HOME/.Codex/commands"
codex_hooks="$HOME/.codex/hooks"
codex_hooks_config="$HOME/.codex/hooks.json"
legacy_skills="$HOME/.Codex/skills"
chaekchaek_root="/Users/ujeonghyeon/Desktop/dev/myDev/2026-chaekchaek"
chaekchaek_hooks="$chaekchaek_root/.codex/hooks"
chaekchaek_config="$chaekchaek_root/.codex/hooks.json"

mkdir -p "$agent_skills" "$codex_commands" "$codex_hooks" "$chaekchaek_hooks"

for source_dir in "$source_skills"/*; do
  [ -d "$source_dir" ] || continue
  [ -f "$source_dir/SKILL.md" ] || continue
  skill_dir="$(basename "$source_dir")"
  [ -n "$skill_dir" ] && [ "$skill_dir" != "." ] && [ "$skill_dir" != ".." ] || exit 1

  agent_target="$agent_skills/$skill_dir"
  if [ -d "$agent_target" ]; then
    rm -rf "$agent_target"
  fi
  cp -R "$source_dir" "$agent_target"

  legacy_target="$legacy_skills/$skill_dir"
  if [ -d "$legacy_target" ]; then
    rm -rf "$legacy_target"
  fi
done

cp "$source_commands"/*.md "$codex_commands/"

for hook in block-secrets.py action-target-nudge.py; do
  cp "$source_hooks/$hook" "$codex_hooks/$hook"
done
for hook in chaekchaek-branch-name-guard.py chaekchaek-pr-title-guard.py chaekchaek-design-system-guard.py; do
  cp "$source_hooks/$hook" "$chaekchaek_hooks/$hook"
  # Keep global files for old-session compatibility while registrations remain removed.
  cp "$source_hooks/$hook" "$codex_hooks/$hook"
done
for stale in "$chaekchaek_hooks/design_system_guard.py" "$chaekchaek_hooks/.DS_Store"; do
  [ ! -e "$stale" ] || rm -f "$stale"
done
rm -f "$codex_hooks/fix-emdash.py"

python3 - "$codex_hooks_config" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
config = json.loads(path.read_text()) if path.exists() else {"hooks": {}}
hooks = config.setdefault("hooks", {})
managed = (
    "block-secrets.py",
    "action-target-nudge.py",
    "fix-emdash.py",
    "chaekchaek-branch-name-guard.py",
    "chaekchaek-pr-title-guard.py",
    "chaekchaek-design-system-guard.py",
)
for event, entries in list(hooks.items()):
    kept = []
    for entry in entries:
        commands = [hook for hook in entry.get("hooks", []) if not any(name in hook.get("command", "") for name in managed)]
        if commands:
            entry["hooks"] = commands
            kept.append(entry)
    hooks[event] = kept

home = Path.home()
hooks.setdefault("PreToolUse", []).append({
    "matcher": r"^(?:Bash|Write|Edit|apply_patch|functions\.exec)$",
    "hooks": [{
        "type": "command",
        "command": f'/usr/bin/python3 "{home}/.codex/hooks/block-secrets.py"',
        "timeout": 5,
        "statusMessage": "Checking secret safety",
    }],
})
hooks.setdefault("UserPromptSubmit", []).append({
    "hooks": [{
        "type": "command",
        "command": f'/usr/bin/python3 "{home}/.codex/hooks/action-target-nudge.py"',
        "timeout": 5,
        "statusMessage": "Checking task target",
    }],
})
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
PY

python3 - "$chaekchaek_config" "$chaekchaek_hooks" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
directory = Path(sys.argv[2])
command = lambda name: f'/usr/bin/python3 "{directory / name}"'
config = {
    "description": "Chaekchaek local branch, PR, and design guards.",
    "hooks": {
        "PreToolUse": [
            {
                "matcher": r"^(?:Bash|exec_command|functions\.exec)$",
                "hooks": [
                    {"type": "command", "command": command("chaekchaek-branch-name-guard.py"), "timeout": 5},
                    {"type": "command", "command": command("chaekchaek-pr-title-guard.py"), "timeout": 5},
                ],
            },
            {
                "matcher": r"^(?:mcp__pencil__execute|apply_patch|Bash|functions\.exec)$",
                "hooks": [{"type": "command", "command": command("chaekchaek-design-system-guard.py"), "timeout": 5}],
            },
        ],
        "PostToolUse": [{
            "matcher": r"^mcp__pencil__(?:get_screenshot|execute)$",
            "hooks": [{"type": "command", "command": command("chaekchaek-design-system-guard.py"), "timeout": 5}],
        }],
        "UserPromptSubmit": [{
            "hooks": [{"type": "command", "command": command("chaekchaek-design-system-guard.py"), "timeout": 5}],
        }],
    },
}
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
PY

echo "Codex skills synced to $agent_skills"
echo "Codex commands synced to $codex_commands"
echo "Global Codex hooks synced to $codex_hooks"
echo "Chaekchaek hooks synced to $chaekchaek_root/.codex"
echo "Hook files changed: start a new Codex session and approve the new hook hashes when prompted."
