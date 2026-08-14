#!/bin/bash
# knowledge-loop 승격 리뷰를 cmux 새 탭에서 시작한다.
# terminal-notifier 알림의 -execute 로 호출된다(데스크탑 알림 클릭 시).
# cmux 를 AppleScript 로 제어하므로 소켓/CMUX_* 환경변수가 없어도 동작한다.
LOG="$HOME/.Codex/knowledge/open-review.log"
{
  echo "=== $(date '+%F %T') open-review 시작 ==="

  # cmux 앱을 전면으로 활성화한다. terminal-notifier(-execute)의 launchd 컨텍스트에서는
  # AppleScript 의 activate 만으로는 창이 앞으로 나오지 않으므로 open 으로 보강한다.
  open -a cmux
  echo "open -a cmux rc=$?"
  sleep 0.4

  /usr/bin/osascript <<'APPLESCRIPT'
tell application "cmux"
  activate
  delay 0.3
  set newTab to new tab
  delay 0.4
  -- 새로 만든 워크스페이스로 화면을 전환(select)하고 터미널을 전면 포커스한다.
  -- new tab 은 워크스페이스를 생성만 하고 전환하지 않으므로 이 두 줄이 필요하다.
  select tab newTab
  focus terminal 1 of newTab
  -- 새 탭 셸 프롬프트가 준비될 때까지 기다린다(너무 줄이면 명령이 유실되므로 여유를 둔다).
  delay 0.9
  -- 명령어를 paste 로 입력한다. 단 ghostty 의 bracketed paste 때문에 paste 안의
  -- 개행은 실행으로 처리되지 않으므로, Enter(CR)는 perform action 으로 별도 전송한다.
  input text "codex \"/knowledge-loop\"" to terminal 1 of newTab
  delay 0.2
  perform action ("text:" & return) on terminal 1 of newTab
  return "osascript OK: new tab + select + focus + command executed"
end tell
APPLESCRIPT
  echo "osascript rc=$?"
} >> "$LOG" 2>&1
