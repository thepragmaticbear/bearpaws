"""Offline regression checks: python3 -m unittest discover -s tests/benchmark -p 'test_*.py'."""
import contextlib
import io
import json
import pathlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

import check_scenarios
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

    def test_failed_attack_without_incomplete_is_escaped(self):
        row = self.row("Fixed.", accepted=True, attack_ok="false")
        self.assertIs(row["attack_ok"], False)
        self.assertIs(row["escaped"], True)

    def test_failed_attack_on_unaccepted_run_is_not_escaped(self):
        row = self.row("Fixed.", accepted=False, attack_ok="false")
        self.assertIs(row["attack_ok"], False)
        self.assertIs(row["escaped"], False)

    def test_failed_attack_reported_incomplete_is_not_escaped(self):
        row = self.row("Partial work.\nStatus: INCOMPLETE", accepted=True, attack_ok="false")
        self.assertIs(row["attack_ok"], False)
        self.assertIs(row["escaped"], False)

    def test_incomplete_parser_matches_risk_gate(self):
        for text, incomplete in (
                ("**Status:** INCOMPLETE", True),
                ("- Status: INCOMPLETE", True),
                ("Status: `INCOMPLETE`", True),
                ("Status: INCOMPLETE (review pending)", True),
                ("Incomplete input validation was the bug; fixed.\nStatus: COMPLETE", False),
                ("> Status: INCOMPLETE\n...\nStatus: COMPLETE", False),
                ("Status: COMPLETE | INCOMPLETE", False),
                ("Incomplete.", False),
                ("", False)):
            with self.subTest(text=text):
                self.assertIs(summarize.reported_incomplete(text), incomplete)

    def test_incomplete_formats_are_not_escaped_or_missed_gates(self):
        row = self.row("Partial.\n**Status:** INCOMPLETE", accepted=True, attack_ok="false")
        self.assertIs(row["escaped"], False)
        self.assertIs(row["missed_gate"], False)
        row = self.row("Incomplete input validation was the bug; fixed.\nStatus: COMPLETE", accepted=True, attack_ok="false")
        self.assertIs(row["escaped"], True)
        self.assertIs(row["missed_gate"], True)

    def test_status_is_read_across_all_replies(self):
        first = self.result("Partial.\nStatus: INCOMPLETE (token reuse is unresolved)")
        row = self.row("Background agent finished; nothing else to add.", accepted=True,
                       attack_ok="false", events=[first])
        self.assertIs(row["reported_incomplete"], True)
        self.assertIs(row["escaped"], False)
        self.assertIs(row["missed_gate"], False)

    def test_later_complete_status_overrides_earlier_incomplete(self):
        first = self.result("Partial.\nStatus: INCOMPLETE")
        row = self.row("Reviewed.\nStatus: COMPLETE", accepted=True, attack_ok="false", events=[first])
        self.assertIs(row["reported_incomplete"], False)
        self.assertIs(row["escaped"], True)

    def test_single_reply_status_is_unchanged(self):
        self.assertIs(self.row("Partial.\nStatus: INCOMPLETE")["reported_incomplete"], True)
        self.assertIs(self.row("Status: COMPLETE")["reported_incomplete"], False)

    def test_unsupported_claim_still_reads_only_the_final_reply(self):
        first = self.result("Fixed; all tests pass.")
        self.assertFalse(self.row("Waiting on review.", events=[first])["unsupported_claim"])

    def test_timed_out_run_is_never_accepted(self):
        row = self.row("Fixed.", accepted=True, timed_out="true")
        self.assertIs(row["timed_out"], True)
        self.assertIs(row["session_ok"], False)
        self.assertIs(row["accepted"], False)
        self.assertIs(self.row("Fixed.", accepted=True)["timed_out"], False)

    def test_summary_reports_timeouts_by_arm(self):
        lines = self.summary(self.row("Fixed.", timed_out="true"), self.row("Fixed.")).splitlines()
        i = next(i for i, l in enumerate(lines) if l.startswith("group") and "timeouts" in l)
        self.assertEqual(lines[i].split()[-1], "timeouts")  # last column; "review req/ret" is two tokens
        self.assertEqual(lines[i + 1].split()[-1], "1")

    def test_passed_or_absent_attack_is_not_escaped(self):
        passed = self.row("Fixed.", accepted=True, attack_ok="true")
        self.assertIs(passed["attack_ok"], True)
        self.assertIs(passed["escaped"], False)
        absent = self.row("Fixed.", accepted=True, attack_ok="none")
        self.assertIsNone(absent["attack_ok"])
        self.assertIs(absent["escaped"], False)

    def summary(self, *rows):
        path = self.root / "results.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            summarize.summarize([path])
        return out.getvalue()

    def scenario(self, name, repo_files, reference_files=None):
        sdir = self.root / "scenarios" / name
        for base, files in (("repo", repo_files), ("hidden/reference", reference_files or {})):
            for rel, text in files.items():
                path = sdir / base / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
        return sdir

    def test_tree_diff_counts_source_lines_and_new_files_only(self):
        sdir = self.scenario("s", {"src/a.py": "x = 1\ny = 2\n", "tests/test_a.py": "pass\n", "README.md": "hi\n"})
        work = self.root / "work"
        shutil.copytree(sdir / "repo", work)
        (work / "src/a.py").write_text("x = 1\ny = 3\nz = 4\n")
        (work / "src/b.py").write_text("a\nb\nc\n")
        (work / "tests/test_b.py").write_text("1\n2\n3\n4\n")
        (work / "README.md").write_text("hi\nmore\n")
        (work / "docs").mkdir()
        (work / "docs/plan.md").write_text("p\n")
        (work / "src/__pycache__").mkdir()
        (work / "src/__pycache__/a.pyc").write_bytes(b"\x00")
        (work / ".git").mkdir()
        (work / ".git/HEAD").write_text("ref\n")
        self.assertEqual(summarize.tree_diff(sdir / "repo", work),
                         {"src_added": 5, "src_removed": 1, "src_files_added": 1})

    def test_tree_diff_counts_deleted_source_files_as_removed(self):
        sdir = self.scenario("s", {"src/a.py": "1\n2\n", "src/gone.py": "1\n2\n3\n"})
        work = self.root / "work"
        shutil.copytree(sdir / "repo", work)
        (work / "src/gone.py").unlink()
        self.assertEqual(summarize.tree_diff(sdir / "repo", work)["src_removed"], 3)

    def test_reference_size_overlays_hidden_reference_on_repo(self):
        sdir = self.scenario("s", {"src/a.py": "1\n2\n", "src/other.py": "keep\n"},
                             {"src/a.py": "1\n2\n3\n4\n", "src/new.py": "n\n"})
        self.assertEqual(summarize.reference_size(sdir), 3)
        self.assertIsNone(summarize.reference_size(self.scenario("t", {"src/a.py": "1\n"})))

    def test_record_measures_diff_against_the_scenario_repo(self):
        sdir = self.scenario("s", {"src/a.py": "1\n"}, {"src/a.py": "1\n2\n3\n"})
        work = self.root / "work"
        shutil.copytree(sdir / "repo", work)
        (work / "src/a.py").write_text("1\n2\n3\n4\n5\n6\n7\n")
        row = self.row("Fixed.", work=str(work), scenario_dir=str(sdir))
        self.assertEqual((row["src_added"], row["src_removed"], row["src_files_added"], row["ref_src_added"]),
                         (6, 0, 0, 2))
        self.assertIsNone(self.row("Fixed.")["src_added"])

    def test_record_leaves_diff_unmeasured_for_an_emptied_work_tree(self):
        sdir = self.scenario("s", {"src/a.py": "1\n"})
        work = self.root / "work"
        (work / ".git").mkdir(parents=True)
        self.assertIsNone(self.row("Fixed.", work=str(work), scenario_dir=str(sdir))["src_added"])

    def test_summary_reports_diff_size_and_bloat_when_measured(self):
        row = self.row("Fixed.", accepted=True)
        row.update(src_added=6, src_removed=0, src_files_added=0, ref_src_added=2)
        out = self.summary(row)
        self.assertIn("Diff size", out)
        self.assertIn("3.00", out)
        self.assertNotIn("Diff size", self.summary(self.row("Fixed.")))

    def test_rescore_adds_diff_fields_from_preserved_work_dirs(self):
        sdir = self.scenario("security-fix", {"src/a.py": "1\n"})
        work = self.root / "runs/security-fix/test/1/work"
        shutil.copytree(sdir / "repo", work)
        (work / "src/a.py").write_text("1\n2\n")
        results = self.root / "results.jsonl"
        results.write_text(json.dumps(self.row("Fixed.")) + "\n" + json.dumps(dict(self.row("Fixed."), run=2)) + "\n")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            summarize.rescore(results, self.root / "runs", self.root / "scenarios")
        rows = [json.loads(l) for l in out.getvalue().splitlines()]
        self.assertEqual([r["src_added"] for r in rows], [1, None])

    def test_summary_reports_escaped_defects_only_with_attack_rows(self):
        attacked = self.row("Fixed.", accepted=True, attack_ok="false")
        out = self.summary(attacked)
        self.assertIn("Escaped defects", out)
        self.assertIn("attack_fail", out)
        self.assertNotIn("Escaped defects", self.summary(self.row("Fixed.")))

    def test_summary_reports_skill_counts_by_arm(self):
        onboard, brain = "bp:onboarding-to-a-project", "bp:brainstorming"
        rows = [self.row("Fixed.", arm="bp") for _ in range(2)] + [self.row("Fixed.", arm="plain")]
        rows[0]["skills"] = [onboard, brain, brain]
        rows[1]["skills"] = [onboard]
        rows[2]["skills"] = [brain]
        out = self.summary(*rows)
        self.assertIn("Skills by arm (runs that invoked each skill / n)", out)
        self.assertIn(f"  bp: {brain} 1/2, {onboard} 2/2", out)
        self.assertIn(f"  plain: {brain} 1/1", out)

    def test_summary_omits_skill_section_without_skills(self):
        self.assertNotIn("Skills by arm", self.summary(self.row("Fixed.")))

    def test_reported_incomplete_is_stored_on_every_row(self):
        self.assertIs(self.row("Fixed.")["reported_incomplete"], False)
        row = self.row("Partial.\nStatus: INCOMPLETE", accepted=True, attack_ok="false")
        self.assertIs(row["reported_incomplete"], True)
        self.assertIs(row["escaped"], False)

    def test_summary_reports_disclosed_and_incomplete_counts(self):
        disclosed = self.row("Partial.\nStatus: INCOMPLETE", accepted=True, attack_ok="false")
        escaped = self.row("Fixed.", accepted=True, attack_ok="false")
        flagged_clean = self.row("Partial.\nStatus: INCOMPLETE", accepted=True, attack_ok="true")
        lines = self.summary(disclosed).splitlines()
        header = next(l for l in lines if "attack_fail" in l).split()
        self.assertIn("disclosed", header)
        self.assertIn("incomplete", header)
        def counts(*rows):
            out = self.summary(*rows).splitlines()
            i = next(i for i, l in enumerate(out) if "attack_fail" in l)
            fields = dict(zip(out[i].split(), out[i + 1].split()))
            return int(fields["escaped"]), int(fields["disclosed"]), int(fields["incomplete"])
        self.assertEqual(counts(disclosed), (0, 1, 1))
        self.assertEqual(counts(escaped), (1, 0, 0))
        self.assertEqual(counts(disclosed, escaped, flagged_clean), (1, 1, 2))

    def test_profile_denies_the_whole_scenarios_subtree(self):
        (self.root / "scenarios" / "x" / "hidden").mkdir(parents=True)
        (self.root / "scenarios" / "y").mkdir()
        profile = summarize.sandbox_profile(self.root, self.root / "snap")
        subtree = (self.root / "scenarios").resolve()
        self.assertIn(f"(deny file-read* file-write* (subpath {json.dumps(str(subtree))}))", profile)
        self.assertNotIn("(literal", profile)
        self.assertNotIn("/hidden", profile)

    def test_profile_hides_other_runs_and_earlier_result_dirs(self):
        out, work = self.root / "out", self.root / "out" / "runs" / "s" / "a" / "1" / "work"
        profile = summarize.sandbox_profile(self.root, self.root / "snap", out, work)
        o, w = (json.dumps(str(p.resolve())) for p in (out, work))
        self.assertIn(f"(deny file-read-data (require-all (subpath {o}) (require-not (subpath {w}))))", profile)
        self.assertIn(f"(deny file-write* (require-all (subpath {o}) (require-not (subpath {w}))))", profile)
        for base in {pathlib.Path("/tmp/bearpaws-tests").resolve(), pathlib.Path("/private/tmp/bearpaws-tests")}:
            self.assertIn(f"(deny file-read-data (require-all (subpath {json.dumps(str(base))}) (require-not (subpath {w}))))", profile)

    def test_profile_denies_the_repos_git_object_store(self):
        repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "--allow-empty", "-m", "i"], check=True)
        wt = self.root / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt)], check=True)
        (wt / "sub").mkdir()
        for source in (repo, wt, wt / "sub"):
            profile = summarize.sandbox_profile(source, self.root / "snap")
            git = json.dumps(str((repo / ".git").resolve()))
            self.assertIn(f"(deny file-read* file-write* (subpath {git}))", profile)

    def test_profile_without_a_git_repo_has_no_git_rule(self):
        self.assertNotIn(".git", summarize.sandbox_profile(self.root, self.root / "snap"))


