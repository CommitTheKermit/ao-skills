#!/usr/bin/env python3
"""비밀값 입력과 자격값 덤프 명령을 실행 전에 차단한다.

PostToolUse 검사는 이미 transcript에 들어간 출력을 회수할 수 없어 보조 방어일 뿐이다.
따라서 위험한 조회는 PreToolUse에서 막고, 감지한 값 자체는 절대 출력하지 않는다.
"""

# usage-stats: hook block-secrets
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys


PATTERNS = [
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("GitHub token", re.compile(r"gh[posru]_[A-Za-z0-9]{36,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
READ_COMMANDS = {"awk", "base64", "cat", "grep", "head", "jq", "less", "more", "rg", "sed", "strings", "tail", "xxd"}
ENV_EXPANSION = re.compile(r"\$(?:\{)?([A-Z_][A-Z0-9_]*)", re.IGNORECASE)
SENSITIVE_ENV_NAME = re.compile(r"(?:API_KEY|CREDENTIAL|PASSWORD|PASSWD|PRIVATE_KEY|SECRET|TOKEN)", re.IGNORECASE)
OUTPUT_COMMAND = re.compile(
    r"(?:^|[;&|]\s*|\n)\s*(?:(?:builtin|command)\s+)?(?:[^\s;&|]*/)?(?:echo|printf)\b[^\n;&|]*",
    re.IGNORECASE,
)
CREDENTIAL_COMMANDS = [
    re.compile(r"(?:^|[;&|]\s*)(?:set|export)\s*(?:$|[;&|])", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:^|[;&|]\s*)export\s+-p(?:\s|$|[;&|])", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\b(?:env|printenv)\s+(?:[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY)[A-Z0-9_]*)\b(?=\s|$|[;&|])", re.IGNORECASE),
    re.compile(r"\bsecurity\s+find-(?:generic|internet)-password\b[^\n;&|]*\s-w(?:\s|$)", re.IGNORECASE),
    re.compile(r"\bgh\s+auth\s+token\b", re.IGNORECASE),
    re.compile(r"\baws\s+configure\s+get\s+(?:aws_secret_access_key|aws_session_token)\b", re.IGNORECASE),
    re.compile(r"\bgcloud\s+auth\s+print-(?:access|identity)-token\b", re.IGNORECASE),
    re.compile(r"\b(?:op\s+(?:read|get)|pass\s+(?:show|grep)|vault\s+(?:read|kv\s+get))\b", re.IGNORECASE),
]


def record_usage() -> None:
    subprocess.run(
        ["python3", str(Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"), "record", "hook", "block-secrets"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def shell_tokens(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return command.split()


def sensitive_path(value: str) -> bool:
    candidate = value.split("=", 1)[-1].rstrip(",:)")
    name = candidate.rsplit("/", 1)[-1].lower()
    if name == ".env" or (name.startswith(".env.") and name.split(".", 2)[-1] not in {"example", "sample", "template"}):
        return True
    if name in {".codex-global-state.json", ".netrc", ".npmrc", "hosts.yml", "id_ed25519", "id_rsa"} or name.endswith(".pem"):
        return True
    return bool(re.fullmatch(r"\.?(?:auth|credentials?|secrets?)(?:[-_.][\w.-]+)?", name))


def command_groups(command: str) -> list[list[str]]:
    groups = [[]]
    for token in shell_tokens(command.replace("\n", " ; ")):
        if token and set(token) <= set(";&|"):
            if groups[-1]:
                groups.append([])
        else:
            groups[-1].append(token)
    return [group for group in groups if group]


def dumps_environment_group(tokens: list[str]) -> bool:
    while tokens and tokens[0].rsplit("/", 1)[-1].lower() == "command":
        tokens = tokens[1:]
    if not tokens:
        return False
    executable = tokens[0].rsplit("/", 1)[-1].lower()
    if executable in {"bash", "sh", "zsh"} and len(tokens) >= 3 and tokens[1] in {"-c", "-lc"}:
        nested = shell_tokens(tokens[2]) if len(tokens) == 3 else tokens[2:]
        return dumps_environment_group(nested)
    if executable == "printenv":
        arguments = tokens[1:]
        return not arguments or all(argument in {"-0", "--null"} for argument in arguments)
    if executable != "env":
        return False
    arguments = tokens[1:]
    if any(argument in {"-0", "--null"} for argument in arguments):
        return True
    position = 0
    while position < len(arguments):
        argument = arguments[position]
        if argument in {"-u", "--unset"} and position + 1 < len(arguments):
            position += 2
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argument):
            position += 1
        else:
            break
    return position == len(arguments)


def dumps_environment(command: str) -> bool:
    return any(dumps_environment_group(group) for group in command_groups(command))


def reads_sensitive_file(command: str) -> bool:
    tokens = shell_tokens(command)
    for index, token in enumerate(tokens):
        if token.rsplit("/", 1)[-1].lower() not in READ_COMMANDS:
            continue
        for argument in tokens[index + 1:]:
            if argument and set(argument) <= set(";&|"):
                break
            if sensitive_path(argument):
                return True
    return False


def dumps_sensitive_expansion(command: str) -> bool:
    outside_single_quotes = re.sub(r"'[^']*'", "", command)
    return any(
        SENSITIVE_ENV_NAME.search(name)
        for match in OUTPUT_COMMAND.finditer(outside_single_quotes)
        for name in ENV_EXPANSION.findall(match.group())
    )


def dumps_kubectl_raw(command: str) -> bool:
    tokens = shell_tokens(command)
    for index, token in enumerate(tokens):
        if token.rsplit("/", 1)[-1].lower() != "kubectl":
            continue
        arguments = []
        for argument in tokens[index + 1:]:
            if argument and set(argument) <= set(";&|"):
                break
            arguments.append(argument.lower())
        raw = any(argument == "--raw" or argument.startswith("--raw=") for argument in arguments)
        config_view = any(arguments[position:position + 2] == ["config", "view"] for position in range(len(arguments) - 1))
        if raw and (config_view or "get" in arguments):
            return True
    return False


def findings(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    text = "\n".join(strings(tool_input))
    hits = [name for name, pattern in PATTERNS if pattern.search(text)]
    commands = "\n".join(
        value for key, value in tool_input.items()
        if key in {"command", "cmd", "input"} and isinstance(value, str)
    )
    if (
        reads_sensitive_file(commands)
        or dumps_environment(commands)
        or dumps_sensitive_expansion(commands)
        or dumps_kubectl_raw(commands)
        or any(pattern.search(commands) for pattern in CREDENTIAL_COMMANDS)
    ):
        hits.append("credential dump command")
    return sorted(set(hits))


def deny(hits: list[str]) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "보안 규칙 위반: " + ", ".join(hits) + " 감지. "
                "비밀값을 출력하지 말고 필요한 비밀은 환경변수 존재 여부만 확인하세요. "
                "이미 노출했다면 즉시 재발급하세요."
            ),
        }
    }, ensure_ascii=False))


