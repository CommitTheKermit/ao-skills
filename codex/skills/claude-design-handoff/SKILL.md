---
name: claude-design-handoff
description: claude.ai/design 핸드오프 링크(`api.anthropic.com/v1/design/...`)를 받아 디자인 번들을 내려받고, 압축을 풀어 README와 prod 산출물·chats 트랜스크립트를 근거로 프로젝트의 디자인 소스를 최신화한다. 사용자가 "Fetch this design file, read its readme, and implement..." 형식의 영어 지시나 `api.anthropic.com/v1/design/` 링크를 붙여넣으면 발동. 추가 Implement 지시(예: "버튼 추가", "글자 카운트 삭제")가 함께 오면 그 변경도 같이 반영.
---

# claude-design-handoff

claude.ai/design 에서 만든 시안의 핸드오프 링크를 받아, **번들을 실제로 내려받아 시안과 정확히 동기화**해 프로젝트의 디자인 소스를 최신화한다. 텍스트 설명만으로 추측 구현하지 않는다.

## 발동 조건

다음 중 하나면 발동한다.

- `api.anthropic.com/v1/design/...` 형태의 핸드오프 링크가 프롬프트에 포함
- "Fetch this design file, read its readme, and implement the relevant aspects of the design. <링크>" 같은 형식의 지시
- 위에 더해 한국어/영어로 구체적 변경 지시(Implement 항목)가 함께 오는 경우 (예: "확인 질문 답변에서 모르겠어요 텍스트 버튼 추가, 텍스트 글자 카운트 삭제")

## 워크플로우

```
[1] 링크 WebFetch → gzip bin 저장   [2] gunzip + tar 압축해제
                                          ↓
[5] 프로젝트 디자인 소스 최신화 ← [4] prod 산출물 + chats 근거 대조 ← [3] README 먼저 읽기
                                          ↓
                              [6] 추가 Implement 지시 반영
                                          ↓
                              [7] 핸드오프 CSS 가드 검증
```

### 1. 링크 받아오기 (gzip 바이너리 주의)

- 핸드오프 링크를 `WebFetch` 로 받는다.
- **응답은 gzip 바이너리(`application/gzip`)라 텍스트로 안 읽힌다.** WebFetch 응답에 적힌 저장 경로(`...tool-results/webfetch-*.bin`)를 기억한다.

### 2. 압축 해제

응답에 적힌 `.bin` 경로를 임시 디렉터리에 풀어낸다.

```bash
mkdir -p <임시디렉터리>
gunzip -c <webfetch-*.bin> | tar -xf - -C <임시디렉터리>
```

### 3. README 먼저 읽기

- 번들 루트의 `README.md` 를 **가장 먼저** 읽는다. 번들 구조/무엇이 prod 산출물인지/어떤 파일을 봐야 하는지 안내가 들어 있다.

### 4. prod 산출물 + chats 근거 대조

- `project/` 의 실제 산출물(prod 계열: `app-prod.jsx` / `styles-prod.css` 등)을 읽는다. 이게 시안의 정답 소스다.
- `chats/` 트랜스크립트를 읽어 디자인 의도/맥락을 파악한다.
- 텍스트 설명만으로 추측하지 말고, 반드시 실제 산출물 코드를 근거로 삼는다.

### 5. 프로젝트 디자인 소스 최신화

- 번들의 prod 산출물을 기준으로 **현재 프로젝트의 대응 디자인 소스를 정확히 동기화**한다. (이 레포 예: `frontend/src/...` 컴포넌트/스타일)
- 번들 구조를 그대로 복붙하지 말고, 프로젝트의 기존 구조/네이밍/관용구에 맞춰 반영한다. 시각적 결과가 시안과 일치하는 것이 목표.

### 6. 추가 Implement 지시 반영

- 링크와 함께 온 구체적 변경 지시(버튼 추가/요소 삭제 등)를 5번 동기화 위에 추가로 반영한다.
- 지시가 시안과 충돌하면 사용자에게 알리고 결정을 받는다.

### 7. 핸드오프 CSS 가드로 검증 (커밋 전)

CSS/컴포넌트를 손으로 동기화하면 빌드/`tsc`/`vitest` 가 못 잡는 "문법상 valid 인데 규칙이 통째로 죽는" 잠복 버그(주석 안 별표+슬래시 조기종료 등)가 섞일 수 있다(이 스킬 작업에서 실제로 발생). `handoff-css-guard` 하네스로 검증한다.

- 하네스가 설치된 프로젝트면(`<frontend>/scripts/validate-handoff.mjs` 존재): `cd frontend && npm run validate-handoff` 로 css-guard/stylelint 실패를 **커밋 전에** 고친다. (편집 즉시 css-guard 훅이 깔려 있으면 구문/누락변수는 이미 block 으로 걸러진다.)
- 미설치면: `handoff-css-guard` 스킬로 설치를 제안한다(자동 설치하지 않음).
- stale 확인: 이 스킬은 번들을 직접 받으므로 라이브 파일목록을 JSON 으로 저장해 `npm run validate-handoff -- --live <json>` 로 디스크 번들과 대조할 수 있다(번들 누락 파일 = stale).

## 마무리

- 변경한 프로젝트 파일 목록과 무엇을 시안에 맞춰 바꿨는지 요약 보고한다.
- 전역 규칙대로, 코드/파일 변경이 완료되면 그 시점에 의미 단위로 커밋한다.

## 절대 어기지 말 것

- WebFetch 결과를 텍스트로 읽으려 하지 않는다. 반드시 `.bin` 을 gunzip+tar 로 푼다.
- README 를 건너뛰지 않는다. 항상 먼저 읽는다.
- 텍스트 설명만으로 추측 구현하지 않는다. prod 산출물 코드가 근거.
- 적용 후 핸드오프 CSS 가드 검증(설치돼 있으면 `validate-handoff`)을 건너뛰지 않는다. CSS 잠복 버그는 빌드/타입체크를 통과하고 렌더링에서만 드러난다.
