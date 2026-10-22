---
name: android-emulator-lease
description: Android 에뮬레이터나 adb를 사용하는 모든 작업 전에 세션별 AVD 임대를 획득하고 명시적인 serial만 사용한다. 병렬 Codex 세션에서 에뮬레이터 시작, 설치, 입력, 종료, adb 서버 조작이 겹치지 않게 한다.
---

# Android Emulator Lease

<!-- usage-stats: skill android-emulator-lease -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill android-emulator-lease >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

Android 에뮬레이터, `adb`, `android run`, `android layout`, `android screen`, Gradle 설치 및 연결 기기 테스트를 사용하기 전에 이 절차를 적용한다. 워크트리는 Git 파일만 분리하며 AVD와 adb 서버는 머신 전체에서 공유된다.

## 플랫폼 실행 경로

Android 검증은 먼저 [plipa-remote-validation](../plipa-remote-validation/SKILL.md)을 읽고 원격으로 제출한다. 저장소·허용 ref·정확한 소스 SHA·프로필 지원 범위를 확인한다. 원격 설정 누락, 장애 또는 미지원 검증을 이유로 자동으로 로컬 실행하지 않는다. 사용자가 로컬 실행이나 특정 로컬 기기를 명시한 경우에만 아래 로컬 절차를 적용하며, [mobile-validation-queue](../mobile-validation-queue/SKILL.md)의 슬롯 안에서 빌드와 기기 임대·설치·정리를 수행한다.

원격 smoke는 검증 후 기기를 정리한다. 사용자에게 계속 조작 가능한 앱이나 로컬 플리파 화면을 남기는 실행 요청을 smoke 성공으로 대체하지 않는다.

## 로컬 모바일 실행 대기열

로컬 모바일 빌드·부팅·설치·연결 테스트·UI 검증 전에 [mobile-validation-queue](../mobile-validation-queue/SKILL.md)를 적용한다. 슬롯 안에서 기존 기기 임대와 설치 검사를 수행하고, 자신이 시작한 기기 정리까지 슬롯을 유지한다. 슬롯 대기를 피하려고 다른 AVD를 추가 실행하지 않는다.

## 임대 도구

```bash
lease="$HOME/.agents/skills/android-emulator-lease/scripts/emulator_lease.py"
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
