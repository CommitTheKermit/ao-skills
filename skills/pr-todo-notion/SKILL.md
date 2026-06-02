---
name: pr-todo-notion
description: GitHub PR을 분석해 Notion의 월별(또는 지정) 페이지 아래에 TODO 하위 페이지를 생성한다. 맨 위에 PR 링크를 달고, 각 TODO 항목 제목에 그 근거가 된 PR 리뷰 코멘트 링크를 매핑한다. 사용자가 "PR 보고 노션에 투두 만들어줘", "PR 리뷰를 노션 TODO로 정리", "이 PR 액션아이템 노션 페이지로" 같은 표현을 쓰면 발동.
---

# pr-todo-notion

GitHub PR의 변경/리뷰 내용을 읽어 Notion 페이지 아래에 체크박스 TODO 페이지를 만든다.
핵심 가치는 **추적 가능성**이다: 각 TODO가 "왜 필요한지"를 실제 PR 리뷰 코멘트 링크로 되짚을 수 있게 한다.

## 산출물 규칙

- 맨 위에 **PR 웹페이지 링크**를 굵게 명시한다.
- 각 TODO 제목 옆에 근거가 된 **리뷰 코멘트 링크**를 `([코멘트](html_url))` 형태로 단다.
- 코멘트에 직접 매핑되지 않는 항목(본문/기획서 기반 파생 액션)은 링크 없이 두되 별도로 섞어 둔다.
- 리뷰어가 남긴 코멘트는 하나도 누락하지 않는다. 모든 코멘트가 최소 한 개의 TODO에 반영돼야 한다.

## 워크플로우

```
[1] PR 데이터 수집  →  [2] PR 성격 판별  →  [3] 노션 대상 페이지 확정
                                                   ↓
                  [5] 보고  ←  [4] TODO 하위 페이지 생성(코멘트 링크 매핑)
```

### 1. PR 데이터 수집

`gh`로 PR 본문과 리뷰 코멘트를 모두 가져온다. 세 종류를 모두 조회한다(빠질 수 있으므로).

```bash
# 본문 / 변경 파일 / 커밋
gh pr view <PR번호> --repo <owner/repo> --json title,body,files,commits,additions,deletions

# 라인 단위 리뷰 코멘트 (가장 중요 - 각 TODO의 근거 링크)
gh api repos/<owner/repo>/pulls/<PR번호>/comments \
  --jq '.[] | {id, path, line, body, html_url}'

# PR 전체 코멘트(이슈 코멘트)
gh api repos/<owner/repo>/issues/<PR번호>/comments --jq '.[] | {id, body, html_url}'

# 리뷰 상태 (APPROVED / CHANGES_REQUESTED 등)
gh api repos/<owner/repo>/pulls/<PR번호>/reviews --jq '.[] | {id, state, body, html_url}'
```

`html_url`이 코멘트 영구 링크(`...pull/N#discussion_rXXXX`)다. 이것을 TODO에 단다.

### 2. PR 성격 판별

- **코드 PR**: 리뷰 코멘트를 파일/라인별 액션 아이템으로 정리. 코멘트 링크 매핑이 1:1로 깔끔하다.
- **문서/기획 PR**(README·기획서 변경): 리뷰 코멘트 + 본문의 미해결 사항(합의 안 된 부분, 의심스러운 가정, 검증 가설)을 액션 아이템으로 묶는다.

성격에 맞게 섹션 제목을 정한다. 사용자가 형식을 지정하면 그것을 우선한다.

### 3. 노션 대상 페이지 확정

- 사용자가 "6월 페이지" 처럼 월/페이지를 지정하면 `Notion search`로 그 페이지를 찾는다.
- 검색 쿼리는 페이지명(예: "6월") 또는 용도("TODO 리스트 모음")로 좁힌다.
- 찾은 페이지를 `Notion fetch`로 열어 부모 ID와 구조를 확인한다.
- 새 TODO는 이 페이지의 **하위 페이지**(`parent: {type:"page_id", page_id: ...}`)로 만든다.
- 동일 워크스페이스의 기존 "리뷰 TODO" 페이지가 있으면 형식을 참고해 톤을 맞춘다.

### 4. TODO 하위 페이지 생성

`Notion notion-create-pages`로 하위 페이지를 만든다.

- icon: 주제에 맞는 이모지 1개
- title: `PR #<번호> <한줄요약> TODO (<팀/리포>)` 형태
- content 맨 위:
  ```markdown
  ## PR #<번호> <제목>
  🔗 **PR 링크: <PR url>**
  <부가 메타: 팀/리뷰상태 등>
  ```
- 각 항목:
  ```markdown
  - [ ] **<해야 할 일(행동 중심)>** ([코멘트](<comment html_url>))
  	- 세부 근거/체크포인트
  ```
- 마지막에 "후속 작업" 섹션으로 일정/회의/범위 재확인 등 운영 TODO를 둔다.

### 5. 보고

사용자에게 생성된 노션 페이지 URL, 매핑한 코멘트 개수, 링크 없이 둔 파생 항목을 한 번에 보고한다.

## 절대 어기지 말 것

- UI/형식을 임의로 확정하지 말고, 사용자가 형식을 지정했으면 따른다. (전역 규칙: UI 결정 전 사용자에게 알릴 것)
- 리뷰 코멘트를 누락하지 않는다.
- 노션 작업만 한 경우 코드 변경이 없으므로 git 커밋하지 않는다.
- 추측으로 코멘트 링크를 만들지 않는다. 반드시 `gh api`가 돌려준 `html_url`만 사용한다.

## 필요 도구

- `gh` CLI (PR/코멘트 조회)
- Notion MCP: `search`, `fetch`, `notion-create-pages`, `notion-update-page`
