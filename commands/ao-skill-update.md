---
description: ao-skills 레포의 스킬/커스텀 커맨드를 변경하고 Claude 전역 설정으로 동기화, 커밋+푸시까지 자동 완료
---

`ao-skill-update` 스킬의 워크플로우를 따른다.

## 시작 절차

1. **요청 파악**: `$ARGUMENTS`가 비어 있으면 사용자에게 "어떤 스킬/커맨드를 만들거나 수정하시겠어요?" 한 줄로 묻는다.
2. **분류**: 신규 스킬 / 신규 커맨드 / 기존 수정 / 삭제 중 어떤 작업인지 결정.
3. **레포에서 편집**: `/Users/ujeonghyeon/Desktop/dev/ao-skills/` 안에서만 편집한다. `~/.claude/` 직접 편집 금지.
4. **README 변경내역 갱신**: "## 최근 변경내역" 섹션 맨 위에 오늘 날짜 항목 추가.
5. **동기화**:
   ```bash
   cp -R /Users/ujeonghyeon/Desktop/dev/ao-skills/skills/. ~/.claude/skills/
   cp /Users/ujeonghyeon/Desktop/dev/ao-skills/commands/*.md ~/.claude/commands/
   ```
   삭제 작업이면 `~/.claude/` 쪽 파일을 별도로 `rm`.
6. **커밋 + 푸시**: 한국어 conventional commits 스타일. `Co-Authored-By` 포함. 커밋 직후 자동 `git push`.

각 단계의 세부 형식(변경내역 항목, 커밋 메시지 prefix 등)은 `ao-skill-update` 스킬 정의를 따른다.

## 종료 보고

- 변경 파일 목록
- 커밋 해시
- 푸시 결과
- 동기화 완료 경로

---

요청: $ARGUMENTS