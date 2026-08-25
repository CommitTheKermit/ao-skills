#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_skills="$repo_root/codex/skills"
source_commands="$repo_root/codex/commands"
source_hooks="$repo_root/codex/hooks"
agent_skills="$HOME/.agents/skills"
codex_commands="$HOME/.Codex/commands"
codex_hooks="$HOME/.codex/hooks"
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

echo "Codex skills synced to $agent_skills"
echo "Codex commands synced to $codex_commands"
echo "Codex hooks synced to $codex_hooks"
