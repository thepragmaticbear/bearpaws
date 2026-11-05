#!/usr/bin/env python3
"""Scorer tests: which text counts as a blocking issue, and what the verdict line means."""
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


if __name__ == "__main__":
    unittest.main()
