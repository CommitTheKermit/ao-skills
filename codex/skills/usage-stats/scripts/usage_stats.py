#!/usr/bin/env python3
"""Count and report personal Codex skill, hook, and harness usage."""

import argparse
import fcntl
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


KINDS = ("skill", "hook", "harness")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
MARKER_RE = re.compile(r"usage-stats:\s+(skill|hook|harness)\s+([A-Za-z0-9][A-Za-z0-9._:-]*)")
SCAN_SUFFIXES = {".md", ".py", ".sh", ".mjs"}


def data_path():
    return Path.home() / ".Codex" / "usage-stats.json"


def _load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "items": {}}
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"cannot read usage data without risking data loss: {path}") from error
    if data.get("version") != 1 or not isinstance(data.get("items"), dict):
        raise RuntimeError(f"unsupported usage data format: {path}")
    return data


def _locked(path, operation):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        return operation(_load(path))


def record(path, kind, name, now=None):
    if kind not in KINDS or not NAME_RE.fullmatch(name):
        raise ValueError("kind or name is invalid")
    timestamp = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def update(data):
        key = f"{kind}:{name}"
        item = data["items"].setdefault(key, {"count": 0, "first_used_at": timestamp})
        item["count"] += 1
        item["last_used_at"] = timestamp
        fd, tmp_name = tempfile.mkstemp(prefix=".usage-stats-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=2, sort_keys=True)
                tmp.write("\n")
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    _locked(path, update)


def discover(root):
    items = set()
    if not root.is_dir():
        return items
    for path in root.rglob("*"):
        try:
            if path.name.startswith("test_") or path.suffix not in SCAN_SUFFIXES or path.stat().st_size > 1_000_000:
                continue
            for kind, name in MARKER_RE.findall(path.read_text(encoding="utf-8")):
                items.add((kind, name))
        except (OSError, UnicodeError):
            continue
    return items


def rows(path, root, kind_filter=None):
    data = _locked(path, lambda current: current)
    registered = discover(root)
    recorded = {tuple(key.split(":", 1)) for key in data["items"] if ":" in key}
    result = []
    for kind, name in registered | recorded:
        if kind_filter and kind != kind_filter:
            continue
        item = data["items"].get(f"{kind}:{name}", {})
        result.append({
            "kind": kind,
            "name": name,
            "count": item.get("count", 0),
            "first_used_at": item.get("first_used_at", "-"),
            "last_used_at": item.get("last_used_at", "-"),
        })
    return sorted(result, key=lambda item: (-item["count"], item["kind"], item["name"].lower()))


def print_table(items):
    headers = ("COUNT", "KIND", "NAME", "FIRST USED (UTC)", "LAST USED (UTC)")
    values = [
        (str(item["count"]), item["kind"], item["name"], item["first_used_at"], item["last_used_at"])
        for item in items
    ]
    widths = [max(len(headers[i]), *(len(row[i]) for row in values)) if values else len(headers[i]) for i in range(len(headers))]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in values:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("kind", choices=KINDS)
    record_parser.add_argument("name")
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--kind", choices=KINDS)
    report_parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "record":
        record(data_path(), args.kind, args.name)
        return

    items = rows(data_path(), Path.home() / ".agents" / "skills", args.kind)
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print_table(items)


if __name__ == "__main__":
    main()
