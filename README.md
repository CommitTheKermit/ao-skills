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
│   └── release-commit/      # 배포/릴리스 직후 release 커밋을 고정 포맷으로 작성하는 스킬
│       └── SKILL.md
└── commands/
    ├── socratic-learn.md    # /socratic-learn - 소크라테스식 학습 모드 진입
    ├── session-handoff.md   # /session-handoff - 세션 문맥 핸드오프 산출물 생성
    ├── stt-refine.md        # /stt-refine - STT 녹취록을 검수본·요약본으로 변환
    ├── pr-todo-notion.md    # /pr-todo-notion - PR을 노션 체크박스 TODO로 정리
    ├── pr-description.md    # /pr-description - PR 디스크립션 작성
    ├── pr-review-answer.md  # /pr-review-answer - PR 리뷰 답변 작성
    └── ao-skill-update.md   # /ao-skill-update - 스킬/커맨드 변경+동기화+커밋+푸시
```

## 스킬 vs 커맨드

| 구분 | 커스텀 커맨드 | 스킬 |
|------|--------------|------|
| 호출 | 사용자가 `/명령` 입력 | 사용자 호출 + 조건 만족 시 자동 발동 |
| 구조 | 단일 `.md` 파일 | 디렉토리 + `SKILL.md` (+ 보조 자원) |
| 메타데이터 | 거의 없음 | frontmatter `description`으로 발동 조건 명시 |
| 용도 | 자주 쓰는 프롬프트 재사용 | 재사용 가능한 "능력/워크플로우" 패키징 |

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

> 스킬은 `description`이 매 대화에 상시 로드되어 자동 발동을 판단한다. 그래서 "자동 발동이 핵심 가치"이거나 "레포 운영에 필수"인 것만 스킬로 둔다. 명시 호출이 자연스러운 기능은 커맨드로 둬서 상시 토큰을 아낀다.

### ao-skill-update
이 레포의 스킬/커스텀 커맨드를 추가/수정/삭제한 뒤 `~/.claude/`로 동기화하고 커밋과 푸시까지 자동 처리하는 워크플로우.

발동 표현: "스킬 만들자", "스킬 수정", "커맨드 추가", "커맨드 변경", "스킬 동기화" 등.

### claude-design-handoff
claude.ai/design 핸드오프 링크(`api.anthropic.com/v1/design/...`)를 받아 디자인 번들을 내려받고(gzip bin → gunzip+tar 압축해제), 번들의 README와 prod 산출물(`app-prod.jsx`/`styles-prod.css` 등)·`chats/` 트랜스크립트를 근거로 프로젝트의 디자인 소스를 시안과 정확히 동기화한다. 텍스트 설명만으로 추측 구현하지 않는다. 함께 온 구체적 변경 지시도 추가 반영.

발동 표현: "Fetch this design file, read its readme, and implement..." 형식 또는 `api.anthropic.com/v1/design/` 링크 붙여넣기.

### release-commit
배포/릴리스 직후 남기는 release 커밋을 고정 포맷(`chore(release): vX.Y.Z 배포`)으로 작성한다. 직전 release 이후의 `git log`를 뽑아 변경 목록·배포 대상·버전 증감을 본문에 채워, 요약 한두 줄로 끝나 추적이 안 되는 빈약한 release 커밋을 막는다.

발동 표현: "release 커밋", "버전 커밋", "릴리스 커밋", "배포 커밋 정리" 등.

### todo
프로젝트별/전역 TODO 를 등록·완료·조회·삭제하고, 항목별 문맥 파일(`todo-context/<슬러그>.md`)을 `(ctx: ...)` 링크로 연결한다. 세션 시작 시 자동 표시되는 `.claude/todo.md`(프로젝트)·`~/.claude/todo.md`(전역) 를 체크리스트 포맷으로 직접 편집한다. 표시/아카이브는 번들된 `todo-session.py` 훅이 SessionStart/SessionEnd 에서 처리하고, 스킬은 항목·문맥 편집만 담당한다.

발동 표현: "todo/투두 추가", "할 일 등록", "todo/투두 완료/체크", "todo/투두 목록", "/todo" 등.

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

## 최근 변경내역

### 2026-06-12 - `todo` 한글 "투두" 트리거 + 항목별 문맥 파일(ctx) 연결
- 기존: 발동 표현이 영문 "todo"뿐이라 "투두 추가" 같은 한글 표현에 자동 발동이 안 됐고, 투두에 작업 문맥을 남길 방법이 없었음
- 변경: (1) description 에 "투두" 표현 추가, (2) 항목 끝 `(ctx: todo-context/<슬러그>.md)` 링크로 문맥 파일을 연결하는 규칙 추가(배경/현재 상태/관련 파일/다음 단계), (3) 훅 시작 안내문에 ctx 파일을 먼저 읽으라는 지침 추가
- 이유: 한글 호출에도 자동 발동되게 하고, 투두 작업 재개 시 문맥 파일만 읽어도 바로 이어갈 수 있게 함
- 영향 파일: `skills/todo/SKILL.md`, `skills/todo/todo-session.py`, `README.md`

### 2026-06-12 - `todo` 기본 범위 전역으로 전환
- 기존: 기본 범위가 프로젝트라, 전역에 넣으려면 매번 "전역"을 명시해야 했음
- 변경: 기본 범위를 **전역**으로 뒤집음. 별도 언급이 없으면 모든 항목이 `~/.claude/todo.md` 로 들어가 어느 프로젝트에서든 리마인드된다. 프로젝트 전용은 "이 프로젝트만/여기서만/전역 말고" 처럼 명시할 때만
- 이유: 별도 지시 없이도 모든 todo 가 교차 프로젝트 리마인더로 쌓이길 원함
- 영향 파일: `skills/todo/SKILL.md`, `README.md`

### 2026-06-12 - `todo` 전역 범위 라우팅·보고 보강
- 기존: 기본 범위가 프로젝트이고, 보고 시 대상 파일을 빠뜨릴 수 있어 전역에 쓰였는지 사용자가 알기 어려웠음
- 변경: (1) 전역 todo 를 "모든 프로젝트에서 보이는 교차 프로젝트 리마인더"로 명문화, (2) 전역 라우팅 신호("어디서든/다른 프로젝트에서도/계속 리마인드" 등) 추가, (3) 모든 액션 보고에 대상 파일·경로를 반드시 명시하도록 규칙화
- 이유: "다른 프로젝트에서도 계속 리마인드 받고 싶다"는 의도를 전역 todo 로 명확히 연결하고, 어디에 썼는지 항상 보이게 하기 위함
- 영향 파일: `skills/todo/SKILL.md`, `README.md`

### 2026-06-12 - 신규 추가: `todo` 스킬
- 종류: 스킬
- 목적: 프로젝트별/전역 TODO 를 등록·완료·조회·삭제하고, 세션 시작 시 미완료 항목을 자동 표시(1시간 초과 시 경과 안내)하며 완료 항목을 세션 시작·종료 시 아카이브한다
- 구성: 스킬은 항목 편집만 담당. 표시·아카이브는 번들 훅 스크립트 `skills/todo/todo-session.py`(SessionStart/SessionEnd)가 처리. 훅 등록(`settings.json`)은 ao-skills 동기화 대상이 아니므로 머신별 1회 수동 등록
- 영향 파일: `skills/todo/SKILL.md`(신규), `skills/todo/todo-session.py`(신규), `README.md`

### 2026-06-10 - `/learn` → `/socratic-learn` 리네임 + `ao-skill-update` 신규 분류 단계 추가
- 변경 1: `commands/learn.md` → `commands/socratic-learn.md` (호출 `/socratic-learn`). 스킬 시절 이름과 일치시켜 일관성 확보
- 변경 2: `ao-skill-update` 워크플로우의 "변경 분류"에, 신규 추가 시 스킬로 저장할지 커맨드로 저장할지 사용자에게 **반드시 묻는** 단계 추가. 판단 기준(자동 발동·상시 토큰 필요 → 스킬, `/이름` 명시 호출로 충분 → 커맨드)을 함께 제시
- 영향 파일: `commands/socratic-learn.md`(리네임), `skills/ao-skill-update/SKILL.md`, `commands/ao-skill-update.md`, `README.md`

### 2026-06-10 - `socratic-learn`/`session-handoff`/`stt-refine`/`pr-todo-notion` 스킬 → 커맨드 전환
- 기존: 4개 기능이 스킬로 존재해 자동 발동용 `description`(167~366자)이 매 대화 상시 로드됨
- 변경: 4개를 커스텀 커맨드(`/session-handoff`, `/stt-refine`, `/pr-todo-notion`, 기존 `/learn`)로 이전하고 스킬은 삭제. `learn.md`는 `socratic-learn` 참조를 제거해 자족화
- 이유: 스킬은 자동 발동 판단을 위해 긴 description을 상시 로드하지만, 이 4개는 사용자가 명시 호출(`/명령`)하는 게 자연스러워 자동 발동 이득이 작음. 커맨드는 짧은 한 줄 description으로 충분해 상시 토큰을 절감 (자동 발동은 포기)
- 유지: `ao-skill-update`(레포 운영 필수), `claude-design-handoff`(링크 붙여넣기 자동 발동이 핵심), `release-commit`은 스킬로 유지
- 영향 파일: `commands/learn.md`, `commands/session-handoff.md`(신규), `commands/stt-refine.md`(신규), `commands/pr-todo-notion.md`(신규), `skills/{socratic-learn,session-handoff,stt-refine,pr-todo-notion}/`(삭제), `README.md`

### 2026-06-09 - 신규 추가: `release-commit` 스킬
- 종류: 스킬
- 목적: 배포/릴리스 직후 남기는 release 커밋을 고정 포맷(`chore(release): vX.Y.Z 배포`)으로 작성하고, 본문은 직전 release 이후의 `git log` 를 뽑아 변경 목록·배포 대상·버전 증감으로 채운다. 요약 한두 줄로 끝나 추적이 안 되는 빈약한 release 커밋을 방지.
- 영향 파일: `skills/release-commit/SKILL.md`, `README.md`

### 2026-06-08 - 신규 추가: `claude-design-handoff` 스킬
- 종류: 스킬
- 목적: 전역 CLAUDE.md의 "클로드 디자인 링크 처리" 규칙을 독립 스킬로 분리. claude.ai/design 핸드오프 링크를 받아 번들을 내려받아 압축 해제하고, README와 prod 산출물·chats 트랜스크립트를 근거로 프로젝트 디자인 소스를 시안과 동기화한다.
- 영향 파일: `skills/claude-design-handoff/SKILL.md`, `README.md`

### 2026-06-08 - `pr-todo-notion` 산출물 단순화
- 기존: PR 링크 헤더 + 팀/리뷰어 메타 줄 + 각 TODO에 코멘트 링크 매핑 + "본문 파생 TODO"/"후속 작업" 섹션 분리
- 변경: 기존 노션 리뷰 TODO 페이지와 100% 동일한 단순 형식(`## N차 리뷰 TODO (날짜, 상태)` 헤더 + `- [ ] 할 일 (위치)` + 세부 근거)만. 코멘트 링크/메타/파생·후속 섹션 제거
- 이유: 산출물이 기존 노션 페이지 형식 대비 과하게 복잡 → 워크스페이스의 기존 리뷰 TODO 페이지 형식에 맞춰 단순화
- 영향 파일: `skills/pr-todo-notion/SKILL.md`, `README.md`

