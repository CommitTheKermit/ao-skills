#!/usr/bin/env python3
"""세션 시작/종료 시 TODO 를 관리하는 Claude Code 훅 스크립트.

사용법:
    todo-session.py start   # SessionStart 훅: 완료 항목 날짜 스탬프 + 현재 프로젝트/공통 미완료 항목을 context 로 노출
    todo-session.py end     # SessionEnd 훅: 완료 항목 날짜 스탬프만 수행

대상 파일:
    - 전역 단일 파일: ~/.claude/todo.md  (모든 항목이 여기 한 곳에 저장된다)

파일 구조:
    # TODO

    ## 공통
    - [ ] 어디서나 보이는 항목

    ## /절대/프로젝트/경로
    - [ ] 그 프로젝트에서만 보이는 항목
    - [x] 완료 항목  (done YYYY-MM-DD)   <- 완료해도 이 섹션에 그대로 남는다

    ## Done (archive)                    <- 과거 평평하게 쌓였던 완료 항목의 레거시 보관소
    ### (미분류)
    - [x] 지난 완료 항목  (archived YYYY-MM-DD)

설계 원칙:
    - 훅이 세션을 막으면 안 되므로 어떤 예외에도 exit 0 으로 끝낸다.
    - 완료(- [x]) 항목은 옮기지 않는다. 원래 프로젝트 섹션에 그대로 두고
      (done YYYY-MM-DD) 날짜 스탬프만 한 번 붙인다(프로젝트별 구분이 그대로 유지됨).
    - "## Done (archive)" 는 과거 flat 아카이브의 레거시 보관소다. 새 완료는 여기로
      이동하지 않는다. 헤더 없이 평평하게 쌓여 있던 기존 항목은 한 번 "### (미분류)"
      하위섹션으로 묶어 보존한다.
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
UNCLASSIFIED_HEADER = "### (미분류)"
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
    """라인들을 (활성 영역, 아카이브 영역) 으로 나눈다.

    아카이브 영역은 "## Done (archive)" 헤더 **다음** 라인들. 헤더가 없으면 두 번째 값은 None.
    """
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


def _stamp_completed(active_lines, today):
    """활성 영역의 완료(- [x]) 항목 중 날짜 스탬프가 없는 것에 (done DATE) 를 붙인다.

    이미 (done ...) 또는 (archived ...) 가 붙어 있으면 건드리지 않는다(중복 방지).
    """
    out = []
    changed = False
    for line in active_lines:
        stripped = line.lstrip()
        if (
            (stripped.startswith("- [x]") or stripped.startswith("- [X]"))
            and "(done " not in line
            and "(archived " not in line
        ):
            out.append(f"{line.rstrip()}  (done {today})")
            changed = True
        else:
            out.append(line)
    return out, changed


def _migrate_legacy_archive(archive_lines):
    """레거시 flat 아카이브 항목을 한 번 '### (미분류)' 하위섹션으로 묶는다.

    이미 어떤 '### ' 하위섹션이 있으면(이미 마이그레이션됨) 건드리지 않는다.
    """
    if any(l.startswith("### ") for l in archive_lines):
        return archive_lines, False
    if not any(
        l.lstrip().startswith(("- [ ]", "- [x]", "- [X]")) for l in archive_lines
    ):
        return archive_lines, False  # 묶을 항목이 없음
    body = list(archive_lines)
    while body and body[0].strip() == "":
        body.pop(0)
    return ["", UNCLASSIFIED_HEADER, ""] + body, True


def process_todo(path):
    """완료 항목 날짜 스탬프 + 레거시 아카이브 1회 마이그레이션.

    완료 항목은 옮기지 않고 원래 섹션에 그대로 둔다. 변경이 있을 때만 파일을 재작성한다.
    """
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return

    active, archive = _split_active_archive(lines)
    today = date.today().isoformat()

    active, stamped = _stamp_completed(active, today)
    migrated = False
    if archive is not None:
        archive, migrated = _migrate_legacy_archive(archive)

    if not (stamped or migrated):
        return  # 변경 없음 - 파일을 건드리지 않는다

    out = list(active)
    while out and out[-1].strip() == "":
        out.pop()
    if archive is not None:
        out.append("")
        out.append(ARCHIVE_HEADER)
        out.extend(archive)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out).rstrip() + "\n")
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

    # 1) 완료 항목 날짜 스탬프 + 레거시 아카이브 마이그레이션
    process_todo(path)

    # 2) 경과 시간 계산 (처리 후, last-access 갱신 전)
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
        "프로젝트 섹션이고, '공통/전역'이라고 하면 공통 섹션에 넣습니다. 완료(- [x]) 항목은 "
        "원래 프로젝트 섹션에 그대로 남고(별도 아카이브로 이동하지 않음), 세션 시작/종료 시 "
        "완료 날짜((done ...))가 자동으로 기록됩니다. 항목 끝의 (ctx: ...) 는 그 투두의 문맥 "
        "파일 경로(~/.claude/todo-context/ 기준)입니다. 해당 투두를 작업할 때 먼저 읽으세요."
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
    process_todo(_global_todo())
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
