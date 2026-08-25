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

mkdir -p "$agent_skills" "$codex_commands" "$codex_hooks"

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
cp "$source_hooks"/*.py "$codex_hooks/"

python3 - "$codex_hooks_config" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if path.exists():
    config = json.loads(path.read_text())
    for event in ("PreToolUse", "PostToolUse"):
        for entry in config.get("hooks", {}).get(event, []):
            commands = [hook.get("command", "") for hook in entry.get("hooks", [])]
            if any("chaekchaek-design-system-guard.py" in command for command in commands):
                matcher = entry.get("matcher", "")
                if "functions\\.exec" not in matcher:
                    entry["matcher"] = f"(?:{matcher}|^functions\\.exec$)"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
PY

echo "Codex skills synced to $agent_skills"
echo "Codex commands synced to $codex_commands"
echo "Codex hooks synced to $codex_hooks"
