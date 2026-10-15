---
name: usage-stats
description: ao-skills가 관리하는 개인 Claude Code 스킬·훅·하네스의 전역 사용 횟수와 최초·최근 사용 시각을 조회한다. 사용자가 "스킬 사용량", "어떤 스킬 자주 써", "안 쓰는 스킬", "훅 사용 횟수", "하네스 통계", "/usage-stats"처럼 사용 현황이나 정리 후보를 묻는 경우 사용한다.
---

# Usage Stats

<!-- usage-stats: skill usage-stats -->

기록은 `~/.claude/settings.json`의 훅이 자동으로 한다. 스킬 본문에서 따로 기록 명령을 실행하지 않는다.

- `PreToolUse`(matcher `Skill`)와 `UserPromptSubmit` 훅이 `usage_stats.py hook`에 훅 입력 JSON을 넘긴다.
- 하네스 스크립트(예: `android-emulator-lease`)는 스스로 `record harness <이름>`을 호출한다.

다음 명령으로 등록된 개인 스킬·훅·하네스 전체를 사용 횟수 내림차순으로 조회한다.

```bash
python3 "$HOME/.claude/skills/usage-stats/scripts/usage_stats.py" report
```

특정 종류만 요청하면 `report --kind skill|hook|harness`를 사용한다. 기계 판독 결과를 요청하면
`report --json`을 사용한다. `0`은 `~/.claude/skills`에 있지만 아직 관측된 실행이 없다는 뜻이다.
카운터는 `~/.claude/usage-stats.json`에 저장하며 프롬프트나 프로젝트 경로는 기록하지 않는다.
Codex 시절 카운터(`~/.codex/usage-stats.json`)와는 합치지 않는다.
