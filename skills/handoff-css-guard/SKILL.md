---
name: handoff-css-guard
description: claude.ai/design export(핸드오프) CSS 를 프로젝트에 적용할 때 빌드·타입체크·단위테스트가 못 잡는 "문법상 valid 인데 규칙이 통째로 죽는" 잠복 버그(주석 안 '별표+슬래시' 조기종료 등)·누락 CSS 변수·클래스 셀렉터 불일치·stale 번들을 잡는 자동화 검증 하네스(css-guard 훅 + validate-handoff 스크립트)를 대상 프로젝트에 설치한다. 사용자가 "핸드오프 CSS 검증/가드 붙여줘", "디자인 export 적용 재발 방지 하네스", "css-guard 설치", "/handoff-css-guard" 같은 표현을 쓰면 발동. claude-design-handoff 스킬의 자매 도구.
---

# handoff-css-guard

claude.ai/design 핸드오프 CSS 를 프로젝트에 옮길 때 반복되는 4종 문제를 막는 자동화 하네스를 **대상 프로젝트에 설치**한다. 사람용 체크리스트 문서는 두지 않고 자동화 도구만 둔다(사람 눈 확인 항목은 프로젝트 TODO 로).

## 왜 필요한가 (막으려는 버그)

핸드오프 CSS 에는 빌드/`tsc`/`vitest` 가 **전부 통과하는데 브라우저 렌더링에서만 깨지는** 잠복 버그가 섞인다. 대표 사례:

- 주석 안에 `별표+슬래시`(예: `sb-sub*/sb-tree*`)가 들어가 CSS 주석이 **조기 종료**되고, 그 뒤 파서가 깨진 상태로 **다음 규칙 블록 전체를 잘못된 셀렉터의 본문으로 삼켜 통째로 버린다**(뒤따르는 `:hover`/`-ico` 등은 살아남아 더 헷갈림).
- `var(--x)` 가 어디에도 정의되지 않고 폴백도 없어 색/간격이 깨짐.
- 시안 CSS 가 기대하는 클래스명과 실제 JSX `className` 불일치로 스타일 미적용.
- 디스크에 받아둔 export 번들이 라이브 시안과 불일치(새 파일 누락 등) = stale.

`tsc`/`vitest` 로는 안 잡히므로 **CSS 자체를 파싱·검사하는 전용 가드**가 필요하다.

## 구성 (자산)

이 스킬 디렉터리의 `assets/` 에 검증된 스크립트가 들어 있다. 설치 = 이들을 대상 프로젝트로 복사 + 배선.

- `assets/css-guard.mjs` - 핵심 가드. ① 구문 무결성(주석 조기종료·미종료·중괄호 불균형 상태머신 + postcss 로 깨진 셀렉터 탐지) ② 누락 CSS 변수(`var(--x)` 가 css 정의·JS `setProperty` 어디에도 없고 폴백도 없음). 파일단위(인자)·전체(`--all`) 모두 지원. 문제 발견 시 exit 1.
- `assets/validate-handoff.mjs` - 수동 오케스트레이터. 가드 전체 스윕 + stylelint + 셀렉터 불일치 리포트(참고) + stale 번들 검사(`--live` diff). css-guard/stylelint 오류는 실패, 셀렉터/stale 은 휴리스틱이라 참고 출력만.
- `assets/css-guard.sh` - PostToolUse 훅 래퍼. 수정된 css 를 css-guard 로 검사, 실패 시 exit 2 로 편집을 되돌린다(block).
- `assets/stylelintrc.json` - 최소 stylelint 규칙(표준 config 는 oklch/모던 문법 노이즈가 커서 미사용).

## 전제

표준 레이아웃을 가정한다: **Vite 류 프런트엔드가 `<repo>/frontend/` 에 있고 CSS 가 `frontend/src/**/*.css`, 토큰(`--x:`)이 그 안에 정의**. 다른 레이아웃이면 "적응" 절을 본다.

## 설치 절차

대상 프로젝트 루트를 `$REPO`, 이 스킬 디렉터리를 `$SKILL` 이라 하자.

1. **가드 스크립트 복사**:
   ```bash
   mkdir -p "$REPO/frontend/scripts"
   cp "$SKILL/assets/css-guard.mjs"        "$REPO/frontend/scripts/css-guard.mjs"
   cp "$SKILL/assets/validate-handoff.mjs" "$REPO/frontend/scripts/validate-handoff.mjs"
   cp "$SKILL/assets/stylelintrc.json"     "$REPO/frontend/.stylelintrc.json"
   ```

