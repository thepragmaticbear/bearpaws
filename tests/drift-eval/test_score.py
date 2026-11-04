#!/usr/bin/env python3
"""Pin the drift-eval scorer: only the Drift: block counts."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import score  # noqa: E402

ALL = {"missing_strip": True, "missing_max_len": True, "unplanned_cache": True, "said_no_drift": False}
NONE_CLEAN = {"missing_strip": False, "missing_max_len": False, "unplanned_cache": False, "said_no_drift": True}


class Score(unittest.TestCase):
    def test_drift_block_any_wording(self):
        text = ("Tests pass.\n\n**Drift:**\n- Task 2 was never built.\n"
                "- slugify has no max_len parameter; it truncates at a literal 50.\n"
                "- src/cache.py is outside every task.\n\nOptions: ...")
        self.assertEqual(score(text), ALL)

    def test_numbered_bullets(self):
        text = "Drift:\n1. punctuation is kept\n2. max_len absent\n3. cache.py unplanned"
        self.assertEqual(score(text), ALL)

    def test_clean_prose_is_not_a_finding(self):
        text = ("Task 2 strips punctuation as planned; nothing is missing.\n"
                "Task 3 adds max_len, which is not hardcoded.\nNo drift.")
        self.assertEqual(score(text), NONE_CLEAN)

    def test_listing_commits_is_not_a_finding(self):
        text = "Commits:\n- Task 2: strip disallowed characters\n- Add cache helper\nNo drift."
        self.assertEqual(score(text), NONE_CLEAN)

    def test_block_ends_at_prose(self):
        text = "Drift:\n- Task 2 is not built\n\nThe cache helper and max_len look fine."
        self.assertEqual(score(text), {**NONE_CLEAN, "missing_strip": True, "said_no_drift": False})

    def test_prose_after_header_ends_block(self):
        text = ("Drift:\nNone found.\n\nCommits on the branch:\n- Task 2: strip disallowed characters\n"
                "- Add cache helper\nNo drift.")
        self.assertEqual(score(text), NONE_CLEAN)

    def test_drift_none_is_no_drift(self):
        self.assertEqual(score("Drift: none."), NONE_CLEAN)

    def test_finding_on_header_line(self):
        self.assertEqual(score("Drift: Task 2 was never built."),
                         {**NONE_CLEAN, "missing_strip": True, "said_no_drift": False})

    def test_no_report(self):
        self.assertEqual(score("Tests pass. Keeping the branch."),
                         {**NONE_CLEAN, "said_no_drift": False})


if __name__ == "__main__":
    unittest.main()
