#!/bin/bash
# grounding-guard 공용 정의. 두 훅 스크립트(grounding-nudge.sh, verify-grounding.sh)가 source 한다.
# - GG_CONCEPT_RE     : 질문이 개념/사양 설명을 요구하는지 판별 (UserPromptSubmit)
# - GG_SOURCE_RE      : 답변 생성 중 출처를 실제로 들여다본 흔적 판별 (Stop)
# - gg_turn_tool_blob : transcript(JSONL)에서 "이번 턴" 어시스턴트 도구사용 문자열 추출
#
# 정규식은 의도적으로 느슨하다(과탐 < 과통과). 차단이 너무 잦으면 GG_CONCEPT_RE 를,
# 기억 기반 답변이 너무 새어 통과하면 GG_SOURCE_RE 를 좁혀 튜닝한다.

# 발동/판정 관찰용 로그 (튜닝 근거). 인자 = 로그 메시지.
gg_log() {
  local d="$HOME/.claude/.grounding-guard"
  mkdir -p "$d" 2>/dev/null
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$d/guard.log" 2>/dev/null
}

# 개념/사양/동작 설명을 요구하는 질문 신호 (한/영).
GG_CONCEPT_RE='개념|무엇|뭐(야|냐|니|지|예요|에요|일까|길래)|뭔지|뭔가요|어떻게 ?(동작|작동|돌아가|구현|처리|쓰|사용)|작동 ?방식|동작 ?(원리|방식)|원리|차이(점|가 |는 |를 )|이란|란 ?(무엇|뭐|뭔)|정의(가|는|를| )|스펙|사양|설명(해|좀|이 |을 | 부탁)|무슨 ?뜻|뜻이 |뜻은|의미(가|는|를)|왜 .*(되|하는지|인지|일까)|how does|what is|what are|what does|explain|difference between|why does|how to'

# 출처를 실제로 들여다본 흔적으로 인정할 신호 (도구명 + Bash 읽기명령 + 파일경로/URL).
GG_SOURCE_RE='Read|Grep|Glob|WebFetch|WebSearch|NotebookRead|Task|Agent|fetch|search|grep|curl|wget|cat|less|view|head|tail|find|sed|awk|rg '

# transcript(JSONL)에서 마지막 사람-텍스트 메시지 이후 어시스턴트가 호출한 도구들의
# "이름 + 주요 인자" 문자열을 표준출력으로 낸다. 인자 $1 = transcript 경로.
gg_turn_tool_blob() {
  local tp="$1"
  [ -f "$tp" ] || return 0
  local idx
  idx=$(jq -rs '
    [ to_entries[]
      | select(.value.type=="user")
      | select( (.value.message.content // [])
                | if type=="string" then (. | length > 0)
                  else (any(.[]?; .type=="text")) end )
      | .key ] | last // -1
  ' "$tp" 2>/dev/null)
  case "$idx" in ''|*[!0-9-]*) idx=-1 ;; esac
  jq -rs --argjson start "$idx" '
    [ .[($start + 1):][]
      | select(.type=="assistant")
      | (.message.content // [])
      | (if type=="array" then .[] else empty end)
      | select(.type=="tool_use")
      | (.name + " " + ((.input.command // .input.file_path // .input.pattern // .input.url // "") | tostring)) ]
    | join("\n")
  ' "$tp" 2>/dev/null
}
