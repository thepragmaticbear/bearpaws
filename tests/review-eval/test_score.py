#!/usr/bin/env python3
"""Scorer tests: which text counts as a blocking issue, and what the verdict line means."""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score  # noqa: E402


class BlockingIssuesTest(unittest.TestCase):
    def test_gate_prose_is_not_a_blocking_issue(self):
        text = ("### [GATE] Failure Mode Enumeration\n"
                "1. It is important to consider a negative amount here.\n\n"
                "### Issues\n#### Critical (Must Fix)\nNone\n#### Important (Should Fix)\nNone\n"
                "#### Minor (Nice to Have)\n- consider TOCTOU\n")
        self.assertEqual(score.blocking_issues(text).strip(), "")

    def test_suggestions_heading_ends_the_blocking_section(self):
        text = ("### Issues\n#### Critical\nNone\n#### Important\n- cap only, no sign check\n"
                "#### Suggestions\n- harden against a TOCTOU race\n### [GATE] What would have to be true\n")
        blocking = score.blocking_issues(text)
        self.assertIn("sign check", blocking)
        self.assertNotIn("TOCTOU", blocking)

    def test_important_section_is_kept(self):
        text = "#### Critical (Must Fix)\nNone\n#### Important (Should Fix)\n- negative amount accepted\n#### Minor\n- style\n"
        self.assertIn("negative amount", score.blocking_issues(text))


class ReimplementsHelperTest(unittest.TestCase):
    def blocking(self, important):
        text = f"#### Critical\nNone\n#### Important\n- {important}\n#### Minor\n- style\n"
        return bool(re.search(score.DEFECTS["reimplements_helper_blocking"], score.blocking_issues(text), re.I))

    def test_reuse_finding_counts(self):
        self.assertTrue(self.blocking("src/duration.py reimplements hms_seconds in src/clock.py; call it"))

    def test_unrelated_already_has_does_not_count(self):
        self.assertFalse(self.blocking("the report says 7 tests but the file already has 10 tests"))


class VerdictTest(unittest.TestCase):
    def test_bare_yes_approves(self):
        self.assertFalse(score.verdict_reject("**Ready to merge?** Yes\n"))

    def test_conditional_yes_rejects(self):
        for line in ("Ready to merge? Yes, after adding the sign check", "Ready to merge? Yes with fixes",
                     "Ready to merge? Yes once the cap is tested"):
            self.assertTrue(score.verdict_reject(line), line)

    def test_no_rejects(self):
        self.assertTrue(score.verdict_reject("Ready to merge? No. The sign check is missing."))


GREEN_REPLY = """### Finding Verdicts
- Finding 1 (negative amount): ADDRESSED — src/billing.py:9 raises ValueError for amount_cents < 0; test_negative_raises covers it.
- Finding 2 (running total): NOT ADDRESSED — src/billing.py:11 still compares amount_cents with total_cents only; refund(order, 600) twice records 1200.

### New Breakage in the Fix Diff
- **Important** — src/billing.py:9: the check is `< 0`, so refund(order, 0) is accepted; the task says amounts must be positive.

### Break Attempts
- Tried: [reasoned] refund(Order(1000), -1) — raises ValueError.
- Tried: [reasoned] two refunds of 600 on a 1000-cent order — both succeed, 1200 recorded.

### What I didn't check
- report() and its SQL, outside the fix diff.

### Out-of-Scope Observations
- src/billing.py:17 report() builds SQL by string concatenation (injection). Pre-existing; not in the fix diff.

### Verdict
Findings remain open: finding 2, and the zero-amount check.
"""

RED_REPLY = """### Issues
#### Critical (Must Fix)
1. **SQL injection in report()** — src/billing.py:19 concatenates customer into the query.
#### Important (Should Fix)
1. **Cumulative cap missing** — src/billing.py:11 ignores refunded_cents, so two refunds of 600 record 1200.
2. **Zero accepted** — src/billing.py:9 uses `< 0`, so refund(order, 0) passes.
#### Minor (Nice to Have)
- docstring style
### Assessment
**Ready to merge?** No
"""


