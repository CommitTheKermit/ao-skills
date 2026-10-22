# ao-skills

Claude Code와 Codex에서 사용하는 개인 스킬(Skill)과 슬래시 커맨드(Slash Command) 모음.

## 구성

```
ao-skills/
├── skills/
│   ├── ao-skill-update/     # 스킬/커맨드 변경 워크플로우 스킬
│   │   └── SKILL.md
│   ├── check-android-review-readiness/ # Play 심사 준비 상태 점검 스킬
│   │   └── SKILL.md
│   ├── claude-design-handoff/ # claude.ai/design 핸드오프 링크로 디자인 소스 최신화 스킬
│   │   └── SKILL.md
│   ├── handoff-css-guard/   # 핸드오프 CSS 검증 하네스 설치 (css-guard 훅 + validate-handoff)
│   │   ├── SKILL.md
│   │   └── assets/          # css-guard.mjs · validate-handoff.mjs · css-guard.sh · stylelintrc.json
│   ├── github-pr-review/    # GitHub PR 검증 및 인라인 리뷰 코멘트 스킬
│   │   └── SKILL.md
│   ├── grounding-guard/     # 개념 출처 강제 훅 번들 (UserPromptSubmit+Stop, 호출용 스킬 아님)
│   │   ├── README.md
│   │   ├── lib.sh
│   │   ├── grounding-nudge.sh
│   │   └── verify-grounding.sh
│   ├── knowledge-loop/      # 세션 지식 추출(훅) + 수동 승격 리뷰 스킬
│   │   ├── SKILL.md
│   │   └── knowledge-extract.sh
│   ├── release-commit/      # 배포/릴리스 직후 release 커밋을 고정 포맷으로 작성하는 스킬
│   │   └── SKILL.md
│   ├── record-android-review-failure/ # Play 심사 실패 사례 수집 스킬
│   │   ├── SKILL.md
│   │   └── references/failure-cases.md
│   ├── step-by-step/        # 단계별 구현·검증 워크플로우 스킬
│   │   └── SKILL.md
│   └── todo/                # 프로젝트별/전역 TODO 관리 스킬 (+ 세션 훅)
│       ├── SKILL.md
│       └── todo-session.py
├── commands/
│   ├── learn-by-doing.md    # /learn-by-doing - 사용자가 직접 쓸 코드 조각 요청
│   ├── socratic-learn.md    # /socratic-learn - 소크라테스식 학습 모드 진입
│   ├── session-handoff.md   # /session-handoff - 세션 문맥 핸드오프 산출물 생성
│   ├── stt-refine.md        # /stt-refine - STT 녹취록을 검수본·요약본으로 변환
│   ├── pr-todo-notion.md    # /pr-todo-notion - PR을 노션 체크박스 TODO로 정리
│   ├── pr-description.md    # /pr-description - PR 디스크립션 작성
│   ├── pr-review-answer.md  # /pr-review-answer - PR 리뷰 답변 작성
│   └── ao-skill-update.md   # /ao-skill-update - 스킬/커맨드 변경+동기화+커밋+푸시
├── codex/                   # Codex 전용 원본과 동기화·검증 스크립트
│   ├── skills/
│   ├── commands/
│   ├── sync.sh
│   └── verify.sh
└── changelog/               # 주차(ISO week)별 변경내역 아카이브 (YYYY-Www.md)
```

`skills/`, `commands/`는 Claude용이고 `codex/`는 Codex용이다. 두 실행 환경의 전역 경로와
도구명이 다르므로 같은 이름의 스킬을 한 디렉터리에서 공유하지 않는다.

## 스킬 vs 커맨드

> 2026-06-12 공식 문서 기준, 커스텀 커맨드는 스킬로 **통합**됐다. 둘 다 `/이름` 호출이 생기고, 둘 다 메타데이터(name+description)가 상시 로드되며 본문은 발동 시에만 로드된다. 상시 토큰 비용은 형태가 아니라 `disable-model-invocation: true` 여부로 결정된다(설정 시 0, 명시 호출은 계속 가능). 상세: `~/.claude/knowledge/docs/skill-vs-command-token-cost.md`

