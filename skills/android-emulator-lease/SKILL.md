---
name: android-emulator-lease
description: Android 에뮬레이터나 adb를 사용하는 모든 작업 전에 세션별 AVD 임대를 획득하고 명시적인 serial만 사용한다. 병렬 Claude Code·Codex 세션에서 에뮬레이터 시작, 설치, 입력, 종료, adb 서버 조작이 겹치지 않게 한다.
---

# Android Emulator Lease

<!-- usage-stats: skill android-emulator-lease -->

Android 에뮬레이터, `adb`, `android run`, `android layout`, `android screen`, Gradle 설치 및 연결 기기 테스트를 사용하기 전에 이 절차를 적용한다. 워크트리는 Git 파일만 분리하며 AVD와 adb 서버는 머신 전체에서 공유된다. 임대 기록은 Codex와 같은 `~/.codex/android-emulator-leases`를 써서 두 도구가 동시에 실행돼도 서로의 임대를 본다.

## 임대 도구

```bash
lease="$HOME/.claude/skills/android-emulator-lease/scripts/emulator_lease.py"
python3 "$lease" status
python3 "$lease" acquire --avd <AVD 이름>
```

AVD를 시작한 뒤 실제 serial을 연결한다.

```bash
android emulator start <AVD 이름>
adb devices -l
python3 "$lease" bind --avd <AVD 이름> --serial <emulator serial>
```

이후 모든 명령에 같은 serial을 명시한다.

```bash
android run --device=<serial> --apks=<apk>
adb -s <serial> shell getprop sys.boot_completed
ANDROID_SERIAL=<serial> ./gradlew :app:installDebug
```

## 필수 규칙

- AVD를 시작하기 전에 `acquire`한다. 이미 다른 세션이 임대한 AVD면 사용하거나 종료하지 않고 다른 AVD를 선택하거나 기다린다.
- 실행 중이지만 임대가 없는 AVD는 소유자를 알 수 없으므로 자동으로 선택하거나 종료하지 않는다. 현재 대화에서 그 AVD를 이 작업이 시작했다는 근거가 있을 때만 `adopt --avd <이름> --serial <serial>`로 인수한다. 근거가 없으면 다른 AVD를 선택한다.
- `adb` 대상 명령, `android run`, 화면 캡처 및 레이아웃 조회, Gradle 설치와 연결 테스트에는 serial을 명시한다. 첫 번째 기기를 암묵적으로 선택하지 않는다.
- `adb kill-server`, `adb reconnect`, QEMU 직접 `kill`, AVD lock 파일 삭제는 다른 세션에 영향을 줄 수 있다. 다른 활성 임대가 있으면 실행하지 않는다.
- 현재 세션이 임대한 AVD만 종료한다. 종료가 확인된 뒤 임대를 해제한다.

```bash
android emulator stop <serial>
python3 "$lease" release --avd <AVD 이름>
```

- 작업 중 연결이 끊겨도 다른 에뮬레이터를 종료하거나 adb 서버를 재시작하지 않는다. `status`로 소유권을 다시 확인한다.
- 강제 종료된 세션의 임대는 15분이 지나고 연결된 serial과 QEMU 프로세스가 모두 없을 때만 `prune`으로 제거한다.

```bash
python3 "$lease" prune
```

전역 `android-emulator-lease-guard` 훅이 소유권 없는 변경 명령을 차단한다. 훅 거부를 우회하지 말고 위 임대 절차를 먼저 수행한다.
