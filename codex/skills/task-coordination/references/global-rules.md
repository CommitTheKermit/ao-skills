<!-- local-task-coordination:start -->
## 동일 기능 담당 등록과 플랫폼별 모바일 실행

- 기능 구현·수정의 이슈·브랜치·코드 작업 전에 `~/.agents/skills/task-coordination/SKILL.md`를 읽고 진행 중인 범위를 조회한 뒤 담당권을 등록한다. 같은 기능은 같은 식별자를 사용하고, 다른 담당자가 있으면 별도 구현을 시작하지 않는다. 리뷰 전용 세션은 구현 담당권을 잡지 않는다. 완료 또는 승인된 인계 때만 담당권을 반환한다.
- Android 검증은 `~/.agents/skills/plipa-remote-validation/SKILL.md`를 먼저 읽고 플리파 원격으로 수행한다. 제출 전 대상 저장소·허용 ref·정확한 커밋 SHA·프로필 지원 범위를 확인한다. 현재 책췍 프로필을 다른 저장소에 사용하지 않는다. 설정 누락·장애·미지원 검증을 자동으로 로컬 실행하지 않고 미검증 사유를 보고한다.
- iOS 빌드·Simulator 부팅·설치·테스트·Archive는 `~/.agents/skills/mobile-validation-queue/SKILL.md`의 공용 실행기로 수행한다. 사용자에게 명시적으로 허용된 로컬 Android 실행도 이 대기열 안에서 기기 임대와 서명·데이터 보존 검사를 수행한다. 기기 정리까지 슬롯을 유지하고 다른 AVD로 우회하지 않는다.
- 원격 Android는 Mac 슬롯을 점유하지 않는다. 같은 SHA의 원격 Android와 로컬 iOS 검증은 호스트별로 병행할 수 있지만, 같은 Mac의 무거운 작업은 직렬 실행한다. 원격 smoke 성공을 전체 UI 시나리오·AAB·Lint 검증으로 대체하지 않는다.
<!-- local-task-coordination:end -->
