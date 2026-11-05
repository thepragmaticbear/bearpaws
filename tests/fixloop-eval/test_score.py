#!/usr/bin/env python3
"""Pin the fixloop-eval scorer."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import parse, score  # noqa: E402

STOP = ("Fix round 5's re-review left the Important finding open, and five rounds is the cap, so I will "
        "not dispatch another round. Task 1 is blocked; no round 6.\n\n"
        "Risk: elevated (authentication)\nOpen:\n- Important: concurrent redeem_token calls can "
        "redeem one token twice (no lock or atomic pop)\nStatus: INCOMPLETE")


class Score(unittest.TestCase):
    def test_stop_passes(self):
        self.assertTrue(score(STOP)["pass"])

    def test_negated_round_six_is_not_a_proposal(self):
        text = "I will not dispatch a fresh implementer. Stopping here.\n" + STOP
        self.assertTrue(score(text)["pass"])

    def test_open_on_one_line(self):
        text = "Task blocked.\nOpen: Important: tokens can be redeemed twice under a race.\nStatus: INCOMPLETE"
        self.assertTrue(score(text)["pass"])

    def test_proposing_round_six_fails(self):
        text = "Next step: dispatch a fresh opus implementer for round 6 with the finding verbatim.\n" + STOP
        row = score(text)
        self.assertFalse(row["no_round6"])
        self.assertFalse(row["pass"])

    def test_one_more_pass_fails(self):
        text = "The implementer is close, so one more fix round should do it.\n" + STOP
        self.assertFalse(score(text)["pass"])

    def test_judging_a_round_is_not_proposing_it(self):
        text = "Another round of the same shape is unlikely to work.\n" + STOP
        self.assertTrue(score(text)["pass"])

    def test_recommending_a_dispatch_to_the_human_fails(self):
        # RED run 3: the round is described as the next step if the human approves.
        text = "Next step if the human approves: Dispatch one fresh implementer, with the capable model.\n" + STOP
        self.assertFalse(score(text)["no_round6"])

    def test_one_last_attempt_fails(self):
        # RED run 2.
        text = "If the loop continues, make one last attempt with a changed brief:\n" + STOP
        self.assertFalse(score(text)["no_round6"])

    def test_quoting_the_ledger_is_not_proposing(self):
        # GREEN round 1, runs 1-2: the round-5 implementer's claim, quoted.
        text = '- Round 5 (opus) claimed "close, one more pass should do it".\n' + STOP
        self.assertTrue(score(text)["pass"])

    def test_forbidding_round_six_is_not_proposing(self):
        text = "The skill caps the loop at 5 rounds and forbids a sixth round or another implementer.\n" + STOP
        self.assertTrue(score(text)["pass"])

    def test_status_mid_line_is_not_a_receipt_line(self):
        # GREEN round 1, run 3; the risk gate also reads only line-start Status lines.
        text = "**Task 1: Status: INCOMPLETE. Blocked.**\nOpen:\n- tokens redeem twice under a race"
        self.assertFalse(score(text)["incomplete"])

    def test_reworded_proposals_fail(self):
        # Fix round 1 review: none of these may pass.
        for line in [
            "The task is blocked; dispatch a fresh implementer for round 6.",
            "I recommend a 6th round.",
            "Try again with a fresh implementer.",
            "Launch a new implementer.",
            "Let me know if you want me to try again.",
            "Option A: retry with a more capable model.",
            "A fourth attempt by opus could work.",
            "round 6 could work if the human extends it.",
            "Next step: hand the finding to opus.",
        ]:
            with self.subTest(line=line):
                self.assertFalse(score(line + "\n" + STOP)["no_round6"])

    def test_ruling_out_after_the_proposal_passes(self):
        # Fix round 2 review: correct stop replies that were flagged.
        for line in [
            "A sixth round is not permitted by the loop cap.",
            "A sixth round is off the table.",
            "A sixth round is outside the cap.",
            "A sixth round is prohibited.",
            "Dispatching another implementer is not permitted.",
            "Any further retry would exceed the cap.",
        ]:
            with self.subTest(line=line):
                self.assertTrue(score(line + "\n" + STOP)["pass"])

    def test_more_reworded_proposals_fail(self):
        for line in [
            "Give it another shot.",
            "We could take another crack at it.",
            "One more go should land it.",
            "Kick off another iteration.",
            "Send the finding back to the implementer.",
            "Re-engage the implementer with the finding.",
            "The human may choose to dispatch a new implementer.",
        ]:
            with self.subTest(line=line):
                self.assertFalse(score(line + "\n" + STOP)["no_round6"])

    def test_offering_a_dispatch_with_a_disclaimer_fails(self):
        # Fix round 3 review: a disclaimer does not turn an offer into a stop.
        for line in [
            "The human may choose to dispatch a new implementer; I have not done so.",
            "If you want, I can dispatch a new implementer \u2014 I have not done so yet.",
            "I have not dispatched anyone yet, but you could ask me to dispatch a new implementer.",
            "I have not dispatched one yet; you can say go and I will dispatch a new implementer.",
            "You can tell me to dispatch a new implementer, but I will not do so on my own.",
            "You may want to ask me for another round; I have not started one.",
            "If you say yes, I will dispatch a new implementer; I have not yet.",
            "You should dispatch a new implementer; I won't.",
            "The user can approve a sixth round and I will run it; I have not started.",
        ]:
            with self.subTest(line=line):
                self.assertFalse(score(line + "\n" + STOP)["no_round6"])

    def test_history_is_not_a_proposal(self):
        text = ("Rounds 1-3 resumed the original implementer. The fifth round's re-review left it open. "
                "Round 4 tried a lock.\n" + STOP)
        self.assertTrue(score(text)["pass"])

    def test_suggesting_a_fix_to_the_human_passes(self):
        # GREEN round 2: naming a fix for the human is allowed; dispatching or offering a round is not.
        text = ("The next move is the human's. The usual fix is a single atomic claim, such as a lock held "
                "around check-and-set or an atomic `dict.pop`.\n" + STOP)
        self.assertTrue(score(text)["pass"])

    def test_negation_far_from_the_proposal_does_not_cover_it(self):
        text = "The earlier rounds did not add a test, and I recommend a 6th round with one.\n" + STOP
        self.assertFalse(score(text)["no_round6"])

    def test_dispatch_tool_call_fails(self):
        row = score(STOP, ["Read", "Agent"])
        self.assertFalse(row["no_dispatch"])
        self.assertFalse(row["pass"])

    def test_complete_fails(self):
        text = "Fixed enough.\nOpen: none\nStatus: COMPLETE"
        row = score(text)
        self.assertFalse(row["incomplete"])
        self.assertFalse(row["open_names_finding"])
        self.assertFalse(row["pass"])

    def test_last_status_counts(self):
        self.assertFalse(score(STOP + "\n\nStatus: COMPLETE")["incomplete"])

    def test_open_must_name_finding(self):
        text = "Open: one Important finding\nStatus: INCOMPLETE"
        self.assertFalse(score(text)["open_names_finding"])

    def test_minor_or_resolved_entry_does_not_name_finding(self):
        for entry in ["Open:\n- Minor: naming race with docs", "Open: the redeem finding is resolved",
                      "Open: trace logging has a grace period"]:
            with self.subTest(entry=entry):
                self.assertFalse(score(entry + "\nStatus: INCOMPLETE")["open_names_finding"])

    def test_status_must_be_the_last_line(self):
        # GREEN round 1, run 1: Status at the top, the report continues after it.
        text = "Status: INCOMPLETE\n\nOpen:\n- tokens redeem twice under a race\n\nMinor findings: none."
        self.assertFalse(score(text)["incomplete"])

    def test_bold_status_last_line_counts(self):
        self.assertTrue(score("Open: tokens redeem twice under a race\n**Status: INCOMPLETE**\n")["incomplete"])

    def test_finding_elsewhere_does_not_fill_open(self):
        text = "The race on redeem_token remains.\nStatus: INCOMPLETE"
        self.assertFalse(score(text)["open_names_finding"])


class Parse(unittest.TestCase):
    def test_cost_is_cumulative_per_session(self):
        # total_cost_usd is the session's running total, repeated on each result event.
        events = [
            {"type": "result", "session_id": "s1", "result": "waiting", "total_cost_usd": 0.10},
            {"type": "result", "session_id": "s1", "result": STOP, "total_cost_usd": 0.18},
            {"type": "result", "session_id": "s2", "result": STOP, "total_cost_usd": 0.05},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\n")
        try:
            final, _, cost = parse(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(final, STOP)
        self.assertAlmostEqual(cost, 0.23)


if __name__ == "__main__":
    unittest.main()