### 2026-06-04 - `ao-skill-update` 커밋 서명 트레일러 제거
- 기존: 커밋에 `Co-Authored-By: Claude ...` 서명 트레일러 포함 지시
- 변경: 서명 트레일러를 넣지 않도록 수정
- 이유: 전역 CLAUDE.md의 "서명 트레일러 넣지 않음" 규칙과 충돌 → 전역 규칙에 맞춤
- 영향 파일: `skills/ao-skill-update/SKILL.md`, `commands/ao-skill-update.md`, `README.md`

### 2026-06-04 - `session-handoff` 핸드오프 파일 구조 변경
- 기존: 산출물을 저장소 루트 `HANDOFF.md` 단일 파일로 저장
- 변경: 최신 진입점을 루트 `handoff.md`(고정 파일명, 덮어쓰기)로 두고, 이력은 `handoff/handoff_yyMMdd_HHmm.md`(콜론 없는 타임스탬프)로 아카이브
- 이유: Claude Code `@` 파일 멘션 정렬 기준이 미문서화라 "최신이 맨 위"를 보장 못 함 → 정렬에 의존하지 않고 고정 진입점 하나로 단일화
- 영향 파일: `skills/session-handoff/SKILL.md`, `README.md`

### 2026-06-03 - 신규 추가: `session-handoff` 스킬
- 종류: 스킬
- 목적: 현재 작업 세션의 문맥을 다음 세션으로 넘기기 위해 핸드오프 프롬프트 + HANDOFF.md 두 산출물을 생성한다.
- 영향 파일: `skills/session-handoff/SKILL.md`, `README.md`

