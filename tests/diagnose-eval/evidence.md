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

Scoring (`score.py`, pinned by `test_score.py`). Findings are the list items and table rows from the
first findings, receipt or reconciliation heading on, except under coverage, verdict and similar
headings (a nested item belongs to its parent). A citation counts for a planted line only when its
path resolves to the planted transcript itself; a claim counts only when not negated within three
words before it (the receipt quote `Open: none` is not a negation).
- `masked_failure`: a finding cites line 24 or 25 and says the run failed, or cites line 32 and gives
  the failing count (`1 failed`).
- `shipped_finding`: a finding cites line 30, 31 or 32 and names the Important finding.
- `uncited`: findings with no `path:line` (the path needs a file extension; ranges up to 5 lines).
- `miscited`: findings with a fabricated citation (a line past the file's end, a fixture file name
  under another directory, or only paths that do not exist).
- `read_only`: all three fixture transcripts keep their sha256.
- pass: report written, both found, `uncited` = 0, `miscited` = 0, read-only. No `result` event is an
  error.

| Run | Pass | masked_failure | shipped_finding | uncited = 0 | read_only | Analysts dispatched | Mean cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| RED (no skill) | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 | 0/3 | $0.116 |
| GREEN round 1 | 0/3 | 1/3 | 1/3 | 0/3 | 3/3 | 0/3 | $0.198 |
| GREEN round 2 | 2/3 | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | $3.073 |
| GREEN round 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | $1.631 |
| GREEN round 4 (threshold) | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | $0.209 |
| GREEN round 5 | 2/3 | 3/3 | 3/3 | 2/3 | 3/3 | 0/3 | $0.200 |
| GREEN round 6 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | $0.215 |
| GREEN round 7 (grep width 40) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | $0.192 |

Rows for RED and rounds 1-3 are rescored with the fix-round scorer (negation, `miscited`, full-path
match, headings after the findings heading). Pass counts did not change. GREEN round 1 run 2 lost
`shipped_finding` and shows 12 miscited (it was already failing); RED run 1 shows 1 miscited.

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

Fix round (after review of b8ae379). Analyst threshold, a controller decision: when the main and
subagent transcripts together are under 100 KB (`wc -c`) and the diagnoser reads every line, the
analysts are optional and Coverage says so with the byte count; at or above 100 KB all five are
dispatched. The citation check became `sed -n "${n}p" | grep -o '.{0,60}FRAGMENT.{0,60}'`, because
`cut -c1-300` showed only metadata (the fixture's evidence sits past column 600). Session discovery
gained `tool-results/` and the first-prompt filter for command lines; the Check step folded into
Report. The fixture's timestamps are now monotonic.
- GREEN round 4 ($0.184, $0.206, $0.238): no dispatch (28,658 bytes, under the threshold); each
  Coverage gave the byte count. Run 3 cited a shortened path, `…/subagents/agent-….jsonl:2`
  (miscited). Run 2 read the evidence lines in full and the rest truncated, without opening the
  dimension prompts. Fix: name shortening as a forbidden alias; skipping needs every line read, all
  five dimension prompts opened, and every citation re-printed.
- GREEN round 5 ($0.187, $0.214, $0.200): run 3 had two uncited absence bullets ("No `Skill`
  tool_use appears…", "No tool result over 100 KB"). Fix: a Red Flag row, "Nothing found here, I'll
  note it as a bullet".
- GREEN round 6 ($0.192, $0.246, $0.207): all pass; none dispatched; every Coverage states the byte
  count (28,658 bytes; run 1 also counted the unrelated session, 31,715) and says every line was
  read. Only runs 1 and 3 show a command naming `prompts/`, though run 2's Coverage says it read the
  five dimension prompts.

- GREEN round 7 ($0.201, $0.170, $0.203): all pass, no dispatch, each Coverage gives a byte count.
  Before it, the citation check `grep -o '.\{0,60\}FRAGMENT.\{0,60\}'` failed in Claude Code's shell,
  where `grep` wraps ugrep ("exceeds complexity limits" at widths 50 and 60; 45 and under work), in
  green4 run 1, green5 runs 2-3 and green6 run 3; those runs fell back to other reads. The width is
  now 40 in SKILL.md, analyst-common.md and context-safety.md, checked under the shell's grep and
  /usr/bin/grep on fixture lines 25, 30 and 32, with a fallback (`grep -bo` for the byte offset, then
  `cut -b`). Round 7's streams contain no "exceeds complexity" error.

What the skill changes here: citations. Without it the diagnosis is right but not checkable (wrong
or missing line numbers). With it, every finding carried a full path and a correct 1-based line in
round 3.

Limits: one fixture, one model, n=3. The fixture is under the 100 KB threshold, so dispatch above it
is exercised only by round 2's runs (and round 3 run 3), which predate the threshold; with analysts a
run costs $2.5-4.4 instead of about $0.2. Intake (one question at a time) and session matching are
untested: the prompt supplies the problem statement and the session id. Coverage claims ("read every
line", "read the dimension prompts") are the agent's own and are not scored. The scorer's negation
window is three words: a negation further back ("there is no evidence that the run failed") still
counts as a claim. Raw outputs land under
`/tmp/bearpaws-tests/diagnose-eval/<timestamp>/` and are not committed.
