#!/usr/bin/env python3
"""소유권 없는 Android 에뮬레이터 조작을 실행 전에 차단한다."""

# usage-stats: hook android-emulator-lease-guard
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


LEASE_SCRIPT_NAME = "emulator_lease.py"
UNINSPECTABLE_ANDROID_COMMAND = "__UNINSPECTABLE_ANDROID_COMMAND__"
ANDROID_DEVICE_COMMANDS = {"layout", "run"}
ADB_NO_TARGET_COMMANDS = {"devices", "help", "start-server", "version"}


def record_usage() -> None:
    subprocess.run(
        [
            "python3",
            str(Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"),
            "record",
            "hook",
            "android-emulator-lease-guard",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def current_owner(payload: dict | None = None) -> str | None:
    owner = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if owner:
        return owner
    # PreToolUse는 실행 셸과 다른 환경에서 동작하므로 훅이 전달한 세션 ID도 사용한다.
    session_id = (payload or {}).get("session_id")
    return session_id if isinstance(session_id, str) and session_id.strip() else None


def lease_directory() -> Path:
    override = os.environ.get("CODEX_ANDROID_LEASE_DIR")
    return Path(override).expanduser() if override else Path.home() / ".codex/android-emulator-leases"


def leases(directory: Path | None = None) -> list[dict]:
    directory = directory or lease_directory()
    result = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("version") == 1:
            result.append(value)
    return result


def owns_avd(avd: str, owner: str | None, current_leases: list[dict]) -> bool:
    return bool(owner) and any(lease.get("avd") == avd and lease.get("owner") == owner for lease in current_leases)


def owns_serial(serial: str, owner: str | None, current_leases: list[dict]) -> bool:
    return bool(owner) and any(lease.get("serial") == serial and lease.get("owner") == owner for lease in current_leases)


def executable_name(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def shell_segments(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments = [[]]
    for token in tokens:
        if token and set(token) <= set(";&|"):
            if segments[-1]:
                segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def extract_commands(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    commands = [
        value
        for key, value in tool_input.items()
        if key in {"cmd", "command", "input"} and isinstance(value, str)
    ]
    code = tool_input.get("code")
    if isinstance(code, str):
        for match in re.finditer(r"\b(?:cmd|command)\s*:\s*(\"(?:\\.|[^\"\\])*\")", code, re.DOTALL):
            try:
                commands.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                continue
        nested_calls = len(re.findall(r"\btools\.exec_command\s*\(", code))
        if nested_calls > len(commands) and re.search(
            r"\b(?:adb|emulator|android|gradle|gradlew|qemu-system)\b",
            code,
            re.IGNORECASE,
        ):
            commands.append(UNINSPECTABLE_ANDROID_COMMAND)
    return list(dict.fromkeys(commands))


def assignment_serial(tokens: list[str], command: str) -> str | None:
    for token in tokens:
        if token.startswith("ANDROID_SERIAL="):
            return token.split("=", 1)[1]
    match = re.search(r"(?:^|\s)ANDROID_SERIAL=([A-Za-z0-9._:-]+)(?:\s|$)", command)
    return match.group(1) if match else None


def command_start(tokens: list[str]) -> int:
    index = 0
    if tokens and executable_name(tokens[0]) == "env":
        index = 1
    while index < len(tokens) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[index]):
        index += 1
    return index


def option_value(tokens: list[str], name: str) -> str | None:
    for index, token in enumerate(tokens):
        if token == name and index + 1 < len(tokens):
            return tokens[index + 1]
        if token.startswith(f"{name}="):
            return token.split("=", 1)[1]
    return None


def require_serial(serial: str | None, owner: str | None, current_leases: list[dict], action: str) -> str | None:
    if not serial:
        return f"{action}에는 대상 serial을 명시해야 합니다. adb -s <serial>, android --device=<serial>, 또는 ANDROID_SERIAL을 사용하세요."
    if serial.startswith("emulator-") and not owns_serial(serial, owner, current_leases):
        return f"{serial}은 현재 Codex 세션에 임대되지 않았습니다. android-emulator-lease의 acquire와 bind를 먼저 실행하세요."
    return None


def android_reason(tokens: list[str], owner: str | None, current_leases: list[dict]) -> str | None:
    try:
        emulator_index = tokens.index("emulator")
    except ValueError:
        emulator_index = -1
    if emulator_index >= 0 and emulator_index + 1 < len(tokens):
        action = tokens[emulator_index + 1]
        arguments = tokens[emulator_index + 2 :]
        if action == "start":
            avd = next((value for value in reversed(arguments) if not value.startswith("-")), None)
            if not avd:
                return "시작할 AVD 이름을 명시해야 합니다."
            if not owns_avd(avd, owner, current_leases):
                return f"{avd}는 현재 Codex 세션에 임대되지 않았습니다. 시작 전에 acquire를 실행하세요."
        if action == "stop":
            serial = next((value for value in reversed(arguments) if not value.startswith("-")), None)
            return require_serial(serial, owner, current_leases, "에뮬레이터 종료")
        return None

    subcommand = tokens[1] if len(tokens) > 1 else None
    if subcommand in ANDROID_DEVICE_COMMANDS or subcommand == "screen":
        if subcommand == "screen" and len(tokens) <= 2:
            return None
        return require_serial(option_value(tokens, "--device"), owner, current_leases, f"android {subcommand}")
    return None


def raw_emulator_reason(tokens: list[str], owner: str | None, current_leases: list[dict]) -> str | None:
    avd = option_value(tokens, "-avd")
    if not avd:
        avd = next((token[1:] for token in tokens if token.startswith("@") and len(token) > 1), None)
    if avd and not owns_avd(avd, owner, current_leases):
        return f"{avd}는 현재 Codex 세션에 임대되지 않았습니다. 시작 전에 acquire를 실행하세요."
    return None


def adb_reason(tokens: list[str], command: str, owner: str | None, current_leases: list[dict]) -> str | None:
    serial = option_value(tokens, "-s") or assignment_serial(tokens, command)
    arguments = tokens[1:]
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"-s", "-H", "-P", "-L"}:
            index += 2
        elif token in {"-d", "-e", "-a"}:
            index += 1
        else:
            break
    action = arguments[index] if index < len(arguments) else None
    if action in ADB_NO_TARGET_COMMANDS or action is None:
        return None
    if action in {"kill-server", "reconnect"}:
        return f"adb {action}는 다른 세션의 모든 기기 연결에 영향을 줄 수 있어 전역 가드가 차단합니다. 개별 serial 상태만 확인하세요."
    return require_serial(serial, owner, current_leases, f"adb {action}")


def gradle_reason(command: str, tokens: list[str], owner: str | None, current_leases: list[dict]) -> str | None:
    if not re.search(r"(?:^|\s)(?:\S*:)?(?:install[A-Za-z0-9_-]*|connected[A-Za-z0-9_-]*AndroidTest)(?:\s|$)", command):
        return None
    return require_serial(assignment_serial(tokens, command), owner, current_leases, "Gradle 설치 또는 연결 기기 테스트")


def avd_from_process_command(command: str) -> str | None:
    match = re.search(r"@([A-Za-z0-9._-]+)(?:\s|$)", command)
    return match.group(1) if match and ("qemu-system" in command or "/emulator" in command) else None


def kill_reason(tokens: list[str], owner: str | None, current_leases: list[dict]) -> str | None:
    executable = executable_name(tokens[0]) if tokens else ""
    if executable in {"pkill", "killall"} and any(re.search(r"(?:qemu|emulator)", token, re.IGNORECASE) for token in tokens[1:]):
        return "QEMU 또는 emulator 전체 종료는 다른 세션의 AVD까지 종료할 수 있어 차단합니다. 임대한 serial에 android emulator stop을 사용하세요."
    if executable != "kill":
        return None
    for token in tokens[1:]:
        if not token.isdigit():
            continue
        completed = subprocess.run(
            ["ps", "-p", token, "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        avd = avd_from_process_command(completed.stdout)
        if avd and not owns_avd(avd, owner, current_leases):
            return f"PID {token}의 {avd} AVD는 현재 세션 소유가 아니므로 종료할 수 없습니다."
    return None


def segment_reason(segment: list[str], command: str, owner: str | None, current_leases: list[dict]) -> str | None:
    if command == UNINSPECTABLE_ANDROID_COMMAND:
        return "functions.exec 안의 Android 명령을 정적으로 확인할 수 없습니다. exec_command의 cmd에 문자열 리터럴을 직접 전달하세요."
    if re.search(r"\brm\b[^\n;&|]*\.android/avd/[^\n;&|]*\.lock", command):
        return "AVD lock 파일 직접 삭제는 다른 세션의 실행 상태를 훼손할 수 있어 차단합니다."
    start = command_start(segment)
    if start >= len(segment):
        return None
    tokens = segment[start:]
    executable = executable_name(tokens[0])
    if executable == LEASE_SCRIPT_NAME or (
        executable in {"python", "python3"}
        and len(tokens) > 1
        and executable_name(tokens[1]) == LEASE_SCRIPT_NAME
    ):
        return None
    if executable == "android":
        return android_reason(tokens, owner, current_leases)
    if executable == "emulator":
        return raw_emulator_reason(tokens, owner, current_leases)
    if executable == "adb":
        return adb_reason(tokens, command, owner, current_leases)
    if executable in {"gradle", "gradlew"}:
        return gradle_reason(command, segment, owner, current_leases)
    if executable in {"kill", "killall", "pkill"}:
        return kill_reason(tokens, owner, current_leases)
    return None


def findings(payload: dict, directory: Path | None = None) -> list[str]:
    owner = current_owner(payload)
    current_leases = leases(directory)
    reasons = []
    for command in extract_commands(payload):
        for segment in shell_segments(command):
            reason = segment_reason(segment, " ".join(segment), owner, current_leases)
            if reason:
                reasons.append(reason)
    return list(dict.fromkeys(reasons))


def deny(reasons: list[str]) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Android 에뮬레이터 임대 규칙 위반: " + " ".join(reasons),
        }
    }, ensure_ascii=False))


def self_test() -> None:
    import tempfile

    previous_thread = os.environ.get("CODEX_THREAD_ID")
    previous_session = os.environ.pop("CODEX_SESSION_ID", None)
    os.environ["CODEX_THREAD_ID"] = "thread-a"
    try:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            lease = {
                "version": 1,
                "avd": "Pixel_A",
                "serial": "emulator-5554",
                "owner": "thread-a",
            }
            (directory / "Pixel_A.json").write_text(json.dumps(lease))
            payload = lambda command: {"tool_input": {"cmd": command}}
            assert findings(payload("adb devices -l"), directory) == []
            assert findings(payload("adb shell getprop sys.boot_completed"), directory)
            assert findings(payload("adb -s emulator-5556 shell input tap 1 1"), directory)
            assert findings(payload("adb -s emulator-5554 shell input tap 1 1"), directory) == []
            assert findings(payload("android emulator start Pixel_B"), directory)
            assert findings(payload("android emulator start Pixel_A"), directory) == []
            assert findings(payload("android run --device=emulator-5554 --apks=app.apk"), directory) == []
            assert findings(payload("./gradlew :app:installDebug"), directory)
            assert findings(payload("ANDROID_SERIAL=emulator-5554 ./gradlew :app:installDebug"), directory) == []
            code = 'const r = await tools.exec_command({cmd: "adb -s emulator-5556 install app.apk"});'
            assert findings({"tool_input": {"code": code}}, directory)
            indirect = 'const command = "adb shell input tap 1 1"; await tools.exec_command({cmd: command});'
            assert findings({"tool_input": {"code": indirect}}, directory)
            assert avd_from_process_command("/sdk/qemu-system-aarch64 @Pixel_A") == "Pixel_A"

            # 훅 프로세스에는 실행 셸의 CODEX_* 환경변수가 없을 수 있다.
            os.environ.pop("CODEX_THREAD_ID")
            own_session = {"session_id": "thread-a", **payload("android emulator start Pixel_A")}
            assert findings(own_session, directory) == []
            own_serial = {"session_id": "thread-a", **payload("adb -s emulator-5554 shell input tap 1 1")}
            assert findings(own_serial, directory) == []
            assert findings({**own_session, "session_id": "thread-b"}, directory)
            assert findings({**own_serial, "session_id": "thread-b"}, directory)
            assert findings(payload("android emulator start Pixel_A"), directory)
            assert findings({**own_session, "session_id": 123}, directory)
            assert findings({"tool_input": {"session_id": "thread-a", "cmd": "android emulator start Pixel_A"}}, directory)
            os.environ["CODEX_SESSION_ID"] = "thread-a"
            assert findings(payload("android emulator start Pixel_A"), directory) == []
    finally:
        if previous_thread is None:
            os.environ.pop("CODEX_THREAD_ID", None)
        else:
            os.environ["CODEX_THREAD_ID"] = previous_thread
        if previous_session is None:
            os.environ.pop("CODEX_SESSION_ID", None)
        else:
            os.environ["CODEX_SESSION_ID"] = previous_session
    print("android_emulator_lease_guard: ok")


def main() -> None:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("hook_event_name") != "PreToolUse":
        return
    reasons = findings(payload)
    if reasons:
        record_usage()
        deny(reasons)


if __name__ == "__main__":
    main()
