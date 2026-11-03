---
name: build-signed-aab
description: Android 프로젝트에서 Play Console 제출용 서명 release AAB를 빌드하고 검증한다. 사용자가 "AAB 빌드", "서명 AAB", "심사용 번들", "bundleRelease", "Play 업로드 파일 만들어줘"처럼 Android App Bundle 산출물을 요청할 때 사용한다. 프로젝트 메모리의 applicationId와 버전을 확인하고 단위 테스트·Lint·서명·manifest·런처 아이콘을 검증한 뒤 버전명 파일로 보관한다.
---

# Build Signed AAB

<!-- usage-stats: skill build-signed-aab -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill build-signed-aab >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

## 플랫폼 실행 경로

Android 검증은 먼저 [plipa-remote-validation](../plipa-remote-validation/SKILL.md)으로 원격 접수 전 연결 상태와 저장소·허용 ref·정확한 소스 SHA·프로필을 확인한다. 서버 꺼짐 또는 원격 연결 불가가 확인되고 미확정 원격 접수가 없으면, 추가 로컬 실행 승인 없이 [jev-local-validation](../jev-local-validation/SKILL.md)으로 전환한다. 인증·403·설정 오류, ref 불일치와 미지원 범위는 오프라인으로 취급하지 않는다. 사용자가 로컬 실행이나 특정 로컬 기기를 명시한 경우에도 아래 로컬 절차와 [mobile-validation-queue](../mobile-validation-queue/SKILL.md)를 적용해 빌드·기기 임대·설치·정리를 한 슬롯 안에서 수행한다. Jev의 UI 결과로 AAB·Lint·단위 테스트를 대체하지 않는다.

현재 `android-smoke`는 release APK·지정 단위 테스트·설치와 실행만 지원한다. AAB 생성, Lint 및 심사 전체 검증은 포함하지 않는다. 아래 명령은 해당 작업을 지원하는 원격 프로필 또는 명시적으로 허용된 로컬 실행 경로가 확보된 뒤 수행한다. APK 성공을 AAB나 Lint 통과로 보고하지 않는다.

## 절차

1. 저장소와 Android 스코프의 `AGENTS.md`를 읽는다.
2. `app/build.gradle.kts` 또는 `app/build.gradle`에서 `applicationId`, `versionCode`, `versionName`과 release signing 설정을 확인한다.
   - Play Console에 이미 사용한 `versionCode`가 불명확하면 빌드 전에 사용자에게 묻는다.
   - 버전과 패키지명은 자동 변경하지 않는다.
   - keystore 경로·별칭·비밀번호 등 비밀값을 출력하지 않는다.
3. Android 명령을 실행하기 전에 명령의 역할을 한 줄로 설명한다.
4. 다음 스크립트를 저장소 루트 또는 Android 루트를 인자로 실행한다.

```bash
bash <skill-dir>/scripts/build-signed-aab.sh <project-root>
```

5. 스크립트가 출력한 application ID, 버전, 서명, 아이콘, SHA-256과 최종 경로를 보고한다.
6. Play Console 업로드나 Git 커밋·푸시는 사용자가 별도로 요청한 경우에만 수행한다.

## 스크립트 동작

`scripts/build-signed-aab.sh`는 `android/gradlew` 또는 루트 `gradlew`를 찾아 다음만 수행한다.

- `:app:testDebugUnitTest :app:bundleRelease`
- 생성된 AAB의 JAR 서명 검증
- bundle manifest의 application ID·버전 추출
- manifest가 가리키는 런처 아이콘의 AAB 포함 여부 검증
- `app/release/<앱ID-끝부분>-<versionName>-code<versionCode>.aab`로 복사
- SHA-256 출력

같은 버전 파일이 있으면 모든 빌드·검증이 성공한 뒤에만 교체한다. `clean`은 실행하지 않는다.
