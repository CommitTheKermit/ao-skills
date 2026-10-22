<!-- local-task-coordination:start -->
## 동일 기능 담당 등록과 로컬 모바일 실행

- 기능 구현·수정의 이슈·브랜치·코드 작업 전에 `~/.agents/skills/task-coordination/SKILL.md`를 읽고 진행 중인 범위를 조회한 뒤 담당권을 등록한다. 같은 기능은 같은 식별자를 사용하고, 다른 담당자가 있으면 별도 구현을 시작하지 않는다. 리뷰 전용 세션은 구현 담당권을 잡지 않는다. 완료 또는 승인된 인계 때만 담당권을 반환한다.
- 로컬 Android/iOS 빌드·기기 부팅·설치·연결 테스트·UI 검증은 `~/.agents/skills/mobile-validation-queue/SKILL.md`의 공용 실행기로 수행한다. 빌드 전에 슬롯을 확보하고 기기 정리까지 유지한다. 기존 Android 기기 임대와 서명·데이터 보존 검사는 별도로 유지한다. 대기열 밖에서 다른 AVD를 추가 실행해 우회하지 않는다.
- 이 두 규칙은 같은 Mac 사용자 계정의 로컬 작업에 적용한다. 원격 플리파 연동이나 다른 호스트 제어를 자동으로 추가하지 않는다.
<!-- local-task-coordination:end -->
