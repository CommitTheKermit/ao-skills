# ao-skills

Claude Code에서 사용 중인 개인 스킬(Skill)과 슬래시 커맨드(Slash Command) 모음.

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
│   └── todo/                # 프로젝트별/전역 TODO 관리 스킬 (+ 세션 훅)
│       ├── SKILL.md
│       └── todo-session.py
├── commands/
│   ├── socratic-learn.md    # /socratic-learn - 소크라테스식 학습 모드 진입
│   ├── session-handoff.md   # /session-handoff - 세션 문맥 핸드오프 산출물 생성
│   ├── stt-refine.md        # /stt-refine - STT 녹취록을 검수본·요약본으로 변환
│   ├── pr-todo-notion.md    # /pr-todo-notion - PR을 노션 체크박스 TODO로 정리
│   ├── pr-description.md    # /pr-description - PR 디스크립션 작성
│   ├── pr-review-answer.md  # /pr-review-answer - PR 리뷰 답변 작성
│   └── ao-skill-update.md   # /ao-skill-update - 스킬/커맨드 변경+동기화+커밋+푸시
└── changelog/               # 주차(ISO week)별 변경내역 아카이브 (YYYY-Www.md)
```

## 스킬 vs 커맨드

> 2026-06-12 공식 문서 기준, 커스텀 커맨드는 스킬로 **통합**됐다. 둘 다 `/이름` 호출이 생기고, 둘 다 메타데이터(name+description)가 상시 로드되며 본문은 발동 시에만 로드된다. 상시 토큰 비용은 형태가 아니라 `disable-model-invocation: true` 여부로 결정된다(설정 시 0, 명시 호출은 계속 가능). 상세: `~/.claude/knowledge/docs/skill-vs-command-token-cost.md`

| 구분 | 커스텀 커맨드 | 스킬 |
|------|--------------|------|
| 호출 | `/명령` + 조건 만족 시 자동 발동 | `/명령` + 조건 만족 시 자동 발동 |
| 구조 | 단일 `.md` 파일 | 디렉토리 + `SKILL.md` (+ 보조 자원) |
| 상시 토큰 | description 상시 로드 (opt-out 가능) | 동일 |
| 용도 | 단일 프롬프트 재사용 | 보조 스크립트/자원이 필요한 워크플로우 패키징 |

## 설치

### 전역 설치 (모든 프로젝트에서 사용)

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

## 스킬 목록

> 스킬/커맨드는 기능상 동일하다(위 "스킬 vs 커맨드" 참고). 부속 파일(훅 스크립트 등)이 필요한 워크플로우만 스킬 디렉터리로 두고, 단일 프롬프트 문서는 커맨드 파일로 둔다.

### ao-skill-update
이 레포의 스킬/커스텀 커맨드를 추가/수정/삭제한 뒤 `~/.claude/`로 동기화하고 커밋과 푸시까지 자동 처리하는 워크플로우.

발동 표현: "스킬 만들자", "스킬 수정", "커맨드 추가", "커맨드 변경", "스킬 동기화" 등.

### build-signed-aab
Android 앱의 단위 테스트와 release bundle 빌드를 실행하고, Play 제출용 AAB의 서명·application ID·버전·런처 아이콘을 검증한 뒤 버전명 파일로 보관한다. 버전과 패키지명은 자동 변경하지 않는다.

발동 표현: "AAB 빌드", "서명 AAB", "심사용 번들", "bundleRelease", "Play 업로드 파일 만들어줘" 등.

### check-android-review-readiness
Android 프로젝트와 Play Console 자료를 최신 Google 공식 정책 및 누적된 실제 심사 실패 사례에 대조하고 Gradle 검사를 실행해 `통과 가능`·`실패 위험`·`확인 불가`로 판정한다. 실제 승인 결과는 보장하지 않는다.

발동 표현: "안드로이드 심사 통과할까", "Play 심사 테스트", "출시 전 정책 점검", "리젝 위험 검사" 등.

### grounding-guard
개념/사양을 **출처 확인 없이 단정하는 환각**을 줄이는 훅 스크립트 번들(사용자 호출용 스킬 아님, `knowledge-loop` 와 같은 훅 컨테이너 패턴). `grounding-nudge.sh`(UserPromptSubmit)가 개념질문에 "출처부터 확인하라" 컨텍스트를 주입하고 이번 턴 플래그를 남기면, `verify-grounding.sh`(Stop)가 그 턴에 출처 도구 사용 흔적도 '추정/미확인' 표기도 없을 때 `exit 2`로 한 번 되돌려 보완을 요구한다. fail-open + `stop_hook_active` + 플래그 1회 소비로 최대 1회만 차단. `~/.claude/settings.json` 훅 등록은 동기화 범위 밖이라 수동(상세: `skills/grounding-guard/README.md`).

### knowledge-loop
세션에서 자동 추출된 지식 후보를 리뷰해 CLAUDE.md 규칙/스킬/영구 문서로 승격하거나 폐기한다. 추출은 번들 훅 `knowledge-extract.sh`(SessionEnd, 머신별 1회 수동 등록)가 게이트(교정/커밋/긴 세션) 통과 시 haiku로 수행해 `~/.claude/knowledge/pending.md`에 적재하고, 승격은 이 스킬에서 사용자 승인으로만 진행한다. `disable-model-invocation: true`라 상시 토큰 비용 0, `/knowledge-loop`로 명시 호출.

### claude-design-handoff
claude.ai/design 핸드오프 링크(`api.anthropic.com/v1/design/...`)를 받아 디자인 번들을 내려받고(gzip bin → gunzip+tar 압축해제), 번들의 README와 prod 산출물(`app-prod.jsx`/`styles-prod.css` 등)·`chats/` 트랜스크립트를 근거로 프로젝트의 디자인 소스를 시안과 정확히 동기화한다. 텍스트 설명만으로 추측 구현하지 않는다. 함께 온 구체적 변경 지시도 추가 반영.

발동 표현: "Fetch this design file, read its readme, and implement..." 형식 또는 `api.anthropic.com/v1/design/` 링크 붙여넣기.

### handoff-css-guard
claude.ai/design export(핸드오프) CSS 를 옮길 때 빌드·`tsc`·`vitest` 가 못 잡는 "문법상 valid 인데 규칙이 통째로 죽는" 잠복 버그(주석 안 `별표+슬래시` 조기종료 등)·누락 CSS 변수·셀렉터 불일치·stale 번들을 잡는 자동화 하네스를 대상 프로젝트에 **설치**한다. `assets/` 의 검증된 스크립트(`css-guard.mjs`/`validate-handoff.mjs`/`css-guard.sh`/`stylelintrc.json`)를 복사하고, 편집 즉시 PostToolUse 훅(구문 무결성+누락 변수, 실패 시 block)과 수동 `npm run validate-handoff`(+stylelint·셀렉터 리포트·stale `--live` diff)를 배선한다. 사람용 체크리스트는 두지 않고 자동화 도구만 둔다. `claude-design-handoff` 의 자매 도구.

발동 표현: "핸드오프 CSS 검증/가드 붙여줘", "디자인 export 적용 재발 방지 하네스", "css-guard 설치" 등.

### release-commit
배포/릴리스 직후 남기는 release 커밋을 고정 포맷(`chore(release): vX.Y.Z 배포`)으로 작성한다. 직전 release 이후의 `git log`를 뽑아 변경 목록·배포 대상·버전 증감을 본문에 채워, 요약 한두 줄로 끝나 추적이 안 되는 빈약한 release 커밋을 막는다.

발동 표현: "release 커밋", "버전 커밋", "릴리스 커밋", "배포 커밋 정리" 등.

### record-android-review-failure
사용자가 제공한 Play Console 거절 통지·스크린샷·설명에서 개인정보를 제거하고 실패 조건과 검출·예방 방법을 공용 사례집에 누적한 뒤 Git으로 공유한다. 중복 사례는 새로 만들지 않고 기존 항목을 보강한다.

발동 표현: "심사 실패 사례 추가", "리젝 사유 기록", "이 실패 요소를 다음 심사 점검에 반영해줘" 등.

### todo
프로젝트별/전역 TODO 를 등록·완료·조회·삭제하고, 항목별 문맥 파일(`todo-context/<슬러그>.md`)을 `(ctx: ...)` 링크로 연결한다. 세션 시작 시 자동 표시되는 전역 `~/.claude/todo.md` 를 `## 공통`/`## <프로젝트 절대경로>` 섹션 체크리스트 포맷으로 직접 편집한다. 완료 항목은 원래 프로젝트 섹션에 그대로 남고(프로젝트별 구분 유지), 미완료 표시·완료 날짜 스탬프는 번들된 `todo-session.py` 훅이 SessionStart/SessionEnd 에서 처리하며, 스킬은 항목·문맥 편집만 담당한다.