class RereviewTest(unittest.TestCase):
    def test_green_reply_passes(self):
        r = score.rereview_score(GREEN_REPLY)
        self.assertEqual((r["f1"], r["f2"]), ("ADDRESSED", "NOT ADDRESSED"))
        self.assertIn("new breakage", r["zero_section"])
        self.assertEqual(r["zero_severity"], "important")
        self.assertTrue(r["sql_only_out_of_scope"])
        self.assertFalse(r["sql_blocking"])
        self.assertTrue(r["findings_remain_open"])
        self.assertTrue(score.rereview_pass(r))

    def test_full_review_reply_has_no_verdicts_and_blocks_on_sql(self):
        r = score.rereview_score(RED_REPLY)
        self.assertEqual((r["f1"], r["f2"]), (None, None))
        self.assertTrue(r["f2_blocking"])
        self.assertEqual(r["zero_severity"], "important")
        self.assertNotIn("new breakage", r["zero_section"])
        self.assertTrue(r["sql_blocking"])
        self.assertFalse(r["sql_only_out_of_scope"])
        self.assertFalse(score.rereview_pass(r))

    def test_attempted_fix_marked_addressed_fails(self):
        r = score.rereview_score(GREEN_REPLY.replace("NOT ADDRESSED", "ADDRESSED"))
        self.assertEqual(r["f2"], "ADDRESSED")
        self.assertFalse(score.rereview_pass(r))

    def test_minor_zero_bug_fails(self):
        r = score.rereview_score(GREEN_REPLY.replace("**Important** — src/billing.py:9", "**Minor** — src/billing.py:9"))
        self.assertEqual(r["zero_severity"], "minor")
        self.assertFalse(score.rereview_pass(r))

    def test_sql_as_new_breakage_fails(self):
        reply = GREEN_REPLY.replace("### Break Attempts",
                                    "- **Important** — src/billing.py:17: SQL injection in report().\n\n### Break Attempts")
        r = score.rereview_score(reply)
        self.assertTrue(r["sql_blocking"])
        self.assertFalse(r["sql_only_out_of_scope"])
        self.assertFalse(score.rereview_pass(r))

    def test_severity_subheadings_inside_new_breakage(self):
        reply = GREEN_REPLY.replace(
            "- **Important** — src/billing.py:9: the check",
            "#### Important\n- src/billing.py:9: the check")
        r = score.rereview_score(reply)
        self.assertEqual((r["zero_severity"], score.rereview_pass(r)), ("important", True))

    def test_unlabelled_severity_word_does_not_set_severity(self):
        reply = GREEN_REPLY.replace(
            "- **Important** — src/billing.py:9: the check is `< 0`, so refund(order, 0) is accepted; the task says amounts must be positive.",
            "- Not critical: src/billing.py:9 uses `< 0`, so refund(order, 0) is accepted. Severity: Minor.")
        r = score.rereview_score(reply)
        self.assertEqual(r["zero_severity"], "minor")
        self.assertFalse(score.rereview_pass(r))

    def test_f2_duplicate_is_not_the_zero_bug(self):
        reply = GREEN_REPLY.replace(
            "- **Important** — src/billing.py:9: the check is `< 0`, so refund(order, 0) is accepted; the task says amounts must be positive.",
            "- **Important** — src/billing.py:11: non-positive headroom: refunded_cents + amount_cents can pass 0 cents left; same as finding 2.")
        r = score.rereview_score(reply)
        self.assertNotIn("new breakage", r["zero_section"] or "")
        self.assertFalse(score.rereview_pass(r))

    def test_verdict_must_say_findings_remain_open(self):
        reply = GREEN_REPLY.replace("Findings remain open: finding 2, and the zero-amount check.",
                                    "All findings addressed, no new Critical/Important")
        r = score.rereview_score(reply)
        self.assertFalse(r["findings_remain_open"])
        self.assertFalse(score.rereview_pass(r))

    def test_break_attempts_required(self):
        reply = re.sub(r"- Tried:[^\n]*\n", "", GREEN_REPLY)
        r = score.rereview_score(reply)
        self.assertEqual(r["break_attempts"], 0)
        self.assertFalse(score.rereview_pass(r))

    def test_first_uppercase_verdict_token_wins(self):
        reply = GREEN_REPLY.replace(
            "ADDRESSED — src/billing.py:9 raises ValueError for amount_cents < 0;",
            "ADDRESSED — src/billing.py:9 raises ValueError for amount_cents < 0; zero is not addressed here (see New Breakage);")
        r = score.rereview_score(reply)
        self.assertEqual(r["f1"], "ADDRESSED")
        self.assertTrue(score.rereview_pass(r))

    ZERO_LINE = ("- **Important** — src/billing.py:9: the check is `< 0`, so refund(order, 0) is accepted; "
                 "the task says amounts must be positive.")

    def with_zero_line(self, line):
        self.assertIn(self.ZERO_LINE, GREEN_REPLY)
        return score.rereview_score(GREEN_REPLY.replace(self.ZERO_LINE, line))

    def test_severity_label_forms_pass(self):
        for line in ("- src/billing.py:9 (Important): `< 0` accepts refund(order, 0); the task says amounts must be positive.",
                     "- **src/billing.py:9** — Important: `< 0` accepts refund(order, 0); amounts must be positive.",
                     "- src/billing.py:9: `< 0` accepts refund(order, 0), but amounts must be positive. Important.",
                     "- Important: src/billing.py:9 — `< 0` accepts refund(order, 0).",
                     "- src/billing.py:9: refund(order, 0) is accepted though the running total check is cumulative. Severity: Important."):
            with self.subTest(line=line):
                r = self.with_zero_line(line)
                self.assertEqual(r["zero_severity"], "important")
                self.assertTrue(score.rereview_pass(r))

    def test_closing_not_critical_is_not_a_label(self):
        r = self.with_zero_line("- src/billing.py:9: `< 0` accepts refund(order, 0), which is not critical.")
        self.assertIsNone(r["zero_severity"])
        self.assertFalse(score.rereview_pass(r))

    def test_f2_duplicates_worded_with_zero_are_not_the_zero_bug(self):
        for line in ("- **Important** — src/billing.py:11: two refunds let the remaining balance go below zero.",
                     "- **Important** — src/billing.py:11: total - 600 - 600 < 0 is never checked."):
            with self.subTest(line=line):
                r = self.with_zero_line(line)
                self.assertNotIn("new breakage", r["zero_section"] or "")
                self.assertFalse(score.rereview_pass(r))

    def test_verdict_forms_pass(self):
        verdict = "### Verdict\nFindings remain open: finding 2, and the zero-amount check.\n"
        self.assertIn(verdict, GREEN_REPLY)
        for form in ("### Verdict: Findings remain open: finding 2, and the zero-amount check.\n",
                     "**Verdict:** Findings remain open: finding 2, and the zero-amount check.\n",
                     "### Verdict\nFinding 2 remains open, and zero is accepted.\n"):
            with self.subTest(form=form):
                r = score.rereview_score(GREEN_REPLY.replace(verdict, form))
                self.assertTrue(r["findings_remain_open"])
                self.assertTrue(score.rereview_pass(r))

    def test_inline_verdict_label_inside_finding_verdicts_stays_there(self):
        reply = GREEN_REPLY.replace("- Finding 2 (running total): NOT ADDRESSED",
                                    "**Verdict:** see below\n- Finding 2 (running total): NOT ADDRESSED")
        self.assertEqual(score.rereview_score(reply)["f2"], "NOT ADDRESSED")


FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class AdversarialAndAccuracyTest(unittest.TestCase):
    def _score_fixture(self, name, fixture_env=None):
        old = os.environ.get("FIXTURE")
        try:
            if fixture_env is not None:
                os.environ["FIXTURE"] = fixture_env
            else:
                os.environ.pop("FIXTURE", None)
            return score.score(os.path.join(FIXTURES, name), "lbl", 1)
        finally:
            if old is not None:
                os.environ["FIXTURE"] = old
            else:
                os.environ.pop("FIXTURE", None)

    def test_planted_valid_fixture_scores_full_accuracy_and_format(self):
        row = self._score_fixture("planted_valid.jsonl")
        for k in ("missing_empty_valueerror", "extra_days_unit", "repeat_or_order_bug", "unknown_units_ignored"):
            self.assertTrue(row["defects"][k], k)
        self.assertEqual(row["defect_accuracy"], 1.0)
        self.assertEqual(row["severity_accuracy"], 1.0)
        self.assertEqual(row["format_compliance"], 1.0)
        self.assertTrue(row["verdict_reject"])

    def test_alternate_headings_still_score(self):
        row = self._score_fixture("planted_alternate_headings.jsonl")
        for k in ("missing_empty_valueerror", "extra_days_unit", "repeat_or_order_bug", "unknown_units_ignored"):
            self.assertTrue(row["defects"][k], k)
        self.assertEqual(row["defect_accuracy"], 1.0)
        self.assertEqual(row["severity_accuracy"], 1.0)
        self.assertGreaterEqual(row["blocking_items"], 4)
        self.assertTrue(row["verdict_reject"])

    def test_wrong_severity_separates_defect_from_severity_accuracy(self):
        row = self._score_fixture("planted_wrong_severity.jsonl")
        self.assertEqual(row["defect_accuracy"], 1.0)
        self.assertEqual(row["severity_accuracy"], 0.0)
        self.assertEqual(row["blocking_items"], 0)
        self.assertGreater(row["format_compliance"], 0.5)

    def test_negated_findings_do_not_score(self):
        row = self._score_fixture("negated_findings.jsonl")
        for k, v in row["defects"].items():
            self.assertFalse(v, f"negated finding matched {k}")
        self.assertEqual(row["defect_accuracy"], 0.0)
        self.assertEqual(row["severity_accuracy"], 0.0)

    def test_rereview_negated_sql_does_not_count_as_sql_finding(self):
        row = self._score_fixture("rereview_negated_sql.jsonl", fixture_env="rereview")
        self.assertFalse(row["rereview"]["sql_mentioned"])
        self.assertFalse(row["rereview"]["sql_blocking"])

    def test_keyword_only_answer_does_not_score(self):
        row = self._score_fixture("keyword_only.jsonl")
        for k, v in row["defects"].items():
            self.assertFalse(v, f"keyword-only matched {k}")
        self.assertEqual(row["defect_accuracy"], 0.0)
        self.assertEqual(row["severity_accuracy"], 0.0)
        self.assertLess(row["format_compliance"], 0.5)

    def test_incorrect_fix_does_not_score(self):
        row = self._score_fixture("incorrect_fix.jsonl")
        for k, v in row["defects"].items():
            self.assertFalse(v, f"incorrect fix matched {k}")
        self.assertEqual(row["defect_accuracy"], 0.0)
        self.assertEqual(row["severity_accuracy"], 0.0)

    def test_tightened_patterns_reject_topic_mentions_and_clean_reports(self):
        # Clean report from report-minimal.txt style should not match defect patterns.
        clean = ("#### Important\n- Empty input, unknown units, repeated and out-of-order units raise ValueError.\n"
                 "- Takes 3 days to run.\n- Uses __all__ properly.\n- Ignored whitespace in tests.\n"
                 "- No negative side effects.\n- Duplicated test setup across two methods.\n")
        for k in score.DEFECTS:
            self.assertFalse(score.defect_found(k, clean), f"clean prose falsely matched {k}")

    def test_summary_and_fixture_modes(self):
        import io
        import tempfile
        from contextlib import redirect_stdout

        r1 = self._score_fixture("planted_valid.jsonl")
        r2 = self._score_fixture("rereview_negated_sql.jsonl", fixture_env="rereview")
        self.assertGreaterEqual(r2["defect_accuracy"], 0.75)
        self.assertEqual(r2["severity_accuracy"], 1.0)
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as tmp:
            tmp.write(json.dumps(r1) + "\n")
            tmp_path = tmp.name
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                score.summary(tmp_path)
            out = buf.getvalue()
            self.assertIn("defect accuracy", out)
            self.assertIn("severity accuracy", out)
            self.assertIn("format compliance", out)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
