# grounding-guard

개념/사양에 대한 **출처 없는 단정(환각)**을 줄이기 위한 훅 스크립트 번들.
사용자 호출용 스킬이 아니라 `~/.claude/settings.json` 훅에서 부르는 스크립트 모음이다
(`knowledge-loop` 와 같은 패턴). 단일 진실 소스는 `ao-skills` 레포이고, `~/.claude/skills/`
로 동기화된다.

## 동작 (두 훅이 한 쌍)

1. **`grounding-nudge.sh`** - `UserPromptSubmit` 훅
   - 질문이 개념/사양 설명 요청(`GG_CONCEPT_RE` 매칭)이면 "답 쓰기 전에 근거를 확보하라"는
     컨텍스트를 주입하고, 이번 턴 플래그(`~/.claude/.grounding-guard/<session_id>.flag`)를 남긴다.
   - 안내문은 **Stop 훅의 통과조건과 1:1로 일치**한다: (A) 구체 사양·API 는 출처 확인 후
     `근거:` 표기, (B) 널리 알려진 표준·일반 개념은 출처 대신 `표준 개념` 으로 명시 + 불확실분
     `추정/미확인` 표기. 이렇게 앞 안내와 뒤 검사를 맞춰, 첫 답변이 곧바로 통과하고 **두 번
     쓰지 않게** 한다(되돌림은 사후 훅이라 한 번 막히면 곧 재작성 = 사용자가 두 번 읽음).
   - 근거: `UserPromptSubmit` 은 `prompt` 필드를 받고, exit 0 stdout 이 Claude 컨텍스트로 들어감.

2. **`verify-grounding.sh`** - `Stop` 훅
   - 플래그가 있는 턴(=개념질문)인데 ① 트랜스크립트에 출처 도구(Read/Grep/Glob/WebFetch 등)
     사용 흔적이 0이고 ② 답변에 '추정/미확인/표준 개념/출처:/근거:' 표기도 없으면 `exit 2`로
     **한 번** 되돌려 근거 확인 또는 불확실성·표준개념 표기를 요구한다.
   - 근거: `Stop` 은 `transcript_path`/`last_assistant_message`/`stop_hook_active` 를 받고,
     block 시 stderr/reason 이 다음 지시로 Claude 에 피드백됨. 8회 연속 차단 시 하네스가 종료.

`lib.sh` 가 공용 정규식과 트랜스크립트 파싱을 담는다.

## 안전장치

- 모든 실패는 **fail-open**(에러/누락 시 `exit 0`)이라 세션을 절대 막지 않는다.
- `stop_hook_active=true`(이미 훅으로 계속 진행 중)면 즉시 통과 + 플래그 1회 소비 →
  **최대 1회만 차단**. 무한루프/8회벽에 걸리지 않는다.
- 개념판별은 `grounding-nudge.sh` 한 곳에서만(플래그로 전달) → 두 훅 일관.

## 한계 (반드시 인지)

- 정규식 기반이라 false positive/negative 가 있다(의도적으로 과통과 쪽). 차단이 잦으면
  `lib.sh` 의 `GG_CONCEPT_RE` 를, 기억답변이 새면 `GG_SOURCE_RE` 를 좁힌다.
- "출처를 봤나"만 검사하지 "제대로 이해했나/'미확인'이 정직한가"는 강제하지 못한다.
  (모델이 형식적으로 '미확인'을 붙이면 통과한다.)

## settings.json 등록 (동기화 범위 밖이라 수동)

```jsonc
"hooks": {
  "UserPromptSubmit": [
    { "hooks": [ { "type": "command",
        "command": "\"$HOME/.claude/skills/grounding-guard/grounding-nudge.sh\"" } ] }
  ],
  "Stop": [
    { "hooks": [ { "type": "command",
        "command": "\"$HOME/.claude/skills/grounding-guard/verify-grounding.sh\"" } ] }
  ]
}
```

> `Stop`/`UserPromptSubmit` 은 matcher 미지원(항상 발동). 등록 후 새 세션부터 적용.
