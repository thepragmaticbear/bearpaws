#!/usr/bin/env python3
"""Render a reviewer prompt template for the review fixture.

Usage: render.py <template.md> <repo-dir>
Supports requesting-code-review/code-reviewer.md style {PLACEHOLDERS} and the
subagent-driven-development prompt files (the fenced prompt block, [FULL TEXT ...]
and [From implementer's report] markers).
"""
import os
import re
import subprocess
import sys
import textwrap

here = os.path.dirname(os.path.abspath(__file__))
template_path, repo = sys.argv[1], sys.argv[2]
task = open(os.path.join(here, "task.txt")).read().strip()
report = open(os.path.join(here, "report.txt")).read().strip()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()

# Package the fixture's current state, including changes outside the head commit.
diff = subprocess.check_output(["git", "diff", base, "--", "src", "tests",
                                ":(exclude)**/__pycache__/**"], cwd=repo, text=True)
untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z",
                                     "--", "src", "tests", ":(exclude)**/__pycache__/**"], cwd=repo)
for path in filter(None, untracked.split(b"\0")):
    extra = subprocess.run(["git", "diff", "--no-index", "--", "/dev/null", os.fsdecode(path)],
                           cwd=repo, capture_output=True, text=True)
    if extra.returncode not in (0, 1):
        raise RuntimeError(extra.stderr)
    diff += extra.stdout
command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
check = subprocess.run(command, cwd=repo, capture_output=True, text=True)
evidence = (f"Executed: {' '.join(command)} — exit {check.returncode}\n"
            + check.stdout + check.stderr
            + "\nNot run: integration checks (the fixture provides no integration suite).")

text = open(template_path).read()
fenced = re.search(r"prompt: \|\n(.*?)\n```", text, re.S)
if fenced:
    text = textwrap.dedent(fenced.group(1))

values = {
    "WHAT_WAS_IMPLEMENTED": report,
    "PLAN_OR_REQUIREMENTS": task,
    "PLAN_REFERENCE": task,
    # PACKAGE=1: the controller passes the conventions it found during onboarding.
    "PROJECT_CONVENTIONS": (open(os.path.join(repo, "CONTRIBUTING.md")).read().strip()
                            if os.environ.get("PACKAGE") == "1" and os.path.exists(os.path.join(repo, "CONTRIBUTING.md"))
                            else ""),
    "REQUIREMENTS": task,
    "DESCRIPTION": report,
    "BASE_SHA": base,
    "HEAD_SHA": head,
    "CHANGED_FILE_DIFF": diff or "No changes in fixture scope src/ and tests/.",
    "VERIFICATION_EVIDENCE": evidence,
    "KNOWN_DECISIONS": "Fixture decision: stdlib parser; no new dependency.",
    "UNRESOLVED_CONCERNS": "Invalid input and repeated units lack visible test coverage; investigate.",
}
for key, value in values.items():
    text = text.replace("{" + key + "}", value)
text = text.replace("[FULL TEXT of task requirements]", task)
text = text.replace("[From implementer's report]", report)
print(text)
print(f"\nThe repository under review is the current directory. Base {base}, head {head}.")
