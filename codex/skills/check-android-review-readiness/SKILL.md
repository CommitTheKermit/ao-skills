---
name: check-android-review-readiness
description: Android 앱의 Google Play 심사 준비 상태를 최신 공식 정책, 프로젝트 정적 검사와 Gradle 테스트, 누적된 실제 심사 실패 사례로 점검한다. "안드로이드 심사 통과할까", "Play 심사 테스트", "출시 전 정책 점검", "리젝 위험 검사", "심사 실패 요소 확인"처럼 제출 전 통과 가능성과 확인 불가 영역을 근거와 함께 판정해 달라는 요청에 사용한다.
---

# Check Android Review Readiness

<!-- usage-stats: skill check-android-review-readiness -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill check-android-review-readiness >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

확인 가능한 범위에서 Google Play 심사 차단 위험을 찾는다. 실제 심사 결과를 보장하지 않는다.

## 절차

1. 저장소 루트와 Android 스코프의 `AGENTS.md`를 읽고 Android 디렉터리 밖을 수정하지 않는다.
2. 앱 종류, 배포 트랙, 대상 국가, 수익화·로그인·민감 권한 사용 여부처럼 적용 정책을 바꾸는 정보는 프로젝트와 제공 자료에서 먼저 찾는다. 찾을 수 없고 판정에 영향을 주면 `확인 불가`로 남긴다.
3. 검사 당일의 공식 Google Play 정책을 웹에서 확인한다.
   - Google Play Console Help와 Android Developers의 공식 페이지를 우선한다.
   - 검색 결과 요약이나 블로그를 정책 근거로 사용하지 않는다.
   - 적용한 정책마다 확인 날짜와 직접 URL을 결과에 남긴다.
4. 누적 사례집을 읽는다.
   - 우선 경로: `/Users/ujeonghyeon/Desktop/dev/myDev/ao-skills/codex/skills/record-android-review-failure/references/failure-cases.md`
   - 없으면 설치된 `record-android-review-failure/references/failure-cases.md`를 찾는다.
   - 사례집이 없으면 숨기지 말고 `확인 불가` 항목으로 보고한다.
5. 프로젝트에서 다음 증거를 확인한다.
   - Gradle의 application ID, SDK 수준, 버전, release 설정
   - 병합 대상 Manifest의 권한, exported 컴포넌트, 딥 링크, 서비스·리시버
   - 개인정보처리방침·데이터 수집·광고·로그인·결제·민감 권한과 관련된 코드 및 리소스
   - 사용자가 제공한 Play 스토어 등록정보, Data safety, App access, 콘텐츠 등급 자료
6. 저장소가 제공하는 Gradle wrapper로 가장 작은 기존 검사를 실행한다. 일반적인 기본값은 Android 루트에서 다음 명령이며 `clean`은 실행하지 않는다.

```bash
./gradlew lint test
```

저장소에 더 구체적인 검증 명령이 있으면 그것을 우선한다. 서명 AAB 생성·검증이 필요한 요청에는 새 로직을 만들지 말고 `$build-signed-aab`를 사용한다.

7. 공식 정책 위반 가능성과 사례집의 실패 조건을 현재 증거에 대조한다. 사례와 비슷하다는 이유만으로 실패를 단정하지 말고, 재현되는 조건과 파일·줄·명령 출력을 함께 제시한다.
8. 아래 기준으로 전체 판정을 하나만 선택한다.

## 판정 기준

- `실패 위험`: 현재 정책 위반이나 제출을 막는 검사 실패가 구체적 증거로 확인됨
- `확인 불가`: 확인된 실패 위험은 없지만 심사에 중요한 자료나 실행 검증이 하나 이상 없음
- `통과 가능`: 적용 가능한 중요 정책·프로젝트 검사·Play Console 자료를 모두 확인했고 실패 위험을 찾지 못함

`통과 가능`은 검사 범위 내 준비 상태이며 Google의 실제 승인 보장이 아니라고 명시한다. 공식 정책과 누적 사례가 충돌하면 최신 공식 정책을 우선한다.

## 결과 형식

```markdown
# Google Play 심사 준비 판정: 통과 가능 | 실패 위험 | 확인 불가

검사일: YYYY-MM-DD
검사 범위: 프로젝트, 실행한 명령, 제공된 Play Console 자료

## 차단·위험 요소
- 심각도 | 근거(파일:줄 또는 명령) | 공식 정책 URL | 관련 사례 ID | 조치

## 통과한 검사
- 검사 | 증거

## 확인 불가
- 필요한 자료 | 확인 방법

## 한계
- 이 결과는 실제 Google Play 심사 승인을 보장하지 않음
```

차단·위험 요소가 없으면 `없음`이라고 쓰고, 실행하지 않은 검사를 통과로 표시하지 않는다.