| 구분 | 커스텀 커맨드 | 스킬 |
|------|--------------|------|
| 호출 | `/명령` + 조건 만족 시 자동 발동 | `/명령` + 조건 만족 시 자동 발동 |
| 구조 | 단일 `.md` 파일 | 디렉토리 + `SKILL.md` (+ 보조 자원) |
| 상시 토큰 | description 상시 로드 (opt-out 가능) | 동일 |
| 용도 | 단일 프롬프트 재사용 | 보조 스크립트/자원이 필요한 워크플로우 패키징 |

## 설치

### Claude 전역 설치

```bash
# 이 레포를 임의 위치에 클론
git clone https://github.com/CommitTheKermit/ao-skills.git
cd ao-skills

# 스킬/커맨드를 ~/.claude 아래에 복사
mkdir -p ~/.claude/skills ~/.claude/commands
cp -R skills/* ~/.claude/skills/
cp commands/* ~/.claude/commands/
```

### 프로젝트 단위 설치

```bash
# 프로젝트 루트에서
mkdir -p .claude/skills .claude/commands
cp -R /path/to/ao-skills/skills/* .claude/skills/
cp /path/to/ao-skills/commands/* .claude/commands/
```

설치 후 Claude Code를 재시작하면 인식됩니다.

### Codex 전역 설치

```bash
cd /path/to/ao-skills
bash codex/sync.sh
bash codex/verify.sh
```

Codex 스킬은 `~/.agents/skills/`, 커맨드는 `~/.Codex/commands/`에 설치된다. 동기화 과정에서
과거 `~/.Codex/skills/`에 복사돼 중복 등록된 ao-skills 사본만 제거한다. 적용은 새 Codex
세션부터 확실하게 반영된다.

## 스킬 목록

> 스킬/커맨드는 기능상 동일하다(위 "스킬 vs 커맨드" 참고). 부속 파일(훅 스크립트 등)이 필요한 워크플로우만 스킬 디렉터리로 두고, 단일 프롬프트 문서는 커맨드 파일로 둔다.

### ao-skill-update
이 레포의 스킬/커스텀 커맨드를 추가/수정/삭제한 뒤 실행 환경별 전역 경로로 동기화하고 커밋과 푸시까지 자동 처리하는 워크플로우. Codex에서는 `codex/` 원본만 편집한다.

발동 표현: "스킬 만들자", "스킬 수정", "커맨드 추가", "커맨드 변경", "스킬 동기화" 등.

### home-server (Codex)
로컬 SSH 별칭으로 개인 홈서버에 접속해 상태·프로젝트·서비스·예약 작업을 확인하고 요청된 원격 작업을 수행한다. Windows 원격 셸의 `Path`, 권한, 인코딩, 인증 컨텍스트와 TLS 오류를 안전하게 처리하며 접속 정보와 비밀값은 공개 스킬 원본에 저장하지 않는다.

발동 표현: "홈서버 접속", "서버에서 확인", "홈서버에서 실행", "Windows 서버 작업" 등.

### home-server-2
전용 SSH 별칭으로 두 번째 Windows 홈서버에 접속해 프로젝트 배포, 서비스 확인, Android 에뮬레이터와 앱 설치 작업을 수행한다. 기존 홈서버와 접속 설정, 프로세스, 복구 상태를 섞지 않는다.

발동 표현: "홈서버2 접속", "새 홈서버에 반영", "홈서버2에서 앱 설치" 등.

### intent-first
코드 구현, 수정, 리팩터링, 리뷰에서 코드 길이보다 사용자의 행동과 도메인 의도가 이름, 타입, 책임, 테스트에 명확히 드러나는지를 우선한다. 현재 요구사항을 설명하지 않는 추상화는 추가하지 않는다.

발동 범위: 코드 구현, 수정, 리팩터링, 리뷰 작업 전반.

### learn-by-implementing
학습자가 실제 코드를 이해하며 구현할 때 관련 코드 위치를 먼저 보여주고, 예측 질문과 설명을 거쳐 승인된 작은 단계만 구현·검증한다. 코드 작성 위임 수준을 유지하고, 매 구현 단계에서 수정 파일의 비자명한 결정 이유와 제약을 확인해 필요한 곳에 기록한다.

