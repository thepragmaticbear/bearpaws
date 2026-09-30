#!/usr/bin/env python3
"""Offline check for complete review packages: python3 tests/review-eval/test_render.py."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


class RenderPackage(unittest.TestCase):
    def test_dispatch_callers_supply_every_template_field(self):
        template = (ROOT / "skills/requesting-code-review/code-reviewer.md").read_text()
        fields = set(re.findall(r"\{([A-Z_]+)\}", template))
        for caller in ["requesting-code-review/SKILL.md",
                       "subagent-driven-development/code-quality-reviewer-prompt.md"]:
            with self.subTest(caller=caller):
                supplied = set(re.findall(r"\{([A-Z_]+)\}", (ROOT / "skills" / caller).read_text()))
                self.assertFalse(fields - supplied, f"missing dispatch fields: {sorted(fields - supplied)}")

    def test_both_templates_include_current_diff_and_evidence(self):
        with tempfile.TemporaryDirectory() as repo:
            env = dict(os.environ, CONVENTION="1", PACKAGE="1")
            subprocess.run([str(HERE / "setup.sh"), repo], env=env, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with open(Path(repo) / "src/duration.py", "a") as f:
                f.write("\n# unstaged review marker\n")
            with open(Path(repo) / "tests/test_duration.py", "a") as f:
                f.write("\n# staged review marker\n")
            subprocess.run(["git", "add", "tests/test_duration.py"], cwd=repo, check=True)
            (Path(repo) / "tests/test_pending.py").write_text("# untracked review marker\n")
            templates = ["requesting-code-review/code-reviewer.md",
                         "subagent-driven-development/code-quality-reviewer-prompt.md"]
            for template in templates:
                with self.subTest(template=template):
                    text = subprocess.check_output([sys.executable, str(HERE / "render.py"),
                                                    str(ROOT / "skills" / template), repo],
                                                   env=env, text=True)
                    self.assertIsNone(re.search(r"\{[A-Z_]+\}", text), text)
                    for required in ["unstaged review marker", "staged review marker", "tests/test_pending.py",
                                     "untracked review marker", "exit 0", "Ran 2 tests",
                                     "Not run:", "stdlib", "repeated units"]:
                        self.assertTrue(required in text, f"missing package content: {required}")
                    self.assertIn("__all__", text)

            (Path(repo) / "tests/test_pending.py").write_text(
                "import unittest\nclass Pending(unittest.TestCase):\n"
                "    def test_empty(self):\n        self.fail('empty input still accepted')\n")
            text = subprocess.check_output([sys.executable, str(HERE / "render.py"),
                                            str(ROOT / "skills" / templates[0]), repo], env=env, text=True)
            for required in ["exit 1", "Ran 3 tests", "FAILED (failures=1)", "empty input still accepted"]:
                self.assertTrue(required in text, f"missing failed-check evidence: {required}")


if __name__ == "__main__":
    unittest.main()
