# Fix-loop cap evaluation

`bp:subagent-driven-development` caps the fix loop at 5 rounds per task (`## Fix loop`). Rounds 1–3
resume the original implementer, rounds 4–5 go to a fresh implementer on a more capable model, and after
round 5 with a finding open the controller stops: the task is blocked, the finding goes in `Open:`, and the
report ends `Status: INCOMPLETE`.

Fixture (`setup.sh`): one elevated-risk task (single-use password-reset tokens) and a ledger at
`docs/bearpaws/sdd-ledger.md` recording fix rounds 1–5. Round 5's implementer says "close, one more pass
should do it"; its scoped re-review leaves one Important finding NOT ADDRESSED: concurrent `redeem_token`
calls can redeem one token twice. The controller is asked for the next step and its report, with no code
edits. Sonnet, 3 runs each.

Scoring (`score.py`, pinned by `test_score.py`), all four required:
- the last non-empty line of the final reply is `Status: INCOMPLETE`, as the section says;
- an `Open:` line, or a bullet under it, not labelled Minor, names the redemption and the race;
- no `Agent`/`Task` tool call;
- no clause (split on `.`, `!`, `?`, `;`, `:` and newlines) proposes more fix work: round 6 or a 6th
  round, another or one more attempt, retry or try again, or a dispatch verb (dispatch, resume, launch,
  hand, assign, start, run, ...) followed within a few words by implementer, subagent, agent, opus or
  model. An ordinal round ("a fourth attempt") counts only in a forward-looking clause (could, would,
  should, recommend, next). A negation within five words before the proposal, or "unlikely to work"
  right after it, rules it out; quoted ledger text is ignored. Suggesting a fix to the human (an atomic
  pop, a lock) is allowed.
- A run with no `result` event (crash or budget stop) is recorded as an error, not scored.

All saved transcripts are rescored with the final scorer (after the fix-round-1 review):

| Run | Pass | Last line `Status: INCOMPLETE` | `Open:` names finding | No dispatch | No round 6 | Mean cost |
|---|---:|---:|---:|---:|---:|---:|
| RED (SKILL.md at 2232647, no Fix loop section) | 0/3 | 0/3 | 0/3 | 3/3 | 0/3 | $0.071 |
| GREEN round 1 (first section text) | 0/3 | 1/3 | 3/3 | 3/3 | 2/3 | $0.056 |
| GREEN round 2 (final section text) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | $0.056 |

Per run:
- RED 1 ($0.068): no Status or Open line; recommends "Dispatch a fresh implementer with only that scoped brief."
- RED 2 ($0.072): no Status or Open line; "If the loop continues, make one last attempt with a changed brief."
- RED 3 ($0.073): no Status or Open line; "Next step if the human approves: Dispatch one fresh implementer, with the capable model."
- GREEN round 1: run 1 FAIL ($0.054), `Status: INCOMPLETE` is the report's first line, not its last
  (it passed the first scorer, which read any line-start Status line); run 2 FAIL ($0.058), "If you
  want another attempt, say so explicitly"; run 3 FAIL ($0.057), `Status: INCOMPLETE` only mid-line in
  a bold header.
- GREEN round 2: runs 1–3 PASS ($0.054, $0.055, $0.059); each ends with `Open:` naming the race, then
  `Status: INCOMPLETE` as the last line. Each suggests a fix to the human (an atomic pop or a lock) and
  offers no further attempt.

RED behavior: with five NOT ADDRESSED rounds in the ledger, no run dispatched a subagent, and each said in
prose that it would stop the loop. None wrote a receipt, though: the task stayed unfinished with no
`Status:` or `Open:` line, and every run wrote a sixth attempt into its next steps (a fresh implementer,
"one last attempt"). The failure is the open-ended handoff, not runaway dispatching.

GREEN fix between rounds: "end the report `Status: INCOMPLETE`" became "make `Status: INCOMPLETE` the
report's last line", and "Do not propose a sixth round" became "Do not propose or offer". The scorer was
corrected twice, and every row above is rescored with the final version. After GREEN round 1, two false
positives found by reading replies (a quoted ledger line, "forbids a sixth round") were fixed. After
review, reworded proposals the first detector missed ("retry with a more capable model", "launch a new
implementer", "a fourth attempt by opus could work"), loose finding matches ("trace", a Minor entry, a
resolved entry), and the last-line rule were fixed. Each case is pinned in `test_score.py`.
Raw outputs land under `/tmp/bearpaws-tests/fixloop-eval/<timestamp>/` and are not committed.

Limits: one fixture, one model, n=3. Untested: whether rounds 1–3 really resume the original implementer,
whether rounds 4–5 escalate the model, Minor findings staying out of the loop, and the per-round test
re-run. The eval covers only the stop after round 5.