발동 표현: "이유를 공부하며 구현", "정답부터 말하지 말고 힌트", "코드 위치를 보여주며 같이 구현", `$learn-by-implementing` 등.

### build-signed-aab
Android 앱의 단위 테스트와 release bundle 빌드를 실행하고, Play 제출용 AAB의 서명·application ID·버전·런처 아이콘을 검증한 뒤 버전명 파일로 보관한다. 버전과 패키지명은 자동 변경하지 않는다.

발동 표현: "AAB 빌드", "서명 AAB", "심사용 번들", "bundleRelease", "Play 업로드 파일 만들어줘" 등.

### check-android-review-readiness
Android 프로젝트와 Play Console 자료를 최신 Google 공식 정책 및 누적된 실제 심사 실패 사례에 대조하고 Gradle 검사를 실행해 `통과 가능`·`실패 위험`·`확인 불가`로 판정한다. 실제 승인 결과는 보장하지 않는다.

발동 표현: "안드로이드 심사 통과할까", "Play 심사 테스트", "출시 전 정책 점검", "리젝 위험 검사" 등.

### claudex
클로드가 의도 확인·설계·검토·질문을 맡고 **파일 작성은 `codex exec` 에 위임**하는 모드를 켜고 끈다. `claudex-guard.py`(PreToolUse)가 플래그 파일 `~/.claude/claudex` 가 있을 때만 `Edit`·`Write`·`NotebookEdit` 과 Bash 의 파일 쓰기(`sed -i`, `tee`, 소스 파일 리다이렉트, 파일 heredoc)를 `deny` 하고, 차단 이유로 위임 절차 전문을 되돌려준다. 코덱스가 막히면 `NEEDS_INPUT:` 으로 멈추고 클로드가 `AskUserQuestion` 으로 사용자에게 옮긴 뒤 `codex exec resume --last` 로 이어붙여, 사용자가 코덱스 터미널을 열 일이 없다. 위임 호출은 `-m gpt-5.6-terra -c model_reasoning_effort="high"` 로 고정한다. `--json` 이벤트는 진행 표시 필터로 고친 파일과 실행 명령을 압축해 보여 준다. 플래그가 없으면 훅은 첫 줄에서 통과하므로 기본은 꺼짐. `~/.claude/settings.json` 훅 등록은 동기화 범위 밖이라 수동.

발동 표현: `/claudex`, `/claudex on|off|status` (`disable-model-invocation: true`).

### grounding-guard
개념/사양을 **출처 확인 없이 단정하는 환각**을 줄이는 훅 스크립트 번들(사용자 호출용 스킬 아님, `knowledge-loop` 와 같은 훅 컨테이너 패턴). `grounding-nudge.sh`(UserPromptSubmit)가 개념질문에 "출처부터 확인하라" 컨텍스트를 주입하고 이번 턴 플래그를 남기면, `verify-grounding.sh`(Stop)가 그 턴에 출처 도구 사용 흔적도 '추정/미확인' 표기도 없을 때 `exit 2`로 한 번 되돌려 보완을 요구한다. fail-open + `stop_hook_active` + 플래그 1회 소비로 최대 1회만 차단. `~/.claude/settings.json` 훅 등록은 동기화 범위 밖이라 수동(상세: `skills/grounding-guard/README.md`).

### knowledge-loop
Codex 최신 user root JSONL 세션을 `replay-audit.py`로 익명 집계하고, 검증된 지식 후보만 AGENTS.md 규칙, 스킬, 영구 문서로 수동 승격한다. subagent, 주입 wrapper, heartbeat는 제외하며 원문, 경로, 세션 ID, 비밀값은 출력하지 않는다. 실시간 SessionEnd 추출은 replay 오탐 검증 전까지 등록하지 않는다.

### claude-design-handoff
claude.ai/design 핸드오프 링크(`api.anthropic.com/v1/design/...`)를 받아 디자인 번들을 내려받고(gzip bin → gunzip+tar 압축해제), 번들의 README와 prod 산출물(`app-prod.jsx`/`styles-prod.css` 등)·`chats/` 트랜스크립트를 근거로 프로젝트의 디자인 소스를 시안과 정확히 동기화한다. 텍스트 설명만으로 추측 구현하지 않는다. 함께 온 구체적 변경 지시도 추가 반영.

