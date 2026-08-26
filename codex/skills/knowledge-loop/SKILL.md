---
name: knowledge-loop
description: 세션에서 자동 추출된 지식 후보(pending.md)를 리뷰해 전역/프로젝트 AGENTS.md 규칙, 스킬, 영구 지식 문서로 승격하거나 폐기한다. /knowledge-loop로 명시 호출.
disable-model-invocation: true
---

# knowledge-loop: 지식 추출-승격 루프

<!-- usage-stats: skill knowledge-loop -->

첫 동작으로 `python3 "$HOME/.agents/skills/usage-stats/scripts/usage_stats.py" record skill knowledge-loop >/dev/null 2>&1 || true`를 이 발동에서 한 번만 실행한다.

Hermes Agent 패턴의 변형. 현재는 **replay 검증과 승격만 수동**이다.
실시간 SessionEnd 추출 훅은 등록하지 않는다. 최신 Codex JSONL replay 결과를 먼저 검증한 뒤
별도 승인으로 활성화한다. 자동 반영을 금지해 잘못된 가설이 AGENTS.md를 오염시키는 것을 막는다.

## 저장소 구조 (~/.Codex/knowledge/)

- `pending.md`: 훅이 적재하는 지식 후보 (memory, 주기적으로 비움)
- `docs/`: 승격된 영구 지식 문서 (knowledge)
- `archive.md`: 처리 완료된 후보 이력
- `extract.log`: 향후 추출 훅 활성화 시 실행 로그 (`rc`=Codex 종료코드, `new`=직전 추출 이후 새 사람 메시지 수)
- `.extract-state`: 향후 추출 훅의 세션별 처리 위치(high-water mark)
- `.nudge-stamp`: 승격 넛지 마지막 안내 시각. 쿨다운용

## replay audit

`replay-audit.py`는 stdlib만으로 `~/.codex/sessions`의 최신 사용자 root 세션 N개를 읽기 전용
집계한다. subagent 전체 세션, 주입된 AGENTS wrapper, heartbeat는 제외하고
`event_msg.payload.type == "turn_aborted"`만 중단으로 센다. 원문, 세션 ID, 경로, 비밀값은
출력하지 않는다.

```bash
python3 "$HOME/.agents/skills/knowledge-loop/replay-audit.py" --latest 100
python3 "$HOME/.agents/skills/knowledge-loop/replay-audit.py" --current
```

## 미등록 자동화 자산

- **추출 후보 (`knowledge-extract.sh`, 미등록)**: 게이트(직전 추출 이후 새 사람 메시지 5개 이상 + 교정/커밋/긴 세션 신호) 통과 시 0~3개 후보 추출.
  - 현재 Codex JSONL의 첫 `session_meta`가 user root인 세션만 처리하고, 주입 wrapper와 heartbeat를 제외한 뒤 high-water mark를 계산한다.
  - 중단은 `event_msg.payload.type == "turn_aborted"`만 센다.
  - 같은 세션이 SessionEnd마다 재추출돼 동일 지식이 중복 적재되지 않도록 `.extract-state` 의 high-water mark 이후 **새 메시지만** 샘플링한다.
  - 거대 붙여넣기(HTML/스킬 번들/명령 출력)는 샘플에서 제외하고 메시지당 2000자로 캡해, 대화성 신호가 묻히지 않게 한다.
  - Codex 호출 실패(rc≠0)나 불릿(`- `)이 아닌 출력(에러 문자열 등)은 적재하지 않는다.
- **승격 넛지 후보 (`knowledge-nudge.sh`, 미등록)**: `pending.md`가 8개 세션 분량 이상 쌓이면 리뷰를 권한다.

`knowledge-extract.sh`와 `knowledge-nudge.sh`는 현재 `~/.codex/hooks.json`에 자동 등록하지 않는다.
replay fixture의 포착률과 오탐률을 확인한 뒤 별도 작업으로 등록한다.

## 리뷰 워크플로우

1. `~/.Codex/knowledge/pending.md`를 읽는다. 비어 있으면 그대로 보고하고 종료.
2. 후보들을 군집화한다. **여러 세션에서 반복 등장한 패턴**을 최우선으로.
3. 각 군집에 대해 승격 대상을 제안하고 **반드시 사용자 승인을 받는다**:
   - **전역 규칙** → `~/.Codex/AGENTS.md` (모든 프로젝트에 적용될 교정 규칙, 1~2줄)
   - **프로젝트 규칙** → `<project>/AGENTS.md` (특정 프로젝트의 짧은 제약·교정·관례, 1~2줄)
   - **프로젝트 기술 문서** → `<project>/docs/<주제>.md` (아키텍처·데이터 모델·스키마·도메인 명세 등 길거나 구조적인 지식). AGENTS.md 본문에 그대로 쓰지 말고 docs 로 빼되, `<project>/AGENTS.md` 엔 "상세는 `docs/<주제>.md` 참조" 한 줄 라우팅만 남긴다
   - **스킬 승격** → ao-skill-update 스킬 워크플로우로 진행 ([스킬후보] 표기 + 3회 이상 반복된 절차만)
   - **영구 지식 문서** → `~/.Codex/knowledge/docs/<주제>.md` (특정 프로젝트에 매이지 않는, 규칙은 아니지만 보존 가치 있는 지식)
   - **폐기** (일회성, 검증 불가, 이미 반영됨)

   분류 기준: **1~2줄로 압축되는 규칙/제약이면 AGENTS.md, 그보다 길거나 구조(코드/스키마/아키텍처)를 담으면 docs + 참조 한 줄.** 프로젝트에 매이면 `<project>/docs/`, 전역 지식이면 `~/.Codex/knowledge/docs/`.
4. 승인된 항목만 반영한다. 반영/폐기된 후보는 pending.md에서 제거하고 archive.md에 날짜와 처리 결과를 남긴다.

## 원칙

- 빈도만으로 승격하지 않는다. "반복됨 + 교정 없이 통과 + 검증됨"을 충족해야 한다.
- AGENTS.md(전역/프로젝트)에는 1~2줄 규칙만 넣는다. 길거나 구조적인 기술 명세는 해당 위치의 docs/로 빼고 AGENTS.md엔 참조 한 줄만 건다 (전역 지식은 `~/.Codex/knowledge/docs/`, 프로젝트 지식은 `<project>/docs/`).
- 승격 문서/스킬은 예시 코드 최소화, 워크플로우 서술 위주 (컨텍스트 절약).
- 리뷰 주기는 주 1회 권장 (cooldown day).
