#!/usr/bin/env python3
"""에이전트 세션별 Android AVD 임대를 관리한다."""

# usage-stats: harness android-emulator-lease
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Callable


LEASE_TTL_SECONDS = 15 * 60
AVD_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
SERIAL_NAME = re.compile(r"^[A-Za-z0-9._:-]+$")


class LeaseError(RuntimeError):
    pass


def record_usage() -> None:
    subprocess.run(
        [
            "python3",
            str(Path.home() / ".claude/skills/usage-stats/scripts/usage_stats.py"),
            "record",
            "harness",
            "android-emulator-lease",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def lease_directory() -> Path:
    override = os.environ.get("CODEX_ANDROID_LEASE_DIR")
    return Path(override).expanduser() if override else Path.home() / ".codex/android-emulator-leases"


def current_owner() -> str:
    owner = (
        os.environ.get("CLAUDE_CODE_SESSION_ID")
        or os.environ.get("CODEX_THREAD_ID")
        or os.environ.get("CODEX_SESSION_ID")
    )
    if not owner:
        raise LeaseError("CLAUDE_CODE_SESSION_ID, CODEX_THREAD_ID, CODEX_SESSION_ID가 모두 없어 임대 소유자를 구분할 수 없습니다.")
    return owner


def validate_avd(avd: str) -> str:
    if not AVD_NAME.fullmatch(avd):
        raise LeaseError(f"유효하지 않은 AVD 이름입니다: {avd}")
    return avd


def validate_serial(serial: str) -> str:
    if not SERIAL_NAME.fullmatch(serial):
        raise LeaseError(f"유효하지 않은 device serial입니다: {serial}")
    return serial


def lease_path(avd: str, directory: Path | None = None) -> Path:
    return (directory or lease_directory()) / f"{validate_avd(avd)}.json"


def read_lease(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as error:
        raise LeaseError(f"임대 파일을 읽을 수 없습니다: {path}: {error}") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise LeaseError(f"지원하지 않는 임대 파일입니다: {path}")
    return data


def write_new_lease(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise
    with os.fdopen(descriptor, "w") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def replace_lease(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def running_avds() -> set[str]:
    completed = subprocess.run(
        ["ps", "-axo", "command="],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    if completed.returncode != 0:
        return set()
    return {
        match.group(1)
        for line in completed.stdout.splitlines()
        if "qemu-system" in line or "/emulator" in line
        for match in [re.search(r"@([A-Za-z0-9._-]+)(?:\s|$)", line)]
        if match
    }


def connected_avd(serial: str) -> str | None:
    try:
        completed = subprocess.run(
            ["adb", "-s", serial, "emu", "avd", "name"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip().splitlines()
    return value[0].strip() if value else None


def timestamp(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).isoformat()


def lease_active(
    lease: dict,
    *,
    now: float | None = None,
    active_avds: set[str] | None = None,
    serial_lookup: Callable[[str], str | None] = connected_avd,
) -> bool:
    current_time = time.time() if now is None else now
    if lease.get("avd") in (running_avds() if active_avds is None else active_avds):
        return True
    serial = lease.get("serial")
    if isinstance(serial, str) and serial_lookup(serial) == lease.get("avd"):
        return True
    try:
        updated = float(lease.get("updated_epoch", lease.get("created_epoch")))
    except (TypeError, ValueError):
        return False
    return current_time - updated <= LEASE_TTL_SECONDS


def new_record(avd: str, owner: str, serial: str | None, now: float, workspace: str) -> dict:
    return {
        "version": 1,
        "avd": avd,
        "serial": serial,
        "owner": owner,
        "session": os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_SESSION_ID"),
        "workspace": workspace,
        "created_at": timestamp(now),
        "created_epoch": now,
        "updated_at": timestamp(now),
        "updated_epoch": now,
    }


def acquire_lease(
    avd: str,
    serial: str | None = None,
    *,
    directory: Path | None = None,
    owner: str | None = None,
    now: float | None = None,
    active_avds: set[str] | None = None,
    serial_lookup: Callable[[str], str | None] = connected_avd,
    allow_running_without_lease: bool = False,
) -> dict:
    avd = validate_avd(avd)
    serial = validate_serial(serial) if serial else None
    owner = owner or current_owner()
    current_time = time.time() if now is None else now
    directory = directory or lease_directory()
    path = lease_path(avd, directory)
    workspace = str(Path.cwd().resolve())
    running = running_avds() if active_avds is None else active_avds
    if serial:
        actual_avd = serial_lookup(serial)
        if actual_avd and actual_avd != avd:
            raise LeaseError(f"{serial}은 {actual_avd} AVD이며 요청한 {avd}와 다릅니다.")

    for _ in range(3):
        existing = read_lease(path)
        if existing:
            if existing.get("owner") == owner:
                existing.update(
                    serial=serial or existing.get("serial"),
                    workspace=workspace,
                    updated_at=timestamp(current_time),
                    updated_epoch=current_time,
                )
                replace_lease(path, existing)
                return existing
            if lease_active(
                existing,
                now=current_time,
                active_avds=running,
                serial_lookup=serial_lookup,
            ):
                raise LeaseError(
                    f"{avd}는 다른 에이전트 세션이 사용 중입니다. 다른 AVD를 선택하거나 임대가 해제될 때까지 기다리세요."
                )
            path.unlink(missing_ok=True)

        if avd in running and not allow_running_without_lease:
            raise LeaseError(
                f"{avd}는 임대 없이 이미 실행 중이라 소유자를 확인할 수 없습니다. 사용하거나 종료하지 말고 다른 AVD를 선택하세요."
            )

        record = new_record(avd, owner, serial, current_time, workspace)
        try:
            write_new_lease(path, record)
            return record
        except FileExistsError:
            continue
    raise LeaseError(f"{avd} 임대를 동시에 갱신하는 세션이 있어 획득하지 못했습니다.")


def adopt_lease(
    avd: str,
    serial: str,
    *,
    directory: Path | None = None,
    owner: str | None = None,
    active_avds: set[str] | None = None,
    serial_lookup: Callable[[str], str | None] = connected_avd,
) -> dict:
    avd = validate_avd(avd)
    serial = validate_serial(serial)
    actual_avd = serial_lookup(serial)
    if actual_avd != avd:
        raise LeaseError(f"{serial}의 AVD는 {actual_avd or '확인 불가'}이며 요청한 {avd}와 다릅니다.")
    return acquire_lease(
        avd,
        serial,
        directory=directory,
        owner=owner,
        active_avds=active_avds,
        serial_lookup=serial_lookup,
        allow_running_without_lease=True,
    )


def bind_lease(avd: str, serial: str, *, directory: Path | None = None, owner: str | None = None) -> dict:
    avd = validate_avd(avd)
    serial = validate_serial(serial)
    owner = owner or current_owner()
    path = lease_path(avd, directory)
    lease = read_lease(path)
    if not lease or lease.get("owner") != owner:
        raise LeaseError(f"현재 세션이 {avd}를 임대하지 않았습니다.")
    actual_avd = connected_avd(serial)
    if actual_avd != avd:
        raise LeaseError(f"{serial}의 AVD는 {actual_avd or '확인 불가'}이며 요청한 {avd}와 다릅니다.")
    now = time.time()
    lease.update(serial=serial, updated_at=timestamp(now), updated_epoch=now, workspace=str(Path.cwd().resolve()))
    replace_lease(path, lease)
    return lease


def release_lease(
    avd: str,
    *,
    directory: Path | None = None,
    owner: str | None = None,
    active_avds: set[str] | None = None,
    serial_lookup: Callable[[str], str | None] = connected_avd,
) -> None:
    avd = validate_avd(avd)
    owner = owner or current_owner()
    path = lease_path(avd, directory)
    lease = read_lease(path)
    if not lease:
        return
    if lease.get("owner") != owner:
        raise LeaseError(f"다른 에이전트 세션이 소유한 {avd} 임대는 해제할 수 없습니다.")
    running = running_avds() if active_avds is None else active_avds
    serial = lease.get("serial")
    if avd in running or (isinstance(serial, str) and serial_lookup(serial) == avd):
        raise LeaseError(f"{avd}가 아직 실행 중입니다. 현재 세션이 종료한 뒤 임대를 해제하세요.")
    path.unlink(missing_ok=True)


def all_leases(directory: Path | None = None) -> list[dict]:
    directory = directory or lease_directory()
    leases = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        lease = read_lease(path)
        if lease:
            leases.append(lease)
    return leases


def prune_leases(directory: Path | None = None) -> list[str]:
    directory = directory or lease_directory()
    active = running_avds()
    removed = []
    for lease in all_leases(directory):
        if not lease_active(lease, active_avds=active):
            lease_path(str(lease["avd"]), directory).unlink(missing_ok=True)
            removed.append(str(lease["avd"]))
    return removed


def print_lease(lease: dict) -> None:
    owner = str(lease.get("owner") or "unknown")
    print(
        f"{lease.get('avd')}\tserial={lease.get('serial') or '-'}\t"
        f"owner={owner[:12]}\tworkspace={lease.get('workspace') or '-'}"
    )


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        lookup = lambda serial: "Pixel_Test" if serial == "emulator-5554" else None
        first = acquire_lease(
            "Pixel_Test",
            directory=directory,
            owner="thread-a",
            now=1000,
            active_avds=set(),
            serial_lookup=lambda _: None,
        )
        assert first["owner"] == "thread-a"
        renewed = acquire_lease(
            "Pixel_Test",
            "emulator-5554",
            directory=directory,
            owner="thread-a",
            now=1010,
            active_avds=set(),
            serial_lookup=lookup,
        )
        assert renewed["serial"] == "emulator-5554"
        try:
            acquire_lease(
                "Pixel_Test",
                directory=directory,
                owner="thread-b",
                now=1020,
                active_avds=set(),
                serial_lookup=lookup,
            )
            raise AssertionError("active lease must not be stolen")
        except LeaseError:
            pass
        release_lease(
            "Pixel_Test",
            directory=directory,
            owner="thread-a",
            active_avds=set(),
            serial_lookup=lambda _: None,
        )
        assert not lease_path("Pixel_Test", directory).exists()
        acquire_lease(
            "Stale_Test",
            directory=directory,
            owner="thread-a",
            now=1,
            active_avds=set(),
            serial_lookup=lambda _: None,
        )
        stolen = acquire_lease(
            "Stale_Test",
            directory=directory,
            owner="thread-b",
            now=LEASE_TTL_SECONDS + 2,
            active_avds=set(),
            serial_lookup=lambda _: None,
        )
        assert stolen["owner"] == "thread-b"
        try:
            acquire_lease(
                "Running_Test",
                directory=directory,
                owner="thread-a",
                now=2000,
                active_avds={"Running_Test"},
                serial_lookup=lambda _: None,
            )
            raise AssertionError("running unleased AVD must not be acquired")
        except LeaseError:
            pass
        adopted = adopt_lease(
            "Running_Test",
            "emulator-5556",
            directory=directory,
            owner="thread-a",
            active_avds={"Running_Test"},
            serial_lookup=lambda serial: "Running_Test" if serial == "emulator-5556" else None,
        )
        assert adopted["serial"] == "emulator-5556"
    print("android_emulator_lease: ok")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="에이전트 세션별 Android AVD 임대 관리")
    subparsers = root.add_subparsers(dest="command", required=True)
    acquire = subparsers.add_parser("acquire")
    acquire.add_argument("--avd", required=True)
    adopt = subparsers.add_parser("adopt")
    adopt.add_argument("--avd", required=True)
    adopt.add_argument("--serial", required=True)
    bind = subparsers.add_parser("bind")
    bind.add_argument("--avd", required=True)
    bind.add_argument("--serial", required=True)
    release = subparsers.add_parser("release")
    release.add_argument("--avd", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("prune")
    subparsers.add_parser("self-test")
    return root


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "self-test":
        self_test()
        return
    record_usage()
    try:
        if arguments.command == "acquire":
            print_lease(acquire_lease(arguments.avd))
        elif arguments.command == "adopt":
            print_lease(adopt_lease(arguments.avd, arguments.serial))
        elif arguments.command == "bind":
            print_lease(bind_lease(arguments.avd, arguments.serial))
        elif arguments.command == "release":
            release_lease(arguments.avd)
            print(f"released\t{arguments.avd}")
        elif arguments.command == "status":
            leases = all_leases()
            if not leases:
                print("no leases")
            for lease in leases:
                print_lease(lease)
        elif arguments.command == "prune":
            removed = prune_leases()
            print("removed\t" + (",".join(removed) if removed else "none"))
    except LeaseError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