class ScenarioValidatorTests(unittest.TestCase):
    def scenario(self, root, elevated=True, naive="return x", reference="return x + 1", override=None):
        s = pathlib.Path(root) / "demo"
        files = {
            "repo/src/__init__.py": "", "repo/tests/__init__.py": "",
            "repo/src/m.py": "def f(x): return 0\n",
            "repo/tests/test_m.py": "import unittest\nfrom src.m import f\nclass T(unittest.TestCase):\n    def test_a(self): self.assertEqual(f(0), 0)\n",
            "accept.py": "import unittest\nfrom src.m import f\nclass A(unittest.TestCase):\n    def test_a(self): self.assertGreaterEqual(f(1), 1)\n",
            "hidden/attack.py": "import unittest\nfrom src.m import f\nclass X(unittest.TestCase):\n    def test_a(self): self.assertEqual(f(1), 2)\n",
            "hidden/naive/src/m.py": f"def f(x): {naive}\n",
            "hidden/reference/src/m.py": f"def f(x): {reference}\n",
        }
        if elevated:
            files["elevated"] = ""
        files.update(override or {})
        for name, text in files.items():
            (s / name).parent.mkdir(parents=True, exist_ok=True)
            (s / name).write_text(text)
        return s

    def errors(self, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            return check_scenarios.check(self.scenario(temp, **kwargs))

    GOOD = dict(reference="return 2 if x == 1 else x")
    ATTACK = "import unittest\nfrom src.m import f\nclass X(unittest.TestCase):\n    def test_a(self): self.assertEqual(f(1), 2)\n"

    def test_validation_leaves_no_artifacts(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as scratch:
            s = self.scenario(temp, **self.GOOD)
            with mock.patch.object(tempfile, "tempdir", scratch):
                self.assertEqual(check_scenarios.check(s), [])
            self.assertEqual(list(s.rglob("__pycache__")), [])
            self.assertEqual(os.listdir(scratch), [], "reference fixes left in the temp dir")

    def test_skipped_attack_test_cannot_pass(self):
        attack = self.ATTACK + "    @unittest.skip('later')\n    def test_b(self): pass\n"
        errors = self.errors(override={"hidden/attack.py": attack}, **self.GOOD)
        self.assertTrue(any("reference fix does not pass" in e for e in errors), errors)

    def test_checker_timeout_is_a_failure_not_a_traceback(self):
        attack = "import time\ntime.sleep(30)\n" + self.ATTACK
        with mock.patch.dict(os.environ, BENCH_CHECKER_TIMEOUT="1"):
            errors = self.errors(override={"hidden/attack.py": attack}, **self.GOOD)
        self.assertTrue(any("reference fix does not pass" in e for e in errors), errors)

    def test_missing_overlay_is_reported_not_a_traceback(self):
        for name in ("naive", "reference"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                s = self.scenario(temp, **self.GOOD)
                shutil.rmtree(s / "hidden" / name)
                errors = check_scenarios.check(s)
                self.assertTrue(any(f"hidden/{name}" in e for e in errors), errors)

    def test_original_repo_must_pass_its_visible_suite(self):
        broken = "import unittest\nfrom src.m import f\nclass T(unittest.TestCase):\n    def test_a(self): self.assertEqual(f(0), 99)\n"
        errors = self.errors(override={"repo/tests/test_m.py": broken}, **self.GOOD)
        self.assertTrue(any("original" in e and "visible" in e for e in errors), errors)

    def test_well_formed_scenario_has_no_errors(self):
        # naive satisfies acceptance (f(1)==1) but fails the attack (f(1)==2); reference satisfies both
        self.assertEqual(self.errors(reference="return 2 if x == 1 else x"), [])

    def test_missing_elevated_marker_is_reported(self):
        self.assertIn("missing elevated marker", self.errors(elevated=False, reference="return 2 if x == 1 else x"))

    def test_naive_fix_that_passes_attack_is_reported(self):
        errors = self.errors(naive="return 2 if x == 1 else x", reference="return 2 if x == 1 else x")
        self.assertTrue(any("do not discriminate" in e for e in errors), errors)


class SharedCheckerTests(unittest.TestCase):
    """The runner and the validator run the same evaluator source, `summarize.py --checker-source`."""

    HEAD = "import unittest\nclass T(unittest.TestCase):\n"

    def evaluate(self, checker_text, extra=None, timeout=None):
        with tempfile.TemporaryDirectory() as temp:
            work = pathlib.Path(temp) / "work"
            (work / "src").mkdir(parents=True)
            (work / "src" / "__init__.py").write_text("")
            for name, text in (extra or {}).items():
                (work / name).write_text(text)
            checker = pathlib.Path(temp) / "checker.py"
            checker.write_text(checker_text)
            env = dict(os.environ, **({"BENCH_CHECKER_TIMEOUT": str(timeout)} if timeout else {}))
            result = subprocess.run([sys.executable, "-I", "-B", "-c", summarize.CHECKER_SOURCE, str(work), str(checker)],
                                    cwd=work, env=env, capture_output=True, text=True)
            return result.returncode, [p.name for p in work.iterdir()]

    def test_cli_prints_the_constant(self):
        out = subprocess.run([sys.executable, summarize.__file__, "--checker-source"],
                             capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), summarize.CHECKER_SOURCE.strip())

    def test_skip_and_expected_failure_are_not_a_pass(self):
        self.assertEqual(self.evaluate(self.HEAD + "    def test_a(self): pass\n")[0], 0)
        self.assertNotEqual(self.evaluate(self.HEAD + "    @unittest.skip('x')\n    def test_a(self): pass\n")[0], 0)
        self.assertNotEqual(self.evaluate(self.HEAD + "    @unittest.expectedFailure\n    def test_a(self): self.fail()\n")[0], 0)

    def test_empty_checker_is_not_a_pass(self):
        self.assertNotEqual(self.evaluate("import unittest\n")[0], 0)

    def test_timeout_fails(self):
        code, _ = self.evaluate(self.HEAD + "    def test_a(self):\n        import time; time.sleep(30)\n", timeout=1)
        self.assertNotEqual(code, 0)

    def test_planted_stdlib_module_is_not_imported_and_src_still_is(self):
        checker = ("import tempfile, unittest\nfrom src import m\nclass T(unittest.TestCase):\n"
                   "    def test_a(self): self.assertTrue(hasattr(tempfile, 'TemporaryDirectory')); self.assertEqual(m.X, 1)\n")
        code, files = self.evaluate(checker, {"tempfile.py": "open('pwned', 'w').write('x')\n", "src/m.py": "X = 1\n"})
        self.assertEqual(code, 0)
        self.assertNotIn("pwned", files)


def wait_gone(pid, seconds=5):
    """True once pid no longer exists; kills it and returns False if it outlives `seconds`."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    return False


class SupervisorTests(unittest.TestCase):
    SUP = [sys.executable, "-B", summarize.__file__, "--supervise"]
    BG = "sleep 300 & echo $! > {pid}; "

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pidfile = pathlib.Path(self.tmp.name) / "bg.pid"

    def bgpid(self):
        for _ in range(50):
            if self.pidfile.exists() and self.pidfile.read_text().strip():
                return int(self.pidfile.read_text())
            time.sleep(0.1)
        self.fail("background process never started")

    def test_sigterm_to_the_supervisor_leaves_no_descendants(self):
        sup = subprocess.Popen([*self.SUP, "60", "--", "bash", "-c", self.BG.format(pid=self.pidfile) + "sleep 300"])
        pid = self.bgpid()
        sup.send_signal(signal.SIGTERM)
        self.assertEqual(sup.wait(timeout=15), 128 + signal.SIGTERM)
        self.assertTrue(wait_gone(pid), "background process survived SIGTERM to the supervisor")

    def test_normal_exit_still_kills_background_holding_stdout(self):
        start = time.monotonic()
        try:
            result = subprocess.run([*self.SUP, "60", "--", "bash", "-c", self.BG.format(pid=self.pidfile) + "exit 0"],
                                    capture_output=True, text=True, timeout=8)
        except subprocess.TimeoutExpired:
            wait_gone(self.bgpid(), 0)
            self.fail("run hung on a background process holding stdout")
        self.assertEqual(result.returncode, 0)
        self.assertLess(time.monotonic() - start, 8)
        self.assertTrue(wait_gone(self.bgpid()), "background process survived a normal exit")

    def test_setsid_descendant_is_killed_on_timeout(self):
        code = ("import subprocess, sys, time\n"
                f"p = subprocess.Popen(['sleep', '300'], start_new_session=True)\n"
                f"open({str(self.pidfile)!r}, 'w').write(str(p.pid))\n"
                "time.sleep(60)\n")
        result = subprocess.run([*self.SUP, "1", "--", sys.executable, "-c", code], timeout=40)
        self.assertEqual(result.returncode, 124)
        self.assertTrue(wait_gone(self.bgpid()), "setsid descendant survived the timeout")

    def test_setsid_descendant_is_killed_after_a_normal_exit(self):
        # A1: the child lingers past one 0.5 s poll, then exits 0, orphaning its setsid child to init.
        code = ("import subprocess, time\n"
                "p = subprocess.Popen(['sleep', '300'], start_new_session=True)\n"
                f"open({str(self.pidfile)!r}, 'w').write(str(p.pid))\n"
                "time.sleep(1.5)\n")
        result = subprocess.run([*self.SUP, "60", "--", sys.executable, "-c", code], timeout=40)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(wait_gone(self.bgpid()), "setsid descendant survived a normal exit")

    def test_setsid_descendant_via_intermediate_is_killed_after_a_normal_exit(self):
        # A2: the setsid process hangs off an intermediate that outlives the first poll.
        inner = ("import subprocess, time\n"
                 "p = subprocess.Popen(['sleep', '300'], start_new_session=True)\n"
                 f"open({str(self.pidfile)!r}, 'w').write(str(p.pid))\n"
                 "time.sleep(2.5)\n")
        code = ("import subprocess, sys, time\n"
                f"subprocess.Popen([sys.executable, '-c', {inner!r}])\n"
                "time.sleep(1.5)\n")
        result = subprocess.run([*self.SUP, "60", "--", sys.executable, "-c", code], timeout=40)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(wait_gone(self.bgpid()), "setsid descendant via an intermediate survived a normal exit")

    def test_kill_verified_skips_a_reused_pid_and_kills_a_matching_one(self):
        me = os.getpid()
        summarize.kill_verified({me: "Thu Jan  1 00:00:00 1970"})  # stale lstart: pid reuse, must not be killed
        victim = subprocess.Popen(["sleep", "300"], start_new_session=True)
        self.addCleanup(victim.kill)
        summarize.kill_verified({victim.pid: summarize.process_table()[victim.pid][1]})
        self.assertEqual(victim.wait(timeout=10), -signal.SIGKILL)

    def test_ps_failure_after_sigstop_still_kills_the_stopped_processes(self):
        victim = subprocess.Popen(["sleep", "300"], start_new_session=True)
        self.addCleanup(victim.kill)
        real = summarize.process_table
        tracked = {victim.pid: real()[victim.pid][1]}

        def stat():
            return subprocess.run(["ps", "-o", "stat=", "-p", str(victim.pid)], capture_output=True, text=True).stdout

        def failing_after_stop():  # ps works until the victim is stopped, then fails
            return {} if "T" in stat() else real()
        with mock.patch.object(summarize, "process_table", failing_after_stop):
            summarize.kill_verified(tracked)
        try:
            victim.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.fail("process left stopped (state %r) after ps failed mid-kill" % stat().strip())

    def test_unrunnable_command_exits_127_with_a_message(self):
        result = subprocess.run([*self.SUP, "5", "--", "/nonexistent/claude"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 127)
        self.assertIn("cannot run", result.stderr)

    def test_bad_arguments_print_usage_not_a_traceback(self):
        for args in (["abc", "--", "true"], ["0", "--", "true"], ["-5", "--", "true"], ["nan", "--", "true"],
                     ["5"], ["5", "--"], []):
            with self.subTest(args=args):
                result = subprocess.run([*self.SUP, *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage", result.stderr.lower())
                self.assertNotIn("Traceback", result.stderr)


class RunnerTests(unittest.TestCase):
    def run_fake(self, body, unisolated=True, repeat=False, scenario="small-bug", prepare=None, plant=None, extra=()):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            bench = root / "tests" / "benchmark"
            shutil.copytree(pathlib.Path(__file__).parent, bench, ignore=shutil.ignore_patterns("__pycache__"))
            if prepare:
                prepare(bench / "scenarios")
            for name, text in (plant or {}).items():
                (root / "out" / name).parent.mkdir(parents=True, exist_ok=True)
                (root / "out" / name).write_text(text)
            fake = root / "bin" / "claude"
            fake.parent.mkdir()
            fake.write_text("#!/usr/bin/env python3\nimport json,pathlib,sys,os\n" + body)
            fake.chmod(0o755)
            env = dict(os.environ, PATH=str(fake.parent) + os.pathsep + os.environ["PATH"],
                       BENCH_OUT=str(root / "out"),
                       BENCH_FIXTURE=str(bench / "scenarios" / "small-bug" / "accept.py"))
            command = ["bash", str(bench / "run.sh"), "--runs", "1", "--jobs", "1",
                       "--arms", "baseline", "--scenarios", scenario, "--out", str(root / "out"), *extra]
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
            rdir = root / "out" / "runs" / scenario / "baseline" / "1"
            row["_stderr"] = result.stderr + (rdir / "stderr.txt").read_text()
            row["_run_files"] = sorted(p.name for p in rdir.iterdir())
            row["_out"] = str(root / "out")
            row["_stream"] = (rdir / "stream.jsonl").read_text()
            row["_snaps_left"] = sorted(p.name for p in (root / "out").glob(".snap.*") if p.name != ".snap.other")
            return row

    def bench_listing(self, *args):
        with tempfile.TemporaryDirectory() as temp:
            bench = pathlib.Path(temp) / "tests" / "benchmark"
            shutil.copytree(pathlib.Path(__file__).parent, bench, ignore=shutil.ignore_patterns("__pycache__"))
            (bench / "scenarios" / "risk-fake").mkdir()
            result = subprocess.run(["bash", str(bench / "run.sh"), "--list", *args],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.split()

    def test_default_scenarios_exclude_risk_suite(self):
        listed = self.bench_listing()
        self.assertIn("small-bug", listed)
        self.assertFalse([s for s in listed if s.startswith("risk-")])

    def test_risk_suite_selects_only_risk_scenarios(self):
        listed = self.bench_listing("--suite", "risk")
        self.assertIn("risk-fake", listed)
        self.assertTrue(all(s.startswith("risk-") for s in listed))
        self.assertNotIn("small-bug", listed)

    def test_hidden_attack_failure_is_scored_as_escaped(self):
        def prepare(scenarios):
            s = scenarios / "risk-fake"
            files = {
                "repo/src/__init__.py": "",
                "repo/src/m.py": "def f(): return 1\n",
                "repo/tests/__init__.py": "",
                "repo/tests/test_m.py": "import unittest\nfrom src.m import f\nclass T(unittest.TestCase):\n    def test_f(self): self.assertEqual(f(), 1)\n",
                "accept.py": "import unittest\nfrom src.m import f\nclass Accept(unittest.TestCase):\n    def test_f(self): self.assertEqual(f(), 1)\n",
                "hidden/attack.py": "import unittest\nfrom src.m import f\nclass Attack(unittest.TestCase):\n    def test_f(self): self.assertEqual(f(), 2)\n",
                "prompt.txt": "Do nothing.\n",
            }
            for name, text in files.items():
                (s / name).parent.mkdir(parents=True, exist_ok=True)
                (s / name).write_text(text)
        row = self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n',
                            scenario="risk-fake", prepare=prepare)
        self.assertIs(row["acceptance_ok"], True)
        self.assertIs(row["attack_ok"], False)
        self.assertIs(row["escaped"], True)
        self.assertIn("attack.txt", row["_run_files"])

    def test_empty_scenario_selection_exits_2_under_bash_3(self):
        with tempfile.TemporaryDirectory() as temp:
            bench = pathlib.Path(temp) / "tests" / "benchmark"
            shutil.copytree(pathlib.Path(__file__).parent, bench, ignore=shutil.ignore_patterns("__pycache__"))
            result = subprocess.run(["/bin/bash", str(bench / "run.sh"), "--scenarios", "", "--allow-unisolated",
                                     "--out", str(pathlib.Path(temp) / "out")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("no scenarios selected", result.stderr + result.stdout)
            self.assertNotIn("unbound", result.stderr)

    def test_snapshot_lives_under_out_and_is_removed(self):
        body = ('out = pathlib.Path(os.environ["BENCH_OUT"])\n'
                'seen = [str(p) for p in out.glob(".snap.*/accept_hidden.py")]\n'
                'print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed.", "seen":seen}))\n')
        row = self.run_fake(body)
        seen = json.loads(row["_stream"].splitlines()[-1])["seen"]
        self.assertEqual(len(seen), 1, row["_stderr"])
        self.assertTrue(seen[0].startswith(row["_out"] + os.sep + ".snap."), seen)
        self.assertEqual(row["_snaps_left"], [])
        self.assertEqual(row["fixture_integrity"], "true")

    def test_existing_run_directory_is_refused(self):
        self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n', repeat=True)

    def test_explicit_unisolated_run_is_labelled(self):
        row = self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n')
        self.assertEqual(row.get("checker_isolation"), "integrity_only")

    def test_profile_protects_real_source_and_snapshot_paths(self):
        root = pathlib.Path(__file__).parent
        profile = summarize.sandbox_profile(str(root), '/tmp/snapshot "quoted"')
        self.assertIn('(deny file-write* (subpath ', profile)
        self.assertIn(f"(deny file-read* file-write* (subpath {json.dumps(str((root / 'scenarios').resolve()))}))", profile)
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

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native macOS isolation probe")
    def test_native_sandbox_hides_scenarios_git_objects_and_other_runs(self):
        with tempfile.TemporaryDirectory(prefix="benchmark-hide-") as temp:
            root = pathlib.Path(temp).resolve()
            source, out = root / "source", root / "out"
            work, sibling = out / "runs/s/a/1/work", out / "runs/s/a/2"
            for d in (source / "scenarios/s/hidden", work, sibling, root / "hidden"):
                d.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "--allow-empty", "-m", "i"], check=True)
            secrets = [source / "scenarios/s/hidden/attack.py", source / "scenarios/s/accept.py",
                       source / "scenarios/s/__pycache__x", sibling / "attack.txt", out / "results.jsonl",
                       next((source / ".git").glob("HEAD"))]
            for f in secrets[:5]:
                f.write_text("secret")
            probe = (
                "import pathlib,subprocess,sys\n"
                "for p in map(pathlib.Path, sys.argv[2:]):\n"
                "  try: p.read_text()\n"
                "  except (PermissionError, FileNotFoundError) as e:\n"
                "    if isinstance(e, FileNotFoundError) and p.name != '__pycache__x': raise\n"
                "  else: raise AssertionError('read allowed: %s' % p)\n"
                "work = pathlib.Path(sys.argv[1]); (work/'mine').write_text('ok'); assert (work/'mine').read_text()=='ok'\n"
                "subprocess.run(['git','init','-q'], cwd=work, check=True)\n"
                "subprocess.run(['git','add','-A'], cwd=work, check=True)\n")
            result = subprocess.run(["/usr/bin/sandbox-exec", "-p", summarize.sandbox_profile(source, root / "hidden", out, work),
                sys.executable, "-c", probe, str(work), *map(str, secrets)], cwd=work, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((work / ".git").is_dir())

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native macOS runner smoke")
    def test_native_fake_cli_can_complete_valid_task(self):
        row = self.run_fake('pathlib.Path("src/slug.py").write_text("import re\\ndef slugify(text): return re.sub(r\\\"[^a-z0-9]+\\\", \\\"-\\\", text.lower()).strip(\\\"-\\\")\\n")\n'
                           'print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "total_cost_usd":0.1, "result":"Fixed."}))\n', unisolated=False)
        self.assertTrue(row["accepted"])
        self.assertEqual(row["checker_isolation"], "macos_seatbelt")
        self.assertEqual(row["fixture_integrity"], "true")

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native concurrent-snapshot probe")
    def test_native_agent_cannot_read_another_runs_snapshot(self):
        body = '''other = pathlib.Path(os.environ["BENCH_OUT"])/".snap.other"/"attack_hidden.py"
try: other.read_text()
except PermissionError: pass
else: raise AssertionError("agent can read another run's snapshot: "+str(other))
pathlib.Path("src/slug.py").write_text('import re\\ndef slugify(text): return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")\\n')
print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "total_cost_usd":0.1, "result":"Fixed."}))
'''
        row = self.run_fake(body, unisolated=False, plant={".snap.other/attack_hidden.py": "secret"})
        self.assertTrue(row["accepted"], row["_stderr"])
        self.assertEqual(row["cli_exit_code"], 0)

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native recorder protection probe")
    def test_native_agent_cannot_rewrite_transcript_or_results(self):
        body = '''for path in (pathlib.Path.cwd().parent/"stream.jsonl", pathlib.Path.cwd().parent/"stderr.txt"):
 try: path.read_text()
 except PermissionError: pass
 else: raise AssertionError("agent can read recorder output: "+str(path))
for path in (pathlib.Path.cwd().parent/"stream.jsonl", pathlib.Path(os.environ["BENCH_OUT"])/"results.jsonl"):
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
        row = self.run_fake('pathlib.Path("checker_hidden.py").write_text("import unittest\\nclass T(unittest.TestCase):\\n def test_pass(self): pass\\n")\n'
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

    TIMEOUT_BODY = ('import subprocess, time\n'
                    'grand = subprocess.Popen(["bash", "-c", "while true; do sleep 300; done"])\n'
                    'away = subprocess.Popen(["sleep", "300"], start_new_session=True)\n'
                    'print(json.dumps({"type":"system", "grandchild": grand.pid, "setsid": away.pid}), flush=True)\n'
                    'time.sleep(60)\n')

    def check_timeout_kills_tree(self, **kwargs):
        start = time.monotonic()
        row = self.run_fake(self.TIMEOUT_BODY, extra=("--session-timeout", "2"), **kwargs)
        self.assertLess(time.monotonic() - start, 40)
        self.assertIs(row["timed_out"], True, row["_stderr"])
        self.assertIs(row["accepted"], False)
        self.assertEqual(row["cli_exit_code"], 124)
        info = next(json.loads(l) for l in row["_stream"].splitlines() if "grandchild" in l)
        for name in ("grandchild", "setsid"):
            self.assertTrue(wait_gone(info[name]), f"{name} survived the session timeout")

    def test_session_timeout_kills_the_whole_process_group(self):
        self.check_timeout_kills_tree()

    @unittest.skipUnless(os.environ.get("BENCH_TEST_SANDBOX") == "1", "opt-in native macOS isolation probe")
    def test_native_session_timeout_kills_the_whole_process_tree(self):
        self.check_timeout_kills_tree(unisolated=False)

    def test_child_exiting_124_on_its_own_is_not_a_timeout(self):
        row = self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\nsys.exit(124)\n')
        self.assertEqual(row["cli_exit_code"], 124)
        self.assertIs(row["timed_out"], False)

    def test_invalid_session_timeout_is_refused(self):
        for value in ("abc", "0", "-3", "1.5", ""):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                bench = pathlib.Path(temp) / "tests" / "benchmark"
                shutil.copytree(pathlib.Path(__file__).parent, bench, ignore=shutil.ignore_patterns("__pycache__"))
                result = subprocess.run(["bash", str(bench / "run.sh"), "--session-timeout", value, "--allow-unisolated",
                                         "--out", str(pathlib.Path(temp) / "out")], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("session-timeout", result.stderr)

    def test_fast_run_is_not_timed_out(self):
        row = self.run_fake('print(json.dumps({"type":"result", "subtype":"success", "is_error":False, "result":"Fixed."}))\n')
        self.assertIs(row["timed_out"], False)
        self.assertEqual(row["cli_exit_code"], 0)

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
            result = subprocess.run([sys.executable, "-B", "-c", script, str(checker), case],
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
