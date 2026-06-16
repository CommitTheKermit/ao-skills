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

## 최근 변경내역 (2026-W25)

> 현재 주차(ISO week)의 변경만 여기 인라인으로 둔다. 지난 주차 이력은 [`changelog/`](changelog/) 의 주차별 파일 참조. (주가 바뀌면 이 섹션 항목을 `changelog/<직전 주차>.md`로 옮긴다.)

### 2026-06-17 - 신규 추가: `grounding-guard` (개념 출처 강제 훅 번들)
- 종류: 훅 스크립트 번들 (사용자 호출용 스킬 아님, `knowledge-loop` 와 같은 컨테이너 패턴)
- 목적: 개념/사양을 출처 확인 없이 단정하는 환각을 줄인다. CLAUDE.md 텍스트 규칙(advisory)이 무시될 수 있다는 한계를 훅(deterministic)으로 보완. `grounding-nudge.sh`(UserPromptSubmit)가 개념질문에 "출처부터 확인" 컨텍스트+플래그를 남기고, `verify-grounding.sh`(Stop)가 출처 흔적도 '추정/미확인' 표기도 없으면 `exit 2`로 한 번 되돌린다. 합성 입력 단위 테스트 7/7 통과
- 안전: 전부 fail-open, `stop_hook_active`+플래그 1회 소비로 최대 1회만 차단(8회벽/루프 회피)
- 활성화: 스크립트 동기화는 완료. `~/.claude/settings.json` 의 `UserPromptSubmit`/`Stop` 훅 등록은 사용자 승인 필요(자동 적용 안 함)
- 영향 파일: `skills/grounding-guard/lib.sh`, `skills/grounding-guard/grounding-nudge.sh`, `skills/grounding-guard/verify-grounding.sh`, `skills/grounding-guard/README.md`(신규), `README.md`

### 2026-06-16 - 전체 커맨드 7개에 `disable-model-invocation: true` 적용
- 기존: `commands/*.md` 7개 모두 frontmatter에 `description`만 있어, 메타데이터가 상시 컨텍스트에 로드돼 토큰을 소모
- 변경: 7개 커맨드 전부(`ao-skill-update`, `pr-description`, `pr-review-answer`, `pr-todo-notion`, `session-handoff`, `socratic-learn`, `stt-refine`)에 `disable-model-invocation: true` 추가
- 이유: 모두 사용자가 `/이름`으로 직접 호출하는 워크플로우라 자동 발동이 불필요. 상시 description 토큰을 0으로 줄이고 명시 호출만 남김
- 영향 파일: `commands/ao-skill-update.md`, `commands/pr-description.md`, `commands/pr-review-answer.md`, `commands/pr-todo-notion.md`, `commands/session-handoff.md`, `commands/socratic-learn.md`, `commands/stt-refine.md`

### 2026-06-16 - knowledge-loop 승격 넛지 쿨다운 3일 → 3시간
- 기존: `knowledge-nudge.sh` 의 `COOLDOWN=259200`(3일). pending 이 임계값을 넘겨도 한 번 안내 후 3일간 침묵해, 넛지가 안 뜬다고 느껴짐
- 변경: `COOLDOWN=10800`(3시간)로 단축. 주석/안내 문구의 "3일" 표기도 "3시간"으로 통일. `THRESHOLD=8` 은 유지
- 이유: 승격(수동)이 잊혀 후보만 쌓이는 것을 더 자주 상기. (쿨다운은 알림 빈도만 정하며 후보 수집은 SessionEnd 마다 별개로 동작)
- 영향 파일: `skills/knowledge-loop/knowledge-nudge.sh`

### 2026-06-16 - 변경내역을 주별 파일로 분리 + README엔 현재 주만 노출
- 기존: 모든 변경내역이 README "최근 변경내역" 한 섹션에 무한 누적돼 257줄 중 150줄(약 60%)을 차지. ao-skill-update가 README를 단일 진실 소스로 매번 읽어 토큰이 계속 증가
- 변경: 마감된 주차 이력을 `changelog/YYYY-Www.md`(ISO 주차)로 분리하고, README엔 현재 주차 항목 + 지난 주차 인덱스(링크)만 남김. `ao-skill-update`의 변경내역 갱신 규칙도 주별 라우팅(현재 주는 README, 주가 바뀌면 직전 주 블록을 changelog로 아카이브)으로 교체
- 이유: README를 짧게 유지해 읽기/diff 토큰을 절감. 과거 이력은 필요할 때만 changelog 파일로 조회
- 영향 파일: `README.md`, `changelog/2026-W24.md`(신규), `changelog/2026-W23.md`(신규), `changelog/2026-W21.md`(신규), `skills/ao-skill-update/SKILL.md`