### 2026-06-02 - 신규 추가: `stt-refine` 스킬
- 종류: 스킬
- 목적: STT 녹취록을 맥락 기반으로 보정한 검수본과 토픽별 재구성 요약본 두 개의 마크다운으로 변환 (연속 회차 통합본 포함)
- 영향 파일: `skills/stt-refine/SKILL.md`, `README.md`

### 2026-06-02 - 신규 추가: `pr-todo-notion` 스킬
- 종류: 스킬
- 목적: GitHub PR을 분석해 Notion 페이지 아래에 TODO 하위 페이지를 만들고, 각 TODO 제목에 근거 리뷰 코멘트 링크를 매핑해 추적 가능하게 함
- 영향 파일: `skills/pr-todo-notion/SKILL.md`, `README.md`

### 2026-05-18 - 신규 추가: `ao-skill-update` 스킬 / `/ao-skill-update` 커맨드
- 종류: 스킬 + 커맨드 (페어)
- 목적: 스킬/커맨드 변경 시 레포를 단일 진실 소스로 두고 `~/.claude/`로 cp -R 동기화 후 커밋+푸시까지 일괄 처리
- 영향 파일: `skills/ao-skill-update/SKILL.md`, `commands/ao-skill-update.md`, `README.md`

### 2026-05-18 - `socratic-learn` / `/learn` 사이클 단순화
- 기존: 응답 1(설명) → 응답 2(확인 질문) → 응답 3(채점) 의 3-응답 구조
- 변경: **응답 1(설명 + 확인 질문)** → **응답 2(사용자 답 → 채점 + 분기)** 의 2-응답 구조
- 이유: 설명 직후 질문을 받아야 학습자가 답할 타이밍을 놓치지 않음. 사이클 호흡을 짧게 가져감.
- 영향 파일: `commands/learn.md`, `skills/socratic-learn/SKILL.md`