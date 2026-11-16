#!/usr/bin/env python3
"""Pin the proportion-eval scorer: test counts, assertion removals, RED order, suite, mutants, cost."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def bash(cmd_id, command, output=""):
    """A Bash tool call and its result, as two stream-json events."""
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": cmd_id, "name": "Bash", "input": {"command": command}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": cmd_id, "content": output}]}},
    ]


def agent(cmd_id, description, subagent_type="general-purpose"):
    return [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": cmd_id, "name": "Agent",
         "input": {"description": description, "subagent_type": subagent_type, "prompt": "..."}}]}}]


def reply(text):
    return [{"type": "result", "session_id": "s", "result": text, "total_cost_usd": 0}]


def edit(cmd_id, path):
    return [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": cmd_id, "name": "Edit", "input": {"file_path": path}}]}}]


GREEN_OUT = "Ran 8 tests in 0.001s\n\nOK"
RED_OUT = "FAIL: test_x (tests.test_x.T.test_x)\nAssertionError: 5 != 30\nFAILED (failures=1)"
TIMEOUT_TEST = "\n    def test_default_timeout(self):\n        self.assertEqual(request_options()['timeout'], 30)\n"
TRIAGE_RULE = "- For billing tickets, ask for the customer's order number before anything else.\n"


class Score(unittest.TestCase):
    def run_score(self, scenario, change, events):
        with tempfile.TemporaryDirectory() as d:
            work = os.path.join(d, "work")
            subprocess.run([os.path.join(HERE, "setup.sh"), work, scenario], check=True)
            change(work)
            log = os.path.join(d, "t.jsonl")
            with open(log, "w") as f:
                f.write("\n".join(json.dumps(e) for e in events) + "\n")
            out = subprocess.run([sys.executable, os.path.join(HERE, "score.py"), log, work, "lbl", scenario, "1"],
                                 capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    @staticmethod
    def read(work, rel):
        with open(os.path.join(work, rel)) as f:
            return f.read()

    @staticmethod
    def write(work, rel, text, mode="w"):
        with open(os.path.join(work, rel), mode) as f:
            f.write(text)

    def sub(self, work, rel, old, new):
        text = self.read(work, rel)
        self.assertIn(old, text)
        self.write(work, rel, text.replace(old, new))

    def timeout_change(self, w):
        self.write(w, "src/config.py", "DEFAULT_TIMEOUT = 30  # seconds\nRETRIES = 2\n")
        self.write(w, "tests/test_client.py", TIMEOUT_TEST, "a")

    # --- exempt scenarios ---

    def test_typo_fix_without_tests_is_expected(self):
        r = self.run_score("typo", lambda w: self.sub(w, "README.md", "recieve", "receive"), [])
        self.assertTrue(r["correct"])
        self.assertEqual((r["test_files_added"], r["test_lines_added"]), (0, 0))
        self.assertIsNone(r["mutants_killed"])
        self.assertTrue(r["expected"])

    def test_test_added_for_exempt_change_is_not_expected(self):
        def change(w):
            self.sub(w, "pyproject.toml", "88", "100")
            self.write(w, "tests/test_config.py",
                       "import unittest\n\n\nclass T(unittest.TestCase):\n"
                       "    def test_line_length(self):\n"
                       "        self.assertIn('line-length = 100', open('pyproject.toml').read())\n")
        r = self.run_score("config", change, [])
        self.assertTrue(r["correct"])
        self.assertEqual((r["test_files_added"], r["test_funcs_added"], r["assertions_added"]), (1, 1, 1))
        self.assertFalse(r["expected"])

    def rename_text(self, w):
        for rel in ("src/text.py", "src/greeting.py", "tests/test_text.py"):
            self.write(w, rel, self.read(w, rel).replace("clean_name", "normalize_name"))

    def rename_money(self, w):
        for rel in ("src/tax.py", "src/invoice.py", "tests/test_tax.py"):
            self.write(w, rel, self.read(w, rel).replace("calc_tax", "compute_tax"))

    def test_rename_keeps_its_assertions(self):
        r = self.run_score("rename", self.rename_text, [])
        self.assertTrue(r["correct"])
        self.assertEqual((r["assertions_added"], r["assertions_removed"]), (0, 0))
        self.assertTrue(r["expected"])
        self.assertFalse(r["verified"])  # no test run seen
        self.assertFalse(r["full_rule"])

    def test_rename_verified_before_and_after(self):
        events = (bash("a", "python3 -m unittest discover -s tests -t . 2>&1 | tail -3", GREEN_OUT)
                  + edit("b", "src/text.py")
                  + bash("c", "python3 -m unittest discover -s tests -t . 2>&1 | tail -3", GREEN_OUT))
        r = self.run_score("rename", self.rename_text, events)
        self.assertTrue(r["verified"])
        self.assertTrue(r["full_rule"])
        # Only after: not verified (no baseline).
        r = self.run_score("rename", self.rename_text, edit("b", "src/text.py") + bash("c", "python3 -m unittest", GREEN_OUT))
        self.assertTrue(r["expected"])
        self.assertFalse(r["verified"])

    def test_run_after_a_batched_edit_counts_as_after(self):
        import score
        self.assertEqual([k for k, _ in score.classify("sed -i '' 's/a/b/' src/text.py && python3 -m unittest")],
                         ["impl_edit", "run"])
        self.assertEqual([k for k, _ in score.classify("python3 -m unittest; sed -i '' 's/a/b/' src/text.py")],
                         ["batched_run", "impl_edit"])  # a baseline, never RED

    def test_batched_runs_are_attributed_only_when_unambiguous(self):
        # Two runs, one summary (grep ate the first run's): which run passed is unknown.
        cmd = ("python3 -m unittest tests.test_slug 2>&1 | grep AssertionError; sed -i '' 's/x/y/' src/slug.py && "
               "python3 -m unittest 2>&1 | tail -3 && git diff")
        def change(w):
            self.write(w, "tests/test_slug.py", "import unittest\nfrom src.slug import slugify\n\n\nclass T(unittest.TestCase):\n"
                       "    def test_lowercase(self):\n        self.assertEqual(slugify('Hello World'), 'hello-world')\n")
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
        out = "AssertionError: 'Hello-World' != 'hello-world'\n----\nRan 9 tests in 0.0s\n\nOK\n"
        r = self.run_score("uncovered", change, edit("a", "tests/test_slug.py") + bash("b", "python3 -m unittest", RED_OUT)
                           + bash("c", cmd, out))
        self.assertTrue(r["failing_first"])
        self.assertFalse(r["verified"])
        # One summary per run, in order: the second (after the edit) is its own and passed.
        cmd2 = ("python3 -m unittest tests.test_slug 2>&1 | tail -1; sed -i '' 's/x/y/' src/slug.py && "
                "python3 -m unittest 2>&1 | tail -3")
        r = self.run_score("uncovered", change, edit("a", "tests/test_slug.py") + bash("b", "python3 -m unittest", RED_OUT)
                           + bash("c", cmd2, "FAILED (failures=1)\nRan 9 tests in 0.0s\n\nOK\n"))
        self.assertTrue(r["verified"])
        r = self.run_score("uncovered", change, edit("a", "tests/test_slug.py") + bash("b", "python3 -m unittest", RED_OUT)
                           + bash("c", cmd2, "OK\nRan 9 tests\n\nFAILED (failures=1)\n"))
        self.assertFalse(r["verified"])

    def test_run_outcome_attribution(self):
        import score
        # A run that never started: its neighbour's OK is not its own.
        out = "Ran 8 tests in 0.0s\n\nOK\n(eval):1: command not found: python\n"
        self.assertEqual((score.run_outcome(out, 0, 2), score.run_outcome(out, 1, 2)), ("unknown", "unknown"))
        out = "Ran 8 tests\n\nOK\n/usr/bin/python3: No module named pytest\n"
        self.assertEqual(score.run_outcome(out, 1, 2), "unknown")
        # Reversed: the startup failure comes first.
        out = "(eval):1: command not found: python\nRan 8 tests in 0.0s\n\nOK\n"
        self.assertEqual((score.run_outcome(out, 0, 2), score.run_outcome(out, 1, 2)), ("unknown", "unknown"))
        self.assertEqual(score.run_outcome("(eval):1: command not found: python\n", 0, 1), "error")
        self.assertEqual(score.run_outcome("Ran 2\n\nFAILED (failures=1)\nRan 2\n\nOK\n", 0, 2), "red")
        self.assertEqual(score.run_outcome("Ran 2\n\nFAILED (failures=1)\nRan 2\n\nOK\n", 1, 2), "green")

    def test_baseline_and_after_from_the_reported_repro(self):
        # python3 OK; edit; python (missing): the OK is the baseline's, not the after-run's.
        cmd = "python3 -m unittest 2>&1 | tail -3; sed -i '' 's/clean_name/normalize_name/g' src/text.py src/greeting.py tests/test_text.py; python -m unittest"
        r = self.run_score("rename", self.rename_text, bash("a", cmd, "Ran 8 tests in 0.0s\n\nOK\n(eval):1: command not found: python\n"))
        self.assertFalse(r["verified"])

    def test_stash_run_output_is_not_a_surviving_red(self):
        # Current tree passes; the stashed (old) tree fails. Only the first run survives, and with
        # two runs in the call its outcome must come from its own summary.
        cmd = "python3 -m unittest tests.test_client 2>&1 | tail -3; git stash -q; python3 -m unittest tests.test_client 2>&1 | tail -3; git stash pop -q"
        events = edit("a", "tests/test_client.py") + bash("b", cmd, "Ran 2 tests\n\nOK\nRan 2 tests\n\nFAILED (failures=1)\n") + edit("c", "src/config.py")
        r = self.run_score("timeout", self.timeout_change, events)
        self.assertFalse(r["failing_first"])
        # And the same output without per-run summaries is unknown, not RED.
        events = edit("a", "tests/test_client.py") + bash("b", cmd, "OK\nAssertionError: 5 != 30\n") + edit("c", "src/config.py")
        self.assertFalse(self.run_score("timeout", self.timeout_change, events)["failing_first"])

    def test_test_edit_after_the_last_green_run_is_not_verified(self):
        events = (bash("a", "python3 -m unittest", GREEN_OUT) + edit("b", "src/text.py")
                  + bash("c", "python3 -m unittest", GREEN_OUT) + edit("d", "tests/test_text.py"))
        self.assertFalse(self.run_score("rename", self.rename_text, events)["verified"])
        events += bash("e", "python3 -m unittest", GREEN_OUT)
        self.assertTrue(self.run_score("rename", self.rename_text, events)["verified"])

    def test_batched_baseline_counts_for_verification_not_red(self):
        import score
        cmd = ("python3 -m unittest 2>&1 | tail -3 && sed -i '' 's/clean_name/normalize_name/g' src/text.py "
               "src/greeting.py tests/test_text.py; python3 -m unittest 2>&1 | tail -3")
        self.assertEqual([k for k, _ in score.classify(cmd)], ["batched_run", "impl_edit", "run"])
        r = self.run_score("rename", self.rename_text, bash("a", cmd, "Ran 8 tests\n\nOK\n...\nRan 8 tests\n\nOK"))
        self.assertTrue(r["verified"])
        # A failing baseline in the same call as the fix is not RED.
        r = self.run_score("timeout", self.timeout_change, edit("a", "tests/test_client.py")
                           + bash("b", "python3 -m unittest 2>&1 | tail -3; sed -i '' 's/5/30/' src/config.py; python3 -m unittest",
                                  "AssertionError\nFAILED (failures=1)\nRan 8\n\nOK"))
        self.assertFalse(r["failing_first"])
        self.assertTrue(r["verified"])

    def test_git_stash_round_trip_is_not_an_edit(self):
        import score
        kinds = lambda c: [k for k, _ in score.classify(c)]
        self.assertEqual(kinds("python3 -m unittest; git stash -q; python3 -m unittest tests.test_invoice; git stash pop -q"), ["run"])
        self.assertEqual(kinds("grep -rn tax src; git diff --stat; git stash list"), [])
        self.assertEqual(kinds("git stash -q; python3 -m unittest"), ["impl_edit", "run"])  # never popped: an edit
        self.assertEqual(kinds("git stash pop"), ["impl_edit"])  # pops an earlier call's stash
        self.assertEqual(kinds("git stash push src/config.py -q"), ["impl_edit"])

    def test_cache_cleanup_is_narrow(self):
        import score
        kinds = lambda c: [k for k, _ in score.classify(c)]
        for cmd in ("find . -name __pycache__ -o -path ./src/config.py -delete",
                    "find . -name '*.pyc' -o -name '*.py' -delete",
                    "find . -name __pycache__ -exec sed -i '' 's/a/b/' {} +",
                    "find . -name __pycache__ -prune -o -name '*.py' -exec rm {} +",
                    "find src -type f -delete"):
            self.assertEqual(kinds(cmd), ["impl_edit"], cmd)
        for cmd in ("find . -name .pytest_cache -type d -exec rm -rf {} +",
                    "find . -type d -name __pycache__ -not -path './.git/*' -exec rm -r {} +",
                    "rm -rf .pytest_cache src/__pycache__"):
            self.assertEqual(kinds(cmd), [], cmd)

    def test_cache_cleanup_is_not_an_edit(self):
        import score
        for cmd in ("find . -name __pycache__ -not -path './.git/*' -exec rm -rf {} +; git status --short",
                    "find . -name '*.pyc' -delete"):
            self.assertEqual([k for k, _ in score.classify(cmd)], [], cmd)
        self.assertEqual([k for k, _ in score.classify("find src -name '*.py' -exec sed -i '' 's/a/b/' {} +")], ["impl_edit"])

    def test_python_probe_blocks_red_but_not_verification(self):
        import score
        probe = 'python3 -c "from src.invoice import invoice_total as t; print(t([(1000, 1)], 0.1, 200))"'
        self.assertEqual([k for k, _ in score.classify(probe)], ["probe_edit"])
        self.assertEqual([k for k, _ in score.classify("python3 -c \"open('src/x.py','w').write('')\"")], ["impl_edit"])
        fix = lambda w: self.sub(w, "src/invoice.py",
                                 "    total = subtotal + calc_tax(subtotal, rate)\n    return max(total - discount_cents, 0)\n",
                                 "    taxable = max(subtotal - discount_cents, 0)\n    return taxable + calc_tax(taxable, rate)\n")
        # A probe before the RED run still erases RED.
        r = self.run_score("deletion", fix, bash("a", probe, "900") + bash("b", "python3 -m unittest", RED_OUT)
                           + edit("c", "src/invoice.py"))
        self.assertFalse(r["failing_first"])
        # A probe after the passing run does not undo verification.
        r = self.run_score("deletion", fix, bash("a", "python3 -m unittest", RED_OUT) + edit("b", "src/invoice.py")
                           + bash("c", "python3 -m unittest", GREEN_OUT) + bash("d", probe, "880"))
        self.assertTrue(r["failing_first"])
        self.assertTrue(r["verified"])

    def test_docs_verified_by_naming_a_check(self):
        change = lambda w: self.write(w, "docs/usage.md", "\n## Configuration\nTimeout: DEFAULT_TIMEOUT.\n", "a")
        r = self.run_score("docs", change, reply("Done.\n\nRisk: routine\nVerified: re-read docs/usage.md against src/client.py\n"))
        self.assertTrue((r["expected"], r["verified"], r["full_rule"]) == (True, True, True))
        for v in ("none", "N/A (docs only)"):
            r = self.run_score("docs", change, reply(f"Done.\nVerified: {v}\nStatus: COMPLETE"))
            self.assertFalse(r["verified"], v)

    def test_money_rename_needs_pinned_run_and_review_and_no_exemption(self):
        pinned = bash("a", "python3 -m unittest discover -s tests -t .", GREEN_OUT)
        after = bash("c", "python3 -m unittest discover -s tests -t .", GREEN_OUT)
        good = reply("Renamed.\n\nRisk: elevated (money)\nVerified: 8 tests OK\nPinned: test_tax\n"
                     "Failing first: none, behavior-preserving rename; test_tax pins it\nReview: OK\nStatus: COMPLETE")
        r = self.run_score("money-rename", self.rename_money,
                           pinned + edit("b", "src/tax.py") + after + agent("d", "Code review of the rename") + good)
        self.assertTrue(r["correct"])
        self.assertEqual((r["pinned_before_edit"], r["review_dispatched"], r["claims_exemption"]), (True, True, False))
        self.assertIn("test_tax pins it", r["failing_first_receipt"])
        self.assertTrue(r["expected"])
        # The saved-run failure: no review, and the receipt treats the rename as exempt routine work.
        bad = reply("Renamed.\n\nRisk: routine\nVerified: tests OK\nFailing first: N/A (exempt rename)\nStatus: COMPLETE")
        r = self.run_score("money-rename", self.rename_money, pinned + edit("b", "src/tax.py") + after + bad)
        self.assertEqual((r["review_dispatched"], r["claims_exemption"], r["expected"]), (False, True, False))
        # Not exempt, said plainly, is not a claim.
        r = self.run_score("money-rename", self.rename_money, pinned + edit("b", "src/tax.py") + after
                           + agent("d", "review", "bp:code-reviewer")
                           + reply("Money code is not exempt.\nRisk: elevated (money)\nFailing first: none, behavior "
                                   "preserved; pinned by tests/test_tax.py\nStatus: COMPLETE"))
        self.assertEqual((r["claims_exemption"], r["expected"]), (False, True))
        # No pinned run before the edit.
        r = self.run_score("money-rename", self.rename_money, edit("b", "src/tax.py") + after
                           + agent("d", "Code review") + good)
        self.assertFalse(r["expected"])

    def test_money_rename_failing_first_says_preserved_and_names_tests(self):
        run = (bash("a", "python3 -m unittest discover -s tests -t .", GREEN_OUT) + edit("b", "src/tax.py")
               + bash("c", "python3 -m unittest discover -s tests -t .", GREEN_OUT) + agent("d", "Code review"))
        receipt = lambda ff: reply(f"Renamed.\nRisk: elevated (money)\nPinned: test_tax passed\nFailing first: {ff}\nStatus: COMPLETE")
        for ff in ("none: behavior preserved; test_tax and test_invoice_total pin it",
                   "no failing test, the rename is behavior-preserving; pinned by tests/test_tax.py",
                   "None. Behaviour is unchanged, so nothing new can fail; TestInvoice pins it",
                   "none: the behavior doesn't change; tests/test_tax.py::test_rounds_half_up pins it"):
            r = self.run_score("money-rename", self.rename_money, run + receipt(ff))
            self.assertEqual((r["failing_first_preserved"], r["expected"]), (True, True), ff)
        # The named test wrapped onto the next line still counts; the next key ends the value.
        r = self.run_score("money-rename", self.rename_money,
                           run + receipt("none, behavior preserved; pinned by\n  tests/test_tax.py"))
        self.assertEqual((r["failing_first_preserved"], r["expected"]), (True, True))
        # A bare placeholder, a reason with no named test, a red run of a renamed test (not a test for
        # the risk), and no line at all.
        for ff in ("N/A", "not applicable, since the change doesn't alter behavior.",
                   "tests/test_tax.py switched to the new name failed with ImportError",
                   "none, no behavior change; the 8 existing tests pin it",
                   "tests/test_tax.py on the new name failed with ImportError. The behavior doesn't change.",
                   "none, behavior preserved; I switched tests/test_tax.py first and saw it fail with ImportError", None):
            text = "Renamed.\nRisk: elevated (money)\nStatus: COMPLETE" if ff is None else None
            r = self.run_score("money-rename", self.rename_money, run + (reply(text) if text else receipt(ff)))
            self.assertEqual((r["failing_first_preserved"], r["expected"]), (False, False), ff)

    def test_money_rename_failing_first_may_point_at_a_pinned_line_that_names_tests(self):
        run = (bash("a", "python3 -m unittest discover -s tests -t .", GREEN_OUT) + edit("b", "src/tax.py")
               + bash("c", "python3 -m unittest discover -s tests -t .", GREEN_OUT) + agent("d", "Code review"))
        receipt = lambda pinned, ff: reply(f"Renamed.\nRisk: elevated (money)\nPinned: {pinned}\n"
                                           f"Failing first: {ff}\nStatus: COMPLETE")
        named = "test_rounds_half_up and test_total_with_tax passed before the edit"
        for ff in ("none, behavior preserved; pinned by the tests above",
                   "none, behavior preserved (see Pinned)", "none; behavior unchanged, the tests listed above pin it"):
            r = self.run_score("money-rename", self.rename_money, run + receipt(named, ff))
            self.assertEqual((r["failing_first_preserved"], r["expected"]), (True, True), ff)
        # Unresolved: the Pinned: line names no test, or there is none, or no pointer at all.
        for pinned, ff in (("the 8 existing tests passed before the edit", "none, behavior preserved; pinned by the tests above"),
                           (named, "none, behavior preserved"),
                           (named, "none, behavior preserved; pinned by the existing suite"),
                           (named, "tests above failed with ImportError; behavior preserved")):
            r = self.run_score("money-rename", self.rename_money, run + receipt(pinned, ff))
            self.assertEqual((r["failing_first_preserved"], r["expected"]), (False, False), (pinned, ff))
        r = self.run_score("money-rename", self.rename_money,
                           run + reply("Renamed.\nRisk: elevated (money)\nFailing first: none, behavior preserved; "
                                       "pinned by the tests above\nStatus: COMPLETE"))
        self.assertFalse(r["failing_first_preserved"])

    # --- plan arm ---

    def plan_run(self, task, text, implement=False):
        def change(w):
            self.write(w, "plan.md", text)
            if implement:
                self.write(w, "src/config.py", "DEFAULT_TIMEOUT = 30\nRETRIES = 2\n")
        return self.run_score("plan-" + task, change, [])

    def test_plan_for_exempt_task_without_a_failing_test_is_expected(self):
        r = self.plan_run("rename", "### Task 1: Rename\n- [ ] Step 1: Run the existing tests (exempt task; no failing test)\n"
                          "- [ ] Step 2: Rename clean_name to normalize_name\n```python\ndef test_normalize_name(self):\n```\n"
                          "- [ ] Step 3: Run tests, expect OK\n")
        self.assertEqual((r["plan_new_tests"], r["plan_failing_step"]), ([], False))
        self.assertTrue(r["expected"])
        self.assertFalse(r["implemented"])

    def test_plan_mutation_check_is_not_a_failing_test_step(self):
        r = self.plan_run("rename", "- [ ] Step 1: Run the existing tests (exempt task)\n- [ ] Step 2: Rename\n"
                          "Temporarily change the body of normalize_name to `return name`.\nRun the tests.\n"
                          "Expected: FAIL in both tests. Restore the body.\n")
        self.assertEqual((r["plan_failing_step"], r["plan_mutation_step"]), (False, True))
        self.assertTrue(r["expected"])

    def test_plan_with_failing_test_for_exempt_task_is_not_expected(self):
        r = self.plan_run("config", "### Task 1\n- [ ] Step 1: Write the failing test\n```python\n"
                          "def test_line_length():\n    assert 'line-length = 100' in open('pyproject.toml').read()\n```\n"
                          "- [ ] Step 2: Run test, verify FAIL\n")
        self.assertEqual((r["plan_new_tests"], r["plan_failing_step"]), (["test_line_length"], True))
        self.assertFalse(r["expected"])

    def test_plan_for_timeout_needs_a_failing_test(self):
        good = self.plan_run("timeout", "- [ ] Step 1: Write the failing test\n```python\n"
                             "def test_default_timeout_is_30(self):\n```\n- [ ] Step 2: Run it, verify FAIL\n", implement=True)
        self.assertTrue(good["expected"])
        self.assertTrue(good["implemented"])
        bad = self.plan_run("timeout", "- [ ] Step 1: Change DEFAULT_TIMEOUT to 30 and run the existing tests\n")
        self.assertFalse(bad["expected"])
        self.assertFalse(self.run_score("plan-timeout", lambda w: None, [])["correct"])

    # --- assertion removal ---

    def test_deleted_assertion_counts_as_removal(self):
        def change(w):
            self.sub(w, "tests/test_invoice.py",
                     "    def test_discount_before_tax(self):\n"
                     "        self.assertEqual(invoice_total([(1000, 1)], 0.1, discount_cents=200), 880)\n\n", "")
        r = self.run_score("deletion", change, [])
        self.assertEqual(r["assertions_removed"], 1)
        self.assertFalse(r["correct"])
        self.assertFalse(r["expected"])

    def test_assertion_replaced_by_vacuous_one_counts_as_removal(self):
        # Code fixed, but the discount-boundary assertion became assertTrue(True): net count is 0.
        def change(w):
            self.sub(w, "src/invoice.py",
                     "    total = subtotal + calc_tax(subtotal, rate)\n    return max(total - discount_cents, 0)\n",
                     "    taxable = max(subtotal - discount_cents, 0)\n    return taxable + calc_tax(taxable, rate)\n")
            self.sub(w, "tests/test_invoice.py",
                     "self.assertEqual(invoice_total([(100, 1)], 0.1, discount_cents=500), 0)", "self.assertTrue(True)")
        r = self.run_score("deletion", change, [])
        self.assertTrue(r["correct"])
        self.assertEqual((r["assertions_added"], r["assertions_removed"]), (1, 1))
        self.assertFalse(r["expected"])

    # --- RED order ---

    def test_uncovered_fix_with_failing_test_first_is_expected(self):
        def change(w):
            self.write(w, "tests/test_slug.py",
                       "import unittest\nfrom src.slug import slugify\n\n\nclass T(unittest.TestCase):\n"
                       "    def test_lowercase(self):\n        self.assertEqual(slugify('Hello World'), 'hello-world')\n")
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
        events = (bash("a", "cat > tests/test_slug.py <<'EOF'\nfrom src.slug import slugify\nEOF")
                  + bash("b", "python3 -m unittest tests.test_slug", RED_OUT)
                  + edit("c", "/tmp/w/src/slug.py")
                  + bash("d", "python3 -m unittest discover -s tests -t .", "OK"))
        r = self.run_score("uncovered", change, events)
        self.assertTrue(r["test_first"])
        self.assertTrue(r["failing_first"])
        self.assertTrue(r["mutants_killed"])
        self.assertTrue(r["expected"])

    def test_failure_after_src_edit_is_not_failing_first(self):
        events = edit("a", "src/config.py") + bash("b", "python3 -m unittest", RED_OUT)
        r = self.run_score("timeout", self.timeout_change, events)
        self.assertTrue(r["correct"])
        self.assertFalse(r["failing_first"])
        self.assertFalse(r["expected"])

    def test_run_batched_with_src_edit_is_not_failing_first(self):
        # Test written first, but run in the same command as the edit: no failure was watched.
        events = (edit("a", "/tmp/w/tests/test_client.py")
                  + bash("b", "python3 -m unittest tests.test_client 2>&1 | tail -6\n"
                              "sed -i '' 's/= 5 /= 30 /' src/config.py", RED_OUT)
                  + bash("c", "git stash push src/config.py -q; python3 -m unittest; git stash pop -q", RED_OUT))
        r = self.run_score("timeout", self.timeout_change, events)
        self.assertTrue(r["test_first"])
        self.assertFalse(r["failing_first"])
        self.assertFalse(r["expected"])

    def test_python_write_to_src_is_an_edit(self):
        # Path(...).write_text in an interpreter heredoc changes src/ before the failing run.
        events = (bash("a", "python3 - <<'EOF'\nfrom pathlib import Path\n"
                            "Path('src/config.py').write_text('DEFAULT_TIMEOUT = 30\\nRETRIES = 2\\n')\nEOF")
                  + bash("b", "python3 -m unittest tests.test_client", RED_OUT))
        r = self.run_score("timeout", self.timeout_change, events)
        self.assertFalse(r["failing_first"])
        self.assertFalse(r["expected"])

    def test_read_next_to_a_test_write_is_not_an_edit(self):
        # cat src/bot.py only reads; the redirect writes tests/. Then RED, then the prompt edit.
        def change(w):
            self.skillmd_test(w, TRIAGE_RULE.strip("- \n"))
            self.write(w, "prompts/triage.md", TRIAGE_RULE, "a")
        events = (bash("a", "cat src/bot.py; cat >> tests/test_prompts.py <<'EOF'\n    def t(self): pass\nEOF\n"
                            "python3 -m unittest tests.test_prompts 2>&1 | tail -5", "FAILED (failures=1)")
                  + bash("b", "python3 - <<'EOF'\np='prompts/triage.md'\nopen(p,'w').write('x')\nEOF"))
        r = self.run_score("skillmd", change, events)
        self.assertTrue(r["test_first"])
        self.assertTrue(r["failing_first"])
        self.assertTrue(r["expected"])

    def test_sed_next_to_a_test_write_is_an_edit(self):
        events = bash("a", "cat >> tests/test_client.py <<'EOF'\nx\nEOF\nsed -i '' 's/5/30/' src/config.py\n"
                           "python3 -m unittest", RED_OUT)
        r = self.run_score("timeout", self.timeout_change, events)
        self.assertTrue(r["test_first"])  # the test write comes first in the command
        self.assertFalse(r["failing_first"])

    def test_runner_or_import_failure_is_not_red(self):
        for out in ("/opt/homebrew/bin/python3: No module named pytest",
                    "(eval):1: command not found: python",
                    "ERROR: tests.test_client\nImportError: cannot import name 'request_options'\nFAILED (errors=1)",
                    "Ran 2 tests in 0.000s\n\nFAILED (errors=1)"):
            events = bash("a", "python3 -m pytest tests/test_client.py", out) + edit("b", "src/config.py")
            r = self.run_score("timeout", self.timeout_change, events)
            self.assertFalse(r["failing_first"], out)

    def test_tailed_unittest_failure_count_is_red(self):
        # `| tail -3` keeps only the summary; failures= (not errors=) means an assertion failed.
        events = (edit("a", "tests/test_client.py")
                  + bash("b", "python3 -m unittest tests.test_client 2>&1 | tail -3", "Ran 2 tests in 0.000s\n\nFAILED (failures=1)")
                  + edit("c", "src/config.py"))
        r = self.run_score("timeout", self.timeout_change, events)
        self.assertTrue(r["failing_first"])
        self.assertTrue(r["expected"])

    def test_python_import_of_test_file_is_a_run(self):
        def change(w):
            self.write(w, "tests/test_slug.py",
                       "from src.slug import slugify\n\n\ndef test_lower():\n"
                       "    assert slugify('Hello World') == 'hello-world'\n")
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
        events = (bash("a", "cat > tests/test_slug.py <<'EOF'\n...\nEOF")
                  + bash("b", 'python3 -c "\nfrom tests.test_slug import *\ntest_lower()"', "AssertionError")
                  + bash("c", "sed -i '' 's/x/y/' src/slug.py"))
        r = self.run_score("uncovered", change, events)
        self.assertTrue(r["failing_first"])
        self.assertTrue(r["correct"])
        self.assertTrue(r["expected"])

    # --- final suite ---

    def test_failing_plain_test_function_fails_the_suite(self):
        # unittest discovery would skip this pytest-style function; the scorer must run it.
        def change(w):
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
            self.write(w, "tests/test_slug.py",
                       "from src.slug import slugify\n\n\ndef test_lower():\n    assert slugify('A') == 'b'\n")
        r = self.run_score("uncovered", change, [])
        self.assertFalse(r["correct"])
        self.assertFalse(r["expected"])

    def test_test_needing_a_fixture_fails_the_suite(self):
        def change(w):
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
            self.write(w, "tests/test_slug.py", "def test_lower(tmp_path):\n    assert True\n")
        self.assertFalse(self.run_score("uncovered", change, [])["correct"])

    # --- mutants: a test must fail when the behavior it claims to pin breaks ---

    def test_test_that_survives_a_small_break_is_not_expected(self):
        # assertGreater passes for 29 too: it does not pin the 30-second default.
        def change(w):
            self.write(w, "src/config.py", "DEFAULT_TIMEOUT = 30  # seconds\nRETRIES = 2\n")
            self.write(w, "tests/test_client.py", "\n    def test_default_timeout(self):\n"
                       "        self.assertGreater(request_options()['timeout'], 5)\n", "a")
        events = (edit("a", "tests/test_client.py") + bash("b", "python3 -m unittest", RED_OUT)
                  + edit("c", "src/config.py"))
        r = self.run_score("timeout", change, events)
        self.assertTrue(r["failing_first"])
        self.assertFalse(r["mutants_killed"])
        self.assertFalse(r["expected"])

    # --- prompt file (skillmd) ---

    def skillmd_test(self, w, phrase):
        self.write(w, "tests/test_prompts.py", "\n    def test_order_number(self):\n"
                   f"        self.assertIn({phrase!r}, system_prompt('triage'))\n", "a")

    def test_prompt_rule_with_red_before_edit_is_expected(self):
        def change(w):
            self.skillmd_test(w, TRIAGE_RULE.strip("- \n"))
            self.write(w, "prompts/triage.md", TRIAGE_RULE, "a")
        events = (edit("a", "/tmp/w/tests/test_prompts.py") + bash("b", "python3 -m unittest", RED_OUT)
                  + edit("c", "/tmp/w/prompts/triage.md"))
        r = self.run_score("skillmd", change, events)
        self.assertTrue(r["correct"])
        self.assertTrue(r["failing_first"])
        self.assertTrue(r["mutants_killed"])
        self.assertTrue(r["expected"])

    def test_prompt_edit_before_red_is_not_failing_first(self):
        def change(w):
            self.skillmd_test(w, TRIAGE_RULE.strip("- \n"))
            self.write(w, "prompts/triage.md", TRIAGE_RULE, "a")
        events = (edit("a", "/tmp/w/prompts/triage.md") + edit("b", "/tmp/w/tests/test_prompts.py")
                  + bash("c", "python3 -m unittest", RED_OUT))
        r = self.run_score("skillmd", change, events)
        self.assertFalse(r["test_first"])
        self.assertFalse(r["failing_first"])
        self.assertFalse(r["expected"])

    def test_opposite_prompt_rule_is_not_correct(self):
        rule = "- For billing tickets, never ask for the order number before anything else.\n"
        def change(w):
            self.skillmd_test(w, rule.strip("- \n"))
            self.write(w, "prompts/triage.md", rule, "a")
        events = (edit("a", "/tmp/w/tests/test_prompts.py") + bash("b", "python3 -m unittest", RED_OUT)
                  + edit("c", "/tmp/w/prompts/triage.md"))
        r = self.run_score("skillmd", change, events)
        self.assertFalse(r["correct"])
        self.assertFalse(r["expected"])

    def test_prompt_rule_without_billing_or_order_is_not_correct(self):
        for rule in ("- Ask for the customer's order number before anything else.\n",
                     "- For billing tickets, ask for the customer's order number.\n"):
            r = self.run_score("skillmd", lambda w, rule=rule: self.write(w, "prompts/triage.md", rule, "a"), [])
            self.assertFalse(r["correct"], rule)

    # --- round 3: plain test classes, prompt ordering, write forms, weak and disabled tests ---

    def test_failing_plain_test_class_fails_the_suite(self):
        def change(w):
            self.timeout_change(w)
            self.write(w, "tests/test_plain.py", "class TestPlain:\n    def test_bad(self):\n        assert False\n")
        r = self.run_score("timeout", change, edit("a", "tests/test_client.py")
                           + bash("b", "python3 -m unittest", RED_OUT) + edit("c", "src/config.py"))
        self.assertFalse(r["correct"])
        self.assertFalse(r["expected"])

    def test_plain_class_needing_arguments_fails_the_suite(self):
        def change(w):
            self.timeout_change(w)
            self.write(w, "tests/test_plain.py", "class TestPlain:\n    def __init__(self, x):\n        pass\n\n"
                       "    def test_ok(self):\n        assert True\n")
        self.assertFalse(self.run_score("timeout", change, [])["correct"])

    def test_prompt_rule_with_reversed_order_is_not_correct(self):
        for rule in ("- For billing tickets, ask for the order number only after greeting first.\n",
                     "- For billing tickets, ask for the order number once you have greeted them first.\n",
                     "- For billing tickets, greet first, then ask for the order number.\n",
                     "- For billing tickets, greet before you ask for the order number.\n",
                     "- For billing tickets, do not ask for the order number before anything else.\n"):
            def change(w, rule=rule):
                self.skillmd_test(w, rule.strip("- \n"))
                self.write(w, "prompts/triage.md", rule, "a")
            r = self.run_score("skillmd", change, edit("a", "tests/test_prompts.py")
                               + bash("b", "python3 -m unittest", RED_OUT) + edit("c", "prompts/triage.md"))
            self.assertFalse(r["correct"], rule)
            self.assertFalse(r["expected"], rule)

    def test_prompt_rule_phrasings_that_put_the_ask_first(self):
        import score
        for rule in ("For billing tickets, ask for the customer's order number before anything else.",
                     "For billing tickets, first ask for the order number.",
                     "Billing tickets: ask for the order number first.",
                     "For billing tickets, before anything else, ask for the order number.",
                     "When handling billing tickets, ask for the customer's order number before anything else",
                     "For billing tickets, ask for the order number first, then greet the customer"):
            self.assertTrue(score.triage_rule_ok(rule), rule)

    def test_prompt_rule_with_condition_or_later_steps_is_expected(self):
        for rule in ("- When handling billing tickets, ask for the customer's order number before anything else.\n",
                     "- For billing tickets, ask for the order number first, then greet the customer.\n"):
            def change(w, rule=rule):
                self.skillmd_test(w, rule.strip("- \n"))
                self.write(w, "prompts/triage.md", rule, "a")
            r = self.run_score("skillmd", change, edit("a", "tests/test_prompts.py")
                               + bash("b", "python3 -m unittest", RED_OUT) + edit("c", "prompts/triage.md"))
            self.assertTrue(r["correct"], rule)
            self.assertTrue(r["mutants_killed"], rule)
            self.assertTrue(r["expected"], rule)

    def test_perl_and_sed_in_place_next_to_a_red_run_are_edits(self):
        for cmd in ("python3 -m unittest tests.test_client 2>&1 | tail -3; perl -pi -e 's/= 5 /= 30 /' src/config.py",
                    "python3 -m unittest tests.test_client; sed --in-place 's/= 5 /= 30 /' src/config.py",
                    "python3 -m unittest tests.test_client && sed -Ei '' 's/5/30/' src/config.py",
                    "python3 -m unittest tests.test_client; python3 -c \"import re; p='src/config.py'\"",
                    "python3 -m unittest tests.test_client; dd if=/tmp/x of=src/config.py",
                    "python3 -m unittest tests.test_client; awk '{print > \"src/config.py\"}' /tmp/x",
                    "python3 -m unittest tests.test_client; git apply /tmp/p.diff",
                    "python3 -m unittest tests.test_client; ruby -i -pe 'x' src/config.py"):
            events = edit("a", "tests/test_client.py") + bash("b", cmd, RED_OUT)
            r = self.run_score("timeout", self.timeout_change, events)
            self.assertFalse(r["failing_first"], cmd)

    def test_read_only_tools_are_not_edits(self):
        import score
        for cmd in ("cat src/config.py; grep -rn TIMEOUT src | head -3",
                    "sed -n '1,5p' src/config.py && git diff src/ && git status --short",
                    "python3 -m unittest discover -s tests -t . 2>&1 | tail -3",
                    "find src -name '*.py'",
                    "rm -rf src/__pycache__ tests/__pycache__"):
            self.assertNotIn("impl_edit", [k for k, _ in score.classify(cmd)], cmd)

    def test_class_fixtures_run_in_the_suite_and_alone(self):
        # setUpClass is only called when the case runs through a TestSuite.
        def change(w):
            self.write(w, "src/config.py", "DEFAULT_TIMEOUT = 30  # seconds\nRETRIES = 2\n")
            self.write(w, "tests/test_defaults.py",
                       "import unittest\nfrom src.client import request_options\n\n\n"
                       "def setUpModule():\n    global READY\n    READY = True\n\n\n"
                       "class Defaults(unittest.TestCase):\n"
                       "    @classmethod\n    def setUpClass(cls):\n        cls.opts = request_options()\n\n"
                       "    def test_default_timeout(self):\n        self.assertTrue(READY)\n"
                       "        self.assertEqual(self.opts['timeout'], 30)\n")
        events = edit("a", "tests/test_defaults.py") + bash("b", "python3 -m unittest", RED_OUT) + edit("c", "src/config.py")
        r = self.run_score("timeout", change, events)
        self.assertTrue(r["correct"])
        self.assertTrue(r["mutants_killed"])
        self.assertEqual(r["weak_tests"], [])
        self.assertTrue(r["expected"])

    def test_output_capture_and_inspection_are_not_edits(self):
        import score
        kinds = lambda c, root=None: [k for k, _ in score.classify(c, root)]
        self.assertEqual(kinds("python3 -m unittest tests.test_client > /tmp/red.txt 2>&1; cat /tmp/red.txt"), ["run"])
        self.assertEqual(kinds("python3 -m unittest tests.test_client 2>&1 | tee /tmp/red.log"), ["run"])
        self.assertEqual(kinds('python3 -m unittest 2>&1 | tee "$TMPDIR/red.log"'), ["run"])
        self.assertEqual(kinds("git -C . status --short; git -c core.pager=cat --no-pager diff"), [])
        self.assertEqual(kinds("ls src/*.py | xargs -I {} cat {}; ls | xargs -n 1 wc -l"), [])
        self.assertEqual(kinds("git -C . checkout src/config.py"), ["impl_edit"])
        self.assertEqual(kinds("ls | xargs -I {} sed -i '' 's/a/b/' {}"), ["impl_edit"])
        # Absolute paths: outside the run's work tree is capture, inside is an edit.
        self.assertEqual(kinds("python3 -m unittest > /work/out/red.txt", "/other"), ["run"])
        self.assertEqual(kinds("python3 -m unittest; echo x > /work/src/config.py", "/work"), ["batched_run", "impl_edit"])
        self.assertEqual(kinds("python3 -m unittest | tee /work/tests/log.txt", "/work"), ["run", "test_edit"])
        self.assertEqual(kinds("python3 -m unittest | tee /tmp/tests/red.log", "/work"), ["run"])

    def test_red_captured_to_a_file_is_red(self):
        for cmd in ("python3 -m unittest tests.test_client > /tmp/red.txt 2>&1; cat /tmp/red.txt",
                    "python3 -m unittest tests.test_client 2>&1 | tee /tmp/red.log"):
            events = edit("a", "tests/test_client.py") + bash("b", cmd, RED_OUT) + edit("c", "src/config.py")
            r = self.run_score("timeout", self.timeout_change, events)
            self.assertTrue(r["failing_first"], cmd)
            self.assertTrue(r["expected"], cmd)

    def test_parser_cases_found_in_saved_transcripts(self):
        import score
        kinds = lambda c: [k for k, _ in score.classify(c)]
        # A subshell run right after a cat heredoc: shlex fuses ";(".
        self.assertEqual(kinds("cat >> tests/t.py <<'EOF'\nx\nEOF\n(python3 -m unittest tests.t 2>&1 | tail -8)"),
                         ["test_edit", "run"])
        # The heredoc belongs to python3, not to the cat earlier on the line: its body writes tests/.
        self.assertEqual(kinds("cat src/bot.py; python3 - <<'EOF'\np='tests/test_p.py'\nopen(p,'w').write('x')\nEOF\n"
                               "python3 -m unittest"), ["test_edit", "run"])
        self.assertEqual(kinds("cat src/bot.py; python3 - <<'EOF'\nopen('src/bot.py','w').write('x')\nEOF"), ["impl_edit"])
        self.assertEqual(kinds("find . -name '*.py' | xargs cat; python -m pytest -q 2>&1 | tail -30"), ["run"])
        self.assertEqual(kinds("find . -name '*.py' | xargs sed -i '' 's/a/b/'"), ["impl_edit"])
        self.assertEqual(kinds("python3 --version; python3 -m pytest --version; python3 -m ruff --version"), [])

    def test_weak_slug_test_survives_mutants(self):
        # != "Hello-World" passes for "hello-worldx" too: it does not pin the slug.
        def change(w):
            self.write(w, "tests/test_slug.py",
                       "import unittest\nfrom src.slug import slugify\n\n\nclass T(unittest.TestCase):\n"
                       "    def test_lowercase(self):\n        self.assertNotEqual(slugify('Hello World'), 'Hello-World')\n")
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
        events = (edit("a", "tests/test_slug.py") + bash("b", "python3 -m unittest", RED_OUT) + edit("c", "src/slug.py"))
        r = self.run_score("uncovered", change, events)
        self.assertTrue(r["correct"])
        # The revert mutant kills it (old output is exactly "Hello-World"), so it is not weak;
        # the appended-x mutant survives the suite, so mutants_killed is False.
        self.assertFalse(r["mutants_killed"])
        self.assertFalse(r["expected"])

    def test_new_test_that_pins_nothing_is_weak_even_if_the_suite_kills(self):
        # A good test kills every mutant; an extra test that only checks the type pins nothing.
        def change(w):
            self.write(w, "tests/test_slug.py",
                       "import unittest\nfrom src.slug import slugify\n\n\nclass T(unittest.TestCase):\n"
                       "    def test_lowercase(self):\n        self.assertEqual(slugify('Hello World'), 'hello-world')\n\n"
                       "    def test_returns_str(self):\n        self.assertIsInstance(slugify('A'), str)\n")
            self.sub(w, "src/slug.py", '.strip("-")', '.strip("-").lower()')
        events = (edit("a", "tests/test_slug.py") + bash("b", "python3 -m unittest", RED_OUT) + edit("c", "src/slug.py"))
        r = self.run_score("uncovered", change, events)
        self.assertTrue(r["mutants_killed"])
        self.assertEqual(r["weak_tests"], ["tests/test_slug.py::T::test_returns_str"])
        self.assertFalse(r["expected"])

    def fix_invoice(self, w):
        self.sub(w, "src/invoice.py",
                 "    total = subtotal + calc_tax(subtotal, rate)\n    return max(total - discount_cents, 0)\n",
                 "    taxable = max(subtotal - discount_cents, 0)\n    return taxable + calc_tax(taxable, rate)\n")

    def test_disabled_boundary_test_counts_as_removal(self):
        boundary = "    def test_discount_never_negative(self):\n"
        for disable in ("    @unittest.skip('flaky')\n" + boundary,
                        "    @unittest.expectedFailure\n" + boundary,
                        "    @unittest.skipIf(True, 'later')\n" + boundary,
                        "    def xtest_discount_never_negative(self):\n",
                        boundary + "        return\n",
                        boundary + "        self.skipTest('later')\n"):
            def change(w, disable=disable):
                self.fix_invoice(w)
                text = self.read(w, "tests/test_invoice.py").replace(boundary, disable)
                self.write(w, "tests/test_invoice.py", "import unittest\n" + text)
            r = self.run_score("deletion", change, [])
            self.assertEqual(r["assertions_removed"], 1, disable)
            self.assertFalse(r["expected"], disable)

    def test_commented_out_assertion_counts_as_removal(self):
        def change(w):
            self.fix_invoice(w)
            self.sub(w, "tests/test_invoice.py",
                     "        self.assertEqual(invoice_total([(100, 1)], 0.1, discount_cents=500), 0)",
                     "        # self.assertEqual(invoice_total([(100, 1)], 0.1, discount_cents=500), 0)\n        pass")
        r = self.run_score("deletion", change, [])
        self.assertEqual(r["assertions_removed"], 1)
        self.assertFalse(r["expected"])

    def test_pytest_skip_marks_count_as_removal(self):
        import score
        before = "def test_a():\n    assert f(1) == 2\n"
        for after in ("import pytest\n@pytest.mark.skip\ndef test_a():\n    assert f(1) == 2\n",
                      "import pytest\n@pytest.mark.xfail\ndef test_a():\n    assert f(1) == 2\n",
                      "import pytest\ndef test_a():\n    pytest.skip('x')\n    assert f(1) == 2\n"):
            self.assertEqual(score.assertions(before), ["assert _(1) == 2"])
            self.assertEqual(score.assertions(after), [], after)

    def test_deletion_fixed_properly_is_expected(self):
        r = self.run_score("deletion", self.fix_invoice, bash("a", "python3 -m unittest", RED_OUT) + edit("b", "src/invoice.py"))
        self.assertTrue(r["correct"])
        self.assertTrue(r["mutants_killed"])
        self.assertEqual((r["assertions_removed"], r["weak_tests"]), (0, []))
        self.assertTrue(r["expected"])

    # --- cost, runner ---

    def test_cost_is_cumulative_per_session(self):
        events = [
            {"type": "result", "session_id": "s1", "total_cost_usd": 0.10},
            {"type": "result", "session_id": "s1", "total_cost_usd": 0.18},
            {"type": "result", "session_id": "s2", "total_cost_usd": 0.05},
        ]
        r = self.run_score("docs", lambda w: None, events)
        self.assertAlmostEqual(r["cost"], 0.23)
        self.assertFalse(r["correct"])

    def test_implementer_prompt_renders_with_the_task(self):
        path = os.path.join(HERE, "..", "..", "skills", "subagent-driven-development", "implementer-prompt.md")
        out = subprocess.run([sys.executable, os.path.join(HERE, "implementer.py"), path, "Fix the typo. Quickly."],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("You are implementing Task 1: Fix the typo", out)
        self.assertIn("\nFix the typo. Quickly.\n", out)
        self.assertNotIn("[FULL TEXT", out)
        self.assertNotIn("[directory]", out)
        self.assertFalse(out.startswith(" "))


if __name__ == "__main__":
    unittest.main()
