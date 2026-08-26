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


def is_human_message(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and not INJECTED.match(stripped) and not HEARTBEAT.match(stripped)


def load_session(path: Path):
    records = []
    try:
        for line in path.open(errors="replace"):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return None
    meta_record = next((item for item in records if item.get("type") == "session_meta"), None)
    if not meta_record:
        return None
    meta = meta_record.get("payload") or {}
    if meta.get("thread_source") != "user" or meta.get("parent_thread_id") or isinstance(meta.get("source"), dict):
        return None
    messages = []
    aborted = tool_calls = commits = 0
    read_fingerprints = Counter()
    for item in records:
        payload = item.get("payload") or {}
        if item.get("type") == "event_msg" and payload.get("type") == "turn_aborted":
            aborted += 1
        if item.get("type") != "response_item":
            continue
        if payload.get("type") == "message" and payload.get("role") == "user":
            text = text_content(payload.get("content"))
            if is_human_message(text):
                messages.append(text)
        if payload.get("type") == "custom_tool_call":
            tool_calls += 1
            arguments = json.dumps(payload.get("input") or payload.get("arguments") or {}, sort_keys=True, ensure_ascii=False)
            if "git commit" in arguments:
                commits += 1
            if re.search(r'"(?:cmd|command)"\s*:\s*"(?:git status|rg |sed -n|find |ls )', arguments):
                read_fingerprints[hashlib.sha256(arguments.encode()).hexdigest()] += 1
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
    }


def rollout_order(path: Path) -> tuple[str, str]:
    match = ROLLOUT_TIMESTAMP.match(path.name)
    return (match.group(1) if match else "", path.name)


def select_sessions(roots: Path | list[Path], latest: int, session_id: str | None = None):
    if isinstance(roots, Path):
        roots = [roots]
    paths = {path for root in roots if root.exists() for path in root.rglob("*.jsonl")}
    selected = []
    seen = set()
    for path in sorted(paths, key=rollout_order, reverse=True):
        session = load_session(path)
        if not session:
            continue
        if session_id and session["session_key"] != session_id:
            continue
        key = session["session_key"] or str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        selected.append(session)
        if len(selected) >= (1 if session_id else latest):
            break
    return selected


def report(sessions: list[dict]) -> dict:
    projects = Counter(session["project"] for session in sessions)
    return {
        "sessions": len(sessions),
        "human_messages": sum(item["messages"] for item in sessions),
        "correction_signals": sum(item["corrections"] for item in sessions),
        "turn_aborted": sum(item["aborted"] for item in sessions),
        "commits": sum(item["commits"] for item in sessions),
        "tool_calls": sum(item["tool_calls"] for item in sessions),
        "repeated_read_candidates": sum(item["repeated_reads"] for item in sessions),
        "projects": [{"anonymous_project": key, "sessions": value} for key, value in projects.most_common()],
        "secret_bearing_messages_redacted": sum(item["contains_secret"] for item in sessions),
    }


def self_test() -> None:
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

        ordered = root / "ordered"
        ordered.mkdir()
        old = ordered / "rollout-2025-01-01T00-00-00-old.jsonl"
        new = ordered / "rollout-2026-01-01T00-00-00-new.jsonl"
        old.write_text(json.dumps({"type": "session_meta", "payload": {"id": "old", "thread_source": "user", "source": "cli", "cwd": "/old"}}))
        new.write_text(json.dumps({"type": "session_meta", "payload": {"id": "new", "thread_source": "user", "source": "cli", "cwd": "/new"}}))
        os.utime(old, (2, 2))
        os.utime(new, (1, 1))
        assert select_sessions(ordered, 1)[0]["session_key"] == "new"
    print("session_replay_audit: ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex user root 세션 익명 replay audit")
    parser.add_argument("--latest", type=int, default=100)
    parser.add_argument("--session-id", help="현재 root session id 한 건 선택")
    parser.add_argument("--current", action="store_true", help="가장 최근 user root session 한 건 선택")
    parser.add_argument("--sessions-dir", type=Path, action="append", help="세션 디렉터리, 반복 지정 가능")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.latest < 1:
        parser.error("--latest must be positive")
    if args.current and args.session_id:
        parser.error("--current and --session-id are mutually exclusive")
    roots = args.sessions_dir or [Path.home() / ".codex/sessions", Path.home() / ".codex/archived_sessions"]
    record_usage()
    print(json.dumps(report(select_sessions(roots, 1 if args.current else args.latest, args.session_id)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
