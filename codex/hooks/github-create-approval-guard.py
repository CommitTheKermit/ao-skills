#!/usr/bin/env python3
"""슛 1회의 GitHub 생성 권한을 예약하고 확인된 성공에만 소비한다."""
# usage-stats: hook github-create-approval-guard
import argparse
import ast
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

NAME = "github-create-approval-guard"
MATCHER = r"^(?:Bash|exec_command|functions\.exec|.*create_(?:issue|pull_request).*|.*github.*(?:graphql|api).*)$"
URL = re.compile(r"https://([^/\s]+)/([^/\s]+/[^/\s]+)/(issues|pull)/(\d+)/?$")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def record_usage():
    recorder = Path.home() / ".agents/skills/usage-stats/scripts/usage_stats.py"
    if recorder.exists():
        subprocess.run([sys.executable, str(recorder), "record", "hook", NAME],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def state_dir():
    return Path(os.environ.get("CODEX_GITHUB_APPROVAL_DIR", str(Path.home() / ".codex/github-create-approvals")))


@contextmanager
def locked_state(session):
    if not session:
        raise ValueError("세션 ID가 없어 생성 승인을 확인할 수 없습니다.")
    root = state_dir()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = digest(session)
    with (root / (key + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / (key + ".json")
        state = json.loads(path.read_text()) if path.exists() else {}
        yield state
        fd, name = tempfile.mkstemp(dir=root)
        try:
            with os.fdopen(fd, "w") as out:
                json.dump(state, out)
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def option(tokens, *names):
    for i, token in enumerate(tokens):
        for name in names:
            if token == name and i + 1 < len(tokens):
                return tokens[i + 1]
            if token.startswith(name + "="):
                return token.split("=", 1)[1]
    return None


def request_info(payload):
    """정적으로 식별할 수 없는 생성 호출은 허용하지 않는다. 일반 호출은 None."""
    name = str(payload.get("tool_name", ""))
    inp = payload.get("tool_input") or {}
    if not isinstance(inp, dict):
        # functions.exec의 FREEFORM 입력도 런타임에 따라 문자열로 전달된다.
        inp = {"code": inp} if isinstance(inp, str) else {}
    kind, repo, title, body = None, None, None, None
    files = {}
    if "github" in name.lower() and re.search(r"\b(?:createIssue|createPullRequest)\b", json.dumps(inp)):
        raise ValueError("GraphQL 생성은 직접 REST 또는 전용 생성 도구 호출로 분리하세요.")
    if "create_issue" in name or "create_pull_request" in name:
        kind = "pull" if "create_pull_request" in name else "issues"
        repo = "/".join(str(inp.get(x, "")) for x in ("owner", "repo"))
        title, body = inp.get("title"), inp.get("body")
    else:
        command = inp.get("command") or inp.get("cmd")
        code = inp.get("code") or (inp.get("input") if name == "functions.exec" else None)
        if isinstance(code, str):
            if not re.search(r"\btools\.(?:exec_command|[^\s(]*create_(?:issue|pull_request))\s*\(", code):
                return None
            # 복잡한 JS를 실행해 해석하지 않는다. 생성은 단일 literal 명령으로 제한한다.
            literal = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
            matches = re.findall(r"\b(?:cmd|command)\s*:\s*(" + literal + ")", code)
            if not re.search(r"\bgh\b.*(?:\bcreate\b|\bapi\b)|create_(?:issue|pull_request)", code, re.S):
                return None
            if len(matches) != 1 or len(re.findall(r"\btools\.", code)) != 1:
                raise ValueError("GitHub 생성은 단일 명령의 독립 도구 호출로 실행하세요.")
            command = ast.literal_eval(matches[0])
        if not isinstance(command, str):
            return None
        lexer = shlex.shlex(command.replace("\n", ";"), posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
        if not tokens or Path(tokens[0]).name != "gh":
            # 인용된 소스/모의 입력의 'gh issue create ...' 문자열은 실행 파일 토큰이 아니다.
            # 각 셸 구간의 실행 파일만 검사한다. echo/rg/which의 인수를 명령으로 취급하지 않는다.
            segments, segment = [], []
            for token in tokens + [";"]:
                if token and set(token) <= set(";&|"):
                    if segment:
                        segments.append(segment)
                        segment = []
                else:
                    segment.append(token)
            for segment in segments:
                index = 0
                while index < len(segment) and (segment[index] in {"env", "command"} or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", segment[index])):
                    index += 1
                if index < len(segment) and Path(segment[index]).name == "gh":
                    nested = shlex.join(segment[index:])
                    if request_info(dict(payload, tool_input={"command":nested})):
                        raise ValueError("GitHub 생성은 gh를 직접 호출하는 명령으로 분리하세요.")
            if tokens and Path(tokens[0]).name in {"sh", "bash", "zsh"} and "-c" in tokens:
                nested = option(tokens, "-c")
                if nested and request_info(dict(payload, tool_input={"command":nested})):
                    raise ValueError("셸 래퍼 안의 GitHub 생성은 직접 호출로 분리하세요.")
            return None
        if "api" in tokens and "graphql" in tokens and re.search(r"\b(?:createIssue|createPullRequest)\b", command):
            raise ValueError("GraphQL 생성은 단일 REST 또는 전용 생성 도구 호출로 분리하세요.")
        if "issue" in tokens and tokens.index("issue") + 1 < len(tokens) and tokens[tokens.index("issue") + 1] == "create":
            kind = "issues"
        elif "pr" in tokens and tokens.index("pr") + 1 < len(tokens) and tokens[tokens.index("pr") + 1] == "create":
            kind = "pull"
        elif "api" in tokens:
            endpoint = next((x for x in tokens if re.search(r"(?:^|/)repos/[^/]+/[^/]+/(issues|pulls)/?$", x)), "")
            fields = any(x in {"-f", "-F", "--field", "--raw-field", "--input"} or x.startswith(("--field=", "--raw-field=", "-f", "-F")) for x in tokens)
            attached_method = next((x[2:] for x in tokens if x.startswith("-X") and len(x) > 2), None)
            method = option(tokens, "-X", "--method") or attached_method or ("POST" if fields else "GET")
            if method.upper() != "POST" or not endpoint:
                return None
            hit = re.search(r"repos/([^/]+/[^/]+)/(issues|pulls)/?$", endpoint)
            repo, kind = hit[1], "pull" if hit[2] == "pulls" else "issues"
        if not kind:
            return None
        if any(x and set(x) <= set(";&|") for x in tokens):
            raise ValueError("한 번의 도구 호출에는 생성 1건만 넣고 셸 연결을 제거하세요.")
        repo = repo or option(tokens, "-R", "--repo") or os.environ.get("GH_REPO")
        title, body = option(tokens, "--title", "-t"), option(tokens, "--body", "-b")
        for i, token in enumerate(tokens):
            field = tokens[i + 1] if token in {"-f", "-F", "--field", "--raw-field"} and i + 1 < len(tokens) else None
            if token.startswith(("--field=", "--raw-field=")):
                field = token.split("=", 1)[1]
            elif token.startswith(("-f", "-F")) and len(token) > 2:
                field = token[2:]
            if field and "=" in field:
                key, value = field.split("=", 1)
                typed = token == "-F" or token.startswith(("-F", "--field"))
                if typed and value.startswith("@"):
                    if value == "@-":
                        raise ValueError("gh api 입력은 명시적인 파일로 전달하세요.")
                    file_path = Path(payload.get("cwd", ".")) / value[1:]
                    value = file_path.read_text()
                    files[str(file_path)] = digest(value)
                if key == "title":
                    title = value
                elif key == "body":
                    body = value
        file = option(tokens, "--body-file")
        if file:
            if file == "-":
                raise ValueError("승인 요청을 식별할 수 있도록 본문은 파일이나 인수로 전달하세요.")
            path = Path(payload.get("cwd", ".")) / file
            body = path.read_text()
            files[str(path)] = digest(body)
        input_file = option(tokens, "--input")
        if input_file:
            if input_file == "-":
                raise ValueError("gh api 입력은 명시적인 파일로 전달하세요.")
            data = json.loads((Path(payload.get("cwd", ".")) / input_file).read_text())
            files[input_file] = digest(data)
            title, body = data.get("title"), data.get("body")
        if not repo:
            remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=payload.get("cwd"),
                                    capture_output=True, text=True, check=False).stdout.strip()
            hit = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", remote)
            repo = hit[1] if hit else None
    if not repo or not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
        raise ValueError("대상 owner/repo를 명시해야 생성 승인을 예약할 수 있습니다.")
    return {"fingerprint": digest([name, inp, files, payload.get("cwd"), repo]),
            "repo": repo, "kind": kind, "title_hash": digest(title) if title else None,
            "body_hash": digest(body) if body is not None else None}


def response_outcome(response, request):
    """성공 영수증과 명백한 HTTP 거절만 확정한다. 나머지는 unknown."""
    if isinstance(response, str):
        try:
            return response_outcome(json.loads(response), request)
        except (ValueError, TypeError):
            text = response
    else:
        text = json.dumps(response, ensure_ascii=False)
    candidates = []
    failed = False
    def visit(value):
        nonlocal failed
        if isinstance(value, dict):
            failed = failed or value.get("isError") is True or value.get("exit_code", 0) not in (0, None) or bool(value.get("session_id"))
            if value.get("html_url") and value.get("number"):
                candidates.append(value["html_url"])
            for key, item in value.items():
                if key in {"output", "text", "content", "structuredContent", "result"}:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str):
            try:
                visit(json.loads(value))
            except ValueError:
                candidates.extend(line.strip() for line in value.splitlines() if URL.fullmatch(line.strip()))
    visit(response)
    if isinstance(response, str):
        candidates.extend(line.strip() for line in response.splitlines() if URL.fullmatch(line.strip()))
    for url in candidates:
        hit = URL.fullmatch(url)
        if hit and hit[2].lower() == request["repo"].lower() and hit[3] == request["kind"] and not failed:
            return "consumed"
    if candidates:
        # 생성 후 라벨 추가가 실패한 경우처럼 URL과 오류가 함께 있으면 재생성을 허용하지 않는다.
        return "unknown"
    # HTTP 4xx는 생성 거절이다. 5xx/timeout/비정상 종료만으로 미생성을 단정하지 않는다.
    if re.search(r"\bHTTP[ /:]+(?:400|401|403|404|405|409|410|422|429)\b", text, re.I):
        return "retryable"
    return "unknown"


def handle(payload):
    event, session = payload.get("hook_event_name"), payload.get("session_id")
    if event == "UserPromptSubmit":
        if str(payload.get("prompt", "")).strip() == "슛":
            with locked_state(session) as state:
                if state.get("status") not in {"pending", "unknown"}:
                    state.clear()
                    state["status"] = "ready"
        return None
    if event not in {"PreToolUse", "PostToolUse"}:
        return None
    request = request_info(payload)
    if request is None:
        return None
    call_id = payload.get("tool_use_id")
    with locked_state(session) as state:
        if event == "PostToolUse":
            if state.get("status") in {"pending", "unknown"} and call_id and state.get("call_id") == call_id and state.get("request", {}).get("fingerprint") == request["fingerprint"]:
                state["status"] = response_outcome(payload.get("tool_response"), request)
                if state["status"] == "unknown":
                    return {"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"GitHub 생성 결과가 미확정입니다. 재시도 전에 생성 여부를 조회하세요. 확인된 URL은 승인 훅의 --reconcile-url로 연결할 수 있습니다."}}
            return None
        if not call_id:
            raise ValueError("호출 ID가 없어 생성 결과를 연결할 수 없습니다.")
        if state.get("status") == "retryable" and state.get("request", {}).get("fingerprint") != request["fingerprint"]:
            raise ValueError("실패 후 재시도 승인은 같은 생성 요청에만 유효합니다. 변경한 요청은 새 슛 승인이 필요합니다.")
        if state.get("status") not in {"ready", "retryable"}:
            raise ValueError("생성 승인이 없거나 다른 생성의 결과가 미확정입니다. 미확정 생성은 먼저 조회하고, 새 생성은 별도 슛 승인을 받으세요.")
        state.update(status="pending", call_id=call_id, request=request)
    return None


def reconcile(session, url):
    """읽기 전용 API로 동일 요청의 생성 영수증을 검증한다. 부재는 성공으로 단정하지 않는다."""
    hit = URL.fullmatch(url)
    if not hit:
        raise ValueError("생성된 issue/PR의 정확한 URL이 필요합니다.")
    with locked_state(session) as state:
        request = state.get("request", {})
        if state.get("status") not in {"pending", "unknown"} or not request.get("title_hash"):
            raise ValueError("제목까지 대조할 수 있는 미확정 요청이 없습니다.")
        if hit[2].lower() != request["repo"].lower() or hit[3] != request["kind"]:
            raise ValueError("예약한 대상과 조회 URL이 다릅니다.")
        endpoint = "pulls" if hit[3] == "pull" else "issues"
        result = subprocess.run(["gh", "api", "--hostname", hit[1], f"repos/{hit[2]}/{endpoint}/{hit[4]}"],
                                capture_output=True, text=True, timeout=20, check=False)
        if result.returncode:
            raise ValueError("GitHub 조회를 확인하지 못했습니다. 보류를 유지합니다.")
        receipt = json.loads(result.stdout)
        if digest(receipt.get("title")) != request["title_hash"] or (request.get("body_hash") and digest(receipt.get("body") or "") != request["body_hash"]):
            raise ValueError("조회한 제목 또는 본문이 예약 요청과 다릅니다.")
        if response_outcome(receipt, request) != "consumed":
            raise ValueError("생성 영수증을 확인하지 못했습니다.")
        state["status"] = "consumed"
    print("생성 영수증을 조회해 승인 1건을 소비했습니다.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconcile-url")
    parser.add_argument("--session-id")
    args = parser.parse_args()
    record_usage()
    try:
        if args.reconcile_url:
            reconcile(args.session_id or os.environ.get("CODEX_THREAD_ID"), args.reconcile_url)
            return
        payload = json.load(sys.stdin)
        result = handle(payload)
        if result:
            print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, subprocess.SubprocessError):
        if args.reconcile_url:
            print("영수증을 확인하지 못해 승인을 보류합니다.", file=sys.stderr)
            sys.exit(1)
        event = locals().get("payload", {}).get("hook_event_name")
        if event == "PreToolUse":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                  "permissionDecisionReason": "생성 승인이 없거나 요청·결과를 확정할 수 없습니다. 단일 gh 생성 명령과 owner/repo, 슛 승인 및 미확정 생성 조회 여부를 확인하세요."}}, ensure_ascii=False))
        elif event == "PostToolUse":
            print(json.dumps({"systemMessage": "GitHub 생성 결과를 확정하지 못했습니다. 재시도 전에 생성 여부를 조회하세요."}, ensure_ascii=False))


if __name__ == "__main__":
    main()
