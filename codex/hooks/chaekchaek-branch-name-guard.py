#!/usr/bin/env python3
"""Chaekchaek의 새 Git 브랜치 이름이 이슈 번호로 시작하는지 검사한다."""

# usage-stats: hook chaekchaek-branch-name-guard
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys


PROJECT_ROOT = Path("/Users/ujeonghyeon/Desktop/dev/myDev/2026-chaekchaek")
BRANCH_NAME = re.compile(r"^[0-9]+-[a-z0-9][a-z0-9._-]*$")
CREATE_OPTIONS = {"switch": ("-c", "-C", "--create", "--force-create"), "checkout": ("-b", "-B", "--orphan")}


def record_usage() -> None:
    subprocess.run(
        ["python3", str(Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"), "record", "hook", "chaekchaek-branch-name-guard"],
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


def created_branch(segment):
    if not segment or segment[0] != "git":
        return None
    index = 1
    while index < len(segment) and segment[index] in ("-C", "-c"):
        index += 2
    if index >= len(segment):
        return None
    subcommand = segment[index]
    arguments = segment[index + 1:]
    if subcommand == "branch":
        return arguments[0] if arguments and not arguments[0].startswith("-") else None
    for position, argument in enumerate(arguments):
        for option in CREATE_OPTIONS.get(subcommand, ()):
            if argument == option and position + 1 < len(arguments):
                return arguments[position + 1]
            if argument.startswith(f"{option}="):
                return argument.split("=", 1)[1]
    return None


def invalid_branches(command):
    branches = filter(None, (created_branch(part) for part in command_segments(command)))
    return [branch for branch in branches if not BRANCH_NAME.fullmatch(branch)]


def is_project_path(value):
    try:
        path = Path(value).resolve()
        return path == PROJECT_ROOT or PROJECT_ROOT in path.parents
    except (OSError, TypeError):
        return False


def self_test():
    assert invalid_branches("git switch -c 100-branch-name") == []
    assert invalid_branches("cd android && git checkout -b wrong-name") == ["wrong-name"]
    assert invalid_branches("git branch -d old-branch") == []
    assert invalid_branches("git switch an-develop") == []
    assert is_project_path(PROJECT_ROOT / "android")
    assert not is_project_path(PROJECT_ROOT.parent)
    print("branch_name_guard: ok")


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
    if not isinstance(command, str) or not invalid_branches(command):
        return
    record_usage()
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "브랜치 이름은 이슈 번호로 시작해야 합니다. 예: 100-branch-name",
    }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