발동 표현: "todo/투두 추가", "할 일 등록", "todo/투두 완료/체크", "todo/투두 목록", "/todo" 등.

### yfix
버그/문제를 곧장 고치지 않고, 먼저 ① 코드를 실제 조사해 "왜 이렇게 동작하는지" 근본 원인을 근거(`파일:라인`)와 함께 설명하고, ② 가능한 해결책 후보들(개수 유동적)을 트레이드오프 표로 비교한 뒤, ③ `AskUserQuestion` 으로 어느 방향으로 고칠지 사용자에게 묻는다. 책임 경계는 **원인 설명 + 비교 + 선택 질문**까지이고, 실제 코드 수정은 스킬 밖 일반 흐름에서 진행한다(분석 단계에선 읽기만). 자명한 오타류는 절차 생략, 원인이 애매하거나 해법이 갈릴 때만 발동.

발동 표현: "/yfix", "왜 이렇게 동작해", "이거 왜 안 돼", "버그 고쳐줘", "어떻게 고칠지 비교해줘" 등.

### no-ai-design
"LLM은 설계를 못한다"는 통념을 반영한 설계 게이트. 새 모듈/기능 구현처럼 설계가 개입되는 작업에서, 구현 전에 설계 결정점(모듈/파일 경계·데이터 모델·공개 인터페이스·알고리즘/라이브러리/패턴)을 추출해 각 결정점마다 옵션 메뉴+트레이드오프를 제시하되 **최종 선택은 사람**이 `AskUserQuestion` 으로 하게 한다(LLM은 메뉴만, 단정 금지). 합의 설계를 설계 노트(`design/<주제>.md`)로 남기고 그 틀 안에서만 구현하며, 코딩 중 합의 안 된 새 설계 결정이 생기면 다시 멈춰 묻는다(구현 가드). 함수 내부/지역 구현은 LLM 자율, 사소·애매하면 "설계 점검할까요?"로 짧게 확인.

