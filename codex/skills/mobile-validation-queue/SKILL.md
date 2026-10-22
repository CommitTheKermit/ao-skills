---
name: mobile-validation-queue
description: 로컬 Android/iOS 빌드, 에뮬레이터 부팅, 설치, 연결 테스트와 UI 검증을 실행할 때 호스트 공용 FIFO 대기열을 사용한다.
---

# mobile-validation-queue

<!-- usage-stats: skill mobile-validation-queue -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill mobile-validation-queue >/dev/null 2>&1 || true`를 한 번 실행한다.

## 실행

같은 Mac 사용자 계정에서 무거운 모바일 작업을 한 번에 하나 실행한다. 검증 시나리오를 수행하는 전경 스크립트 전체를 감싼다. 기기 부팅이나 빌드를 먼저 실행하고 뒤늦게 줄을 서지 않는다.

```sh
queue="$HOME/.agents/skills/mobile-validation-queue/scripts/validation_queue.py"
python3 "$queue" status
python3 "$queue" run --label '책췍 Android 검증' -- sh /absolute/path/validate-android.sh
python3 "$queue" cancel JOB_ID --owner SESSION_ID
```

- `--owner`, `AGENT_SESSION_ID`, `CODEX_THREAD_ID`, `CODEX_SESSION_ID`로 안정적인 소유자를 지정한다. 대기와 실행 시작 시에만 상태를 출력하며, 에이전트가 짧은 주기로 반복 조회하지 않는다.
- FIFO 순서와 프로세스 파일 잠금으로 한 슬롯만 실행한다. 중첩 실행기는 실제 상위 프로세스와 작업 토큰을 확인한 뒤 같은 슬롯을 사용한다. 환경변수만 복사해 다른 세션이 슬롯을 재사용할 수 없다.
- 슬롯 안에서 Android는 기존 `android-emulator-lease`를 추가로 획득하고 명시적 serial을 사용한다. iOS는 명시적 UDID를 사용한다. 소유자가 불명확한 실행 중인 기기를 재사용·종료하지 않는다.
- 가능한 경우 빌드 후 기기를 부팅한다. Gradle은 `--no-daemon`을 사용한다. 검증 종료 시 자신이 시작한 기기만 종료하고 임대를 해제한 뒤 슬롯을 반환한다. 다른 세션 기기를 종료해 메모리를 확보하지 않는다.
- UI 조작까지 포함하는 작업은 소유 전경 스크립트를 계속 실행한 상태에서 수행한다. 별도 도구 호출이 필요하면 스크립트가 명시적 완료 신호를 기다리게 하고, 해당 도구 호출이 동일 작업임을 기록한다. 빌드 명령 종료를 전체 기기 검증 완료로 간주하지 않는다.
- 플리파의 로컬 상시 사용처럼 기기를 계속 켜야 하면 사용 기간 동안 슬롯을 유지한다. 실행 후 즉시 슬롯을 반환하고 기기만 남겨두지 않는다. 원격 플리파 연결은 이 스킬의 범위가 아니다.
- 명령 실패는 종료 코드를 보존하고 슬롯을 반환한다. 취소는 담당 실행기가 자신의 명령 프로세스 그룹만 종료한다. 남은 자식 프로세스가 확인되면 `blocked`로 유지한다. detached 프로세스를 남기는 명령은 지원하지 않는다.
- 감독 프로세스 강제 종료 시 실행 중 기록은 자동 삭제하지 않는다. `status`로 PID·PGID를 확인하고 관련 빌드와 기기가 모두 정리됐다는 근거를 확인한 뒤 `recover JOB_ID --confirmed-stopped`를 사용한다. 프로세스 또는 파일 잠금이 살아 있으면 복구를 거부한다. 오래됐다는 이유로 다른 작업을 종료하지 않는다.
- 대기 중 감독 프로세스가 종료된 작업만 다음 실행기가 자동으로 건너뛴다. 실기기나 외부에서 이미 실행 중인 작업은 이 대기열이 자동으로 인수하지 않는다.
- 상태는 `~/.local/state/agent-coordination/mobile.sqlite3`와 `mobile.lock`에 저장한다. 같은 호스트 사용자 계정의 세션은 경로를 공유한다. `AGENT_COORDINATION_DIR`은 테스트 격리용이다. 원격 호스트나 다른 사용자 계정까지 직렬화하지 않는다.
- `check`는 현재 호출이 유효한 상위 대기열 실행 안인지 확인한다. 책췍의 `test-ios-hig.sh`는 직접 실행해도 자동으로 이 실행기를 거친다. 임의의 Gradle/adb/Xcode 명령을 운영체제 수준에서 차단하는 훅은 아니다.

## 검증 범위

양 플랫폼의 동일 시나리오 검증 요구와 APK 서명·데이터 보존 규칙을 그대로 유지한다. 슬롯 획득이나 빌드 성공을 앱 실행 성공으로 보고하지 않는다. 실제 검증 결과에는 소스 커밋, 변경 여부, 플랫폼·기기와 시나리오를 남긴다.
