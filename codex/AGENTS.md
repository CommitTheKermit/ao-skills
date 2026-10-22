# 원격 검증 작업

- 플리파 원격 실행과 클라이언트를 변경할 때는 [plipa-remote-validation](skills/plipa-remote-validation/SKILL.md)을 먼저 읽는다. 설치본은 선택 동기화하고 사설 연결 설정은 Git 밖에 둔다.
# Codex 작업 조율 자산

- 동일 기능 담당 등록을 수정할 때는 [task-coordination](skills/task-coordination/SKILL.md)을 먼저 읽는다. 전역 규칙의 관리 블록 원본은 [global-rules.md](skills/task-coordination/references/global-rules.md)이며, 적용 시 해당 블록만 교체하고 나머지 사용자 규칙은 보존한다.
- 모바일 실행 대기열을 수정할 때는 [mobile-validation-queue](skills/mobile-validation-queue/SKILL.md)를 먼저 읽는다. 프로세스 통합 검증은 `python3 -m unittest discover -s codex/skills/mobile-validation-queue/scripts -p 'test_*.py'`로 수행한다.
- 변경한 설치형 스킬만 `codex/sync.sh --skills ...`로 동기화하고 `codex/verify.sh --skills ...`로 확인한다.
