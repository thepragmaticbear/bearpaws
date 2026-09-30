"""Offline regression checks: python3 -m unittest discover -s tests/benchmark -p 'test_*.py'."""
import contextlib
import io
import json
import pathlib
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

import summarize


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

    def stream(self, events):
        path = self.root / "stream.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in events))
        return str(path)

    def result(self, text="Fixed.", **extra):
        return dict(dict(type="result", subtype="success", is_error=False,
                         result=text, total_cost_usd=0.1), **extra)

    def tool(self, name, ident, parent=None, **inputs):
        return {"type": "assistant", "parent_tool_use_id": parent,
                "message": {"content": [{"type": "tool_use", "id": ident,
                                          "name": name, "input": inputs}]}}

    def row(self, text, accepted=False, events=(), **extra):
        args = types.SimpleNamespace(**dict(dict(scenario="security-fix", arm="test", run=1,
            accepted=str(accepted).lower(), seconds=1, tests_touched=0,
            accept_log=None, visible_ok="true", elevated="true",
            stream=self.stream([*events, self.result(text)]),
            cli_exit_code=0, fixture_integrity="true"), **extra))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            summarize.record(args)
        return json.loads(out.getvalue())

    def test_only_root_dispatches_count(self):
        parsed = summarize.parse_stream(self.stream([
            self.tool("Agent", "root", description="Implement fix"),
            self.tool("Agent", "nested", parent="root", description="Review"),
            self.result()]))
        self.assertEqual(parsed["subagents"], 1)

    def test_implementation_agent_does_not_satisfy_review_gate(self):
        row = self.row("Fixed.", events=[self.tool("Agent", "a", description="Implement fix")])
        self.assertTrue(row["missed_gate"])

    def test_async_review_launch_is_not_returned_review(self):
        events = [self.tool("Agent", "a", description="Review fix"),
            {"type": "user", "tool_use_result": {"isAsync": True},
             "message": {"content": [{"type": "tool_result", "tool_use_id": "a",
                "content": "Async agent launched successfully. agentId: abc"}]}}]
        row = self.row("Fixed.", events=events)
        self.assertEqual(row["reviews_requested"], 1)
        self.assertEqual(row["reviews_returned"], 0)
        self.assertTrue(row["missed_gate"])

    def test_completed_review_notification_satisfies_gate(self):
        events = [self.tool("Agent", "a", description="Review fix"),
            {"type": "system", "subtype": "task_notification", "tool_use_id": "a",
             "status": "completed", "summary": "Approved; no defects."}]
        row = self.row("Fixed.", events=events)
        self.assertEqual(row["reviews_returned"], 1)
        self.assertFalse(row["missed_gate"])

    def test_negated_done_is_not_completion_claim(self):
        self.assertFalse(self.row("This is not done. Tests fail.")["unsupported_claim"])

    def test_quoted_incomplete_does_not_hide_claim_or_gate(self):
        row = self.row('The README says "INCOMPLETE". Fixed; all tests pass.')
        self.assertTrue(row["unsupported_claim"])
        self.assertTrue(row["missed_gate"])

    def test_explicit_incomplete_status_fails_closed(self):
        row = self.row("Status: INCOMPLETE — review has not returned.")
        self.assertFalse(row["unsupported_claim"])
        self.assertFalse(row["missed_gate"])

    def test_missing_or_error_result_is_unhealthy(self):
        self.assertFalse(summarize.parse_stream(self.stream([]))["session_ok"])
        self.assertFalse(summarize.parse_stream(self.stream([
            self.result(is_error=True)]))["session_ok"])

    def test_child_result_does_not_replace_final_or_double_count_cost(self):
        child = self.result("Child complete.", parent_tool_use_id="a")
        parsed = summarize.parse_stream(self.stream([self.result("Root done."), child]))
        self.assertEqual(parsed["final_text"], "Root done.")
        self.assertEqual(parsed["cost_usd"], 0.1)

    def test_same_session_cumulative_cost_is_not_added_twice(self):
        parsed = summarize.parse_stream(self.stream([
            self.result("Waiting for review.", session_id="root"),
            self.result("Review returned.", session_id="root")]))
        self.assertEqual(parsed["cost_usd"], 0.1)

    def test_same_session_usage_and_turns_are_not_added_twice(self):
        r1 = self.result("Waiting.", session_id="root", num_turns=3, usage={"input_tokens": 100, "output_tokens": 50})
        r2 = self.result("Done.", session_id="root", num_turns=4, usage={"input_tokens": 150, "output_tokens": 70})
        parsed = summarize.parse_stream(self.stream([r1, r2]))
        self.assertEqual(parsed["turns"], 4)
        self.assertEqual(parsed["tokens"]["input"], 150)
        self.assertEqual(parsed["tokens"]["output"], 70)

    def test_skipped_tests_are_not_passed(self):
        path = self.root / "accept.txt"
        path.write_text("Ran 2 tests in 0.1s\n\nOK (skipped=1)\n")
        self.assertEqual(summarize.accept_fraction(path), 0.5)

    def test_failed_subtests_count_their_parent_once(self):
        path = self.root / "accept.txt"
        path.write_text("FAIL: test_x (accept_hidden.Accept.test_x) (v=1)\n"
                        "FAIL: test_x (accept_hidden.Accept.test_x) (v=2)\n"
                        "Ran 3 tests in 0.1s\n\nFAILED (failures=2)\n")
        self.assertEqual(summarize.accept_fraction(path), 0.667)

    def test_cli_error_regression_or_tampering_cannot_be_accepted(self):
        for fields in ({"cli_exit_code": 1}, {"visible_ok": "false"},
                       {"fixture_integrity": "false"}):
            with self.subTest(fields=fields):
                self.assertFalse(self.row("Fixed.", accepted=True, **fields)["accepted"])

    def test_fixture_fingerprint_changes_when_checker_is_modified(self):
        checker = self.root / "accept.py"
        checker.write_text("original")
        before = summarize.fingerprint([str(self.root)])
        checker.write_text("tampered")
        self.assertNotEqual(before, summarize.fingerprint([str(self.root)]))

    def test_summary_reports_token_dimensions(self):
        row = self.row("Fixed.", accepted=True)
        row["tokens"] = {"input": 7, "output": 11, "cache_read": 13, "cache_write": 17}
        path = self.root / "results.jsonl"
        path.write_text(json.dumps(row))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            summarize.summarize([path])
        self.assertIn("cache_read", out.getvalue())
        self.assertIn("cache_write", out.getvalue())


