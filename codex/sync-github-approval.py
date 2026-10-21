#!/usr/bin/env python3
"""승인 훅만 설치·등록하며 다른 이벤트 핸들러와 설정을 보존한다."""
import argparse
import copy
import json
from pathlib import Path
import shlex
import shutil
import tempfile
import os

NAME = "github-create-approval-guard.py"
MATCHER = r"^(?:Bash|exec_command|functions\.exec|.*create_(?:issue|pull_request).*|.*github.*(?:graphql|api).*)$"


def configured(config, destination):
    result = copy.deepcopy(config)
    hooks = result.setdefault("hooks", {})
    for event, entries in hooks.items():
        kept = []
        for entry in entries:
            handlers = [h for h in entry.get("hooks", []) if NAME not in h.get("command", "")]
            if handlers:
                entry["hooks"] = handlers
                kept.append(entry)
        hooks[event] = kept
    for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
        entry = {"hooks":[{"type":"command", "command":f"/usr/bin/python3 {shlex.quote(str(destination / NAME))}",
                           "timeout":5, "statusMessage":"Checking GitHub creation approval"}]}
        if event != "UserPromptSubmit":
            entry["matcher"] = MATCHER
        hooks.setdefault(event, []).append(entry)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--config", type=Path, default=Path.home()/".codex/hooks.json")
    parser.add_argument("--destination", type=Path, default=Path.home()/".codex/hooks")
    args = parser.parse_args()
    source = Path(__file__).parent / "hooks" / NAME
    current = json.loads(args.config.read_text()) if args.config.exists() else {"hooks":{}}
    desired = configured(current, args.destination)
    if args.verify:
        assert current == desired, "승인 훅의 등록이 원본과 다릅니다."
        assert source.read_bytes() == (args.destination/NAME).read_bytes(), "승인 훅 설치본이 다릅니다."
        print("GitHub approval hook verification passed")
        return
    args.destination.mkdir(parents=True, exist_ok=True)
    args.config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, args.destination/NAME)
    fd, name = tempfile.mkstemp(dir=args.config.parent)
    with os.fdopen(fd, "w") as out:
        json.dump(desired, out, ensure_ascii=False, indent=2)
        out.write("\n")
    os.replace(name, args.config)
    print("GitHub approval hook synced")


if __name__ == "__main__":
    main()
