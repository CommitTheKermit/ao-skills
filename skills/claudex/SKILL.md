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
codex exec -m gpt-5.6-terra -c model_reasoning_effort="high" --json \
  -C <프로젝트 루트> --approve-for-me - <<'CLAUDEX_SPEC' > /tmp/codex-last.jsonl 2>/dev/null
<2단계 스펙 그대로>
CLAUDEX_SPEC

jq -rf ~/.claude/skills/claudex/claudex-progress.jq --arg root "<프로젝트 루트>/" /tmp/codex-last.jsonl
```

모델과 추론 강도는 **매 호출 명시한다.** 코덱스 기본값(`~/.codex/config.toml` 의
`model = "gpt-5.6-sol"`, `model_reasoning_effort = "medium"`)은 대화형 작업 기준이다.
클로드가 의도를 확정하고 스펙까지 짜 준 구현 작업에는 더 센 쪽을 쓴다.

`--json` 은 코덱스가 고친 파일과 실행한 명령을 사용자에게 보이기 위해 붙인다. 마지막 40줄만
남기면 그 진행 상황은 보이지 않는다. `jq` 출력은 그대로 사용자에게 보여 준다. 코덱스가 한 일은
그 몇 줄에 압축되어 있다.

heredoc 과 `jq` 파이프를 한 줄에 잇지 않는다. 따옴표가 충돌해 셸이 깨질 수 있으므로 JSONL을
파일에 받은 뒤 `jq`를 별도 명령으로 실행한다. 종료 토큰은 스펙 본문에 없는 것으로 고른다. 특히
스펙 안에 `codex exec` 예시가 있으면 본문에 등장한 토큰에서 heredoc 이 끊기지 않게 주의한다.

원본 이벤트는 `/tmp/codex-last.jsonl` 에 남는다. 이상하면 그 파일을 직접 `jq`로 확인한다. 오래
걸리는 작업은 `run_in_background` 로 던지고, 도는 동안에도 같은 `jq` 명령으로 이 파일을 훑어
중간 진행 상황을 사용자에게 보고한다.

### 4. NEEDS_INPUT 처리 (클로드 → 사용자 → 코덱스)

코덱스가 `NEEDS_INPUT:` 을 내고 멈췄으면, 그 질문을 클로드가 `AskUserQuestion` 으로
사용자에게 옮긴다. 코덱스 원문을 그대로 던지지 말고 선택지 형태로 재구성한다.

답이 나오면 세션을 이어붙인다.

```bash
codex exec resume --last -m gpt-5.6-terra -c model_reasoning_effort="high" --json \
  "<사용자가 고른 답>" > /tmp/codex-last.jsonl 2>/dev/null

jq -rf ~/.claude/skills/claudex/claudex-progress.jq --arg root "<프로젝트 루트>/" /tmp/codex-last.jsonl
```

resume 은 세션을 이어받으므로 작업 루트와 승인 방식을 다시 지정하지 않는다. 그래서 위임할 때와
달리 `-C` 와 `--approve-for-me` 를 주면 에러가 난다. 클로드는 처음 위임했던 디렉토리에서 이 명령을
실행해야 `--last` 가 맞는 세션을 잡는다.

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

진행 표시에는 `jq`가 필요하다. macOS에는 `/usr/bin/jq`로 이미 있다.

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

## 코덱스 쪽 하네싱은 그대로 적용된다

`codex exec` 로 위임해도 코덱스에 설정해 둔 것들은 살아 있다. 2026-09-01 `codex-cli 0.151.0`
에서 `codex exec -s read-only` 로 실측했다.

| 항목 | 결과 | 확인 방법 |
| --- | --- | --- |
| 프로젝트 `AGENTS.md` | 적용 | 코덱스가 해당 파일의 문장을 그대로 인용 |
| 전역 `~/.codex/AGENTS.md` | 적용 | 위와 같은 응답에서 확인 |
| `~/.codex/config.toml` | 적용 | `--ignore-user-config` 를 주지 않는 한 로드된다 (`codex exec --help`) |
| ponytail 등 플러그인 | 적용 | 코덱스가 "Ponytail full 모드 적용 중"이라고 응답 |
| 스킬 | 적용 | 호출 가능한 스킬 이름을 나열함 |
| MCP 서버 | 적용 | 실행 중 MCP 서버 토큰 갱신 로그가 stderr 에 찍힘 |
| 훅 | **미확증** | 아래 |

훅은 간접 근거만 있다. `~/.codex/config.toml` 의 `[hooks.state]` 에 `trusted_hash` 가
저장되어 있고, `codex exec --help` 의 `--dangerously-bypass-hook-trust` 설명이 "persisted
hook trust 없이 enabled 훅을 실행한다"라고 되어 있어 exec 가 훅을 실행함을 전제한다. 다만
발동 조건 단어를 넣은 프롬프트와 뺀 대조군이 같은 응답을 내서 직접 관측에는 실패했다.
**적용된다고 추정하되 실측은 아님.**

따라서 위임한 작업의 커밋 규칙·문체 규칙은 코덱스 쪽 `AGENTS.md` 를 따른다. 클로드 쪽
`CLAUDE.md` 와 내용이 어긋나 있으면 위임 결과도 어긋난다.

## 한계

Bash 우회를 100% 막지는 못한다. `sed -i`, `tee`, 소스 파일로의 리다이렉트, 파일 heredoc은
잡지만 창의적 우회는 샌다. `Edit`·`Write` 경로가 막히면 코덱스로 가는 것이 자연스러워서
실질적으로 충분하다고 보고 그 선에서 멈춘 것이다. 새는 패턴이 실제로 관찰되면
`claudex-guard.py` 의 `BASH_WRITE` 에 추가한다.

훅은 플래그 파일이 없으면 첫 줄에서 그냥 통과한다. 꺼 두면 평소 클로드 그대로다.
