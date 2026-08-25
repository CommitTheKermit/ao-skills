#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_skills="$repo_root/codex/skills"
design_guard="$repo_root/codex/hooks/chaekchaek-design-system-guard.py"

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
    | while IFS= read -r -d '' skill_file; do
        sed -n 's/^name:[[:space:]]*//p' "$skill_file" | head -1
      done \
    | sort -u
)"

installed_duplicates="$(
  for root_dir in "$HOME/.agents/skills" "$HOME/.Codex/skills"; do
    find "$root_dir" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 2>/dev/null \
      | while IFS= read -r -d '' skill_file; do
          sed -n 's/^name:[[:space:]]*//p' "$skill_file" | head -1
        done
  done | sort | uniq -d
)"

duplicates="$(
  comm -12 \
    <(printf '%s\n' "$source_names" | sed '/^$/d' | sort -u) \
    <(printf '%s\n' "$installed_duplicates" | sed '/^$/d' | sort -u)
)"

if [ -n "$duplicates" ]; then
  printf 'Duplicate Codex skill names:\n%s\n' "$duplicates" >&2
  exit 1
fi

for skill_dir in "$source_skills"/*; do
  [ -f "$skill_dir/SKILL.md" ] || continue
  skill_name="$(sed -n 's/^name:[[:space:]]*//p' "$skill_dir/SKILL.md" | head -1)"
  [ -n "$skill_name" ] || { echo "Missing skill name: $skill_dir" >&2; exit 1; }
  rg -q -F "usage-stats: skill $skill_name" "$skill_dir/SKILL.md" \
    || { echo "Missing usage-stats marker: $skill_dir" >&2; exit 1; }
  rg -q -F "record skill $skill_name" "$skill_dir/SKILL.md" \
    || { echo "Missing usage-stats recorder: $skill_dir" >&2; exit 1; }
done

rg -q -F "usage-stats: hook chaekchaek-design-system-guard" "$design_guard" \
  || { echo "Missing usage-stats marker: $design_guard" >&2; exit 1; }
rg -q -F '"hook",' "$design_guard" \
  || { echo "Missing usage-stats recorder: $design_guard" >&2; exit 1; }
python3 "$design_guard" --self-test

echo "Codex skill verification passed"