def self_test() -> None:
    fake = "sk-" + "A" * 32
    blocked_environment_dumps = (
        "/usr/bin/env",
        "command env",
        "env -0",
        "/usr/bin/printenv -0",
        "bash -lc env",
    )
    safe_environment_commands = (
        "env VAR=x cmd",
        "env -u NAME cmd",
        "printenv PATH",
        'test -n "$API_TOKEN"',
        "echo '$API_TOKEN'",
    )
    for command in blocked_environment_dumps:
        assert findings({"tool_input": {"command": command}}) == ["credential dump command"]
    for command in safe_environment_commands:
        assert findings({"tool_input": {"command": command}}) == []
    assert findings({"tool_input": {"content": fake}}) == ["OpenAI API key"]
    assert findings({"tool_input": {"command": "cat .env"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "sed -n '1,5p' .env.local"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "rg TOKEN .env"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "jq . /tmp/fake/.codex-global-state.json"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "printf '%s\\n' \"$FAKE_API_TOKEN\""}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "echo $TOKEN"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "echo ${FAKE_PASSWORD}\nprintf ok"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "cat\n/tmp/fake/auth.json"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "rg FAKE /tmp/fake/credentials.json"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "export -p"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "kubectl config view --raw"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "kubectl get --raw"}}) == ["credential dump command"]
    assert findings({"tool_input": {"cmd": "gh auth token"}}) == ["credential dump command"]
    assert findings({"tool_input": {"command": "test -n \"$API_TOKEN\""}}) == []
    assert findings({"tool_input": {"command": "env FAKE_MODE=test command"}}) == []
    assert findings({"tool_input": {"command": "env FAKE_PASSWORD=test command"}}) == []
    assert findings({"tool_input": {"command": "env -u OPENAI_API_KEY command"}}) == []
    assert findings({"tool_input": {"command": "printenv PATH"}}) == []
    assert findings({"tool_input": {"command": "echo '${OPENAI_API_KEY}'"}}) == []
    assert findings({"tool_input": {"command": "echo $PATH"}}) == []
    assert findings({"tool_input": {"command": "rg '\\.env' .gitignore"}}) == []
    assert findings({"tool_input": {"command": "cat .env.example"}}) == []
    assert findings({"tool_input": {"command": "gh auth status"}}) == []
    assert findings({"tool_input": {"command": "security find-generic-password -s name"}}) == []
    assert findings({"tool_input": {"command": "aws sts get-caller-identity"}}) == []
    assert findings({"tool_input": {"command": "git status"}}) == []
    print("block_secrets: ok")


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
    hits = findings(payload)
    if hits:
        record_usage()
        deny(hits)


if __name__ == "__main__":
    main()
