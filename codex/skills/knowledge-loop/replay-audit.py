#!/usr/bin/env python3
"""최신 Codex user root 세션을 원문 없이 읽기 전용 집계한다."""

# usage-stats: harness session-replay-audit
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


INJECTED = re.compile(r"^(?:# AGENTS\.md instructions\b|<developer\b|<environment_context>|<permissions\b|<collaboration_mode>|Message Type:\s*(?:NEW_TASK|MESSAGE|FINAL_ANSWER)\b)", re.IGNORECASE)
HEARTBEAT = re.compile(r"^\s*<heartbeat>.*?</heartbeat>\s*$", re.IGNORECASE | re.DOTALL)
CONTEXT_BLOCK = re.compile(r"<(in-app-browser-context|recommended_plugins|skill|environment_context|app-context)\b[^>]*>.*?</\1>", re.DOTALL)
QUESTION_REPLY = re.compile(r"<send_user_message_question_reply>\s*(.*?)\s*</send_user_message_question_reply>", re.DOTALL)
CORRECTION = re.compile(r"(?:아니|말고|잘못|틀렸|다시|왜 .*했|하지 말|no,|instead)", re.IGNORECASE)
SECRET = re.compile(r"(?:sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|gh[posru]_[A-Za-z0-9]{36,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
ROLLOUT_TIMESTAMP = re.compile(r"^rollout-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})-")


def record_usage() -> None:
    subprocess.run(
        ["python3", str(Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"), "record", "harness", "session-replay-audit"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )


def text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", "")) for item in content
            if isinstance(item, dict) and item.get("type") in {"input_text", "text"}
        )
    return ""


def human_text(text: str) -> str:
    """주입 문맥을 걷어내되 함께 전달된 실제 요청과 사용자 답변은 보존한다."""
    if INJECTED.match(text.strip()) and not text.lstrip().startswith("<environment_context>"):
        return ""
    if HEARTBEAT.match(text):
        return ""
    text = CONTEXT_BLOCK.sub("", text).strip()
    if INJECTED.match(text) or text.startswith(("<subagent_notification", "<turn_aborted")):
        return ""
    def answers(match):
        try:
            rows = json.loads(match.group(1))
        except (TypeError, json.JSONDecodeError):
            return ""
        if not isinstance(rows, list):
            return ""
        return "\n".join(row["answer"] for row in rows if isinstance(row, dict) and isinstance(row.get("answer"), str))
    text = QUESTION_REPLY.sub(answers, text)
    if text.startswith(("# Files mentioned by the user:", "# Files pasted by the user:")):
        parts = re.split(r"## My request(?: for Codex)?:", text, maxsplit=1)
        text = parts[1] if len(parts) == 2 else ""
    text = re.sub(r"<image\b[^>]*>.*?</image>", "", text, flags=re.DOTALL)
    return text.strip()


def is_human_message(text: str) -> bool:
    return bool(human_text(text))


def session_metadata(path: Path):
    try:
        with path.open(errors="replace") as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and item.get("type") == "session_meta":
                    return item.get("payload") or {}
    except OSError:
        pass
    return None


def is_user_root(meta) -> bool:
    return isinstance(meta, dict) and meta.get("thread_source") == "user" and not meta.get("parent_thread_id") and not isinstance(meta.get("source"), dict)


def load_session(path: Path):
    return load_segments([path])


def load_segments(paths: list[Path]):
    """동일 root의 로컬 분할 파일을 합산한다. 다른 root의 상속 이력은 펼치지 않는다."""
    meta = session_metadata(paths[0])
    if not is_user_root(meta):
        return None
    messages = []
    aborted = tool_calls = commits = 0
    duplicates = ignored = history_bases = malformed = 0
    read_fingerprints = Counter()
    seen_in_prior_files = set()
    for path in paths:
        segment_meta = session_metadata(path) or {}
        history_bases += bool(segment_meta.get("history_base"))
        file_fingerprints = set()
        with path.open(errors="replace") as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if not isinstance(item, dict):
                    continue
                payload = item.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                abort = item.get("type") == "event_msg" and payload.get("type") == "turn_aborted"
                response = item.get("type") == "response_item"
                user = response and payload.get("type") == "message" and payload.get("role") == "user"
                tool = response and payload.get("type") in {"custom_tool_call", "function_call"}
                if not (abort or user or tool):
                    continue
                fingerprint = hashlib.sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                file_fingerprints.add(fingerprint)
                if fingerprint in seen_in_prior_files:
                    duplicates += 1
                    continue
                if abort:
                    aborted += 1
                if user:
                    text = human_text(text_content(payload.get("content")))
                    if text:
                        messages.append(text)
                    else:
                        ignored += 1
                if tool:
                    tool_calls += 1
                    arguments = payload.get("input") or payload.get("arguments") or {}
                    if not isinstance(arguments, str):
                        arguments = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
                    if re.search(r"\bgit\s+commit\b", arguments):
                        commits += 1
                    if re.search(r'"(?:cmd|command)"\s*:\s*"(?:git status|rg |sed -n|find |ls )', arguments):
                        read_fingerprints[hashlib.sha256(arguments.encode()).hexdigest()] += 1
        seen_in_prior_files.update(file_fingerprints)
    project = hashlib.sha256(str(meta.get("cwd", "?")).encode()).hexdigest()[:8]
    return {
        "session_key": str(meta.get("id") or meta.get("session_id") or ""),
        "messages": len(messages),
        "corrections": sum(bool(CORRECTION.search(message)) for message in messages),
        "aborted": aborted,
        "commits": commits,
        "tool_calls": tool_calls,
        "repeated_reads": sum(count - 1 for count in read_fingerprints.values() if count > 1),
        "project": project,
        "contains_secret": any(SECRET.search(message) for message in messages),
        "segments": len(paths),
        "duplicate_records_ignored": duplicates,
        "ignored_user_wrappers": ignored,
        "history_base_segments": history_bases,
        "malformed_lines": malformed,
    }


def rollout_order(path: Path) -> tuple[str, str]:
    match = ROLLOUT_TIMESTAMP.match(path.name)
    return (match.group(1) if match else "", path.name)


def select_sessions(roots: Path | list[Path], latest: int, session_id: str | None = None, session_ids: set[str] | None = None):
    if isinstance(roots, Path):
        roots = [roots]
    paths = {path for root in roots if root.exists() for path in root.rglob("*.jsonl")}
    grouped = {}
    for path in sorted(paths, key=rollout_order, reverse=True):
        meta = session_metadata(path)
        if not is_user_root(meta):
            continue
        key = str(meta.get("id") or meta.get("session_id") or str(path.resolve()))
        if session_id and key != session_id:
            continue
        if session_ids is not None and key not in session_ids:
            continue
        grouped.setdefault(key, []).append(path)
    groups = list(grouped.values())
    if session_ids is None:
        groups = groups[:1 if session_id else latest]
    return [load_segments(sorted(group, key=rollout_order)) for group in groups]


def report(sessions: list[dict]) -> dict:
    projects = Counter(session["project"] for session in sessions)
    return {
        "sessions": len(sessions),
        "human_messages": sum(item["messages"] for item in sessions),
        "correction_signals": sum(item["corrections"] for item in sessions),
        "turn_aborted": sum(item["aborted"] for item in sessions),
        "commit_command_candidates": sum(item["commits"] for item in sessions),
        "tool_calls": sum(item["tool_calls"] for item in sessions),
        "repeated_read_candidates": sum(item["repeated_reads"] for item in sessions),
        "projects": [{"anonymous_project": key, "sessions": value} for key, value in projects.most_common()],
        "sessions_with_secret_candidates": sum(item["contains_secret"] for item in sessions),
        **{key: sum(item[key] for item in sessions) for key in ("segments", "duplicate_records_ignored", "ignored_user_wrappers", "history_base_segments", "malformed_lines")},
    }


def self_test() -> None:
    assert human_text('<skill>다시 하지 말고 확인</skill>') == ''
    assert human_text('<in-app-browser-context source="ambient-ui-state">다시 확인</in-app-browser-context>\n실제 요청') == '실제 요청'
    assert human_text('<recommended_plugins>다시 확인</recommended_plugins>\n# AGENTS.md instructions for /tmp') == ''
    assert human_text('<send_user_message_question_reply>[{"question":"다시 바꿀까요?","answer":"네"}]</send_user_message_question_reply>') == '네'
    assert human_text('# Files mentioned by the user:\n/path\n## My request:\n본문은 내가 작성할게') == '본문은 내가 작성할게'
    assert human_text('아니 이 부분은 내가 작성할게') == '아니 이 부분은 내가 작성할게'
    assert human_text('<environment_context>설정</environment_context>\n진짜 요청') == '진짜 요청'
    assert human_text('<send_user_message_question_reply>broken</send_user_message_question_reply>') == ''
    assert not is_user_root(['invalid metadata'])
    fake = "sk-" + "B" * 32
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        sessions = root / "sessions"
        archived = root / "archived_sessions"
        sessions.mkdir()
        archived.mkdir()
        rows = [
            {"type": "session_meta", "payload": {"id": "root", "thread_source": "user", "source": "cli", "cwd": "/private/project"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md instructions for /tmp"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "<heartbeat>continue</heartbeat>"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Message Type: NEW_TASK\nTask name: /root/subagent"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "첫 요청"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "둘째 요청"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "아니 다시 확인 " + fake}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "넷째 요청"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "다섯째 요청"}]}},
            {"type": "event_msg", "payload": {"type": "turn_aborted"}},
            {"type": "event_msg", "payload": {"type": "turn_aborted"}},
            {"type": "event_msg", "payload": {"type": "task_complete", "last_agent_message": "turn_aborted"}},
        ]
        encoded_rows = "\n".join(json.dumps(row) for row in rows)
        (sessions / "rollout-2026-01-02T00-00-00-root.jsonl").write_text(encoded_rows)
        (archived / "rollout-2026-01-02T00-00-01-root-copy.jsonl").write_text(encoded_rows)
        subagent = sessions / "rollout-2026-01-03T00-00-00-subagent.jsonl"
        subagent.write_text(json.dumps({"type": "session_meta", "payload": {"id": "sub", "thread_source": "subagent", "parent_thread_id": "root", "source": {"subagent": {}}, "cwd": "/private/project"}}))
        selected = select_sessions([sessions, archived], 10)
        result = report(selected)
        encoded = json.dumps(result)
        assert result["sessions"] == 1
        assert result["human_messages"] == 5
        assert result["turn_aborted"] == 2
        assert result["correction_signals"] == 1
        assert fake not in encoded and "/private/project" not in encoded

        segment = sessions / 'rollout-2026-01-04T00-00-00-root-part2.jsonl'
        continuation = [
            {"type":"session_meta", "payload":{"id":"root", "thread_source":"user", "source":"cli", "cwd":"/private/project", "history_base":{"thread_id":"root"}}},
            rows[4],
            {"timestamp":"2026-01-04T00:00:01Z", "type":"response_item", "payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"<skill>아니 다시</skill>"}]}},
            {"timestamp":"2026-01-04T00:00:02Z", "type":"response_item", "payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"<in-app-browser-context>다시</in-app-browser-context>\n새 요청"}]}},
            {"timestamp":"2026-01-04T00:00:03Z", "type":"response_item", "payload":{"type":"function_call","name":"exec_command","arguments":"{\"cmd\":\"git commit -m example\"}"}},
        ]
        segment.write_text('\n'.join(json.dumps(row) for row in continuation)+'\n{incomplete')
        combined = report(select_sessions([sessions, archived], 10))
        assert combined['sessions'] == 1 and combined['segments'] == 3
        assert combined['human_messages'] == 6 and combined['correction_signals'] == 1
        assert combined['turn_aborted'] == 2 and combined['tool_calls'] == 1
        assert combined['commit_command_candidates'] == 1
        assert combined['duplicate_records_ignored'] > 0 and combined['malformed_lines'] == 1
        assert combined['history_base_segments'] == 1
        assert not select_sessions([sessions, archived], 10, session_ids={'absent'})

        ordered = root / "ordered"
        ordered.mkdir()
        old = ordered / "rollout-2025-01-01T00-00-00-old.jsonl"
        new = ordered / "rollout-2026-01-01T00-00-00-new.jsonl"
        old.write_text(json.dumps({"type": "session_meta", "payload": {"id": "old", "thread_source": "user", "source": "cli", "cwd": "/old"}}))
        new.write_text(json.dumps({"type": "session_meta", "payload": {"id": "new", "thread_source": "user", "source": "cli", "cwd": "/new"}}))
        os.utime(old, (2, 2))
        os.utime(new, (1, 1))
        assert select_sessions(ordered, 1)[0]["session_key"] == "new"
        assert len(select_sessions(ordered, 1, session_ids={'old','new'})) == 2
        repeated = root / 'rollout-2026-01-05T00-00-00-repeated.jsonl'
        repeated.write_text('\n'.join(json.dumps(row) for row in [rows[0], rows[4], rows[4]]))
        assert load_session(repeated)['messages'] == 2
    print("session_replay_audit: ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex user root 세션 익명 replay audit")
    parser.add_argument("--latest", type=int, default=100)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--session-id", help="root session id 한 건 선택")
    selection.add_argument("--session-ids-file", type=Path, help="조사 대상을 고정한 JSON 문자열 배열 파일")
    selection.add_argument("--current", action="store_true", help="가장 최근 rollout 파일의 user root 한 건 선택 (호출 중 세션과 다를 수 있음)")
    parser.add_argument("--sessions-dir", type=Path, action="append", help="세션 디렉터리, 반복 지정 가능")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.latest < 1:
        parser.error("--latest must be positive")
    ids = None
    if args.session_ids_file:
        try:
            ids = json.loads(args.session_ids_file.read_text())
        except (OSError, json.JSONDecodeError):
            parser.error("session ids file must contain a JSON array")
        if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item for item in ids):
            parser.error("session ids must be a nonempty array of nonempty strings")
        ids = set(ids)
    roots = args.sessions_dir or [Path.home() / ".codex/sessions", Path.home() / ".codex/archived_sessions"]
    record_usage()
    result = report(select_sessions(roots, 1 if args.current else args.latest, args.session_id, ids))
    if ids is not None:
        result.update(requested_sessions=len(ids), missing_sessions=len(ids)-result['sessions'])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