발동 표현: "/no-ai-design", "설계 먼저", "구조부터 정하고", "아키텍처 정하자", "이 기능 어떻게 짤지" 등.

## 커맨드 목록

| 커맨드 | 설명 |
|--------|------|
| `/socratic-learn` | 소크라테스식 점진 학습 모드 진입 |
| `/session-handoff` | 작업 세션 문맥을 핸드오프 프롬프트 + `handoff.md`로 정리 |
| `/stt-refine` | STT 녹취록을 검수본·요약본 두 마크다운으로 변환 (통합본 포함) |
| `/pr-todo-notion` | GitHub PR을 Notion 단순 체크박스 TODO 페이지로 정리 |
| `/pr-description` | PR 디스크립션을 정해진 형식으로 작성 |
| `/pr-review-answer` | PR 리뷰 코멘트 질문에 대한 답변을 정해진 형식으로 작성 |
| `/step-by-step` | 구현을 작은 단계로 쪼개 단계마다 검증·보고·승인을 거치며 진행 (코드 작성은 코덱스 위임) |
| `/ao-skill-update` | 스킬/커맨드 변경 + 전역 동기화 + 커밋 + 푸시 |

## 최근 변경내역 (2026-W33)

> 현재 주차(ISO week)의 변경만 여기 인라인으로 둔다. 지난 주차 이력은 [`changelog/`](changelog/) 의 주차별 파일 참조. (주가 바뀌면 이 섹션 항목을 `changelog/<직전 주차>.md`로 옮긴다.)

### 2026-08-11 - `step-by-step` 구현 단계를 코덱스 위임으로 전환
- 기존: 3단계 "구현"을 클로드가 직접 수행
- 변경: 3단계를 `codex exec` 위임으로 바꾸고, 1단계 예고를 그대로 코덱스 스펙으로 넘기게 함. 위임 후 `git diff` 검토를 의무화하고, 위임하지 않는 예외(한 줄 수정·미세 교정·2연속 실패)와 사전 세팅 표(권한 허용·샌드박스·승인·작업 루트·출력 처리)를 추가
- 이유: 코드 생성은 코덱스, 설계·검토·질문은 클로드로 역할을 나누기 위해
- 영향 파일: `commands/step-by-step.md`, `README.md`

### 2026-08-11 - 신규 추가: `step-by-step`
- 종류: 커맨드
- 목적: 구현 작업을 검증 가능한 작은 단계로 쪼개고, 단계마다 완료/다음을 구분선으로 보고하며, 미결정 사항을 다음 단계로 넘기기 전에 AskUserQuestion 으로 해소
- 영향 파일: `commands/step-by-step.md`, `README.md`

### 2026-08-10 - 신규 추가: `check-android-review-readiness`
- 종류: 스킬
- 목적: 최신 공식 정책·프로젝트 검사·누적 실패 사례로 Google Play 심사 준비 상태 판정
- 영향 파일: `skills/check-android-review-readiness/SKILL.md`, `skills/check-android-review-readiness/agents/openai.yaml`, `README.md`

### 2026-08-10 - 신규 추가: `record-android-review-failure`
- 종류: 스킬
- 목적: 사용자 제보 Android 심사 실패 요소를 정규화해 Git 기반 공용 사례집에 축적
- 영향 파일: `skills/record-android-review-failure/SKILL.md`, `skills/record-android-review-failure/references/failure-cases.md`, `skills/record-android-review-failure/agents/openai.yaml`, `README.md`

### 2026-08-10 - 신규 추가: `build-signed-aab`
- 종류: 스킬
- 목적: Android 앱의 테스트·release bundle 빌드·서명·manifest·런처 아이콘을 한 번에 검증하고 Play 제출용 버전명 AAB로 보관
- 영향 파일: `skills/build-signed-aab/SKILL.md`, `skills/build-signed-aab/scripts/build-signed-aab.sh`, `skills/build-signed-aab/agents/openai.yaml`, `README.md`

### 지난 변경내역
- [`2026-W26`](changelog/2026-W26.md) - 2026-06-22 ~ 06-28
- [`2026-W25`](changelog/2026-W25.md) - 2026-06-15 ~ 06-21
- [`2026-W24`](changelog/2026-W24.md) - 2026-06-08 ~ 06-14
- [`2026-W23`](changelog/2026-W23.md) - 2026-06-01 ~ 06-07
- [`2026-W21`](changelog/2026-W21.md) - 2026-05-18 ~ 05-24
