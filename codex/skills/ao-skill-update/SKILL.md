---
name: ao-skill-update
description: ao-skills 레포의 Codex 전용 스킬/커맨드를 변경하고 전역 Codex 설정에 동기화한 뒤 커밋·푸시한다. 사용자가 "스킬 만들자", "스킬 수정", "커맨드 변경", "스킬 동기화"라고 요청하면 사용한다.
---

# ao-skill-update (Codex)

`/Users/ujeonghyeon/Desktop/dev/myDev/ao-skills`를 단일 진실 소스로 사용한다. Claude용 원본과
Codex용 원본을 섞지 않는다.

## 저장 위치

- Claude용: `skills/`, `commands/`
- Codex용: `codex/skills/`, `codex/commands/`
- Codex 설치본: `~/.agents/skills/`, `~/.Codex/commands/`

Codex 작업에서는 `codex/` 아래만 편집한다. 전역 설치본을 직접 수정하지 않는다. 이 저장소는
개인 설정 저장소이므로 새 브랜치를 만들지 않고 `main`에서 커밋·푸시한다.

## 절차

1. 신규 추가, 기존 수정, 삭제 중 하나로 분류한다.
2. 신규인데 사용자가 형태를 지정하지 않았다면 부속 파일 유무를 기준으로 스킬 또는 커맨드를
   먼저 선택받는다.
3. 스킬은 `codex/skills/<name>/`, 커맨드는 `codex/commands/<name>.md`에서 편집한다.
4. `README.md`의 현재 ISO 주차 변경내역 맨 위에 기존·변경·이유·영향 파일을 기록한다.
5. `bash codex/sync.sh`로 동기화한다.
6. 아래 검증을 실행한다.

   ```bash
   bash codex/verify.sh
   ```

7. 한국어 conventional commit을 만들고 `git push origin main`을 실행한다. 서명 트레일러는
   넣지 않는다.

## 신규 파일 형식

스킬은 다음 frontmatter가 필수다.

```yaml
---
name: skill-name
description: 발동 조건과 수행 내용
---
```

커맨드는 `description` frontmatter를 권장한다. 훅이나 자산이 필요한 작업은 스킬로, 단일 문서로
충분하면 커맨드로 둔다.

## 동기화 원칙

`codex/sync.sh`는 Codex 스킬을 `~/.agents/skills/`에 설치하고, 과거 `~/.Codex/skills/`에
복사돼 중복 등록된 같은 디렉터리를 제거한다. 제거 대상은 `codex/skills/`의 정확한 하위
디렉터리로 제한되며 원본으로 복구할 수 있다.

삭제 작업은 원본과 설치본에서 같은 이름만 제거한다. 다른 스킬이나 사용자 데이터를 건드리지
않는다.

## 변경내역

현재 주차는 `date +%G-W%V`로 구한다. `README.md`의 주차가 같으면 새 항목을 맨 위에 추가한다.
주차가 바뀌었으면 기존 항목을 `changelog/<직전 주차>.md`로 옮기고 지난 변경내역 링크를
추가한다.

## 종료 보고

- 변경 파일
- 검증 결과
- 커밋 해시
- `origin/main` 푸시 결과
- 동기화 경로
- 설치형 하네스 자산을 바꿨다면 기존 프로젝트 사본 재전파 필요 여부
