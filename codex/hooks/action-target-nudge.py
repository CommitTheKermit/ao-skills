#!/usr/bin/env python3
"""변경 요청에 작업 대상과 완료 증거를 상기시키는 soft nudge."""

# usage-stats: hook action-target-nudge
import json
from pathlib import Path
import re
import subprocess
import sys


MUTATION = re.compile(
    r"(?:\b(?:add|build|change|commit|create|delete|deploy|edit|fix|implement|migrate|push|refactor|remove|rename|update|write)\b|"
    r"추가|구현|수정|변경|삭제|제거|생성|만들|고쳐|적용|커밋|푸시|배포|마이그레이션|리팩터)",
    re.IGNORECASE,
)
READ_ONLY = re.compile(r"(?:설명만|분석만|조회만|읽기만|수정하지|변경하지|보고만|진단만|설계만|추천|용어|상태만|PR 리뷰|review only|status only|do not (?:edit|change|modify))", re.IGNORECASE)
QUOTED_MUTATION_TERM = re.compile(r"(?:['\"`])(?:add|build|change|delete|edit|fix|implement|remove|update|write|추가|구현|수정|변경|삭제|제거|적용)(?:['\"`])", re.IGNORECASE)
TERM_MEANING = re.compile(r"(?:뜻|의미|무슨 말|what does|meaning|mean\b)", re.IGNORECASE)
IMPLEMENTATION_GUIDANCE = re.compile(
    r"(?:\bui\b|화면).{0,40}(?:구현|implementation).{0,30}(?:접근|방안|방식|방법|방향|전략|계획|설계|approach|strategy|plan|design)",
    re.IGNORECASE,
)
HOW_TO = re.compile(
    r"(?:\bhow\s+(?:do|can|should|to)\b|어떻게\s.{0,50}(?:하|해|할|고치|고쳐|수정|변경|구현)|(?:수정|변경|구현|추가|삭제|적용)(?:하는|할)\s*(?:방법|법|절차)|(?:방법|절차).{0,40}(?:설명|알려|가이드))",
    re.IGNORECASE,
)
CONTEXT = (
    "변경 작업 soft nudge: 실행 전에 operation, target repo, branch, device, artifact, "
    "source of truth, exclusions 중 이번 작업 결과를 바꿀 항목을 확인하세요. 해당 없는 항목은 생략합니다. "
    "완료라고 말하기 전에는 요청과 직접 연결된 최소 evidence를 실행하고 결과를 확인하세요. "
    "이 안내는 의미를 판정하거나 작업을 차단하지 않습니다."
)


def is_mutation(prompt: str) -> bool:
    return bool(MUTATION.search(prompt)) and not (
        READ_ONLY.search(prompt)
        or (QUOTED_MUTATION_TERM.search(prompt) and TERM_MEANING.search(prompt))
        or IMPLEMENTATION_GUIDANCE.search(prompt)
        or HOW_TO.search(prompt)
    )


def record_usage() -> None:
    subprocess.run(
        ["python3", str(Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"), "record", "hook", "action-target-nudge"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def self_test() -> None:
    assert is_mutation("로그인 버그 수정해줘")
    assert is_mutation("build and deploy the app")
    assert not is_mutation("로그인 흐름을 설명만 해줘")
    assert not is_mutation("왜 이 오류가 생기는지 분석해줘")
    assert not is_mutation("최근 세션 100개 조회")
    assert not is_mutation("PR 리뷰만 해줘")
    assert not is_mutation("구현하지 말고 설계만 추천해줘")
    assert not is_mutation("update라는 용어를 설명해줘")
    assert not is_mutation('"update"가 무슨 뜻이야?')
    assert not is_mutation('"수정"이 무슨 뜻이야?')
    assert not is_mutation("UI 구현 접근 방식만 설계해줘")
    assert not is_mutation("UI 구현 방안을 설계해줘")
    assert not is_mutation("design-only UI implementation plan")
    assert not is_mutation("로그인 화면을 수정하는 방법을 설명해줘")
    assert not is_mutation("어떻게 고쳐야 할지 설명해줘")
    assert not is_mutation("how to update dependencies")
    print("action_target_nudge: ok")


def main() -> None:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    prompt = str(payload.get("prompt", ""))
    if payload.get("hook_event_name") != "UserPromptSubmit" or not is_mutation(prompt):
        return
    record_usage()
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": CONTEXT,
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
