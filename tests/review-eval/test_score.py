#!/usr/bin/env python3
"""Scorer tests: which text counts as a blocking issue, and what the verdict line means."""
import os
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


class VerdictTest(unittest.TestCase):
    def test_bare_yes_approves(self):
        self.assertFalse(score.verdict_reject("**Ready to merge?** Yes\n"))

    def test_conditional_yes_rejects(self):
        for line in ("Ready to merge? Yes, after adding the sign check", "Ready to merge? Yes with fixes",
                     "Ready to merge? Yes once the cap is tested"):
            self.assertTrue(score.verdict_reject(line), line)

    def test_no_rejects(self):
        self.assertTrue(score.verdict_reject("Ready to merge? No. The sign check is missing."))


if __name__ == "__main__":
    unittest.main()
