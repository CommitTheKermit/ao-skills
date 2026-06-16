#!/bin/bash
# SessionStart 훅: pending 지식 후보가 일정량 쌓이면 /knowledge-loop 승격 리뷰를 권한다.
# 쿨다운(기본 3시간)으로 매 세션 반복 안내를 막는다. 승격(수동)이 잊혀 후보만 쌓이는 것을 방지. (Fix 1)

KNOW_DIR="$HOME/.claude/knowledge"
PENDING="$KNOW_DIR/pending.md"
STAMP="$KNOW_DIR/.nudge-stamp"
THRESHOLD=8       # pending 누적 세션(## 헤더) 수 임계값
COOLDOWN=10800    # 재안내 쿨다운 3시간(초)

[ -f "$PENDING" ] || exit 0

sessions=$(grep -c '^## ' "$PENDING" 2>/dev/null)
sessions=${sessions:-0}
[ "$sessions" -ge "$THRESHOLD" ] || exit 0

now=$(date +%s)
if [ -f "$STAMP" ]; then
  last=$(cat "$STAMP" 2>/dev/null)
  last=${last:-0}
  [ $(( now - last )) -ge "$COOLDOWN" ] || exit 0
fi
echo "$now" > "$STAMP"

ctx="지식 후보가 ${sessions}개 세션 분량 쌓였습니다. 시간 날 때 /knowledge-loop 로 승격 리뷰를 권장합니다(마지막 안내 후 3시간+ 경과). 후보 파일: ~/.claude/knowledge/pending.md"

# SessionStart additionalContext 로 주입 (todo-session.py 와 동일 형식). ctx 는 따옴표/역슬래시 없는 통제된 문자열.
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"

exit 0
