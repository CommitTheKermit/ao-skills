---
name: run
description: 플리파의 로컬 서비스와 Android 에뮬레이터를 시작하거나 재연결하고 대상 앱·이전 테스트·실시간 화면 연결을 확인한다. 플리파 문맥의 "run", "플리파 실행", "에뮬+서비스 켜줘", "다시 실행" 요청에 사용한다. 일반 프로젝트 실행이나 Ouroboros run에는 적용하지 않는다.
---

# 플리파 실행

<!-- usage-stats: skill run -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill run >/dev/null 2>&1 || true`를 한 번 실행한다.

## 실행 대상

- 플리파: `/Users/ujeonghyeon/Desktop/dev/myDev/plipa`
- 기본 AVD: `Pixel_6a_API_33_2`
- 기본 대상 앱: `com.chamsae.chaekchaek.integration`
- 기본 서비스: `http://127.0.0.1:4317/`
- APK 소스 위치: `/Users/ujeonghyeon/Desktop/dev/myDev/2026-chaekchaek/android`

위 값은 현재 기본값이다. 사용자의 이번 지시를 우선하고, 플리파의 `README.md`, `플리파.command`, `device.py`, `emulator.py`, `server.py`를 실행 방법과 API의 기준으로 확인한다. 경로가 없으면 임의 프로젝트로 대체하지 않는다. `PLIPA_PORT`·`PLIPA_DATA`가 지정됐으면 동일한 설정으로 접속한다.

요청을 받으면 서비스와 에뮬레이터를 함께 준비한다고 짧게 알린다. 기본 동작은 **꺼진 구성요소만 시작하고 정상 실행 중인 구성요소는 재사용**하는 것이다. "다시 실행"만으로 정상 프로세스를 강제 종료하지 않는다.

## 1. 서비스 준비

1. 플리파에서 `git status --untracked-files=no`를 확인한다. 실행만 하므로 변경 파일을 수정·커밋하거나 브랜치를 바꾸지 않는다.
2. 정확한 서비스 포트를 `lsof -nP -iTCP:4317 -sTCP:LISTEN`으로 확인한다. 다른 포트 설정이면 그 포트를 사용한다. 리스너가 있으면 해당 PID의 실행 명령과 작업 디렉터리를 확인해 플리파인지 판별한다. 포트만 보고 프로세스를 종료하거나 인증값을 보내지 않는다.
3. 정상 플리파이면 `/api/state` 응답을 확인하고 재사용한다. 다른 프로그램이거나 소유자를 확인할 수 없으면 충돌을 보고하고 중단한다.
4. 서비스가 없으면 `플리파.command`와 동일하게 `.venv`를 준비한다. `.venv/bin/python -c 'import grpc, emulator_pb2'`가 실패할 때만 `.venv/bin/python -m pip install -r requirements.txt`를 실행한다. 가상환경 자체가 없으면 먼저 `python3 -m venv .venv`를 실행한다.
5. 플리파를 작업 디렉터리로 하여 `.venv/bin/python server.py`를 지속 실행 세션에서 시작한다. 시작한 PID 또는 실행 세션 ID를 보존한다. 서버가 `/api/state`에 정상 응답할 때까지 최대 15초 확인한다. 기동 실패를 반복 실행으로 덮지 않는다.

서비스가 비정상이고 재시작이 필요하면 기존 프로세스가 플리파임을 확인하고 현재 세션·AI 진행 상태부터 확인한다. 진행 중인 AI나 다른 사용자의 작업을 임의 중단하지 않는다. 안전하게 재시작할 수 있는 플리파만 정상 종료한 뒤 재기동한다. 포트 전체 일괄 종료·`kill -9`·기기 초기화는 사용하지 않는다.

## 2. 에뮬레이터와 앱 준비

플리파의 `.venv/bin/python`에서 `device` 모듈을 사용한다.

