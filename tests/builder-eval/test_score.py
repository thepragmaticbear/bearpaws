#!/usr/bin/env python3
"""Pin the builder-eval scorer."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import parse, score, surfaces_single_use  # noqa: E402

BUILDER = {"description": "Builder check", "prompt": "You are a talented backend builder who has to\n"
           "plan to build the design at docs/x.md without talking to its author."}
SPEC = {"description": "Review spec document", "prompt": "You are a spec document reviewer."}
ASKS = "Builder check raised one question: can a reset token be used more than once?"


class Routine(unittest.TestCase):
    def test_no_dispatch_passes(self):
        self.assertTrue(score("routine", "Self-review done. Please review the design.")["pass"])

    def test_any_dispatch_fails(self):
        self.assertFalse(score("routine", "Done.", [BUILDER])["pass"])
        self.assertFalse(score("routine", "Done.", [SPEC])["pass"])


class Elevated(unittest.TestCase):
    def test_builder_check_and_question_passes(self):
        self.assertTrue(score("elevated", ASKS, [BUILDER])["pass"])

    def test_no_dispatch_fails(self):
        self.assertFalse(score("elevated", ASKS)["pass"])

    def test_spec_reviewer_is_not_the_builder_check(self):
        row = score("elevated", ASKS, [SPEC])
        self.assertFalse(row["builder_check"])
        self.assertFalse(row["pass"])

    def test_phrase_split_across_lines_counts(self):
        d = {"description": "x", "prompt": "who has to plan\n   to build it"}
        self.assertTrue(score("elevated", ASKS, [d])["pass"])

    def test_question_missing_fails(self):
        text = "Builder check: should failed attempts be rate limited? Should sessions be revoked?"
        self.assertFalse(score("elevated", text, [BUILDER])["pass"])


class SingleUse(unittest.TestCase):
    def test_phrasings_that_surface_it(self):
        for text in [
            "Are reset tokens single-use?",
            "Is the link one-time, or can it be reused?",
            "The design never says whether a token can be redeemed more than once.",
            "Should the token be invalidated after a successful reset?",
            "I added: a token is deleted after its first use.",
            "Token replay: nothing stops the same link working twice.",
            "Tokens are now marked used after redemption.",
        ]:
            self.assertTrue(surfaces_single_use(text), text)

    def test_phrasings_that_do_not(self):
        for text in [
            "Tokens expire after 30 minutes.",
            "The link is emailed once per request.",
            "This is a one-time setup step for the table.",
            "Should we reuse the existing email helper?",
            "Should a new token invalidate older ones?",
            "Is the token compared in constant time?",
        ]:
            self.assertFalse(surfaces_single_use(text), text)

    def test_token_and_reuse_must_share_a_sentence(self):
        self.assertFalse(surfaces_single_use("The token is hashed. Can the helper be reused?"))


class Parse(unittest.TestCase):
    def test_counts_only_top_level_dispatches(self):
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": BUILDER},
                {"type": "tool_use", "name": "Read", "input": {}}]}},
            {"type": "assistant", "parent_tool_use_id": "t1", "message": {"content": [
                {"type": "tool_use", "name": "Task", "input": SPEC}]}},
            {"type": "result", "result": ASKS, "total_cost_usd": 0.12},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\nnot json\n")
        try:
            final, dispatches, cost = parse(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(final, ASKS)
        self.assertEqual(dispatches, [BUILDER])
        self.assertAlmostEqual(cost, 0.12)

    def test_no_result_event_is_none(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("{}\n")
        try:
            self.assertIsNone(parse(f.name)[0])
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
