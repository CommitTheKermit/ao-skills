---
name: usage-stats
description: ao-skills가 관리하는 개인 Codex 스킬·훅·하네스의 전역 사용 횟수와 최초·최근 사용 시각을 조회한다. 사용자가 "스킬 사용량", "어떤 스킬 자주 써", "안 쓰는 스킬", "훅 사용 횟수", "하네스 통계", "/usage-stats"처럼 사용 현황이나 정리 후보를 묻는 경우 사용한다.
---

# Usage Stats

<!-- usage-stats: skill usage-stats -->

첫 동작으로 아래 기록 명령을 이 발동에서 한 번만 실행한다.

```bash
python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill usage-stats >/dev/null 2>&1 || true
```

다음 명령으로 등록된 개인 스킬·훅·하네스 전체를 사용 횟수 내림차순으로 조회한다.

```bash
python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" report
```

특정 종류만 요청하면 `report --kind skill|hook|harness`를 사용한다. 기계 판독 결과를 요청하면
`report --json`을 사용한다. `0`은 계측 대상으로 등록됐지만 아직 관측된 실행이 없다는 뜻이다.
카운터는 `~/.Codex/usage-stats.json`에 저장하며 프롬프트나 프로젝트 경로는 기록하지 않는다.
