#!/usr/bin/env python3
"""세션 시작/종료 시 TODO 를 관리하는 Claude Code 훅 스크립트.

사용법:
    todo-session.py start   # SessionStart 훅: 완료 항목 아카이브 + 미완료 항목을 context 로 노출
    todo-session.py end     # SessionEnd 훅: 완료 항목 아카이브만 수행

대상 파일:
    - 전역  : ~/.claude/todo.md
    - 프로젝트: <project>/.claude/todo.md

설계 원칙:
    - 훅이 세션을 막으면 안 되므로 어떤 예외에도 exit 0 으로 끝낸다.
    - 완료(- [x]) 항목은 삭제하지 않고 "## Done (archive)" 섹션으로 이동한다.
    - 세션 시작 출력에는 미완료(- [ ]) 항목만 보여준다.
    - 마지막 접속 후 임계값(기본 1시간)을 넘으면 경과 시간 안내 한 줄을 덧붙인다.
"""

import sys
import os
import json
import time
from datetime import date, datetime

THRESHOLD_SECONDS = 3600  # "오랜만" 강조 임계값: 1시간
ARCHIVE_HEADER = "## Done (archive)"


def _read_payload():
    """훅이 stdin 으로 넘기는 JSON payload 를 안전하게 파싱한다."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _project_dir(payload):
    return (
        payload.get("cwd")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )


def _todo_targets(payload):
    home = os.path.expanduser("~")
    global_todo = os.path.join(home, ".claude", "todo.md")
    project_todo = os.path.join(_project_dir(payload), ".claude", "todo.md")
    targets = [("전역", global_todo)]
    # 프로젝트 todo 가 전역과 동일 경로면 중복 제거
    if os.path.abspath(project_todo) != os.path.abspath(global_todo):
        targets.append(("프로젝트", project_todo))
    return targets


def _split_active_archive(lines):
    """라인들을 (활성 영역, 아카이브 영역) 으로 나눈다."""
    for i, line in enumerate(lines):
        if line.strip() == ARCHIVE_HEADER:
            return lines[:i], lines[i + 1:]
    return lines, None


def archive_completed(path):
    """완료(- [x]) 항목을 활성 영역에서 아카이브 영역으로 이동한다."""
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return

    active, archive = _split_active_archive(lines)
    if archive is None:
        archive = []

    today = date.today().isoformat()
    moved = []
    kept = []
    for line in active:
        stripped = line.lstrip()
        if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            moved.append(f"{line.rstrip()}  (archived {today})")
        else:
            kept.append(line)

    if not moved:
        return  # 변경 없음 - 파일을 건드리지 않는다

    # 활성 영역 끝의 빈 줄 정리
    while kept and kept[-1].strip() == "":
        kept.pop()

    new_lines = list(kept)
    new_lines.append("")
    new_lines.append(ARCHIVE_HEADER)
    new_lines.append("")
    # 기존 아카이브의 선두 빈 줄 제거 후 합치기
    archive_body = [l for l in archive]
    while archive_body and archive_body[0].strip() == "":
        archive_body.pop(0)
    new_lines.extend(moved)
    new_lines.extend(archive_body)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines).rstrip() + "\n")
    except Exception:
        return


def read_incomplete(path):
    """활성 영역의 미완료(- [ ]) 항목 라인을 반환한다."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return []
    active, _ = _split_active_archive(lines)
    items = []
    for line in active:
        stripped = line.lstrip()
        if stripped.startswith("- [ ]"):
            items.append(stripped)
    return items


def _last_access_path():
    return os.path.join(os.path.expanduser("~"), ".claude", ".todo-last-access")


def _read_last_access():
    p = _last_access_path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            return float(f.read().strip())
    except Exception:
        return None


def _write_last_access(ts):
    try:
        os.makedirs(os.path.dirname(_last_access_path()), exist_ok=True)
        with open(_last_access_path(), "w", encoding="utf-8") as f:
            f.write(str(ts))
    except Exception:
        pass


def _format_elapsed(seconds):
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간"
    days = hours // 24
    return f"{days}일"


def run_start(payload):
    targets = _todo_targets(payload)

    # 1) 완료 항목 아카이브
    for _, path in targets:
        archive_completed(path)

    # 2) 경과 시간 계산 (아카이브 후, last-access 갱신 전)
    now = time.time()
    last = _read_last_access()
    elapsed_note = None
    if last is not None and (now - last) > THRESHOLD_SECONDS:
        elapsed_note = f"마지막 접속으로부터 {_format_elapsed(now - last)} 경과"
    _write_last_access(now)

    # 3) 미완료 항목 수집
    sections = []
    total = 0
    for label, path in targets:
        items = read_incomplete(path)
        total += len(items)
        if items:
            body = "\n".join(items)
            sections.append(f"[{label}] ({path})\n{body}")

    if total == 0 and elapsed_note is None:
        return  # 보여줄 것 없음 - 조용히 종료

    parts = ["저장된 TODO 목록입니다. 세션을 시작하며 사용자에게 아래 내용을 보기 좋게 안내하세요."]
    if elapsed_note:
        parts.append(f"⏰ {elapsed_note}")
    if sections:
        parts.append("\n\n".join(sections))
    else:
        parts.append("(미완료 TODO 없음)")
    parts.append(
        "TODO 관리: 사용자가 자연어로 '~ todo에 추가/완료'라고 하면 해당 파일의 "
        "'- [ ]'/'- [x]' 항목을 직접 편집하세요. 전역=~/.claude/todo.md, "
        "프로젝트=<project>/.claude/todo.md. 완료 항목은 세션 시작/종료 시 자동 아카이브됩니다."
    )
    context = "\n\n".join(parts)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


def run_end(payload):
    for _, path in _todo_targets(payload):
        archive_completed(path)
    _write_last_access(time.time())


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "start"
    payload = _read_payload()
    try:
        if mode == "end":
            run_end(payload)
        else:
            run_start(payload)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
