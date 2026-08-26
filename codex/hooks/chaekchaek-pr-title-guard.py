#!/usr/bin/env python3
"""Chaekchaek Android PR 제목이 [AN]으로 시작하는지 검사한다."""

# usage-stats: hook chaekchaek-pr-title-guard
import json
from pathlib import Path
import shlex
import subprocess
import sys


PROJECT_ROOT = Path("/Users/ujeonghyeon/Desktop/dev/myDev/2026-chaekchaek")
PREFIX = "[AN]"


def record_usage() -> None:
    subprocess.run(
        ["python3", str(Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"), "record", "hook", "chaekchaek-pr-title-guard"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )


def command_segments(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    segment = []
    for token in lexer:
        if token and all(char in ";&|" for char in token):
            if segment:
                yield segment
                segment = []
        else:
            segment.append(token)
    if segment:
        yield segment


def title_argument(arguments):
    for index, argument in enumerate(arguments):
        if argument in {"-t", "--title"}:
            return arguments[index + 1] if index + 1 < len(arguments) else ""
        if argument.startswith("--title="):
            return argument.split("=", 1)[1]
        if argument.startswith("-t") and len(argument) > 2:
            return argument[2:].removeprefix("=")
    return None


def invalid_pr_commands(command):
    invalid = []
    for segment in command_segments(command):
        if not segment or segment[0] != "gh":
            continue
        try:
            index = segment.index("pr", 1)
        except ValueError:
            continue
        if index + 1 >= len(segment) or segment[index + 1] not in {"create", "edit"}:
            continue
        action = segment[index + 1]
        title = title_argument(segment[index + 2:])
        if action == "create" and title is None:
            invalid.append("gh pr create에는 --title이 필요합니다")
        elif title is not None and not title.startswith(PREFIX):
            invalid.append(f"PR 제목은 {PREFIX}으로 시작해야 합니다")
    return invalid


def is_project_path(value):
    try:
        path = Path(value).resolve()
        return path == PROJECT_ROOT or PROJECT_ROOT in path.parents
    except (OSError, TypeError):
        return False


def self_test():
    assert invalid_pr_commands('gh pr create --title "[AN] feat: 홈 연결"') == []
    assert invalid_pr_commands("gh pr create --fill") == ["gh pr create에는 --title이 필요합니다"]
    assert invalid_pr_commands('gh pr edit 136 --title "fix: 제목 수정"') == ["PR 제목은 [AN]으로 시작해야 합니다"]
    assert invalid_pr_commands("gh pr list") == []
    assert is_project_path(PROJECT_ROOT / "android")
    assert not is_project_path(PROJECT_ROOT.parent)
    print("pr_title_guard: ok")


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if not is_project_path(payload.get("cwd") or Path.cwd()):
        return
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or tool_input.get("cmd", "")
    violations = invalid_pr_commands(command) if isinstance(command, str) else []
    if not violations:
        return
    record_usage()
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ". ".join(violations),
    }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
