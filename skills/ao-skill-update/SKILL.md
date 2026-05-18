---
name: ao-skill-update
description: ao-skills 레포의 스킬/커스텀 커맨드를 신규 추가하거나 수정한 뒤 Claude 전역 설정(~/.claude/)으로 cp -R 동기화하고 커밋/푸시까지 완료하는 워크플로우. 사용자가 "스킬 만들자", "스킬 수정", "/X 커맨드 추가", "커맨드 변경", "스킬 동기화" 같은 표현을 쓰면 발동.
---

# ao-skill-update

스킬/커스텀 커맨드를 변경할 때 `ao-skills` 레포를 단일 진실 소스로 사용하고, 변경 후 `~/.claude/`로 동기화한 뒤 커밋과 푸시까지 마친다.

## 단일 진실 소스

- 레포 경로: `/Users/ujeonghyeon/Desktop/dev/ao-skills`
- `~/.claude/skills/`, `~/.claude/commands/`는 **레포의 사본**일 뿐. 직접 수정하지 않는다.
- 모든 편집은 레포 안에서 한다.

## 워크플로우

```
[1] 변경 분류  →  [2] 레포에서 편집  →  [3] README 변경내역 갱신
                                              ↓
        [5] 커밋 + 푸시  ←  [4] ~/.claude/ 로 cp -R 동기화
```

### 1. 변경 분류
사용자 요청을 다음 중 하나로 분류한다.

- **신규 스킬**: `skills/<name>/SKILL.md` 새로 만든다
- **신규 커맨드**: `commands/<name>.md` 새로 만든다
- **기존 수정**: 해당 파일을 편집
- **삭제**: 파일/디렉토리 제거 + 동기화 시 `~/.claude/`에서도 별도 삭제

### 2. 레포에서 편집

- 스킬: `/Users/ujeonghyeon/Desktop/dev/ao-skills/skills/<name>/SKILL.md`
- 커맨드: `/Users/ujeonghyeon/Desktop/dev/ao-skills/commands/<name>.md`

신규 스킬은 frontmatter 필수.

```yaml
---
name: skill-name
description: <발동 조건과 무엇을 하는지>
---
```

신규 커맨드는 description frontmatter 권장.

```yaml
---
description: <이 커맨드가 무엇을 하는지 한 줄>
---
```

### 3. README 변경내역 갱신

`README.md`의 "## 최근 변경내역" 섹션 **맨 위**에 항목 추가. 날짜는 시스템 컨텍스트의 `currentDate`를 사용한다.

**수정인 경우**:
```markdown
### YYYY-MM-DD - <한 줄 요약>
- 기존: <as-is>
- 변경: <to-be>
- 이유: <왜 바꾸는가>
- 영향 파일: `path/...`
```

**신규인 경우**:
```markdown
### YYYY-MM-DD - 신규 추가: `<이름>`
- 종류: 스킬 / 커맨드
- 목적: <한 문장>
- 영향 파일: `path/...`
```

신규 추가 시 README의 "## 스킬 목록" 또는 "## 커맨드 목록" 표/문단도 함께 갱신한다.

### 4. ~/.claude/ 로 동기화

레포의 `skills/`, `commands/`를 그대로 `~/.claude/` 아래로 매번 덮어쓰기.

```bash
cp -R /Users/ujeonghyeon/Desktop/dev/ao-skills/skills/. ~/.claude/skills/
cp /Users/ujeonghyeon/Desktop/dev/ao-skills/commands/*.md ~/.claude/commands/
```

삭제 처리는 `cp`만으로 안 되므로, 삭제 작업일 때는 `~/.claude/skills/<name>` 또는 `~/.claude/commands/<name>.md`를 별도로 `rm`해야 한다.

### 5. 커밋 + 푸시

- 작업 디렉토리: 레포 루트
- 커밋 메시지 한국어, 기존 레포의 conventional commits 스타일 따른다.
  - 신규: `feat: <이름> 스킬/커맨드 추가`
  - 수정: `refactor: <이름> <변경 요약>`
  - 삭제: `chore: <이름> 스킬/커맨드 제거`
  - 문서만: `docs: README 변경내역 갱신`
- 본문에 무엇/왜 1~2줄
- `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` 라인 포함
- 커밋 직후 `git push` 자동 실행

## 절대 어기지 말 것

- `~/.claude/` 의 파일을 직접 편집하지 않는다. 항상 레포가 먼저.
- README 변경내역 섹션을 빼먹지 않는다.
- 동기화 단계를 건너뛰지 않는다 (cp 누락 시 실제 환경에 반영 X).
- 푸시 실패 시 원인을 사용자에게 알리고 멈춘다. 강제 푸시 금지.

## 종료 시 보고

사용자에게 다음을 한 화면에 보고한다.

- 변경된 파일 목록
- 커밋 해시 한 줄
- 푸시 결과 (성공/실패 + 원격 브랜치)
- 동기화된 `~/.claude/` 경로
