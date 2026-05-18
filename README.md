# ao-skills

Claude Code에서 사용 중인 개인 스킬(Skill)과 슬래시 커맨드(Slash Command) 모음.

## 구성

```
ao-skills/
├── skills/
│   ├── socratic-learn/      # 소크라테스식 점진 학습 스킬
│   │   └── SKILL.md
│   └── ao-skill-update/     # 스킬/커맨드 변경 워크플로우 스킬
│       └── SKILL.md
└── commands/
    ├── learn.md             # /learn - 학습 모드 진입
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

### socratic-learn
소크라테스식 점진 학습 도우미. 새 개념을 작은 단위로 분해 -> 코드/시각화로 설명 -> 확인 질문 -> 채점/교정 -> 다음 단계 선택의 사이클을 반복합니다.

발동 표현: "X 학습 도와줘", "X 배우고 싶어", "X 개념부터 다시" 등.

### ao-skill-update
이 레포의 스킬/커스텀 커맨드를 추가/수정/삭제한 뒤 `~/.claude/`로 동기화하고 커밋과 푸시까지 자동 처리하는 워크플로우.

발동 표현: "스킬 만들자", "스킬 수정", "커맨드 추가", "커맨드 변경", "스킬 동기화" 등.

## 커맨드 목록

| 커맨드 | 설명 |
|--------|------|
| `/learn` | 소크라테스식 점진 학습 모드 진입 |
| `/pr-description` | PR 디스크립션을 정해진 형식으로 작성 |
| `/pr-review-answer` | PR 리뷰 코멘트 질문에 대한 답변을 정해진 형식으로 작성 |
| `/ao-skill-update` | 스킬/커맨드 변경 + 전역 동기화 + 커밋 + 푸시 |

## 최근 변경내역

### 2026-05-18 - 신규 추가: `ao-skill-update` 스킬 / `/ao-skill-update` 커맨드
- 종류: 스킬 + 커맨드 (페어)
- 목적: 스킬/커맨드 변경 시 레포를 단일 진실 소스로 두고 `~/.claude/`로 cp -R 동기화 후 커밋+푸시까지 일괄 처리
- 영향 파일: `skills/ao-skill-update/SKILL.md`, `commands/ao-skill-update.md`, `README.md`

### 2026-05-18 - `socratic-learn` / `/learn` 사이클 단순화
- 기존: 응답 1(설명) → 응답 2(확인 질문) → 응답 3(채점) 의 3-응답 구조
- 변경: **응답 1(설명 + 확인 질문)** → **응답 2(사용자 답 → 채점 + 분기)** 의 2-응답 구조
- 이유: 설명 직후 질문을 받아야 학습자가 답할 타이밍을 놓치지 않음. 사이클 호흡을 짧게 가져감.
- 영향 파일: `commands/learn.md`, `skills/socratic-learn/SKILL.md`