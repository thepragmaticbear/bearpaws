# Compact review package evaluation

Behavioral pressure baseline **PASS**: a fresh Codex session using the existing
dispatch skill and `package-pressure.txt` retained unstaged/untracked files,
the failed four-test check, the unrun integration check, the stdlib decision,
and the repeated-unit concern. No behavioral failure was demonstrated and no
new dispatch-policy or rationalization rule was added.

Structural **RED**: `python3 tests/review-eval/test_render.py` failed for both
existing templates because their rendered payload omitted the current diff
and verification evidence. After the template fields were added, the caller
contract test failed with missing `CHANGED_FILE_DIFF`, `VERIFICATION_EVIDENCE`,
`KNOWN_DECISIONS`, and `UNRESOLVED_CONCERNS` in the dispatch skill's field list.

Structural **GREEN**: the templates expose those four fields, the caller list
supplies them, and the fixture renderer fills them. The offline check covers
committed, staged, unstaged and untracked changes; both template styles;
actual successful and failed command results; missing-check disclosure;
conventions; decisions; concerns; and unresolved named placeholders.

Run: `python3 tests/review-eval/test_render.py`.

Controller pressure re-test **PASS**: `/tmp/bearpaws-package-green.jsonl` retained
all package fields and the supplied facts. The baseline had already passed;
this does not establish a new behavioral improvement.

Rendered reviewer pressure **RED**: `/tmp/bearpaws-rendered-package-green.jsonl`
had no execution tools but nevertheless reported:

> Tried: [executed] not run by me. Supplied evidence says `/opt/homebrew/opt/python@3.14/bin/python3.14 -m unittest discover -s tests -t .` exited `0`, ran 2 tests, OK.

The rationalization "not run by me. Supplied evidence says" treated controller
evidence as reviewer execution, violating the existing `[executed]` rule.
The template now explicitly keeps supplied results in Verification Evidence,
outside reviewer Break Attempts, and requires the reviewer's own tool output
for an executed label. A fresh rendered-reviewer re-test is pending.

Structural GREEN does not prove reviewer behavior or cost reduction.
