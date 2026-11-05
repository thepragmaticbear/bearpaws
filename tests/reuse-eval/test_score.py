#!/usr/bin/env python3
"""Pin the reuse-eval scorer's cost: total_cost_usd is a session's running total."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class Cost(unittest.TestCase):
    def test_cost_is_cumulative_per_session(self):
        # A session that ends several turns repeats its running total; other sessions add.
        events = [
            {"type": "result", "session_id": "s1", "result": "waiting", "total_cost_usd": 0.10},
            {"type": "result", "session_id": "s1", "result": "done", "total_cost_usd": 0.18},
            {"type": "result", "session_id": "s2", "result": "done", "total_cost_usd": 0.05},
        ]
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "s.jsonl")
            with open(log, "w") as f:
                f.write("\n".join(json.dumps(e) for e in events) + "\n")
            work = os.path.join(d, "work")
            os.mkdir(work)
            out = subprocess.run([sys.executable, os.path.join(HERE, "score.py"), log, work, "lbl", "1"],
                                 capture_output=True, text=True, check=True).stdout
        self.assertAlmostEqual(json.loads(out)["cost"], 0.23)


if __name__ == "__main__":
    unittest.main()
