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

here = os.path.dirname(os.path.abspath(__file__))
template_path, repo = sys.argv[1], sys.argv[2]
task = open(os.path.join(here, "task.txt")).read().strip()
report = open(os.path.join(here, "report.txt")).read().strip()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()

text = open(template_path).read()
fenced = re.search(r"prompt: \|\n(.*?)\n```", text, re.S)
if fenced:
    text = "\n".join(line[4:] if line.startswith("    ") else line for line in fenced.group(1).splitlines())

values = {
    "WHAT_WAS_IMPLEMENTED": report,
    "PLAN_OR_REQUIREMENTS": task,
    "PLAN_REFERENCE": task,
    "REQUIREMENTS": task,
    "DESCRIPTION": report,
    "BASE_SHA": base,
    "HEAD_SHA": head,
}
for key, value in values.items():
    text = text.replace("{" + key + "}", value)
text = text.replace("[FULL TEXT of task requirements]", task)
text = text.replace("[From implementer's report]", report)
print(text)
print(f"\nThe repository under review is the current directory. Base {base}, head {head}.")
