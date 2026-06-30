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

# 컨텍스트 주입.
# 안내문은 Stop 훅(verify-grounding.sh)의 통과조건과 1:1로 일치시켜, 첫 답변이 곧바로
# 통과하고 두 번 쓰지 않게 한다. 통과조건 = 답변에 (출처/근거) 또는 (추정/미확인/표준 개념)
# 표기 중 하나가 보이거나, 이번 턴에 출처 도구를 실제로 호출한 흔적이 있을 것.
cat <<'EOF'
[근거 우선 안내] 이 질문은 개념·사양·동작의 사실 설명을 요구할 수 있습니다. 답변을 한 번에 통과시켜 다시 쓰는 일이 없게, 답을 쓰기 전에 아래 중 하나를 끝내고 그 흔적을 답변에 남기세요. (둘 중 아무 표시도 없으면 종료 시 한 번 되돌려져 두 번 쓰게 됩니다.)
- (A) 구체 사양·동작(프로젝트 코드·도구·라이브러리·API 등): Read/Grep/Glob/WebFetch/WebSearch 로 출처를 먼저 확인하고, 답변에 "근거:" 로 파일경로/URL 을 적는다.
- (B) 널리 알려진 표준·일반 개념이라 별도 출처가 불필요하면: 출처를 찾는 대신 그 설명을 "표준 개념" 이라고 밝히고, 확실치 않은 부분은 '추정' 또는 '미확인' 으로 표기한다.
즉 모든 사실 설명 답변에는 (출처/근거) 또는 (추정/미확인/표준 개념) 표기 중 하나가 반드시 보여야 합니다. 확실한 사실과 추측을 같은 톤으로 섞지 마세요.
EOF
exit 0
