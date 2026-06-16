#!/bin/bash
# UserPromptSubmit 훅: 질문이 개념/사양 설명 요청이면
#   (1) "출처부터 확인하라" 컨텍스트를 주입(exit 0 stdout 이 Claude 컨텍스트로 들어감)
#   (2) 이번 턴 플래그를 남겨 Stop 훅(verify-grounding.sh)이 종료 시 강제하게 한다.
# 모든 실패는 fail-open(그냥 통과)으로 사용자 세션을 막지 않는다.

set -o pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/lib.sh" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
prompt=$(printf '%s' "$input" | jq -r '.prompt // empty' 2>/dev/null)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
[ -n "$prompt" ] || exit 0

# 슬래시 커맨드/매우 짧은 입력은 제외
case "$prompt" in /*) exit 0 ;; esac
[ "${#prompt}" -ge 6 ] || exit 0

# 개념질문 신호가 없으면 아무것도 하지 않음
printf '%s' "$prompt" | grep -qiE "$GG_CONCEPT_RE" || exit 0

# 이번 턴 플래그 (Stop 훅이 이 세션의 이번 종료를 검사하도록)
FLAG_DIR="$HOME/.claude/.grounding-guard"
mkdir -p "$FLAG_DIR" 2>/dev/null
[ -n "$session_id" ] && : > "$FLAG_DIR/$session_id.flag" 2>/dev/null
gg_log "nudge fired session=${session_id:0:8}"

# 컨텍스트 주입
cat <<'EOF'
[근거 우선 안내] 이번 질문은 개념·사양·동작에 대한 사실 설명을 요구할 수 있습니다. 기억에만 의존해 단정하지 말고, 관련 공식 문서·소스코드를 Read/Grep/Glob/WebFetch/WebSearch 로 먼저 확인한 뒤 근거(파일경로/URL)와 함께 설명하세요. 확인하지 못한 부분은 '추정' 또는 '미확인'으로 표기하세요. (출처 확인도 불확실성 표기도 없이 개념을 단정하면 종료 시 한 번 되돌려집니다.)
EOF
exit 0
