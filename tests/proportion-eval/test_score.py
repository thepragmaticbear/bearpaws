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


def edit(cmd_id, path):
    return [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": cmd_id, "name": "Edit", "input": {"file_path": path}}]}}]


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

    def test_rename_keeps_its_assertions(self):
        def change(w):
            for rel in ("src/tax.py", "src/invoice.py", "tests/test_tax.py"):
                self.write(w, rel, self.read(w, rel).replace("calc_tax", "compute_tax"))
        r = self.run_score("rename", change, [])
        self.assertTrue(r["correct"])
        self.assertEqual((r["assertions_added"], r["assertions_removed"]), (0, 0))
        self.assertTrue(r["expected"])

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
        self.assertFalse(r["test_first"])
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
        self.assertEqual(kinds("python3 -m unittest; echo x > /work/src/config.py", "/work"), ["impl_edit"])
        self.assertEqual(kinds("python3 -m unittest | tee /work/tests/log.txt", "/work"), ["test_edit", "run"])
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