1. `device.devices()`와 `device.avds()`로 확인한다. 연결된 기기는 `device.adb(serial, 'emu', 'avd', 'name')`으로 AVD 이름을 확인한다. 첫 번째 기기를 무조건 선택하지 않는다.
2. 대상 AVD가 이미 실행 중이면 해당 serial을 재사용한다. offline/부팅 중인 동일 AVD는 기다리고 중복 실행하지 않는다. 없을 때만 `device.boot(avd_name)`으로 시작한다. 이 함수의 인증된 gRPC 실행 설정을 유지한다.
3. 대상 기기의 연결 상태가 `device`이고 `device.adb(serial, 'shell', 'getprop', 'sys.boot_completed').strip() == '1'`인지 최대 120초 확인한다. 긴 대기 중에도 60초 이내로 사용자에게 진행 상황을 알린다. 시간 초과 시 원인을 보고하고 자동 초기화·무한 재부팅하지 않는다.
4. `device.adb(serial, 'shell', 'pm', 'path', package)`로 대상 앱 설치를 확인한다. 설치돼 있으면 빌드·재설치하지 않는다. 없으면 누락을 보고한다. APK 설치 또는 빌드가 요청 범위에 포함됐을 때만 `run-android-app` 스킬로 이어가며 일반 실행에 디버거 대기를 사용하지 않는다.

## 3. 테스트 복원과 앱 열기

HTTP API는 Python 표준 라이브러리 등으로 호출한다. `/api/state`의 `csrf`는 메모리에서만 보관하고 POST 요청의 `X-Plipa-CSRF` 헤더로 전달한다. 요청 본문은 JSON이다. CSRF·gRPC 인증값·전체 세션 데이터를 도구 출력이나 파일에 남기지 않는다.

- 현재 세션이 선택한 serial·package와 일치하면 유지한다.
- 현재 세션이 없으면 `/api/state`의 `sessions`에서 같은 serial·package의 가장 최근 기록을 골라 `/api/load`에 `{"id": ...}`를 보낸다.
- 일치하는 이전 기록도 없으면 `/api/start`에 `serial`, `package`, 짧은 테스트 `title`을 보낸다.
- 현재 세션이 다른 대상이면 자동으로 덮어 바꾸지 말고 대상 전환 의사를 확인한다. serial이 달라진 이전 기록도 파일을 직접 고쳐 연결하지 않는다.
- AI 실행·승인 대기 상태면 유지하고 앱 재실행을 생략한다. 그 외에는 `/api/launch`로 대상 앱을 연다. 시작 목적으로 `/api/chat`, `/api/approve`, `/api/stop`을 호출하지 않는다.

## 4. 연결 검증과 화면 열기

1. `/api/state`의 선택 세션과 기기·패키지가 일치하는지 확인한다.
2. `/api/stream`에 현재 `session` ID와 임시 고유 `viewer` ID를 보내 첫 PNG 프레임을 확인한다. 프로토콜은 4바이트 big-endian 길이와 PNG 본문이며 길이 0은 heartbeat다. 소켓 응답 제한과 전체 15초 제한을 두고 프레임 크기는 16 MiB 이하로 검사한다. 검증용 연결은 반드시 닫고 이미지는 저장·출력하지 않는다. HTML 응답이나 ADB 스크린샷 성공만으로 스트리밍 성공이라 보고하지 않는다.
3. 사용 가능한 브라우저 도구로 기존 플리파 탭을 찾아 재사용한다. 연결 오류 화면이면 새로고침하고, 탭이 없을 때만 만든다. 사용자에게 남길 탭은 `markDeliverable()`로 표시한다. 브라우저 도구가 없으면 실행된 로컬 URL을 제공한다. 브라우저 조작을 위해 셸 `open`이나 `--open`으로 우회하지 않는다.
4. 서비스 응답, 대상 AVD·앱 실행, 실시간 프레임 확인 결과와 URL을 짧게 보고한다. 하나라도 실패하면 해당 부분을 구분한다. 단순 실행 결과를 소스 변경이나 커밋으로 남기지 않는다.

실행 과정에서 운영 데이터 변경 테스트, AI 지시, 증거 외부 전송, 앱 소스 수정, 스냅샷 초기화는 수행하지 않는다.
