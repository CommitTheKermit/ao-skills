#!/usr/bin/env python3
"""세션 시작/종료 시 TODO 를 관리하는 Claude Code 훅 스크립트.

사용법:
    todo-session.py start   # SessionStart 훅: 완료 항목 아카이브 + 현재 프로젝트/공통 미완료 항목을 context 로 노출
    todo-session.py end     # SessionEnd 훅: 완료 항목 아카이브만 수행

대상 파일:
    - 전역 단일 파일: ~/.claude/todo.md  (모든 항목이 여기 한 곳에 저장된다)

파일 구조:
    # TODO

    ## 공통
    - [ ] 어디서나 보이는 항목

    ## /절대/프로젝트/경로
    - [ ] 그 프로젝트에서만 보이는 항목

    ## Done (archive)
    - [x] 지난 완료 항목  (archived YYYY-MM-DD)

설계 원칙:
    - 훅이 세션을 막으면 안 되므로 어떤 예외에도 exit 0 으로 끝낸다.
    - 완료(- [x]) 항목은 삭제하지 않고 "## Done (archive)" 섹션으로 이동한다.
    - 세션 시작 출력에는 '공통' 섹션 + 현재 cwd 프로젝트 섹션의 미완료(- [ ]) 항목만 보여준다.
    - 헤더 없는 머리말 영역의 항목은 '공통' 으로 취급한다(구버전 호환).
    - 마지막 접속 후 임계값(기본 1시간)을 넘으면 경과 시간 안내 한 줄을 덧붙인다.
"""

import sys
import os
import json
import time
from datetime import date

THRESHOLD_SECONDS = 3600  # "오랜만" 강조 임계값: 1시간
ARCHIVE_HEADER = "## Done (archive)"
COMMON_KEY = "공통"


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


def _global_todo():
    return os.path.join(os.path.expanduser("~"), ".claude", "todo.md")


def _split_active_archive(lines):
    """라인들을 (활성 영역, 아카이브 영역) 으로 나눈다."""
    for i, line in enumerate(lines):
        if line.strip() == ARCHIVE_HEADER:
            return lines[:i], lines[i + 1:]
    return lines, None


def _parse_sections(active_lines):
    """활성 라인을 [(header, body_lines)] 로 분리한다.

    header 는 '## ' 다음의 문자열. 첫 머리말(헤더 이전)은 header=None.
    """
    sections = []
    header = None
    body = []
    for line in active_lines:
        if line.startswith("## "):
            sections.append((header, body))
            header = line[3:].strip()
            body = []
        else:
            body.append(line)
    sections.append((header, body))
    return sections


def _is_common(header):
    return header is None or header == COMMON_KEY


def _has_checkbox(body):
    return any(l.lstrip().startswith(("- [ ]", "- [x]", "- [X]")) for l in body)


def _prune_empty_project_sections(active_lines):
    """항목이 하나도 없는 프로젝트 섹션(헤더만 남은 것)을 제거한다.

    '공통' 섹션과 머리말(header=None)은 비어 있어도 유지한다.
    """
    out = []
    for header, body in _parse_sections(active_lines):
        if not _is_common(header) and not _has_checkbox(body):
            continue
        if header is not None:
            out.append(f"## {header}")
        out.extend(body)
    return out


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

    # 완료 항목이 빠져 헤더만 남은 프로젝트 섹션 정리
    kept = _prune_empty_project_sections(kept)

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


def collect_display(path, cwd_abs):
    """표시 대상(공통 + 현재 프로젝트)의 미완료 항목을 [(라벨, [items])] 로 반환한다."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return []

    active, _ = _split_active_archive(lines)
    common_items = []
    project_items = []
    for header, body in _parse_sections(active):
        items = [l.lstrip() for l in body if l.lstrip().startswith("- [ ]")]
        if not items:
            continue
        if _is_common(header):
            common_items.extend(items)
        else:
            try:
                same = os.path.abspath(header) == cwd_abs
            except Exception:
                same = False
            if same:
                project_items.extend(items)

    result = []
    if common_items:
        result.append((COMMON_KEY, common_items))
    if project_items:
        label = os.path.basename(cwd_abs.rstrip("/")) or cwd_abs
        result.append((label, project_items))
    return result


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
    path = _global_todo()

    # 1) 완료 항목 아카이브
    archive_completed(path)

    # 2) 경과 시간 계산 (아카이브 후, last-access 갱신 전)
    now = time.time()
    last = _read_last_access()
    elapsed_note = None
    if last is not None and (now - last) > THRESHOLD_SECONDS:
        elapsed_note = f"마지막 접속으로부터 {_format_elapsed(now - last)} 경과"
    _write_last_access(now)

    # 3) 표시 대상(공통 + 현재 프로젝트) 미완료 항목 수집
    cwd_abs = os.path.abspath(_project_dir(payload))
    display = collect_display(path, cwd_abs)
    total = sum(len(items) for _, items in display)

    if total == 0 and elapsed_note is None:
        return  # 보여줄 것 없음 - 조용히 종료

    parts = ["저장된 TODO 목록입니다. 세션을 시작하며 사용자에게 아래 내용을 보기 좋게 안내하세요."]
    if elapsed_note:
        parts.append(f"⏰ {elapsed_note}")
    if display:
        blocks = []
        for label, items in display:
            blocks.append(f"[{label}]\n" + "\n".join(items))
        parts.append("\n\n".join(blocks))
    else:
        parts.append("(현재 프로젝트/공통 미완료 TODO 없음)")
    parts.append(
        "TODO 관리: 모든 항목은 전역 ~/.claude/todo.md 한 파일에 저장되며 "
        "'## 공통' 과 '## <프로젝트 절대경로>' 섹션으로 분류됩니다. 추가 기본값은 현재 "
        "프로젝트 섹션이고, '공통/전역'이라고 하면 공통 섹션에 넣습니다. 완료(- [x])는 "
        "세션 시작/종료 시 자동 아카이브됩니다. 항목 끝의 (ctx: ...) 는 그 투두의 문맥 파일 "
        "경로(~/.claude/todo-context/ 기준)입니다. 해당 투두를 작업할 때 먼저 읽으세요."
    )
    parts.append(
        "완료 자동 제안: 사용자가 '완료'라고 말하지 않아도, 이번 프롬프트로 시작한 작업이 "
        "위 목록의 미완료 항목을 완성했다고 판단되면 응답을 마치기 전에 어느 항목인지 짚어 "
        "완료 처리를 제안하세요. 동의를 받은 뒤에만 해당 항목을 - [x] 로 바꿉니다(확인 없이 "
        "자동 체크하지 않음). 항목을 부분만 진척시켰거나 매칭이 모호하면 제안하지 않거나 "
        "후보를 제시해 되묻습니다."
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
    archive_completed(_global_todo())
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