### 2026-06-16 - `ao-skill-update` 브랜치 예외 명문화
- 기존: 전역 "새 작업은 새 브랜치" 규칙과 이 레포의 main 직커밋 관례가 충돌해, 작업 때마다 새 브랜치 생성/머지 고민이 반복됐다
- 변경: "단일 진실 소스"에 브랜치 예외 한 줄 추가 - ao-skills 는 개인 설정 단일 저장소라 새 브랜치 규칙의 예외이며 `main` 에서 바로 편집·커밋·푸시한다
- 이유: 동일 충돌 반복 방지. main 정본과 `~/.claude/` 동기화 상태가 항상 일치하게 유지
- 영향 파일: `skills/ao-skill-update/SKILL.md`, `README.md`

### 2026-06-16 - `knowledge-loop` 승격 분류에 "프로젝트 기술 문서" 경로 추가
- 기존: 프로젝트 도메인 지식은 경로가 `<project>/CLAUDE.md` 하나뿐이라, 긴 기술 명세(아키텍처/데이터 모델 등)도 상시 로드되는 CLAUDE.md 본문에 그대로 적재됐다. "길면 docs로 빼라"는 원칙은 있었으나 전역 `~/.claude/knowledge/docs/`만 가리켜 프로젝트 레포 내부 라우팅으로 이어지지 않았다
- 변경: 승격 대상에 **프로젝트 기술 문서 → `<project>/docs/<주제>.md`** 경로 추가. CLAUDE.md엔 "상세는 `docs/<주제>.md` 참조" 한 줄만 남긴다. 분류 기준 명시(1~2줄 규칙이면 CLAUDE.md, 길거나 구조적이면 docs + 참조). 원칙 섹션도 프로젝트 docs를 포함하도록 보강
- 이유: CLAUDE.md는 매 세션/프롬프트에 상시 로드돼 긴 명세가 항상 토큰을 먹는다. 필요할 때만 읽히는 docs로 빼고 라우팅만 남기는 게 토큰 효율적
- 영향 파일: `skills/knowledge-loop/SKILL.md`, `README.md`

### 2026-06-16 - `knowledge-loop` 추출 신뢰성 개선 + 승격 넛지 추가
- 기존: ① 같은 세션이 SessionEnd마다 재추출돼 동일 지식이 중복 적재(예: 한 결정이 7~8회), ② claude 호출 실패 시 에러 문자열("API Error...")이 지식으로 적재됨, ③ 거대 붙여넣기(HTML/스킬 번들)가 `tail -c 15000` 샘플을 채워 실제 대화 신호가 잘려 false negative 발생, ④ 수동 승격(`/knowledge-loop`)을 부르는 알림이 없어 후보만 쌓임
- 변경: ① `.extract-state` 의 세션별 high-water mark 이후 새 메시지만 샘플링, ② claude 종료코드(rc=0) + 불릿(`- `) 출력만 적재(에러/잡문 배제), ③ 붙여넣기 블록 제외 + 메시지당 2000자 캡, ④ `knowledge-nudge.sh`(SessionStart)가 pending 8세션 이상 시 3일 쿨다운으로 리뷰 권유. extract.log 에 `rc`/`new` 필드 추가
- 이유: 추출 단계는 자동으로 돌고 있었으나 중복/오적재/누락으로 신뢰도가 낮았고, 승격 단계는 트리거가 없어 한 번도 실행되지 않았음
- 영향 파일: `skills/knowledge-loop/knowledge-extract.sh`, `skills/knowledge-loop/knowledge-nudge.sh`(신규), `skills/knowledge-loop/SKILL.md`, `README.md` (별도: `~/.claude/settings.json` SessionStart 훅 등록)

### 지난 변경내역
- [`2026-W24`](changelog/2026-W24.md) - 2026-06-08 ~ 06-14
- [`2026-W23`](changelog/2026-W23.md) - 2026-06-01 ~ 06-07
- [`2026-W21`](changelog/2026-W21.md) - 2026-05-18 ~ 05-24
