# Codex hooks

- `block-secrets.py`: 평문 비밀값과 자격값 덤프 명령을 PreToolUse에서 차단한다. PostToolUse는
  이미 도구 출력이 transcript에 기록된 뒤라 비밀을 회수할 수 없으며 보조 경고만 가능하다.
- `action-target-nudge.py`: 변경 요청에 대상과 완료 증거를 확인하라는 soft context를 주입한다.
- `chaekchaek-*.py`: Chaekchaek 프로젝트 `.codex`에만 설치하는 branch, PR, design guard다.

비밀값 감지 메시지는 패턴 이름만 출력한다. 감지한 값, 명령 결과, 파일 본문은 출력하지 않는다.
훅 파일이 바뀌면 새 Codex 세션에서 변경된 hook hash를 다시 신뢰해야 한다.
