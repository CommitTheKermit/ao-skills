---
name: plipa-remote-validation
description: Mac에서 홈서버 플리파에 정확한 커밋의 Android 빌드, 단위 테스트와 설치·실행 검증을 제출하고 결과를 받는다.
---

# 플리파 원격 검증

<!-- usage-stats: skill plipa-remote-validation -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill plipa-remote-validation >/dev/null 2>&1 || true`를 한 번 실행한다.

## 기본 라우팅과 지원 경계

- 다른 세션에서도 Android 빌드·테스트·설치·실행 검증의 기본 진입점은 이 스킬이다. 현재 서버 설정은 책췍용이다. 제출 전에 대상 저장소와 서버 설정의 저장소·허용 ref·프로필이 일치하는지 확인한다. 다른 프로젝트를 책췍 프로필에 제출하지 않는다.
- 검증할 변경이 포함된 40자리 SHA를 사용한다. 로컬 미커밋 변경이나 서버에서 가져올 수 없는 커밋은 검증되지 않는다. 제출을 위해 보호 브랜치에 직접 push하거나 이전 커밋으로 대체하지 않는다.
- 설정 누락, 허용 ref 불일치, 장애 또는 미지원 범위는 차단 사유와 미검증 항목을 보고한다. 자동으로 Mac 빌드·AVD 실행으로 전환하지 않는다. 사용자가 로컬 실행을 명시한 경우에만 `mobile-validation-queue`와 `android-emulator-lease`를 적용한다.
- iOS는 `mobile-validation-queue`를 사용한다. 양 플랫폼 비교 시 동일 소스 SHA를 기준으로 하고 로컬 변경 여부도 기록한다. 서로 다른 호스트의 Android 원격 작업과 iOS 로컬 작업은 병행할 수 있다.
- 결과의 소스 SHA·프로필이 제출한 값과 일치하는지 확인하고 결과 ZIP을 수집한다. 빌드·단위 테스트·설치·실행·요청한 UI 시나리오를 각각 보고하며 smoke 밖의 시나리오는 미검증으로 남긴다.

## 실행 경로

`~/.config/plipa-remote/client.json`의 SSH 별칭과 서버 실행기 설정을 사용한다. 이 파일은 Git 밖에 두고 접속 주소·사용자·개인키·원격 절대경로를 문서나 출력에 복사하지 않는다. 원격 설정이 없으면 추측하지 않는다. 서버 접근·설정 변경에는 `home-server-2`를 적용한다.

```sh
client="$HOME/.agents/skills/plipa-remote-validation/scripts/remote_validation.py"
python3 "$client" submit --sha <40자리-커밋-SHA> --profile android-smoke --request-id <고정된-요청-ID>
python3 "$client" wait <작업-ID>
python3 "$client" results <작업-ID> --output /absolute/path/result.zip
python3 "$client" cancel <작업-ID>
```

- 서버의 허용 브랜치에서 가져올 수 있는 커밋만 제출한다. 커밋하지 않은 로컬 변경은 포함되지 않는다. 동일 요청 재시도는 같은 request-id와 내용을 사용한다.
- 서버가 정한 Gradle 작업과 APK·기기 설정만 사용한다. 클라이언트가 셸 명령, 저장소 경로, 서명 키나 임의 AVD를 지정하지 않는다.
- 빌드·실제 실행된 단위 테스트·서명 검사·데이터 보존 설치·foreground 앱 실행을 구분한다. `android-smoke`는 로그인·저장·전체 화면 시나리오나 iOS 검증을 대신하지 않는다.
- 서버 작업은 SSH 연결과 분리되어 유지된다. 연결 실패 시 새 요청을 중복 제출하지 말고 기존 request-id 또는 작업 목록으로 확인한다. `wait`는 최대 40초 기다린 뒤 현재 상태를 반환한다.
- Mac에서 원격 완료를 기다리는 동안 로컬 모바일 대기열 슬롯을 잡지 않는다. Mac의 iOS 검증은 기존 로컬 실행기로 별도로 수행한다.
- 취소는 서버가 정리를 마친 `cancelled` 상태와 구분한다. `blocked` 또는 비정상 중단은 소유 프로세스·AVD를 확인하기 전 자동 복구하지 않는다.
- 결과 ZIP에는 소스 SHA, APK 해시·서명 검사, 테스트 결과와 실행 근거를 포함한다. APK·서명 설정·원격 접속 정보는 기본 결과 묶음에서 제외한다. 기존 결과 파일을 덮어쓰지 않는다.
- 플리파 서버에서 사용하는 대기열은 Windows용이다. Mac의 `mobile-validation-queue` 스크립트를 원격에 복사하지 않는다.