발동 표현: "Fetch this design file, read its readme, and implement..." 형식 또는 `api.anthropic.com/v1/design/` 링크 붙여넣기.

### handoff-css-guard
claude.ai/design export(핸드오프) CSS 를 옮길 때 빌드·`tsc`·`vitest` 가 못 잡는 "문법상 valid 인데 규칙이 통째로 죽는" 잠복 버그(주석 안 `별표+슬래시` 조기종료 등)·누락 CSS 변수·셀렉터 불일치·stale 번들을 잡는 자동화 하네스를 대상 프로젝트에 **설치**한다. `assets/` 의 검증된 스크립트(`css-guard.mjs`/`validate-handoff.mjs`/`css-guard.sh`/`stylelintrc.json`)를 복사하고, 편집 즉시 PostToolUse 훅(구문 무결성+누락 변수, 실패 시 block)과 수동 `npm run validate-handoff`(+stylelint·셀렉터 리포트·stale `--live` diff)를 배선한다. 사람용 체크리스트는 두지 않고 자동화 도구만 둔다. `claude-design-handoff` 의 자매 도구.

발동 표현: "핸드오프 CSS 검증/가드 붙여줘", "디자인 export 적용 재발 방지 하네스", "css-guard 설치" 등.

### incident-postmortem
조사와 수정이 끝난 장애를 `docs/incidents/`에 포스트모템(요약, 영향, 타임라인, 근본 원인, 증거, 조치, 런북, 미해결)으로 남긴다. 인덱스와 프로젝트 `AGENTS.md`/`CLAUDE.md`에 라우팅을 걸어 다음 장애 때 사람과 에이전트가 증상부터 대조하게 한다. 템플릿은 `assets/template.md`.

발동 표현: "포스트모템", "인시던트 기록", "장애 문서로 남겨", "이 문제 상황 문서화", "/incident-postmortem" 등.

### github-pr-review (Claude)
GitHub PR의 전체 diff와 호출 경로, 관련 테스트를 검토하고 재현 가능한 문제만 변경 줄에 인라인 코멘트로 제출한다. 문제가 없으면 빈 리뷰를 만들지 않는다.

발동 표현: "리뷰해줘", "PR 리뷰", "리뷰 돌려줘", "이상한 부분 코멘트해줘" 등.

### sol-two-pass-pr-review (Codex)
독립된 GPT-6.1 Sol high 리뷰어 2명으로 PR을 검토하고 수정한 뒤, 새로운 2명으로 다시 검토하고 수정한다. 차수별 수정점은 PR 인라인 리뷰로 남기고 발견 사항과 수정 내용을 같은 표 형식으로 보고한다.

원본: [`codex/skills/sol-two-pass-pr-review/SKILL.md`](codex/skills/sol-two-pass-pr-review/SKILL.md)

발동 표현: "$sol-two-pass-pr-review", "Sol high 2명으로 리뷰하고 수정 후 다시 독립 리뷰" 등.

### release-commit
배포/릴리스 직후 남기는 release 커밋을 고정 포맷(`chore(release): vX.Y.Z 배포`)으로 작성한다. 직전 release 이후의 `git log`를 뽑아 변경 목록·배포 대상·버전 증감을 본문에 채워, 요약 한두 줄로 끝나 추적이 안 되는 빈약한 release 커밋을 막는다.

발동 표현: "release 커밋", "버전 커밋", "릴리스 커밋", "배포 커밋 정리" 등.

### run-android-app
Android 앱을 에뮬레이터나 연결 기기에 실행한다. 일반 실행에서는 `android run --debug`를 사용하지 않으며 사용자가 디버거 연결이나 브레이크포인트 실행을 명시한 경우에만 디버거 대기 모드를 사용한다.

발동 표현: "앱 실행해줘", "에뮬레이터 띄워줘", "Android 앱 설치하고 실행" 등.

### android-emulator-lease
Android 에뮬레이터를 사용하는 Claude Code·Codex 세션마다 AVD 임대를 원자적으로 획득하고 실제 serial을 연결한다. 전역 PreToolUse 훅은 임대되지 않은 에뮬레이터의 시작, 설치, 입력, 종료와 adb 서버 전체 조작을 실행 전에 차단한다. 임대 없이 실행 중인 AVD는 자동 인수하지 않는다.

