---
name: record-android-review-failure
description: 사용자가 제공한 Google Play Android 앱 심사 거절 메일, Play Console 메시지, 스크린샷, 재현 설명에서 실패 조건과 해결 내용을 추출해 공용 사례집에 누적한다. "심사 실패 사례 추가", "리젝 사유 기록", "Play 심사 거절 내용 모아줘", "이 실패 요소를 다음 심사 점검에 반영해줘"처럼 실제 심사 실패 자료를 지식으로 남겨 달라는 요청에 사용한다.
---

# Record Android Review Failure

실제 Google Play 심사 실패 자료를 최소한의 재사용 가능한 사실로 정규화하고 Git으로 공유한다.

## 절차

1. 사용자가 제공한 자료 전체를 읽고 다음을 구분한다.
   - `확인됨`: Play Console 또는 Google의 실제 거절 통지가 제시됨
   - `제보됨`: 사용자의 설명만 있고 원문 증거는 없음
   - 원인을 추측해야만 하는 내용은 사례로 저장하지 않고 사용자에게 부족한 증거를 알린다.
2. 계정, 이메일, 앱 이름, 패키지명, 주문·결제 정보 등 재현에 불필요한 식별 정보와 비밀값을 제거한다. 거절 문구는 핵심만 짧게 요약하고 원본 파일은 저장하지 않는다.
3. `/Users/ujeonghyeon/Desktop/dev/myDev/ao-skills/codex/skills/record-android-review-failure/references/failure-cases.md`를 전부 읽는다.
4. 정책 영역, 실패 조건, 검출 방법이 같은 기존 사례를 찾는다.
   - 같으면 새 항목을 만들지 말고 기존 항목의 증거 수준·검출 방법·해결 내용을 보강한다.
   - 다르면 `ARF-YYYYMMDD-NN` 형식으로 그 날짜의 다음 번호를 부여해 파일 끝에 추가한다.
5. 사례는 파일에 정의된 스키마를 그대로 사용한다. 정책명을 확정할 수 없으면 `미분류`로 기록하고 추측해서 채우지 않는다.
6. 변경 diff에서 개인정보, 자격 증명, 원본 첨부가 들어가지 않았는지 확인한다.
7. 스킬 디렉터리를 전역 사본에 동기화한다.

```bash
bash /Users/ujeonghyeon/Desktop/dev/myDev/ao-skills/codex/sync.sh
```

8. 저장소의 사용자 변경을 보존하고 사례집 파일만 stage한 뒤 다음 형식으로 커밋하고 `main`에 push한다.

```text
docs: Android 심사 실패 사례 ARF-YYYYMMDD-NN 기록
```

정확히 같은 제보라 변경할 내용이 없으면 커밋·푸시하지 않고 중복 사례 ID만 보고한다. push에 실패하면 강제 push하지 말고 원인을 보고한다.

## 결과 보고

- 추가 또는 갱신한 사례 ID와 증거 수준
- 저장한 실패 조건과 검출 방법의 요약
- 커밋 해시, push 결과, 전역 동기화 경로
- 저장하지 않은 민감정보 또는 확인 불가 내용
