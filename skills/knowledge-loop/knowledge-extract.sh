#!/bin/bash
# SessionEnd 훅: 세션에서 지식 후보를 추출해 ~/.claude/knowledge/pending.md에 적재
# 게이트를 통과한 세션만 haiku로 추출. 승격은 /knowledge-loop에서 수동으로.

# 추출용 헤드리스 세션이 다시 훅을 타는 재귀 방지
[ -n "$CLAUDE_KNOWLEDGE_EXTRACT" ] && exit 0

input=$(cat)
transcript=$(echo "$input" | jq -r '.transcript_path // empty')
cwd=$(echo "$input" | jq -r '.cwd // "?"')
session_id=$(echo "$input" | jq -r '.session_id // "unknown"')
[ -f "$transcript" ] || exit 0

KNOW_DIR="$HOME/.claude/knowledge"
mkdir -p "$KNOW_DIR"

# 사람 메시지만 추출 (tool_result 제외)
human_txt=$(jq -r '
  select(.type=="user")
  | .message.content
  | if type=="string" then .
    else ([.[]? | select(.type=="text") | .text] | join("\n")) end
  | select(length>0)
' "$transcript" 2>/dev/null)

n_user=$(echo "$human_txt" | grep -c '[^[:space:]]')
interrupts=$(grep -c 'Request interrupted by user' "$transcript" 2>/dev/null)
commits=$(grep -c 'git commit' "$transcript" 2>/dev/null)

# 게이트: 실질 대화 5개 미만이면 스킵, 신호(교정/커밋/긴 세션) 없으면 스킵
[ "$n_user" -ge 5 ] || exit 0
if [ "$interrupts" -eq 0 ] && [ "$commits" -eq 0 ] && [ "$n_user" -lt 15 ]; then
  exit 0
fi

# 사람 메시지 최근 15KB만 사용 (토큰 절약)
sample=$(echo "$human_txt" | tail -c 15000)

prompt="다음은 한 Claude Code 세션에서 사용자가 보낸 메시지들이다. 다음 세션에도 가치가 남을 지식 후보를 0~3개 추출하라.

추출 대상:
- 도메인/프로젝트 지식 (용어, 제약, 결정사항)
- 사용자가 AI를 교정한 규칙 (반복 방지 가치가 있는 것)
- 반복된 절차 (스킬 후보면 줄 끝에 [스킬후보] 표기)

제외: 일회성 잡담, 단순 질문, AI 사용 팁, 이미 자명한 내용.
출력: 마크다운 불릿(- )만, 각 1줄, 한국어. 추출할 것이 없으면 NONE만 출력.

---
$sample"

(
  result=$(CLAUDE_KNOWLEDGE_EXTRACT=1 claude -p --model claude-haiku-4-5-20251001 "$prompt" 2>>"$KNOW_DIR/extract.log")
  if [ -n "$result" ] && [ "$result" != "NONE" ] && ! echo "$result" | grep -q '^NONE$'; then
    {
      echo ""
      echo "## $(date '+%Y-%m-%d %H:%M') | $(basename "$cwd") | ${session_id:0:8} (교정 ${interrupts}회, 커밋 ${commits}건)"
      echo "$result"
    } >> "$KNOW_DIR/pending.md"
  fi
) >/dev/null 2>&1 &

exit 0