발동 표현: Android 에뮬레이터, `adb`, `android run`, 연결 기기 Gradle 작업을 사용하는 모든 요청.

### record-android-review-failure
사용자가 제공한 Play Console 거절 통지·스크린샷·설명에서 개인정보를 제거하고 실패 조건과 검출·예방 방법을 공용 사례집에 누적한 뒤 Git으로 공유한다. 중복 사례는 새로 만들지 않고 기존 항목을 보강한다.

발동 표현: "심사 실패 사례 추가", "리젝 사유 기록", "이 실패 요소를 다음 심사 점검에 반영해줘" 등.

### step-by-step
Codex 구현 작업을 검증 가능한 작은 단계로 나누고, 단계마다 범위 승인·구현·검증·보고·커밋을 반복한다. 보고할 때는 전체 진행 단계 체크리스트를 완료 섹션 위에 표시한다.

발동 표현: "$step-by-step", "/step-by-step", "한 단계씩 구현해줘" 등.

### todo
프로젝트별/전역 TODO 를 등록·완료·조회·삭제하고, 항목별 문맥 파일을 연결한다. Claude는 `~/.claude/todo.md`, Codex는 `~/.Codex/todo.md`를 사용하며 각 플랫폼 전용 스킬과 훅이 해당 파일만 읽는다.

발동 표현: "todo/투두 추가", "할 일 등록", "todo/투두 완료/체크", "todo/투두 목록", "/todo" 등.

### yfix
버그/문제를 곧장 고치지 않고, 먼저 ① 코드를 실제 조사해 "왜 이렇게 동작하는지" 근본 원인을 근거(`파일:라인`)와 함께 설명하고, ② 가능한 해결책 후보들(개수 유동적)을 트레이드오프 표로 비교한 뒤, ③ `AskUserQuestion` 으로 어느 방향으로 고칠지 사용자에게 묻는다. 책임 경계는 **원인 설명 + 비교 + 선택 질문**까지이고, 실제 코드 수정은 스킬 밖 일반 흐름에서 진행한다(분석 단계에선 읽기만). 자명한 오타류는 절차 생략, 원인이 애매하거나 해법이 갈릴 때만 발동.

발동 표현: "/yfix", "왜 이렇게 동작해", "이거 왜 안 돼", "버그 고쳐줘", "어떻게 고칠지 비교해줘" 등.

### usage-stats
`ao-skills`가 관리하는 개인 스킬·훅·하네스의 사용 횟수와 최초·최근 사용 시각을 누적하고(Claude `~/.claude/usage-stats.json`, Codex `~/.Codex/usage-stats.json`), 등록됐지만 아직 안 쓴 항목까지 함께 조회한다. 프롬프트와 프로젝트 경로는 저장하지 않는다.

발동 표현: "스킬 사용량", "어떤 스킬 자주 써", "안 쓰는 스킬", "훅 사용 횟수", "/usage-stats" 등.

### flow-first
앱 기능 구현·수정 전에 요구사항 충돌과 사용자 왕복 플로우를 확인하고, 합의한 동작을 구현·검증·문서 갱신까지 추적한다.

발동 표현: "/flow-first", "플로우 먼저 확인하고 구현" 등.

### document-memory-routing
지속 보관 문서를 작성하거나 갱신할 때 후속 작업에서 읽을 조건과 경로를 프로젝트 CLAUDE.md(또는 그것이 불러오는 AGENTS.md)에 함께 연결한다.

발동 범위: 문서화, 기록해두기, 문서 갱신 요청 전반.

### parallel-pr-review
대화를 공유하지 않는 독립 서브에이전트 3개로 PR을 병렬 리뷰하고 주 에이전트가 후보를 직접 재검증하는 Claude용 스킬이다.

발동 표현: "병렬 리뷰", "독립 리뷰 3건", "테라 병렬리뷰" 등.

### run-plipa
플리파 로컬 서비스와 Android 에뮬레이터를 시작하거나 재연결하고 대상 앱, 이전 테스트, 실시간 화면 연결까지 확인한다. Codex의 전역 `run` 스킬을 옮긴 것으로, Claude 내장 `run` 스킬과 겹치지 않게 이름을 바꿨다.

