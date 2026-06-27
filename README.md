# ao-skills

Claude Code에서 사용 중인 개인 스킬(Skill)과 슬래시 커맨드(Slash Command) 모음.

## 구성

```
ao-skills/
├── skills/
│   ├── ao-skill-update/     # 스킬/커맨드 변경 워크플로우 스킬
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

### todo
프로젝트별/전역 TODO 를 등록·완료·조회·삭제하고, 항목별 문맥 파일(`todo-context/<슬러그>.md`)을 `(ctx: ...)` 링크로 연결한다. 세션 시작 시 자동 표시되는 전역 `~/.claude/todo.md` 를 `## 공통`/`## <프로젝트 절대경로>` 섹션 체크리스트 포맷으로 직접 편집한다. 완료 항목은 원래 프로젝트 섹션에 그대로 남고(프로젝트별 구분 유지), 미완료 표시·완료 날짜 스탬프는 번들된 `todo-session.py` 훅이 SessionStart/SessionEnd 에서 처리하며, 스킬은 항목·문맥 편집만 담당한다.

발동 표현: "todo/투두 추가", "할 일 등록", "todo/투두 완료/체크", "todo/투두 목록", "/todo" 등.

### yfix
버그/문제를 곧장 고치지 않고, 먼저 ① 코드를 실제 조사해 "왜 이렇게 동작하는지" 근본 원인을 근거(`파일:라인`)와 함께 설명하고, ② 가능한 해결책 후보들(개수 유동적)을 트레이드오프 표로 비교한 뒤, ③ `AskUserQuestion` 으로 어느 방향으로 고칠지 사용자에게 묻는다. 책임 경계는 **원인 설명 + 비교 + 선택 질문**까지이고, 실제 코드 수정은 스킬 밖 일반 흐름에서 진행한다(분석 단계에선 읽기만). 자명한 오타류는 절차 생략, 원인이 애매하거나 해법이 갈릴 때만 발동.

발동 표현: "/yfix", "왜 이렇게 동작해", "이거 왜 안 돼", "버그 고쳐줘", "어떻게 고칠지 비교해줘" 등.

## 커맨드 목록

| 커맨드 | 설명 |
|--------|------|
| `/socratic-learn` | 소크라테스식 점진 학습 모드 진입 |
| `/session-handoff` | 작업 세션 문맥을 핸드오프 프롬프트 + `handoff.md`로 정리 |
| `/stt-refine` | STT 녹취록을 검수본·요약본 두 마크다운으로 변환 (통합본 포함) |
| `/pr-todo-notion` | GitHub PR을 Notion 단순 체크박스 TODO 페이지로 정리 |
| `/pr-description` | PR 디스크립션을 정해진 형식으로 작성 |
| `/pr-review-answer` | PR 리뷰 코멘트 질문에 대한 답변을 정해진 형식으로 작성 |
| `/ao-skill-update` | 스킬/커맨드 변경 + 전역 동기화 + 커밋 + 푸시 |

## 최근 변경내역 (2026-W26)

> 현재 주차(ISO week)의 변경만 여기 인라인으로 둔다. 지난 주차 이력은 [`changelog/`](changelog/) 의 주차별 파일 참조. (주가 바뀌면 이 섹션 항목을 `changelog/<직전 주차>.md`로 옮긴다.)

### 2026-06-27 - 신규 추가: `yfix` (버그 원인 설명 + 해결책 트레이드오프 비교 후 선택 질문)
- 종류: 스킬
- 목적: 버그/문제를 곧장 고치지 않고 ① 코드를 실제 조사해 근본 원인을 근거(`파일:라인`)와 함께 설명, ② 해결책 후보들(개수 유동적)을 트레이드오프 표로 비교, ③ `AskUserQuestion` 으로 어느 방향으로 고칠지 선택을 묻는다. 실제 수정은 스킬 밖 일반 흐름. 트리거는 명시적 `/yfix` + 버그 수정 맥락 자동 감지(자명한 오타류는 생략)
- 출처: `ooo interview` 로 요구사항(책임 경계=분석+질문까지, 코드 실제 조사, 후보 수 유동적, 항상 절차 준수)을 정리해 생성
- 영향 파일: `skills/yfix/SKILL.md`, `README.md`

### 지난 변경내역
- [`2026-W25`](changelog/2026-W25.md) - 2026-06-15 ~ 06-21
- [`2026-W24`](changelog/2026-W24.md) - 2026-06-08 ~ 06-14
- [`2026-W23`](changelog/2026-W23.md) - 2026-06-01 ~ 06-07
- [`2026-W21`](changelog/2026-W21.md) - 2026-05-18 ~ 05-24