2. **훅 스크립트 복사 + 실행권한**:
   ```bash
   mkdir -p "$REPO/.claude/hooks"
   cp "$SKILL/assets/css-guard.sh" "$REPO/.claude/hooks/css-guard.sh"
   chmod +x "$REPO/.claude/hooks/css-guard.sh"
   ```

3. **PostToolUse 훅 등록** - `$REPO/.claude/settings.json` 의 `hooks.PostToolUse` 에서 `Edit|Write` matcher 의 `hooks` 배열에 아래를 추가(기존 typecheck 훅 등과 공존):
   ```json
   {
     "type": "command",
     "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/css-guard.sh\"",
     "statusMessage": "CSS 가드 점검 중"
   }
   ```
   matcher 블록이 없으면 새로 만든다. (이 변경은 자동 적용이 아니라 **사용자 승인** 후 settings.json 편집으로 반영한다.)

4. **stylelint devDependency + npm 스크립트**:
   ```bash
   cd "$REPO/frontend" && npm install -D stylelint
   ```
   `frontend/package.json` 의 `scripts` 에 추가:
   ```json
   "css-guard": "node scripts/css-guard.mjs --all",
   "validate-handoff": "node scripts/validate-handoff.mjs"
   ```

5. **설치 검증** (반드시 한다 - 추측 금지):
   - 정상: `cd "$REPO/frontend" && node scripts/css-guard.mjs --all` 가 exit 0(거짓양성 0).
   - 버그 픽스처로 검출 확인: 임시 css 에 주석 조기종료(`/* a*/b */`)와 `var(--nope)` 를 넣고 `node scripts/css-guard.mjs <fixture>` 가 검출 + exit 1 인지 확인 후 픽스처 삭제.
   - 훅: `printf '{"tool_input":{"file_path":"<fixture 경로>"}}' | CLAUDE_PROJECT_DIR="$REPO" bash "$REPO/.claude/hooks/css-guard.sh"` 가 exit 2.

## 사용

- **편집 즉시(훅)**: `frontend/**/*.css` 를 편집하면 PostToolUse 훅이 자동 검사. 실패 시 block + stderr 로 사유.
- **핸드오프 직후(수동)**: `cd frontend && npm run validate-handoff`.
- **stale 번들 검사**: node 는 MCP 를 못 부르므로, Claude 가 DesignSync(`list_files`) 결과(경로 배열)를 JSON 으로 저장해 넘긴다:
  ```bash
  npm run validate-handoff -- --live live-files.json
  ```
  디스크 번들(`.design-handoff/`)에 없는 라이브 파일을 stale 후보로 경고한다.

## 적응 (비표준 레이아웃)

- 프런트엔드 디렉터리명이 `frontend/` 가 아니면: `assets/css-guard.sh` 의 `*/frontend/*` case 와 `frontend/scripts/...` 경로, `validate-handoff.mjs`/`css-guard.mjs` 의 위치를 그 디렉터리에 맞춘다. 두 `.mjs` 는 자기 위치 기준(`SCRIPT_DIR`)으로 `src`/repo 루트를 잡으므로 `<frontend>/scripts/` 에 두면 대개 그대로 동작한다.
- 토큰 정의가 여러 css 에 흩어져 있어도 `collectDefinedVars()` 가 `src` 전체 + `setProperty("--x")`(ts/tsx)를 집계하므로 보통 오탐 없음. 그래도 거짓양성이 나면 그 변수의 정의/주입 위치를 확인해 누락 여부를 판단한다.
- 디스크 번들 경로가 `.design-handoff/` 가 아니면 `validate-handoff.mjs` 의 `bundleDir` 를 맞춘다.

## 주의

- 셀렉터 불일치/stale 은 **휴리스틱**이라 동적 className(`grade-${x}`)·템플릿 리터럴에서 오탐이 난다. 그래서 둘은 실패가 아니라 "참고" 출력이다. 구문/누락변수만 실패(block)로 막는다.
- stylelint 의 `declaration-block-no-duplicate-properties` 는 기존 코드 오탐을 피하려 `severity: warning`(비차단). 새 핸드오프의 중복 속성은 경고로 보인다.
- 이 가드 자체를 편집할 때 **주석에 `별표+슬래시`를 텍스트로 쓰면 .mjs 의 JS 블록 주석마저 조기 종료**된다(막으려는 바로 그 버그). 주석엔 그 시퀀스를 쓰지 말 것.
