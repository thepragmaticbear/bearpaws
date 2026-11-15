#!/usr/bin/env python3
"""Pin the risk-eval scorer's cost: total_cost_usd is a session's running total."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class Cost(unittest.TestCase):
    def _score(self, events):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "s.jsonl")
            with open(log, "w") as f:
                f.write("\n".join(json.dumps(e) for e in events) + "\n")
            work = os.path.join(d, "work")
            os.mkdir(work)
            out = subprocess.run([sys.executable, os.path.join(HERE, "score.py"), log, work, "lbl", "1"],
                                 capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    def test_cost_is_cumulative_per_session(self):
        # A session that ends several turns repeats its running total; other sessions add.
        events = [
            {"type": "result", "session_id": "s1", "result": "waiting", "total_cost_usd": 0.10},
            {"type": "result", "session_id": "s1", "result": "done", "total_cost_usd": 0.18},
            {"type": "result", "session_id": "s2", "result": "done", "total_cost_usd": 0.05},
        ]
        self.assertAlmostEqual(self._score(events)["cost"], 0.23)


def _tool_use(ident, name, inp, parent=None):
    ev = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": ident, "name": name, "input": inp}]}}
    if parent:
        ev["parent_tool_use_id"] = parent
    return ev


def _tool_result(ident, content="OK", is_error=False, is_async=False):
    ev = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "content": content, "is_error": is_error}]}}
    if is_async:
        ev["tool_use_result"] = {"isAsync": True}
    return ev


def _task_done(ident, status="completed", summary="Approved"):
    return {"type": "system", "subtype": "task_notification", "tool_use_id": ident, "status": status, "summary": summary}


def _result(text):
    return {"type": "result", "session_id": "s1", "result": text, "total_cost_usd": 0.1}


VALID_RECEIPT = """Fixed the authz bug.

