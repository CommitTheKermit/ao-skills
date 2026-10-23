---
name: jev-local-validation
description: 플리파 서버 꺼짐·연결 불가가 원격 접수 전에 확인되거나 사용자가 로컬 검증을 지정했을 때 Android 앱을 공용 대기열·기기 임대 안에서 빌드하고 Jev 뷰 트리 시나리오로 검증한다.
---

# Jev 로컬 Android 검증

<!-- usage-stats: skill jev-local-validation -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill jev-local-validation >/dev/null 2>&1 || true`를 한 번 실행한다.

## 진입 조건과 범위

- [plipa-remote-validation](../plipa-remote-validation/SKILL.md)의 접수 전 오프라인 분기를 통과했거나 사용자가 로컬 Android 검증을 명시하면 사용한다. 이 오프라인 대체 경로는 상시 허용되어 있어 매번 실행 승인을 묻지 않는다. 인증·403·설정 문제와 미확정 원격 접수를 우회하지 않는다.
- 대상 앱의 Android 스코프·정확한 소스 SHA·변경 여부·검증할 사용자 행동과 성공 조건을 정한다. 다른 프로젝트에도 사용할 수 있지만 책췍 패키지나 원격 프로필을 기본값으로 강제하지 않는다.
- 기본 실행기는 `~/.agents/skills/jev-local-validation/scripts/run.py`다. `python3 "$HOME/.agents/skills/jev-local-validation/scripts/run.py" --runtime-info`로 고정 설치본의 소스 SHA·버전·모듈 경로를 먼저 확인한다. `~/.local/share/jev-mobile-use/current`가 가리키는 비편집 설치본을 격리 실행하며 개발 체크아웃이나 `PYTHONPATH`를 사용하지 않는다. 설치본이 없거나 영수증이 다르면 중단한다. 소스 안내는 `/Users/ujeonghyeon/Desktop/dev/myDev/jev-mobile-use-driver/docs/usage.md`와 `docs/integrations.md`를 읽되 다른 세션의 브랜치를 바꾸거나 pull/reset하지 않는다.
- 원격 smoke와 로컬 UI 시나리오의 검증 범위를 맞춘다. 단위 테스트·빌드·설치·전면 실행·UI 시나리오는 각각 별도 근거다. Jev 트리 성공은 서버 저장, 시각적 완성도, AAB·Lint나 iOS 성공을 뜻하지 않는다.

## 준비와 실행

1. 시나리오 JSON의 `goal`, 대상 `package`, 허용된 `allowed_actions`, 독립적인 `expect`를 준비한다. 실제 앱 트리 조회와 선택자 확정은 아래 대기열·기기 임대를 확보한 뒤 수행한다. 저장·삭제·게시 등은 현재 요청에서 허용된 구체적인 행동만 포함한다. 시작 상태부터 성공 조건이 이미 충족되는 빈 검증을 피한다. 다단계 검증은 필요한 중간 상태도 독립적으로 확인한다. 벤치마크 전용 실행 코드를 일반 CLI 기능으로 간주하지 않는다.
2. [mobile-validation-queue](../mobile-validation-queue/SKILL.md)의 전경 실행기로 전체 작업을 감싼다. 슬롯 획득 전에 Gradle·에뮬레이터·adb 실행을 시작하지 않는다. 임시 owner를 쓰는 도구는 대화 동안 고정한 `AGENT_SESSION_ID`를 사용한다. 별도 호출로 조작할 때도 소유 전경 스크립트가 완료 신호를 기다려 정리까지 슬롯을 유지해야 한다.
3. 슬롯 안에서 대상 SHA의 Android APK와 요청된 단위 테스트를 프로젝트의 실제 Gradle 작업으로 수행한다. `--no-daemon`을 사용한다. APK 경로만 보고 출처를 추정하거나 예전 APK를 최신 변경의 검증에 재사용하지 않는다. 빌드가 실패하면 UI 실행으로 덮지 않는다. 명시적으로 기존 APK만 검사하는 요청이면 APK 해시·버전과 소스 출처의 한계를 기록한다.
4. [android-emulator-lease](../android-emulator-lease/SKILL.md)로 AVD를 임대·부팅·serial 바인딩한다. 이미 임대 중이거나 소유자가 불명확한 기기는 조작하지 않는다. 모든 기기 명령에 동일한 serial을 명시한다.
5. [run-android-app](../run-android-app/SKILL.md)의 `preflight-install.py`로 패키지·버전·서명을 검사한 뒤 데이터 보존 설치와 전면 실행을 수행한다. 검사 실패 시 삭제·강제 다운그레이드로 우회하지 않는다. 성공 조건을 확인할 수 있는 초기 상태로 준비한다.
   기본 Droidrun 드라이버는 Mobilerun Portal이 필요하다. 확인된 조합은 `mobilerun-core-local==0.6.3`과 Portal 0.7.27이다. Portal 준비도 같은 대기열·임대 안에서 패키지·버전·서명을 검사하고 데이터 보존 설치한다. 기존 접근성 서비스 목록을 보존하며 필요한 서비스만 추가하고 변경 전 설정을 기록해 정리 시 복원한다. 기본 삭제 옵션이 있는 upstream 설치 도우미를 무조건 호출하지 않는다. 준비되지 않았으면 중단하고 ADB 드라이버로 자동 전환하지 않는다. 드라이버가 연결 중 바꾼 키보드는 정상 종료 시 복원하며 강제 종료했다면 기존 설정을 확인한다.
6. `TYPESAFE_API_KEY`를 환경변수로 주입한다. 이미 승인된 Git 밖의 비밀 환경파일을 사용할 수 있으며 현재 개인 파일은 `~/.config/plipa-jev/temporary.env`다. 키 내용을 출력·복사·문서화하지 않는다. CLI가 .env를 자동으로 읽는다고 가정하지 않는다. 키가 없거나 만료되면 실행을 중단하고 사유를 보고한다.
7. 동일한 대기열 작업 안에서 아래 CLI를 형식 검사 후 실행한다. `scenario`, `serial`, `output`은 확인한 절대경로와 소유 serial로 설정한다. 출력 폴더는 실행별 새 경로를 쓴다.

   ```sh
   python3 "$HOME/.agents/skills/jev-local-validation/scripts/run.py" \
     --scenario "$scenario" --serial "$serial" --output "$output"
   python3 "$HOME/.agents/skills/jev-local-validation/scripts/run.py" \
     --scenario "$scenario" --serial "$serial" --output "$output" --execute
   ```

8. `result.json`의 status·reason·trace·마지막 트리·API 호출 수·토큰 수와 `events.jsonl`의 요청·응답·판단 기록, 입력 확인과 단계별 시간을 확인한다. `done`이라는 모델 응답이나 종료 코드만으로 성공을 판단하지 않는다. 단계별 상태와 최종 조건이 실제로 충족됐는지 확인한다. 한글을 포함한 명시적 Unicode 입력과 `clear: true` 교체 입력을 지원하며 실제 입력값 일치를 확인한다. 화면 구조가 모호하거나 필요한 행동·입력 대상을 확인할 수 없으면 해당 범위를 미검증으로 남긴다. 낮은 확신도·반복 상태·단계 한도를 풀어 성공시키지 않는다.
9. 기본 조작은 뷰 트리 관찰 → 허용된 대상 판단 → 실행 직전 대상 확인 → 터치/입력 → 상태 확인이다. 매 단계 스크린샷을 만들지 않는다. 픽셀 디자인 검증이 요청됐거나 트리만으로 판단할 수 없을 때 필요한 캡처만 추가한다. `--capture-on-failure` 캡처는 마스킹되지 않으므로 공유 전 확인한다.
10. 자신이 시작한 기기의 종료를 확인하고 임대를 반환한 뒤 슬롯을 해제한다. `blocked` 대기열 기록은 관련 프로세스·기기의 종료 근거를 확인한 뒤에만 복구한다. 다른 세션 작업을 중단하거나 다른 AVD로 우회하지 않는다.

## 완료 근거

전환 사유, 대상 소스 SHA/변경 여부, APK 해시·버전·서명 검사, 고정 설치본의 소스 SHA·패키지 버전, AVD/serial, 빌드·단위 테스트·설치·전면 실행·시나리오별 결과, result.json 경로, Jev 호출·사용 토큰과 기기 정리를 구분해 보고한다. 키·전체 세션 원문·개인정보가 담긴 원본 트리는 커밋하지 않는다. iOS는 기존 모바일 대기열에서 같은 시나리오로 별도 검증한다.
