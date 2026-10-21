import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("guard", Path(__file__).with_name("github-create-approval-guard.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def payload(event="PreToolUse", call="call-1", cmd="gh issue create -R owner/repo --title test --body body"):
    return dict(hook_event_name=event, session_id="test-session", tool_use_id=call,
                tool_name="Bash", tool_input={"command": cmd}, cwd="/tmp")


def reserve(queue):
    try:
        guard.handle(payload())
        queue.put(True)
    except ValueError:
        queue.put(False)


class ApprovalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, CODEX_GITHUB_APPROVAL_DIR=self.tmp.name)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def approve(self):
        guard.handle(dict(hook_event_name="UserPromptSubmit", session_id="test-session", prompt="슛"))

    def status(self):
        with guard.locked_state("test-session") as state:
            return state.get("status")

    def finish(self, response, call="call-1"):
        event = payload("PostToolUse", call)
        event["tool_response"] = response
        guard.handle(event)

    def test_no_approval_denied(self):
        with self.assertRaises(ValueError):
            guard.handle(payload())

    def test_success_consumes_once(self):
        self.approve()
        guard.handle(payload())
        self.assertEqual(self.status(), "pending")
        self.finish({"exit_code": 0, "output": "https://github.com/owner/repo/issues/12\n"})
        self.assertEqual(self.status(), "consumed")
        with self.assertRaises(ValueError):
            guard.handle(payload(call="call-2"))
        self.finish({"exit_code":1,"output":"HTTP 403"})
        self.assertEqual(self.status(), "consumed")

    def test_created_then_metadata_error_not_retryable(self):
        self.approve()
        guard.handle(payload())
        self.finish({"exit_code":1,"output":"https://github.com/owner/repo/issues/12\nHTTP 403 adding labels"})
        self.assertEqual(self.status(), "unknown")

    def test_403_retains_only_same_request(self):
        self.approve()
        guard.handle(payload())
        self.finish({"exit_code": 1, "output": "HTTP 403: Forbidden"})
        self.assertEqual(self.status(), "retryable")
        with self.assertRaises(ValueError):
            guard.handle(payload(cmd="gh issue create -R other/repo --title test"))
        guard.handle(payload(call="call-2"))
        self.assertEqual(self.status(), "pending")

    def test_unknown_and_new_approval_cannot_duplicate(self):
        self.approve()
        guard.handle(payload())
        self.finish({"exit_code": 1, "output": "connection reset"})
        self.approve()
        self.assertEqual(self.status(), "unknown")
        with self.assertRaises(ValueError):
            guard.handle(payload(call="call-2"))

    def test_wrong_call_or_receipt_not_success(self):
        self.approve()
        guard.handle(payload())
        self.finish({"exit_code": 0, "output": "https://github.com/owner/repo/issues/12"}, "other-call")
        self.assertEqual(self.status(), "pending")
        self.finish({"exit_code": 0, "output": "https://github.com/other/repo/issues/12"})
        self.assertEqual(self.status(), "unknown")

    def test_api_and_mcp_receipts(self):
        for command in ["gh api repos/owner/repo/issues -f title=test", "gh api -X POST repos/owner/repo/pulls", "gh api -XPOST repos/owner/repo/issues", "gh api repos/owner/repo/issues -ftitle=test"]:
            request = guard.request_info(payload(cmd=command))
            kind = request["kind"]
            self.assertEqual(guard.response_outcome({"number": 1, "html_url": f"https://github.com/owner/repo/{kind}/1"}, request), "consumed")
        event = payload()
        event.update(tool_name="mcp__github__create_issue", tool_input={"owner":"owner", "repo":"repo", "title":"test"})
        request = guard.request_info(event)
        self.assertEqual(guard.response_outcome({"isError": True, "content":[{"text":"HTTP 403"}]}, request), "retryable")
        self.assertEqual(guard.response_outcome({"content":[{"text":json.dumps({"number":1,"html_url":"https://github.com/owner/repo/issues/1"})}]}, request), "consumed")

    def test_graphql_creation_requires_supported_path(self):
        with self.assertRaises(ValueError):
            guard.request_info(payload(cmd="gh api graphql -f 'query=mutation { createIssue(input:{}) { issue { id } } }'"))

    def test_code_mode_static_command_and_dynamic_denial(self):
        event = payload()
        event.update(tool_name="functions.exec", tool_input={"code":'text(await tools.exec_command({cmd:"gh issue create -R owner/repo --title test"}));'})
        self.assertEqual(guard.request_info(event)["repo"], "owner/repo")
        event["tool_input"]={"input":event["tool_input"]["code"]}
        self.assertEqual(guard.request_info(event)["repo"], "owner/repo")
        event["tool_input"]={"code":'const cmd="gh issue create"; await tools.exec_command({cmd});'}
        with self.assertRaises(ValueError):
            guard.request_info(event)
        event["tool_input"]["code"] = 'await tools.apply_patch("gh issue create documentation");'
        self.assertIsNone(guard.request_info(event))

    def test_body_file_change_not_same_retry(self):
        file = Path(self.tmp.name) / "body.md"
        file.write_text("first")
        command = f"gh issue create -R owner/repo --title test --body-file {file}"
        first = guard.request_info(payload(cmd=command))["fingerprint"]
        file.write_text("second")
        self.assertNotEqual(first, guard.request_info(payload(cmd=command))["fingerprint"])

    def test_multiple_creations_denied_and_read_allowed(self):
        with self.assertRaises(ValueError):
            guard.request_info(payload(cmd="gh issue create -R owner/repo; gh pr create -R owner/repo"))
        for cmd in ["gh issue list", "gh api repos/owner/repo/issues", "git status"]:
            self.assertIsNone(guard.request_info(payload(cmd=cmd)))

    def test_quoted_fixture_is_not_a_creation(self):
        command = "python3 - <<'PY'\nfixture = {'command': 'gh issue create -R owner/repo --title smoke'}\nprint(fixture)\nPY"
        self.assertIsNone(guard.request_info(payload(cmd=command)))
        for command in ["command -v gh", "echo gh issue create", "git status; gh issue list"]:
            self.assertIsNone(guard.request_info(payload(cmd=command)))
        for command in ["echo start; gh issue create -R owner/repo", "bash -c 'gh issue create -R owner/repo'"]:
            with self.assertRaises(ValueError):
                guard.request_info(payload(cmd=command))

    def test_concurrent_only_one_reservation(self):
        self.approve()
        ctx = multiprocessing.get_context("fork")
        queue = ctx.Queue()
        workers = [ctx.Process(target=reserve, args=(queue,)) for _ in range(3)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(sum(queue.get(timeout=1) for _ in workers), 1)

    def test_reconcile_checks_read_receipt(self):
        self.approve()
        guard.handle(payload())
        self.finish({"exit_code":1,"output":"timeout"})
        result = type("Result", (), {"returncode":0,"stdout":json.dumps({"html_url":"https://github.com/owner/repo/issues/12","number":12,"title":"test","body":"body"})})()
        with patch.object(guard.subprocess, "run", return_value=result) as call:
            guard.reconcile("test-session", "https://github.com/owner/repo/issues/12")
            self.assertEqual(call.call_args.args[0][1], "api")
        self.assertEqual(self.status(), "consumed")


if __name__ == "__main__":
    unittest.main()