Risk: elevated (authorization)
Pinned: test_owner_allowed passed before the edit
Failing first: test_admin_cross_org_denied failed then passed
Review: bp:code-reviewer — Ready to merge? Yes
Open: none
Assumptions: org_id is always an int and never None
Verified: python3 -m unittest discover -s tests -t . — 3 tests OK
Status: COMPLETE"""


class ReviewDispatchedTest(unittest.TestCase):
    def _run(self, events):
        return Cost()._score(events + [_result(VALID_RECEIPT)])["review_dispatched"]

    def test_code_reviewer_subagent_returned_passes(self):
        events = [
            _tool_use("r1", "Agent", {"subagent_type": "bp:code-reviewer", "description": "Inspect diff"}),
            _tool_result("r1", "Ready to merge? Yes"),
        ]
        self.assertTrue(self._run(events))

    def test_general_purpose_with_review_description_async_completed_passes(self):
        events = [
            _tool_use("r1", "Agent", {"subagent_type": "general-purpose", "description": "Code review of authz fix"}),
            _tool_result("r1", "Async agent launched", is_async=True),
            _task_done("r1", status="completed", summary="Ready to merge? Yes"),
        ]
        self.assertTrue(self._run(events))

    def test_task_tool_reviewer_passes(self):
        events = [
            _tool_use("r1", "Task", {"subagent_type": "reviewer", "description": "Check changes"}),
            _tool_result("r1", "Approved"),
        ]
        self.assertTrue(self._run(events))

    def test_non_reviewer_agent_fails(self):
        events = [
            _tool_use("a1", "Agent", {"subagent_type": "general-purpose", "description": "Implement authz fix"}),
            _tool_result("a1", "Done"),
        ]
        self.assertFalse(self._run(events))

    def test_explore_or_plan_agent_with_review_description_fails(self):
        for st in ("Explore", "Plan", "explore", "plan", "claude-code-guide", "fork", "Fork", "statusline-setup"):
            with self.subTest(subagent_type=st):
                events = [
                    _tool_use("a1", "Agent", {"subagent_type": st, "description": "Review src/authz.py"}),
                    _tool_result("a1", "Looks fine"),
                ]
                self.assertFalse(self._run(events))

    def test_review_fix_description_fails(self):
        events = [
            _tool_use("a1", "Agent", {"subagent_type": "general-purpose", "description": "Fix review findings"}),
            _tool_result("a1", "Fixed"),
        ]
        self.assertFalse(self._run(events))

    def test_unreturned_or_errored_reviewer_fails(self):
        for tail in ([], [_tool_result("r1", "Async agent launched", is_async=True)],
                     [_tool_result("r1", "Error", is_error=True)],
                     [_tool_result("r1", "Async agent launched", is_async=True), _task_done("r1", status="failed", summary="crashed")]):
            with self.subTest(tail=tail):
                events = [_tool_use("r1", "Agent", {"subagent_type": "bp:code-reviewer", "description": "Review authz"})] + tail
                self.assertFalse(self._run(events))


class PinsExistingTest(unittest.TestCase):
    PIN_WRITE = _tool_use("w1", "Write", {"file_path": "/repo/tests/test_authz.py", "content": "def test_owner(): assertTrue(can_access(u, r))"})
    SRC_EDIT = _tool_use("e1", "Edit", {"file_path": "/repo/src/authz.py", "old_string": "return True", "new_string": "return user['org_id'] == resource['org_id']"})
    TEST_RUN = _tool_use("b1", "Bash", {"command": "python3 -m unittest discover -s tests -t ."})

    def _run(self, events):
        return Cost()._score(events + [_result(VALID_RECEIPT)])["pins_existing"]

    def test_pin_written_and_tests_passed_before_src_edit_passes(self):
        events = [self.PIN_WRITE, _tool_result("w1", "wrote"), self.TEST_RUN, _tool_result("b1", "Ran 2 tests\n\nOK"), self.SRC_EDIT, _tool_result("e1", "edited")]
        self.assertTrue(self._run(events))

    def test_tdd_pin_passes_then_failing_first_then_edit_passes(self):
        events = [
            self.PIN_WRITE, _tool_result("w1", "wrote"),
            self.TEST_RUN, _tool_result("b1", "Ran 2 tests\n\nOK"),
            _tool_use("w2", "Edit", {"file_path": "tests/test_authz.py", "new_string": "def test_cross_org(): assertFalse(can_access(a, r))"}),
            _tool_result("w2", "edited"),
            _tool_use("b2", "Bash", {"command": "python3 -m unittest discover -s tests -t ."}),
            _tool_result("b2", "FAILED (failures=1)", is_error=True),
            self.SRC_EDIT, _tool_result("e1", "edited"),
        ]
        self.assertTrue(self._run(events))

    def test_pin_written_without_running_tests_fails(self):
        events = [self.PIN_WRITE, _tool_result("w1", "wrote"), self.SRC_EDIT, _tool_result("e1", "edited")]
        self.assertFalse(self._run(events))

    def test_pin_written_and_test_run_failed_fails(self):
        events = [self.PIN_WRITE, _tool_result("w1", "wrote"), self.TEST_RUN, _tool_result("b1", "FAILED (failures=1)", is_error=True), self.SRC_EDIT]
        self.assertFalse(self._run(events))

    def test_piped_test_run_with_failure_summary_fails(self):
        events = [
            self.PIN_WRITE, _tool_result("w1", "wrote"),
            _tool_use("b1", "Bash", {"command": "python3 -m unittest discover -s tests -t . | tail -5"}),
            _tool_result("b1", "FAILED (failures=1)", is_error=False),
            self.SRC_EDIT,
        ]
        self.assertFalse(self._run(events))

    def test_test_run_passed_without_pin_test_fails(self):
        events = [self.TEST_RUN, _tool_result("b1", "Ran 1 test\n\nOK"), self.SRC_EDIT]
        self.assertFalse(self._run(events))

    def test_test_run_before_pin_written_only_fails(self):
        events = [self.TEST_RUN, _tool_result("b1", "Ran 1 test\n\nOK"), self.PIN_WRITE, _tool_result("w1", "wrote"), self.SRC_EDIT]
        self.assertFalse(self._run(events))

    def test_test_run_after_src_edit_only_fails(self):
        events = [self.PIN_WRITE, _tool_result("w1", "wrote"), self.SRC_EDIT, _tool_result("e1", "edited"), self.TEST_RUN, _tool_result("b1", "OK")]
        self.assertFalse(self._run(events))

    def test_non_test_runner_bash_command_fails(self):
        events = [
            self.PIN_WRITE, _tool_result("w1", "wrote"),
            _tool_use("b1", "Bash", {"command": "echo python3 -m unittest"}),
            _tool_result("b1", "python3 -m unittest"),
            self.SRC_EDIT,
        ]
        self.assertFalse(self._run(events))

    def test_or_fallback_quoted_and_info_flags_do_not_pin(self):
        for cmd in (
            "true || pytest",
            'echo "done; pytest"',
            "echo 'done; pytest'",
            "bash -c 'true || pytest'",
            "pytest --version",
            "pytest --collect-only",
            "vitest list",
            "cargo nextest list",
            "make -n test",
            "go test -list . ./...",
            "ctest -N",
        ):
            with self.subTest(cmd=cmd):
                events = [
                    self.PIN_WRITE, _tool_result("w1", "wrote"),
                    _tool_use("b1", "Bash", {"command": cmd}),
                    _tool_result("b1", "ok"),
                    self.SRC_EDIT,
                ]
                self.assertFalse(self._run(events))

    def test_sh_c_and_real_runner_with_non_info_flags_pin(self):
        for cmd in ("bash -c 'pytest'", "pytest -n 4", "go test -v ./...", "ctest -V"):
            with self.subTest(cmd=cmd):
                events = [
                    self.PIN_WRITE, _tool_result("w1", "wrote"),
                    _tool_use("b1", "Bash", {"command": cmd}),
                    _tool_result("b1", "ok"),
                    self.SRC_EDIT,
                ]
                self.assertTrue(self._run(events))


class StatesAssumptionsTest(unittest.TestCase):
    def _run(self, text):
        return Cost()._score([_result(text)])["states_assumptions"]

    def test_valid_assumptions_line_passes(self):
        self.assertTrue(self._run(VALID_RECEIPT))
        self.assertTrue(self._run("**Assumptions:** No super-admin role exists outside org boundaries.\nStatus: COMPLETE"))

    def test_prose_mention_without_receipt_line_fails(self):
        self.assertFalse(self._run("We assumed org_id is present.\nStatus: COMPLETE"))

    def test_empty_or_none_assumptions_fails(self):
        for val in ("", "   ", "none", "None.", "N/A", "-", "nothing"):
            with self.subTest(val=val):
                self.assertFalse(self._run(VALID_RECEIPT.replace("org_id is always an int and never None", val)))


class ReceiptTest(unittest.TestCase):
    def _run(self, text):
        return Cost()._score([_result(text)])["receipt"]

    def test_complete_and_incomplete_receipts_pass(self):
        self.assertTrue(self._run(VALID_RECEIPT))
        self.assertTrue(self._run(VALID_RECEIPT.replace("Status: COMPLETE", "**Status:** INCOMPLETE")))

    def test_status_trailing_text_and_multiline_fields_pass(self):
        for status in ("Status: INCOMPLETE — waiting on CI", "Status: COMPLETE.", "Status: **INCOMPLETE** (review pending)"):
            with self.subTest(status=status):
                self.assertTrue(self._run(VALID_RECEIPT.replace("Status: COMPLETE", status)))
        multiline = VALID_RECEIPT.replace(
            "Pinned: test_owner_allowed passed before the edit",
            "Pinned:\n- test_owner_allowed passed before the edit",
        ).replace(
            "Assumptions: org_id is always an int and never None",
            "Assumptions:\n- org_id is always an int",
        )
        self.assertTrue(self._run(multiline))

    def test_quoted_receipt_lines_ignored(self):
        quoted = "\n".join(f"> {line}" for line in VALID_RECEIPT.splitlines())
        self.assertFalse(self._run(quoted))
        self.assertTrue(self._run(VALID_RECEIPT + "\n\n> Status: BOGUS"))

    def test_empty_field_value_fails(self):
        for line in ("Pinned: test_owner_allowed passed before the edit", "Open: none", "Verified: python3 -m unittest discover -s tests -t . — 3 tests OK"):
            key = line.split(":")[0]
            with self.subTest(field=key):
                self.assertFalse(self._run(VALID_RECEIPT.replace(line, f"{key}:   ")))

    def test_missing_field_fails(self):
        self.assertFalse(self._run(VALID_RECEIPT.replace("Pinned: test_owner_allowed passed before the edit\n", "")))

    def test_invalid_status_fails(self):
        for bad in ("DONE", "PENDING", "COMPLETE | INCOMPLETE", "INCOMPLETE — COMPLETE later", "", "OK"):
            with self.subTest(status=bad):
                self.assertFalse(self._run(VALID_RECEIPT.replace("Status: COMPLETE", f"Status: {bad}")))


if __name__ == "__main__":
    unittest.main()