발동 표현: "플리파 실행", "에뮬+서비스 켜줘", "/run-plipa" 등.

### eli5 · hallmark · ip-as-logo
외부에서 가져와 Codex에 설치해 쓰던 스킬을 그대로 옮겼다. 각각 쉬운 설명, 안티 AI 슬롭 디자인, 의인화 IP 로고 생성용이다.

## 커맨드 목록

| 커맨드 | 설명 |
|--------|------|
| `/socratic-learn` | 소크라테스식 점진 학습 모드 진입 |
| `/session-handoff` | 작업 세션 문맥을 핸드오프 프롬프트 + `handoff.md`로 정리 |
| `/stt-refine` | STT 녹취록을 검수본·요약본 두 마크다운으로 변환 (통합본 포함) |
| `/pr-todo-notion` | GitHub PR을 Notion 단순 체크박스 TODO 페이지로 정리 |
| `/pr-description` | PR 디스크립션을 정해진 형식으로 작성 |
| `/pr-review-answer` | PR 리뷰 코멘트 질문에 대한 답변을 정해진 형식으로 작성 |
| `/learn-by-doing` | 다음 구현에서 의미 있는 2~10줄을 사용자가 직접 쓰도록 TODO(human)을 남기고 요청 (명시 호출 전용) |
| `/resume-review` | 이력서·포트폴리오를 훑어보기·JD·사실 대조로 진단하고 고칠 목록을 냄 (명시 호출 전용) |
| `/resume-write` | 이력서·포트폴리오 문구를 라벨·이슈 형식과 근거 경계에 맞춰 고침 (명시 호출 전용) |
| `/ao-skill-update` | 스킬/커맨드 변경 + 전역 동기화 + 커밋 + 푸시 |

## 최근 변경내역 (2026-W43)

- 플리파 원격 검증 스킬과 SSH 클라이언트를 추가한다. 고정 커밋 제출·대기·취소·결과 ZIP 수집을 서버 실행기와 연결하고 Mac 대기열을 점유하지 않는다. 영향: `codex/skills/plipa-remote-validation`.
- 기존 브랜치 재사용·AVD 임대에 기능 담당 등록과 로컬 모바일 FIFO 실행기를 추가한다. 여러 세션의 중복 구현과 빌드·기기 경합을 줄인다. `codex/skills/task-coordination`, `mobile-validation-queue`, `android-emulator-lease`, `run-android-app`, `sol-two-pass-pr-review`를 갱신하고, 설치본에만 있던 플리파 `run`을 관리 원본으로 편입한다. 원격 플리파는 제외한다.


### 2026-10-21 - 승인 수명과 설치·예약 검증을 보강
- 기존: GitHub 승인 훅은 전역 설치본에만 있었고 생성 시도 전에 승인을 소비했다. 앱 실행 스킬에는 설치본과 APK의 버전·서명 비교가 없었다.
- 변경: 관리 원본에 승인 예약·성공 소비·실패 재시도·미확정 보류와 회귀 테스트를 추가했다. 설치 전 읽기 전용 비교와 예약 기록 검증 하네스, 훅·하네스 선택 동기화/검증을 추가했다.
- 이유: 실패한 생성에서 재승인을 반복하거나 불명확한 생성에서 중복 생성하지 않게 하고, 설치 대상과 예약 완료 근거를 확인한다.
- 영향 파일: `codex/hooks/github-create-approval-guard.py`, `codex/hooks/test_github_create_approval_guard.py`, `codex/hooks/README.md`, `codex/sync-github-approval.py`, `codex/sync.sh`, `codex/verify.sh`, `codex/skills/ao-skill-update/SKILL.md`, `codex/skills/run-android-app/`, `codex/harnesses/scheduled-task-verification.py`

관리 자산 선택 적용:

```sh
bash codex/sync.sh --hooks github-create-approval-guard
bash codex/verify.sh --hooks github-create-approval-guard
bash codex/sync.sh --skills run-android-app ao-skill-update
bash codex/verify.sh --skills run-android-app ao-skill-update
bash codex/sync.sh --harnesses scheduled-task-verification
bash codex/verify.sh --harnesses scheduled-task-verification
```

