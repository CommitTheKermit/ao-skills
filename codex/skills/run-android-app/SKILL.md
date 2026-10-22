---
name: run-android-app
description: Android 앱을 에뮬레이터나 연결 기기에 빌드, 설치, 실행해 달라는 요청에 사용한다. 일반 실행은 디버거 대기 없이 수행하고, 사용자가 디버거 연결을 명시한 경우에만 디버그 대기 모드를 사용한다.
---

# Run Android App

<!-- usage-stats: skill run-android-app -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill run-android-app >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

## 로컬 모바일 실행 대기열

로컬 모바일 빌드·부팅·설치·연결 테스트·UI 검증 전에 [mobile-validation-queue](../mobile-validation-queue/SKILL.md)를 적용한다. 슬롯 안에서 기존 기기 임대와 설치 검사를 수행하고, 자신이 시작한 기기 정리까지 슬롯을 유지한다. 슬롯 대기를 피하려고 다른 AVD를 추가 실행하지 않는다.

## 실행 규칙

1. 대상 프로젝트, 기기, 실행할 APK를 확인한다.
2. 에뮬레이터를 사용한다면 먼저 `android-emulator-lease` 스킬을 적용해 AVD를 임대한다. 다른 세션이 임대한 AVD를 사용하거나 종료하지 않는다.
3. 대기열 슬롯 안에서 현재 소스의 APK를 먼저 빌드한다. 그다음 필요한 경우 임대한 에뮬레이터를 시작하고 실제 serial을 임대에 연결한다.
4. 설치 직전에 아래 읽기 전용 검사를 실행한다. 대상 패키지명은 요청과 프로젝트 설정에서 확인한다. 조회 실패를 미설치로 간주하지 않는다.

   ```sh
   python3 "$HOME/.agents/skills/run-android-app/scripts/preflight-install.py" --apk /absolute/path/app.apk --serial <serial> --package <applicationId>
   ```

   종료 코드 0일 때만 진행한다. 낮은 versionCode, 다른 패키지 또는 다른 서명이면 원인과 기기/APK 비교값을 보고한다. 인증서 회전은 단순 불일치로 호환성을 확정할 수 없으므로 별도 검증한다. 자동 uninstall, 데이터 삭제, downgrade 강제 옵션을 사용하지 않는다. 삭제가 필요한 경우 데이터 영향과 서명/대상 근거를 제시하고 새 명시적 승인을 받는다.

   APK SHA-256과 versionName/versionCode, 설치본과 대상의 인증서 SHA-256을 근거로 남긴다. `--source-sha`는 빌드 기록의 선언값이며 현재 git HEAD나 인수만으로 APK 출처를 증명하지 않는다. 검사와 설치 사이에 APK 또는 설치본이 바뀌면 다시 검사한다.

5. 일반 실행은 `android run --device=<serial> --apks=<apk>`처럼 명시적인 serial과 함께 `--debug` 없이 수행한다.
6. debug APK를 실행한다는 이유만으로 `android run --debug`를 추가하지 않는다. debug 빌드 타입과 디버거 대기 옵션은 별개다.
7. 사용자가 디버거 연결, 브레이크포인트 실행, 디버거 대기를 명시한 경우에만 대기 동작을 먼저 알리고 `--debug`를 사용한다.
8. 현재 작업에서 시작한 에뮬레이터만 종료하고, 종료 확인 후 임대를 해제한다. 기존 실행 중인 AVD는 명시적 요청 없이 종료하지 않는다.
9. 실행 결과에는 사용한 AVD, serial, 설치 전 비교 결과, 앱 실행 성공 여부, 임대 해제 여부를 간단히 보고한다.
