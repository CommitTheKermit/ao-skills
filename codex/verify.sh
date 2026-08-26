#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_skills="$repo_root/codex/skills"
source_hooks="$repo_root/codex/hooks"
chaekchaek_root="/Users/ujeonghyeon/Desktop/dev/myDev/2026-chaekchaek"

bad_refs="$(rg -n -i --glob 'SKILL.md' --glob '*.md' --glob '*.py' --glob '*.sh' --glob '!verify.sh' \
  '(~/.claude|\.claude/|CLAUDE\.md|CLAUDE_PROJECT_DIR|AskUserQuestion|codex exec.+위임)' \
  "$repo_root/codex" \
  | rg -v 'stt-refine\.md.*Oh My Claude Code' || true)"
if [ -n "$bad_refs" ]; then
  printf '%s\n' "$bad_refs" >&2
  exit 1
fi

source_names="$(
  find "$source_skills" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 \
    | while IFS= read -r -d '' skill_file; do sed -n 's/^name:[[:space:]]*//p' "$skill_file" | head -1; done \
    | sort -u
)"
installed_duplicates="$(
  for root_dir in "$HOME/.agents/skills" "$HOME/.Codex/skills"; do
    find "$root_dir" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 2>/dev/null \
      | while IFS= read -r -d '' skill_file; do sed -n 's/^name:[[:space:]]*//p' "$skill_file" | head -1; done
  done | sort | uniq -d
)"
duplicates="$(comm -12 <(printf '%s\n' "$source_names" | sed '/^$/d' | sort -u) <(printf '%s\n' "$installed_duplicates" | sed '/^$/d' | sort -u))"
if [ -n "$duplicates" ]; then
  printf 'Duplicate Codex skill names:\n%s\n' "$duplicates" >&2
  exit 1
fi

for skill_dir in "$source_skills"/*; do
  [ -f "$skill_dir/SKILL.md" ] || continue
  skill_name="$(sed -n 's/^name:[[:space:]]*//p' "$skill_dir/SKILL.md" | head -1)"
  [ -n "$skill_name" ] || { echo "Missing skill name: $skill_dir" >&2; exit 1; }
  rg -q -F "usage-stats: skill $skill_name" "$skill_dir/SKILL.md" || { echo "Missing usage-stats marker: $skill_dir" >&2; exit 1; }
  rg -q -F "record skill $skill_name" "$skill_dir/SKILL.md" || { echo "Missing usage-stats recorder: $skill_dir" >&2; exit 1; }
done

for hook in block-secrets action-target-nudge chaekchaek-branch-name-guard chaekchaek-pr-title-guard chaekchaek-design-system-guard; do
  file="$source_hooks/$hook.py"
  rg -q -F "usage-stats: hook $hook" "$file" || { echo "Missing usage-stats marker: $file" >&2; exit 1; }
  rg -q -F 'usage_stats.py' "$file" || { echo "Missing usage-stats recorder: $file" >&2; exit 1; }
  python3 "$file" --self-test
done

replay="$source_skills/knowledge-loop/replay-audit.py"
rg -q -F 'usage-stats: harness session-replay-audit' "$replay"
rg -q -F '"harness", "session-replay-audit"' "$replay"
python3 "$replay" --self-test
bash -n "$source_skills/knowledge-loop/knowledge-extract.sh"
rg -q -F '.payload.type=="turn_aborted"' "$source_skills/knowledge-loop/knowledge-extract.sh"
[ ! -e "$HOME/.codex/hooks/fix-emdash.py" ] || { echo "Stale fix-emdash.py remains installed" >&2; exit 1; }

python3 - "$repo_root" "$chaekchaek_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

repo = Path(sys.argv[1])
project = Path(sys.argv[2])
global_config = json.loads((Path.home() / ".codex/hooks.json").read_text())
local_config = json.loads((project / ".codex/hooks.json").read_text())

def commands(config):
    return [hook.get("command", "") for entries in config.get("hooks", {}).values() for entry in entries for hook in entry.get("hooks", [])]

global_commands = commands(global_config)
local_commands = commands(local_config)
assert any("block-secrets.py" in command for command in global_commands)
assert any("action-target-nudge.py" in command for command in global_commands)
assert any("check-commit-msg.py" in command for command in global_commands)
assert not any("fix-emdash.py" in command or "chaekchaek-" in command for command in global_commands)
for name in ("chaekchaek-branch-name-guard.py", "chaekchaek-pr-title-guard.py", "chaekchaek-design-system-guard.py"):
    assert any(name in command for command in local_commands)
assert not any("block-secrets.py" in command or "action-target-nudge.py" in command for command in local_commands)
post_matchers = [entry.get("matcher", "") for entry in local_config["hooks"]["PostToolUse"]]
assert any("get_screenshot" in matcher and "execute" in matcher for matcher in post_matchers)

for name in ("block-secrets.py", "action-target-nudge.py"):
    source = repo / "codex/hooks" / name
    installed = Path.home() / ".codex/hooks" / name
    assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(installed.read_bytes()).digest()
for name in ("chaekchaek-branch-name-guard.py", "chaekchaek-pr-title-guard.py", "chaekchaek-design-system-guard.py"):
    source = repo / "codex/hooks" / name
    installed = project / ".codex/hooks" / name
    assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(installed.read_bytes()).digest()
PY

echo "Codex skill verification passed"
