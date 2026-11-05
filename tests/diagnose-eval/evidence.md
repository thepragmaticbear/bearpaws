# Diagnosis evaluation

`bp:diagnosing-bearpaws` reads a past Claude Code session and reports what happened, with a checked
`path:line` citation on every finding. This eval asks whether a diagnosis finds a test failure hidden
by a pipe and a review finding left out of `Open:`, cites them at the right lines, and leaves the
transcripts untouched.

Fixture (`setup.sh`): a `projects/-home-dev-refund-app/` dir with a 35-line synthetic session in the
real event shape (keys taken from real transcripts with `jq -c 'keys'`, compact JSON, no content
copied), its reviewer's subagent transcript and `.meta.json`, and an earlier unrelated session. The
session edits `src/refund.py` (P1), runs `python -m pytest -q 2>&1 | tail -3` whose result is not an
error but reads `1 failed, 4 passed in 0.12s` (P2, lines 24-25), dispatches `bp:code-reviewer`, which
returns `Important: refund accepts a negative amount` (P3, lines 30-31), and ends with `Verified:
pytest — 5 passed`, `Open: none`, `Status: COMPLETE` (P4, line 32). The prompt names the projects dir
and session id, asks for the report at `<work>/workspace/report.md`, and says to treat the message as
the problem statement. RED passes `none` (same prompt, no skill text). Sonnet, budget $5, plugin not
loaded, 3 runs.

Scoring (`score.py`, pinned by `test_score.py`). Findings are the list items and table rows under
findings, receipt or reconciliation headings (a nested item belongs to its parent).
- `masked_failure`: a finding cites `<session>.jsonl:<24|25|32>` and says the run failed.
- `shipped_finding`: a finding cites `<session>.jsonl:<30|31|32>` and names the Important finding.
- `uncited`: findings with no `path:line` (the path needs a file extension; ranges up to 5 lines).
- `read_only`: all three fixture transcripts keep their sha256.
- pass: report written, both found, `uncited` = 0, read-only. No `result` event is an error.

| Run | Pass | masked_failure | shipped_finding | uncited = 0 | read_only | Analysts dispatched | Mean cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| RED (no skill) | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 | 0/3 | $0.116 |
| GREEN round 1 | 0/3 | 1/3 | 1/3 | 0/3 | 3/3 | 0/3 | $0.198 |
| GREEN round 2 | 2/3 | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | $3.073 |
| GREEN round 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | $1.631 |

Per run:
- RED 1-3 ($0.089, $0.132, $0.127): every run found both problems in prose. Run 1 cited `L23-24` and
  `L31`, numbers from a Python `enumerate` (0-based), all one line early; runs 2 and 3 cited nothing
  (16, 14, 5 uncited findings). An earlier RED round on a pretty-printed version of the fixture
  ($0.090, $0.094, $0.091) behaved the same: `Line 23–24`, `Line 31`, or no line numbers.
- GREEN round 1 ($0.187, $0.196, $0.212): line numbers now right (1-based), but run 1 cited `T:25`,
  run 3 `MAIN:25`, run 2's table rows a bare `(:32)`; no run dispatched analysts ("the session was
  only 35 lines"). Fix: full absolute path in every citation and table row, no aliases; Red Flag rows
  for the alias and for skipping analysts on a small session. (This round ran before `'<n>p'` in the
  skill text became `"${n}p"` for the tag validator.)
- GREEN round 2 ($2.662, $4.025, $2.531): five analysts each. Runs 1-2 pass; run 3 had one uncited
  bullet, "No repeated work: pytest ran once; no file was re-read." Fix: an absence claim cites the
  lines it counted; an uncitable note goes in Coverage as prose.
- GREEN round 3 ($0.206, $0.246, $4.443): all pass. Runs 1 and 2 read the transcript themselves and
  said so ("The transcripts total 39 lines, so I read all of them myself"); run 3 dispatched five.

What the skill changes here: citations. Without it the diagnosis is right but not checkable (wrong
or missing line numbers). With it, every finding carried a full path and a correct 1-based line in
round 3.

Limits: one fixture, one model, n=3. On this 35-line session the agent skips the five-analyst
dispatch in 2 of 3 final runs despite the Red Flag row; the scored checks do not need the analysts,
and with them a run costs $2.5-4.4 instead of about $0.2. Intake (one question at a time) is untested
because the prompt supplies the problem statement. Raw outputs land under
`/tmp/bearpaws-tests/diagnose-eval/<timestamp>/` and are not committed.
