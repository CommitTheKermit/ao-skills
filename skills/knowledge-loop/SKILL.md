---
name: knowledge-loop
description: 세션에서 자동 추출된 지식 후보(pending.md)를 리뷰해 전역/프로젝트 CLAUDE.md 규칙, 스킬, 영구 지식 문서로 승격하거나 폐기한다. /knowledge-loop로 명시 호출.
disable-model-invocation: true
---

# knowledge-loop: 지식 추출-승격 루프

Hermes Agent 패턴의 변형. **추출은 자동(SessionEnd 훅), 승격은 수동(이 스킬)**.
자동 반영을 금지해 잘못된 가설이 CLAUDE.md를 오염시키는 것을 막는다.

## 저장소 구조 (~/.claude/knowledge/)

- `pending.md`: 훅이 적재하는 지식 후보 (memory, 주기적으로 비움)
- `docs/`: 승격된 영구 지식 문서 (knowledge)
- `archive.md`: 처리 완료된 후보 이력
- `extract.log`: 추출 훅 에러 로그

## 리뷰 워크플로우

1. `~/.claude/knowledge/pending.md`를 읽는다. 비어 있으면 그대로 보고하고 종료.
2. 후보들을 군집화한다. **여러 세션에서 반복 등장한 패턴**을 최우선으로.
3. 각 군집에 대해 승격 대상을 제안하고 **반드시 사용자 승인을 받는다**:
   - **전역 규칙** → `~/.claude/CLAUDE.md` (모든 프로젝트에 적용될 교정 규칙)
   - **프로젝트 규칙** → `<project>/CLAUDE.md` (특정 프로젝트 도메인 지식)
   - **스킬 승격** → ao-skill-update 스킬 워크플로우로 진행 ([스킬후보] 표기 + 3회 이상 반복된 절차만)
   - **영구 문서** → `~/.claude/knowledge/docs/<주제>.md` (규칙은 아니지만 보존 가치 있는 지식)
   - **폐기** (일회성, 검증 불가, 이미 반영됨)
4. 승인된 항목만 반영한다. 반영/폐기된 후보는 pending.md에서 제거하고 archive.md에 날짜와 처리 결과를 남긴다.

## 원칙

- 빈도만으로 승격하지 않는다. "반복됨 + 교정 없이 통과 + 검증됨"을 충족해야 한다.
- CLAUDE.md에 넣는 규칙은 1~2줄로 압축한다. 길어지면 docs/로 빼고 참조만 건다.
- 승격 문서/스킬은 예시 코드 최소화, 워크플로우 서술 위주 (컨텍스트 절약).
- 리뷰 주기는 주 1회 권장 (cooldown day).
