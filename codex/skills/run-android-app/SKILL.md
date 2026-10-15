---
name: run-android-app
description: Android 앱을 에뮬레이터나 연결 기기에 빌드, 설치, 실행해 달라는 요청에 사용한다. 일반 실행은 디버거 대기 없이 수행하고, 사용자가 디버거 연결을 명시한 경우에만 디버그 대기 모드를 사용한다.
---

# Run Android App

<!-- usage-stats: skill run-android-app -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill run-android-app >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

## 실행 규칙

1. 대상 프로젝트, 기기, 실행할 APK를 확인한다.
2. 에뮬레이터를 사용한다면 먼저 `android-emulator-lease` 스킬을 적용해 AVD를 임대한다. 다른 세션이 임대한 AVD를 사용하거나 종료하지 않는다.
3. 필요한 경우 임대한 에뮬레이터를 시작하고 실제 serial을 임대에 연결한 뒤 현재 소스의 APK를 빌드한다.
4. 일반 실행은 `android run --device=<serial> --apks=<apk>`처럼 명시적인 serial과 함께 `--debug` 없이 수행한다.
5. debug APK를 실행한다는 이유만으로 `android run --debug`를 추가하지 않는다. debug 빌드 타입과 디버거 대기 옵션은 별개다.
6. 사용자가 디버거 연결, 브레이크포인트 실행, 디버거 대기를 명시한 경우에만 대기 동작을 먼저 알리고 `--debug`를 사용한다.
7. 현재 작업에서 시작한 에뮬레이터만 종료하고, 종료 확인 후 임대를 해제한다. 기존 실행 중인 AVD는 명시적 요청 없이 종료하지 않는다.
8. 실행 결과에는 사용한 AVD, serial, 앱 실행 성공 여부, 임대 해제 여부를 간단히 보고한다.