예약 기록 형식과 완료 근거는 전역 볼트 `workflows/scheduled-task-verification.md`를 읽는다. 승인 훅의 이벤트·복구·신뢰 범위는 [`codex/hooks/README.md`](codex/hooks/README.md)를 읽는다.

### 2026-10-21 - Codex 기존 리뷰 스킬 2종 삭제
- 기존: `github-pr-review` 원본과 설치본, `terra-parallel-pr-review` 전역 설치본이 있었고 새 Sol 스킬은 기존 스킬의 검토 기준을 참조했다.
- 변경: 요청한 두 Codex 스킬을 삭제하고, 필요한 호출 경로 검토와 후보 반증 기준은 Sol 스킬 안으로 옮긴다. README에서 Claude용 기존 스킬과 구분한다.
- 이유: 기존 리뷰 스킬 삭제 후에도 Sol 두 차례 리뷰가 독립적으로 동작하게 한다.
- 영향 파일: `codex/skills/github-pr-review/SKILL.md` 삭제, `codex/skills/sol-two-pass-pr-review/SKILL.md`, `README.md`, 전역 설치본 두 경로 삭제

### 2026-10-21 - 신규 추가: `sol-two-pass-pr-review`
- 기존: 단일 PR 인라인 리뷰와 독립 리뷰 스킬은 있었으나 Sol 2명의 리뷰, 수정, 새로운 2명의 재리뷰를 연결하는 Codex 절차는 없었다.
- 변경: 차수마다 GPT-6.1 Sol high 리뷰어 2명을 새로 생성하고, 확인된 수정점의 인라인 리뷰, 수정과 검증, 동일 형식의 1차/2차 보고를 수행하는 스킬을 추가한다.
- 이유: 리뷰 독립성을 유지하면서 각 차수의 발견 사항과 수정 근거를 추적한다.
- 영향 파일: `codex/skills/sol-two-pass-pr-review/SKILL.md`, `README.md`

### 2026-10-20 - 신규 추가: `/resume-review`
- 종류: 커맨드
- 목적: 이력서·포트폴리오를 훑어보기 기준, JD 대조, 사실 대조로 진단하고 고칠 목록을 우선순위로 내는 절차를 고정한다 (명시 호출 전용)
- 영향 파일: `commands/resume-review.md`, `README.md`

### 2026-10-20 - 신규 추가: `/resume-write`
- 종류: 커맨드
- 목적: '라벨: 설명', '이슈: 상황 → 한 일' 형식과 근거 경계를 지키며 전후 비교 → 승인 → 반영 → 확인 순서로 문구를 고치는 절차를 고정한다 (명시 호출 전용)
- 영향 파일: `commands/resume-write.md`, `README.md`

> 현재 주차(ISO week)의 변경만 여기 인라인으로 둔다. 지난 주차 이력은 [`changelog/`](changelog/) 참조.

### 지난 변경내역
- [`2026-W42`](changelog/2026-W42.md) - 2026-10-12 ~ 10-18
- [`2026-W41`](changelog/2026-W41.md) - 2026-10-05 ~ 10-11
- [`2026-W40`](changelog/2026-W40.md) - 2026-09-28 ~ 10-04
- [`2026-W39`](changelog/2026-W39.md) - 2026-09-21 ~ 09-27
- [`2026-W38`](changelog/2026-W38.md) - 2026-09-14 ~ 09-20
- [`2026-W36`](changelog/2026-W36.md) - 2026-08-31 ~ 09-06
- [`2026-W35`](changelog/2026-W35.md) - 2026-08-24 ~ 08-30
- [`2026-W33`](changelog/2026-W33.md) - 2026-08-10 ~ 08-16
- [`2026-W26`](changelog/2026-W26.md) - 2026-06-22 ~ 06-28
- [`2026-W25`](changelog/2026-W25.md) - 2026-06-15 ~ 06-21
- [`2026-W24`](changelog/2026-W24.md) - 2026-06-08 ~ 06-14
- [`2026-W23`](changelog/2026-W23.md) - 2026-06-01 ~ 06-07
- [`2026-W21`](changelog/2026-W21.md) - 2026-05-18 ~ 05-24
