---
name: claudex
description: 클로드가 의도 확인·설계·검토·질문을 맡고 파일 작성은 codex exec 에 위임하는 모드를 켜고 끈다. PreToolUse 훅으로 클로드의 직접 편집을 결정론적으로 차단한다. `/claudex` 로 토글, `/claudex on|off|status`.
disable-model-invocation: true
---

# claudex

**클로드는 묻고 설계하고 검토한다. 코드는 코덱스가 쓴다.**

클로드는 의도가 흐리면 사용자에게 되묻는다. 코덱스는 안 묻고 추측해서 만든다. 그런데 구현
품질과 요금제는 코덱스 쪽이 낫다. 이 모드는 둘을 갈라서, 사용자가 코덱스 터미널을 따로 열지
않고 클로드 세션 안에서만 대화하게 한다.

`/step-by-step` 과는 다르다. 그쪽은 단계마다 예고와 승인을 받는 리듬이고, 이쪽은 리듬 없이
상시 적용되는 위임 규칙이다.

## 토글

| 입력 | 동작 |
| --- | --- |
| `/claudex` | 현재 상태를 뒤집는다 |
| `/claudex on` | 켠다 |
| `/claudex off` | 끈다 |
| `/claudex status` | 켜짐/꺼짐만 보고한다 |

상태는 플래그 파일 하나로 저장한다. 있으면 켜짐, 없으면 꺼짐.

```bash
touch ~/.claude/claudex   # on
rm -f ~/.claude/claudex   # off
ls    ~/.claude/claudex   # status
```

토글한 뒤에는 바뀐 상태를 한 줄로 보고한다. 켰으면 "이제 파일 작성은 코덱스가 한다", 껐으면
"이제 클로드가 직접 고친다".

`~/.claude/settings.json` 에 훅이 등록되어 있어야 실제로 강제된다. 등록 방법은 아래
"설치" 절. `/claudex status` 시 훅 등록 여부도 함께 확인해 보고한다.

## 켜져 있을 때의 작업 방식

훅이 `Edit`·`Write`·`NotebookEdit` 과 Bash 의 파일 쓰기를 차단하므로, 아래 절차 외에는
파일을 고칠 방법이 없다.

### 1. 의도 확정 (클로드)

요구사항이 애매하면 **착수 전에** `AskUserQuestion` 으로 확정한다. 이 모드에서 클로드를
쓰는 이유가 이것이다. 산문으로 묻고 답을 기다리지 않는다.

선택지마다 `preview` 에 실제 코드나 화면 모양을 넣고, 추천안을 첫 번째에 두고 `(추천)` 을
붙인다.

### 2. 스펙 작성 (클로드)

코덱스는 이 대화의 맥락을 **하나도 못 받는다.** 스펙에 없으면 엉뚱한 걸 만든다.

- 고칠 파일의 경로와, 기존 코드에서 따라야 할 규약 (네이밍, 계층, 쓰는 라이브러리)
- 만들 타입·함수의 시그니처
- 건드리면 안 되는 범위
- 검증 방법 (돌릴 테스트나 빌드 명령)

말미에 이 한 줄을 반드시 붙인다.

```
애매한 지점이 있으면 추측해서 만들지 말고, NEEDS_INPUT: 으로 시작하는 질문 목록만 내고 멈춰라.
```

### 3. 위임 (코덱스)

```bash
codex exec -C <프로젝트 루트> --sandbox workspace-write --approve-for-me - <<'SPEC' 2>&1 | tail -40
<2단계 스펙 그대로>
SPEC
```

오래 걸리면 `run_in_background` 로 던지고, 기다리는 동안 다음 스펙을 쓴다.

### 4. NEEDS_INPUT 처리 (클로드 → 사용자 → 코덱스)

코덱스가 `NEEDS_INPUT:` 을 내고 멈췄으면, 그 질문을 클로드가 `AskUserQuestion` 으로
사용자에게 옮긴다. 코덱스 원문을 그대로 던지지 말고 선택지 형태로 재구성한다.

답이 나오면 세션을 이어붙인다.

```bash
codex exec resume --last "<사용자가 고른 답>" 2>&1 | tail -40
```

`--last` 는 현재 작업 디렉토리 기준 최신 세션을 잡는다. 다른 디렉토리를 오갔으면 세션 id 를
직접 지정한다.

### 5. 검토 (클로드)

`git diff` 를 **직접 읽는다.** 코덱스가 "했다"고 한 말을 믿지 않는다. 스펙과 다르거나 범위를
넘었으면 되돌리고 스펙을 고쳐 다시 시킨다.

검증 명령(테스트·빌드)을 **실제로 돌린다.** 통과 여부를 추측하지 않는다.

## 위임이 손해일 때

스펙 쓰는 비용이 코드 쓰는 비용보다 크면 위임이 손해다.

- 오타, 한 줄 수정, 시그니처 변경에 따른 호출부 정리
- 코덱스 결과를 검토한 뒤의 미세 교정
- 코덱스가 두 번 연속 스펙을 못 맞춘 지점

이때 훅을 우회하지 않는다. 사용자에게 "이건 직접 고치는 게 빠르다"고 보고하고
`/claudex off` 를 제안한 뒤, 사용자가 끄면 직접 고친다. 끝나면 다시 켤지 묻는다.

## 설치

### 1. 훅 등록 (동기화 범위 밖이라 수동)

`~/.claude/settings.json` 의 `hooks.PreToolUse` 에 항목을 추가한다.

```jsonc
"PreToolUse": [
  {
    "matcher": "Edit|Write|NotebookEdit|Bash",
    "hooks": [ { "type": "command",
        "command": "python3 \"$HOME/.claude/skills/claudex/claudex-guard.py\"" } ]
  }
]
```

### 2. 코덱스 호출 권한

같은 파일의 `permissions.allow` 에 `Bash(codex exec:*)` 를 넣는다. 없으면 위임할 때마다
승인 프롬프트가 뜬다.

### 3. 확인

```bash
python3 ~/.claude/skills/claudex/claudex-guard.py --selftest
```

## 한계

Bash 우회를 100% 막지는 못한다. `sed -i`, `tee`, 소스 파일로의 리다이렉트, 파일 heredoc은
잡지만 창의적 우회는 샌다. `Edit`·`Write` 경로가 막히면 코덱스로 가는 것이 자연스러워서
실질적으로 충분하다고 보고 그 선에서 멈춘 것이다. 새는 패턴이 실제로 관찰되면
`claudex-guard.py` 의 `BASH_WRITE` 에 추가한다.

훅은 플래그 파일이 없으면 첫 줄에서 그냥 통과한다. 꺼 두면 평소 클로드 그대로다.
