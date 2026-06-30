#!/bin/bash
# Stop 훅: 개념질문 턴(grounding-nudge.sh 가 남긴 플래그 존재)인데
#   - 이번 턴 출처 확인 흔적이 0이고
#   - 답변에 '추정/미확인' 등 불확실성 표기도 없으면
# 한 번(exit 2) 되돌려 근거 확인 또는 불확실성 표기를 요구한다.
# fail-open + stop_hook_active + 플래그 1회 소비로 최대 1회만 차단(무한루프/8회벽 회피).

set -o pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/lib.sh" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)

# 훅으로 인한 계속 진행 중이면 재차단 금지
stop_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$stop_active" = "true" ] && exit 0

session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
last_msg=$(printf '%s' "$input" | jq -r '.last_assistant_message // empty' 2>/dev/null)

# 개념질문 턴이 아니면 통과
FLAG_DIR="$HOME/.claude/.grounding-guard"
flag="$FLAG_DIR/$session_id.flag"
{ [ -n "$session_id" ] && [ -f "$flag" ]; } || exit 0
# 플래그는 평가 즉시 소비(중복 차단/스테일 방지)
rm -f "$flag" 2>/dev/null

# 답변이 이미 출처/불확실성/표준개념을 명시했으면 통과.
# (널리 알려진 표준·일반 개념은 출처 대신 '표준 개념'으로 정직히 밝히면 첫 턴에 통과 -
#  grounding-nudge.sh 의 (B) 탈출구와 일치. '미확인' 의역도 정상 준수.)
if printf '%s' "$last_msg" | grep -qE '추정|미확인|확인 (못|하지 못|불가)|출처[:：]|근거[:：]|표준 ?개념|일반 ?개념'; then
  gg_log "pass(marker) session=${session_id:0:8}"
  exit 0
fi

# 이번 턴 출처 확인 흔적이 있으면 통과
[ -f "$transcript" ] || exit 0
blob=$(gg_turn_tool_blob "$transcript")
if printf '%s' "$blob" | grep -qiE "$GG_SOURCE_RE"; then
  gg_log "pass(source) session=${session_id:0:8}"
  exit 0
fi

# 출처 흔적 0 + 불확실성 표기 0 -> 한 번 되돌림
gg_log "BLOCK session=${session_id:0:8} (no source, no marker)"
cat >&2 <<'EOF'
[grounding-guard] 이 답변은 개념·사양을 사실로 설명하는데 이번 턴에 출처(Read/Grep/Glob/WebFetch/WebSearch 등)를 한 번도 확인하지 않았고, 답변에 '추정/미확인' 표기도 없습니다. 기억 기반 단정은 환각 위험이 있습니다. 다음 중 하나로 보완한 뒤 마무리하세요: (1) 관련 공식 문서·소스코드를 직접 확인하고 근거(파일경로/URL)와 함께 다시 설명, 또는 (2) 확인할 출처가 없거나 불가능하면 단정 표현을 '추정/미확인'으로 바꿔 명시.
EOF
exit 2
