---
name: home-server-2
description: 두 번째 Windows 홈서버에 전용 SSH 별칭으로 접속해 상태 확인, 프로젝트 배포, 서비스와 Android 에뮬레이터 작업을 수행한다. 사용자가 "홈서버2 접속", "새 홈서버에 반영", "홈서버2에서 앱 설치"처럼 두 번째 개인 서버를 명시할 때 사용한다.
---

# 홈서버2 원격 작업

<!-- usage-stats: skill home-server-2 -->

첫 동작으로 아래 명령을 이 발동에서 한 번만 실행한다.

```bash
python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill home-server-2 >/dev/null 2>&1 || true
```

## 접속 정보 분리

스킬 원본은 공개될 수 있다. 호스트명, 주소, 사용자명, 개인키 경로, 저장소 절대경로와 토큰은
스킬, 프로젝트 파일, 커밋, 응답에 기록하지 않는다. 접속은 Git 밖의 `~/.ssh/config`에 둔
`home-server-2` 별칭만 사용한다. 별칭이 없거나 호스트 키 검증이 실패하면 값을 추측하거나
호스트 키 검증을 끄지 말고 중단한다.

Git 밖의 `~/.config/home-server-2/status-url`이 있으면 세션 시작 시 그 주소의 상태 응답을
먼저 조회한다. 실패하거나 현재성을 확인할 수 없으면 SSH로 직접 확인한다. 주소나 응답의
비밀값은 출력하거나 저장소로 복사하지 않는다.

## 시작 점검

요청에서 결과를 바꾸는 수행 작업, 대상 저장소와 브랜치, 서비스, Android 기기, 설치 산출물과
기준 소스만 짧게 고정한다. 이미 명확한 항목은 다시 묻지 않는다.

다음 순서로 접속과 원격 정체성을 확인한다.

```bash
ssh -o ConnectTimeout=10 home-server-2 'Write-Output $env:COMPUTERNAME; Write-Output $env:USERNAME'
```

원격 기본 셸은 PowerShell일 수 있다. 여러 줄 PowerShell은 로컬에서 UTF-16LE Base64로 만든
`-EncodedCommand`를 사용한다. Base64는 암호화가 아니므로 비밀값을 포함하지 않는다.

- 장치 시간, Tailscale과 OpenSSH 상태, 실제 프로젝트 경로를 읽기 전용으로 확인한다.
- 프로젝트는 `git status --untracked-files=no`, 현재 브랜치, remote와 원격 차이를 먼저 확인한다.
- 프로젝트 경로를 사용자명으로 조합하지 않는다. 기존 checkout, 예약 작업, 문서에서 확인한다.
- 서비스와 예약 작업은 정확한 이름, 실행 사용자, working directory, 트리거와 최근 결과를 확인한다.
- Android 작업은 SDK 경로, AVD, `adb devices -l`, 패키지 설치 상태를 각각 확인한다.
- 환경변수와 인증은 존재 여부와 필요한 작업의 성공 여부만 확인하고 값을 출력하지 않는다.
- Windows에서 도구가 보이지 않으면 Machine과 User의 최신 `Path`를 현재 PowerShell 프로세스에
  다시 불러온 뒤 누락 여부를 판단한다.

## 변경 수행

사용자가 요청한 배포와 앱 설치는 확인된 대상에 한해 이어서 수행한다.

- Git 변경은 같은 목적의 기존 작업 브랜치를 재사용하고 pull 전에 원격 차이와 작업 트리를 확인한다.
- 정상 실행 중인 서비스와 예약 작업은 재사용한다. 소유자를 확인하지 않은 프로세스나 포트를
  일괄 종료하지 않는다.
- Git이 Windows TLS 백엔드 오류로 실패한 경우에만 해당 명령에서
  `git -c http.sslBackend=openssl`을 사용한다. 인증서 검증을 끄거나 전역 설정을 바꾸지 않는다.
- APK는 기준 소스와 빌드 변형을 확인한 뒤 특정 에뮬레이터 serial에 설치한다. 설치 후 패키지
  경로와 실행 가능한 런처 진입점을 확인한다.
- 재부팅, AVD wipe, 앱 데이터 삭제, 방화벽 차단처럼 현재 복구 경로나 데이터를 끊는 작업은
  직전에 사용자 허락을 받는다.
- Windows OpenSSH 세션에서 직접 띄운 장기 프로세스는 세션 종료와 함께 끝날 수 있다. 기존
  예약 작업을 사용하거나 세션 밖에서 생성된 프로세스인지 확인한다.

## 완료 검증

설정값만 보고 완료하지 않고 요청한 도착 지점에서 실제 증거를 확인한다.

- Git 배포: 원격 checkout의 branch, commit, `git status --untracked-files=no`
- 서비스: 예약 작업 상태, 소유 프로세스와 리스너, 로컬 응답과 허용된 HTTPS 응답
- Android: 대상 serial의 `device` 상태, 설치된 패키지 경로, 앱 실행 후 foreground activity
- 플리파 화면: Android `boot_completed`, Emulator gRPC 프레임, 브라우저 화면을 별도 증거로 확인한다.

접속 성공, 코드 배포, 서비스 응답, 앱 설치와 실제 화면 표시는 서로 다른 상태로 보고한다.
실행하지 못한 항목과 이유를 완료 항목과 분리하며 접속 정보와 비밀값은 최종 응답에 반복하지 않는다.