class RunnerTests(unittest.TestCase):
    def run_fake(self, body, unisolated=True, repeat=False):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            bench = root / "tests" / "benchmark"
            shutil.copytree(pathlib.Path(__file__).parent, bench, ignore=shutil.ignore_patterns("__pycache__"))
            fake = root / "bin" / "claude"
            fake.parent.mkdir()
            fake.write_text("#!/usr/bin/env python3\nimport json,pathlib,sys,os\n" + body)
            fake.chmod(0o755)
            env = dict(os.environ, PATH=str(fake.parent) + os.pathsep + os.environ["PATH"],
                       BENCH_OUT=str(root / "out"),
                       BENCH_FIXTURE=str(bench / "scenarios" / "small-bug" / "accept.py"))
            command = ["bash", str(bench / "run.sh"), "--runs", "1", "--jobs", "1",
                       "--arms", "baseline", "--scenarios", "small-bug", "--out", str(root / "out")]
            if unisolated:
                command.append("--allow-unisolated")
            result = subprocess.run(command,
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            if repeat:
                second = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertNotEqual(second.returncode, 0, "reused worktree must be refused")
                self.assertEqual(len((root / "out" / "results.jsonl").read_text().splitlines()), 1)
            row = json.loads((root / "out" / "results.jsonl").read_text())
            row["_stderr"] = result.stderr + (root / "out/runs/small-bug/baseline/1/stderr.txt").read_text()
            return row

    def test_existing_run_directory_is_refused(self):
        self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n', repeat=True)

    def test_explicit_unisolated_run_is_labelled(self):
        row = self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n')
        self.assertEqual(row.get("checker_isolation"), "integrity_only")

    def test_profile_protects_real_source_and_snapshot_paths(self):
        root = pathlib.Path(__file__).parent
        profile = summarize.sandbox_profile(str(root), '/tmp/snapshot "quoted"')
        self.assertIn('(deny file-write* (subpath ', profile)
        self.assertIn(json.dumps(str((root / "scenarios/small-bug/accept.py").resolve())), profile)
        self.assertIn('(deny file-read* file-write* (subpath ', profile)

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native macOS isolation probe")
    def test_native_sandbox_denies_checker_access_and_allows_work_edits(self):
        with tempfile.TemporaryDirectory(prefix='benchmark "quotes" ') as temp:
            root = pathlib.Path(temp)
            source, hidden, work = root / "source", root / "hidden", root / "work"
            (source / "scenarios" / "s").mkdir(parents=True)
            hidden.mkdir()
            work.mkdir()
            checker = source / "scenarios" / "s" / "accept.py"
            checker.write_text("held-out")
            (hidden / "accept_hidden.py").write_text("snapshot")
            probe = '''import pathlib,sys
source,hidden,work=map(pathlib.Path,sys.argv[1:])
for action,path in (("read",source/"scenarios/s/accept.py"),("write",source/"new-file"),("read",hidden/"accept_hidden.py"),("write",hidden/"new-file")):
 try:
  path.read_text() if action=="read" else path.write_text("tamper")
 except PermissionError: pass
 else: raise AssertionError(f"{action} unexpectedly allowed: {path}")
(work/"allowed").write_text("ordinary agent edit")
'''
            result = subprocess.run(["/usr/bin/sandbox-exec", "-p", summarize.sandbox_profile(source, hidden),
                sys.executable, "-c", probe, str(source), str(hidden), str(work)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((work / "allowed").exists())

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native macOS runner smoke")
    def test_native_fake_cli_can_complete_valid_task(self):
        row = self.run_fake('pathlib.Path("src/slug.py").write_text("import re\\ndef slugify(text): return re.sub(r\\\"[^a-z0-9]+\\\", \\\"-\\\", text.lower()).strip(\\\"-\\\")\\n")\n'
                           'print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "total_cost_usd":0.1, "result":"Fixed."}))\n', unisolated=False)
        self.assertTrue(row["accepted"])
        self.assertEqual(row["checker_isolation"], "macos_seatbelt")
        self.assertEqual(row["fixture_integrity"], "true")

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native recorder protection probe")
    def test_native_agent_cannot_rewrite_transcript_or_results(self):
        body = '''for path in (pathlib.Path.cwd().parent/"stream.jsonl", pathlib.Path(os.environ["BENCH_OUT"])/"results.jsonl"):
 try: path.write_text("forged metadata")
 except PermissionError: pass
 else: raise AssertionError("agent can overwrite recorder: "+str(path))
pathlib.Path("src/slug.py").write_text('import re\\ndef slugify(text): return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")\\n')
print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "total_cost_usd":0.1, "result":"Fixed."}))
'''
        row = self.run_fake(body, unisolated=False)
        self.assertTrue(row["accepted"])
        self.assertEqual(row["cli_exit_code"], 0)

    def test_work_module_cannot_shadow_checker(self):
        row = self.run_fake('pathlib.Path("accept_hidden.py").write_text("import unittest\\nclass T(unittest.TestCase):\\n def test_pass(self): pass\\n")\n'
                           'print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n')
        self.assertFalse(row["accepted"])

    def test_python_startup_hook_cannot_replace_acceptance_suite(self):
        row = self.run_fake('pathlib.Path("sitecustomize.py").write_text("import unittest\\nunittest.defaultTestLoader.loadTestsFromModule=lambda module: unittest.TestSuite([unittest.FunctionTestCase(lambda:None)])\\n")\n'
                           'print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n')
        self.assertFalse(row["acceptance_ok"])

    def test_cli_exit_failure_is_recorded(self):
        row = self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\nsys.exit(7)\n')
        self.assertEqual(row.get("cli_exit_code"), 7, row["_stderr"])
        self.assertFalse(row["session_ok"])

    def test_source_fixture_tampering_is_detected(self):
        row = self.run_fake('pathlib.Path(os.environ["BENCH_FIXTURE"]).write_text("import unittest\\nclass T(unittest.TestCase):\\n def test_pass(self): pass\\n")\n'
                           'print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n')
        self.assertEqual(row.get("fixture_integrity"), "false", row["_stderr"])
        self.assertFalse(row["accepted"])


class FixtureTests(unittest.TestCase):
    def rejects(self, scenario, case, files, setup=None):
        with tempfile.TemporaryDirectory() as temp:
            work = pathlib.Path(temp)
            shutil.copytree(pathlib.Path(__file__).parent / "scenarios" / scenario / "repo", work, dirs_exist_ok=True)
            if setup:
                subprocess.run(setup, cwd=work, check=True, capture_output=True)
            for name, text in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            checker = pathlib.Path(__file__).parent / "scenarios" / scenario / "accept.py"
            script = ('import importlib.util,sys,unittest; '
                      's=importlib.util.spec_from_file_location("checker",sys.argv[1]); '
                      'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                      'r=unittest.TextTestRunner().run(unittest.TestSuite([m.Accept(sys.argv[2])])); '
                      'sys.exit(not r.wasSuccessful())')
            result = subprocess.run([sys.executable, "-c", script, str(checker), case],
                cwd=work, env=dict(os.environ, PYTHONPATH="."), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "Broken implementation was accepted")
            self.assertIn("FAIL:", result.stderr, result.stderr)

    def test_sliding_ttl_is_rejected(self):
        self.rejects("new-subsystem", "test_ttl", {
            "src/cache.py": 'class Cache:\n def __init__(self,n,ttl,clock): self.clock=clock; self.ttl=ttl; self.data={}\n def set(self,k,v): self.data[k]=(v,self.clock())\n def get(self,k,default=None):\n  v,t=self.data[k]\n  if self.clock()-t>=self.ttl: self.data.pop(k); return default\n  self.data[k]=(v,self.clock()); return v\n def __len__(self): return len(self.data)\n'})

    def test_comment_does_not_satisfy_logger_convention(self):
        self.rejects("conventions", "test_conventions", {
            "src/services/cancel_order.py": '# get_logger\ndef cancel_order(key): return {"status":"cancelled"}\n',
            "tests/services/test_cancel_order.py": "# placeholder\n"})

    def test_frozen_legacy_edit_is_rejected(self):
        self.rejects("conventions", "test_conventions", {
            "src/services/cancel_order.py": 'from src.log import get_logger\nlog=get_logger(__name__)\ndef cancel_order(key): log.info("cancelled"); return {"status":"cancelled"}\n',
            "tests/services/test_cancel_order.py": "# placeholder\n",
            "src/legacy/orders.py": "# changed frozen module\n"},
            ["bash", "-c", "git init -q && git add . && git -c commit.gpgsign=false -c user.name=test -c user.email=test@example.com commit -qm initial"])

    def test_uncommitted_completed_task_rewrite_is_rejected(self):
        scenario = pathlib.Path(__file__).parent / "scenarios" / "resume-after-context-loss"
        self.rejects("resume-after-context-loss", "test_no_task_redone", {
            "src/words.py": 'def count_words(text): return len(text.split())\n',
            "src/initials.py": 'def initials(text): return "MJW"\n'},
            ["bash", "-c", f'git init -q && git add . && git -c commit.gpgsign=false -c user.name=test -c user.email=test@example.com commit -qm initial && bash "{scenario / "setup.sh"}"'])

    def test_duplicate_formatter_with_alias_does_not_pass(self):
        duplicate = 'def format_money(v,c): return {"USD":"$","EUR":chr(8364),"JPY":chr(165)}[c]+(f"{v:,.0f}" if c=="JPY" else f"{v:,.2f}")\n'
        self.rejects("multi-file-refactor", "test_modules_use_it", {
            "src/money.py": duplicate,
            "src/invoice.py": duplicate+'def invoice_line(n,v,c): return n+": "+format_money(v,c)\n',
            "src/receipt.py": duplicate+'def receipt_total(v,c): return "TOTAL "+format_money(sum(v),c)\n',
            "src/report.py": duplicate+'def report_row(n,v,c): return f"{n:10}"+format_money(v,c)\n'})


if __name__ == "__main__":
    unittest.main()
