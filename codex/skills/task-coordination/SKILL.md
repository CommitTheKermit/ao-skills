---
name: task-coordination
description: 같은 저장소의 여러 세션에서 기능 구현을 시작하거나 인계할 때 공용 담당 등록으로 동일 기능 중복 구현을 방지한다.
---

# task-coordination

<!-- usage-stats: skill task-coordination -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill task-coordination >/dev/null 2>&1 || true`를 한 번 실행한다.

## 시작과 완료

이슈·브랜치·구현을 시작하기 전에 진행 중인 작업과 범위를 조회한다. 같은 기능의 후속 수정·테스트·문서는 같은 식별자를 사용한다. 리뷰만 하는 세션은 별도 구현 담당권을 잡지 않는다.

```sh
registry="$HOME/.agents/skills/task-coordination/scripts/task_registry.py"
python3 "$registry" list --repo /absolute/repo
python3 "$registry" claim --repo /absolute/repo --feature issue:123 --scope '이번에 구현할 동작과 범위'
python3 "$registry" release --repo /absolute/repo --feature issue:123
```

- 이슈가 있으면 `issue:번호`, 없으면 합의한 `feature:이름`을 사용한다. 표시 제목의 유사도로 자동 합치거나 같은 기능에 다른 키를 만들어 우회하지 않는다. 목록의 범위가 겹치고 판단이 모호하면 사용자에게 확인한다.
- `claim`은 SQLite 트랜잭션으로 동시에 한 담당자만 성공한다. 다른 담당자가 있으면 새 구현을 시작하지 않는다. 기존 세션에 메시지를 보내는 권한은 별도로 확인한다.
- `--owner`, `AGENT_SESSION_ID`, `CODEX_THREAD_ID`, `CODEX_SESSION_ID` 순서로 소유자를 정한다. 자동 ID가 없는 도구는 대화 동안 고정된 `AGENT_SESSION_ID`를 지정한다. 명령마다 새 ID를 만들지 않는다.
- Git common-dir를 저장소 키로 사용하므로 같은 저장소의 워크트리는 공유한다. 별도 clone·다른 사용자·다른 호스트는 자동 통합하지 않는다.
- 등록은 완료·명시적 인계까지 유지한다. 경과 시간이나 프로세스 부재만으로 담당권을 삭제하지 않는다. 단순 대화 응답 종료를 기능 완료로 간주하지 않는다.
- 인계는 기존 담당자가 `handoff --repo ... --feature ... --to-owner 새ID`로 수행한다. 종료된 세션의 복구는 실제 상태와 사용자 인계 승인을 확인한 뒤 기존 `--owner`를 지정해 수행한다. 소유자 값은 로컬 협업 식별자이며 보안 인증 수단이 아니다.
- 목록에는 담당자·워크트리·브랜치·범위가 표시된다. `claim` 성공 후에만 독립 작업 브랜치 생성/변경을 진행한다. 실제 브랜치를 정한 뒤 같은 소유자로 다시 claim해 정보를 갱신한다.
- 공용 상태는 `~/.local/state/agent-coordination/tasks.sqlite3`에 둔다. `AGENT_COORDINATION_DIR`은 테스트용 격리에만 사용하고 실제 세션마다 별도 경로로 바꾸지 않는다.

이 규칙은 모든 파일 수정이나 명령 실행을 가로채는 훅이 아니다. 진입 규칙을 지키는 세션 사이에서 동일 식별자의 중복 담당을 막는다.
