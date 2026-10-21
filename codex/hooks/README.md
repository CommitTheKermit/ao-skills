# Codex hooks

- `block-secrets.py`: 평문 비밀값과 자격값 덤프 명령을 PreToolUse에서 차단한다. PostToolUse는
  이미 도구 출력이 transcript에 기록된 뒤라 비밀을 회수할 수 없으며 보조 경고만 가능하다.
- `action-target-nudge.py`: 변경 요청에 대상과 완료 증거를 확인하라는 soft context를 주입한다.
- `android-emulator-lease-guard.py`: 세션 임대와 명시적 serial 없이 실행되는 Android 에뮬레이터 조작을 차단한다.
- `github-create-approval-guard.py`: `슛` 1회를 단일 생성 요청에 예약한다. 확인된 issue/PR URL 또는 API 영수증에만 소비하고, HTTP 4xx 거절은 동일 요청 재시도를 허용한다. 통신 실패, 호출 중단, 결과 형식 미확인은 보류한다. 명령·본문 파일·저장소가 바뀌면 새 승인이 필요하다.
- `chaekchaek-*.py`: Chaekchaek 프로젝트 `.codex`에만 설치하는 branch, PR, design guard다.

비밀값 감지 메시지는 패턴 이름만 출력한다. 감지한 값, 명령 결과, 파일 본문은 출력하지 않는다.
훅 파일이 바뀌면 새 Codex 세션에서 변경된 hook hash를 다시 신뢰해야 한다.

## GitHub 승인 훅 적용과 검증

`bash codex/sync.sh --hooks github-create-approval-guard`와 `bash codex/verify.sh --hooks github-create-approval-guard`를 사용한다. 다른 훅 등록을 보존하며 `UserPromptSubmit`, `PreToolUse`, `PostToolUse`에 연결한다. 스킬 변경에 전체 동기화를 사용할 필요는 없다.

복합 셸, 여러 생성, 동적 JS 생성 호출은 단일 직접 호출로 분리한다. `gh issue/pr create`에는 `-R owner/repo`를 권장한다. CLI JSON/URL 영수증과 MCP `html_url`/`number` 결과를 확인하며 `functions.exec`는 단일 literal 명령만 처리한다. 임의 스크립트, 외부 클라이언트, 훅 미지원 경로까지 통제하는 보안 경계는 아니다.

상태는 `~/.codex/github-create-approvals/`에 세션·요청 해시, 대상 저장소, 호출 ID, 단계만 기록한다. 본문과 토큰은 저장하지 않는다. 기존 임시 승인 파일은 이전하지 않으며 새 `슛`부터 적용한다.

결과가 불명확하면 issue/PR 목록을 조회한다. 같은 요청이 생성됐다면 아래 읽기 전용 재확인으로 예약을 소비한다. 제목·본문 해시와 저장소·유형까지 대조한다.

```sh
python3 "$HOME/.codex/hooks/github-create-approval-guard.py" --session-id <session-id> --reconcile-url https://github.com/owner/repo/issues/123
```

검색 결과가 없다는 이유만으로 보류를 해제하지 않는다. 이 버전은 생성 영수증을 확인할 수 없는 중단 요청의 자동 재시도를 허용하지 않는다. 보류 중 새 `슛`으로 덮어쓰지 않으며 상태 파일을 임의 삭제하지 않는다.

이벤트와 `tool_use_id`/`tool_response` 계약 근거: [공식 Hooks 문서](https://learn.chatgpt.com/docs/hooks#posttooluse), 2026-10-21 확인. 회귀 테스트는 실제 GitHub 생성 없이 임시 상태와 모의 응답으로 수행한다. 훅 신뢰 등록과 새 세션에서의 실제 이벤트 전달은 별도 확인 대상이다.
