---
name: run-android-app
description: Android 앱을 에뮬레이터나 연결 기기에 빌드, 설치, 실행해 달라는 요청에 사용한다. 일반 실행은 디버거 대기 없이 수행하고, 사용자가 디버거 연결을 명시한 경우에만 디버그 대기 모드를 사용한다.
---

# Run Android App

<!-- usage-stats: skill run-android-app -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill run-android-app >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

## 실행 규칙

1. 대상 프로젝트, 기기, 실행할 APK를 확인한다.
2. 필요한 경우 에뮬레이터를 시작하고 현재 소스의 APK를 빌드한다.
3. 일반 실행은 `android run --device=<serial> --apks=<apk>`처럼 `--debug` 없이 수행한다.
4. debug APK를 실행한다는 이유만으로 `android run --debug`를 추가하지 않는다. debug 빌드 타입과 디버거 대기 옵션은 별개다.
5. 사용자가 디버거 연결, 브레이크포인트 실행, 디버거 대기를 명시한 경우에만 대기 동작을 먼저 알리고 `--debug`를 사용한다.
6. 실행 결과에는 사용한 기기와 앱 실행 성공 여부만 간단히 보고한다.
