#!/usr/bin/env bash
# PostToolUse(Edit|Write) 훅: 수정된 frontend 의 .css 파일을 css-guard 로 즉시 검사.
# 빌드/타입체크/단위테스트가 못 잡는 "문법상 valid 인데 규칙이 통째로 죽는" CSS 잠복 버그
# (주석 안 '* /' 조기종료, 미종료 주석, 괄호 불균형, 누락 CSS 변수)를 편집 즉시 막는다.
# 실패 = 종료코드 2 + stderr 로 오류를 Claude 에게 돌려보내 스스로 고치게 한다.

input="$(cat)"
f="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")"

case "$f" in
  *.css) ;;
  *) exit 0 ;;
esac
case "$f" in
  */node_modules/*|*/dist/*|*/lib/*) exit 0 ;;
esac
# 토큰 정의가 frontend/src 기준이라 frontend 의 css 만 대상으로 한다.
case "$f" in
  */frontend/*) ;;
  *) exit 0 ;;
esac

guard="$CLAUDE_PROJECT_DIR/frontend/scripts/css-guard.mjs"
[ -f "$guard" ] || exit 0

out="$(node "$guard" "$f" 2>&1)"
if [ $? -ne 0 ]; then
  {
    echo "[css-guard 실패] $f - 아래 CSS 무결성 문제를 해결할 것"
    printf '%s\n' "$out" | head -40
  } >&2
  exit 2
fi
exit 0
