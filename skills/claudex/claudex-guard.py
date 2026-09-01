#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit|Bash): claudex 모드가 켜져 있을 때만
클로드의 직접 파일 편집을 막고 codex exec 위임으로 되돌려보낸다.

플래그 파일이 없으면 아무것도 하지 않는다 (기본 꺼짐). 켜고 끄는 것은 `/claudex`.
"""
import json
import os
import re
import sys

FLAG = os.path.expanduser("~/.claude/claudex")

# ponytail: 대표 패턴만 잡는다. Bash 우회를 100% 막지는 못하므로,
# 새는 패턴이 실제로 관찰되면 그때 여기에 추가한다.
SRC_EXT = r"py|ts|tsx|js|jsx|kt|kts|java|swift|go|rs|c|h|cpp|css|scss|html|vue|rb|php|sh"
BASH_WRITE = re.compile(
    r"\bsed\s+-i\b"                      # 인플레이스 치환
    r"|\btee\b"                          # 파이프로 파일 쓰기
    r"|>\s*[^\s|&>]*\.(?:" + SRC_EXT + r")\b"  # 소스 파일로 리다이렉트
    r"|>\s*[^\s|&>]+\s*<<"               # 파일로 heredoc
)

REASON = (
    "claudex 모드: 파일을 만들고 고치는 일은 codex exec 에 위임한다.\n"
    "\n"
    "  codex exec -m gpt-5.6-terra -c model_reasoning_effort=high \\\n"
    "    -C <프로젝트 루트> --sandbox workspace-write --approve-for-me - <<'SPEC' 2>&1 | tail -40\n"
    "  <스펙>\n"
    "  SPEC\n"
    "\n"
    "코덱스는 이 대화의 맥락을 하나도 못 받는다. 스펙에 반드시 넣을 것:\n"
    "  - 고칠 파일의 경로와, 기존 코드에서 따라야 할 규약 (네이밍, 계층, 쓰는 라이브러리)\n"
    "  - 만들 타입/함수의 시그니처\n"
    "  - 건드리면 안 되는 범위\n"
    "  - 말미에 한 줄: \"애매한 지점이 있으면 추측해서 만들지 말고,\n"
    "    NEEDS_INPUT: 으로 시작하는 질문 목록만 내고 멈춰라.\"\n"
    "\n"
    "NEEDS_INPUT 이 돌아오면 AskUserQuestion 으로 사용자에게 묻고,\n"
    "답을 codex exec resume --last -m gpt-5.6-terra -c model_reasoning_effort=high \"<답>\" 으로 이어붙인다. 사용자는 코덱스 터미널을 열지 않는다.\n"
    "끝나면 git diff 를 직접 읽고 검토한다. 코덱스가 \"했다\"고 한 말을 믿지 않는다.\n"
    "\n"
    "스펙 쓰는 비용이 코드 쓰는 비용보다 크면(오타, 한 줄 수정, 호출부 정리) 사용자에게\n"
    "그렇게 보고하고 /claudex off 를 제안한다. 우회해서 직접 고치지 않는다."
)


def main():
    if not os.path.exists(FLAG):
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name") == "Bash":
        cmd = (data.get("tool_input") or {}).get("command", "")
        if "claudex" in cmd:          # 모드를 끄는 명령은 스스로 막지 않는다
            sys.exit(0)
        if not BASH_WRITE.search(cmd):
            sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def selftest():
    block = [
        "sed -i 's/a/b/' src/App.tsx",
        "cat > src/App.tsx <<'EOF'",
        "echo 'x' > src/main.py",
        "cat foo | tee bar.txt",
    ]
    allow = [
        "codex exec -C . --sandbox workspace-write --approve-for-me - <<'SPEC'",
        "git diff",
        "npm test > /dev/null 2>&1",
        "npm test > /tmp/out.log",
        "grep -rn 'foo' src/",
    ]
    for c in block:
        assert BASH_WRITE.search(c), f"차단 실패: {c!r}"
    for c in allow:
        assert not BASH_WRITE.search(c), f"오탐: {c!r}"
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
