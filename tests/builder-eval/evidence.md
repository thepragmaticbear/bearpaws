# Builder check evaluation

`bp:brainstorming` runs a builder check only for elevated-risk designs. After the spec self-review, a
design that covers elevated-risk work (see `bp:using-bearpaws`) goes to a fresh subagent with
`skills/brainstorming/builder-check-prompt.md`. The subagent plans to build the design without the
author and lists only the questions where a wrong guess would change the plan, ranked; the author answers
or folds in each before the user review. Routine designs get the self-review only. The check replaces
`spec-document-reviewer-prompt.md`, which the skill named in a `<see>` line but never told the agent to
dispatch.

Fixture (`setup.sh`): a small app with two committed design docs. `routine-design.md` renames a
settings button and changes its color. `elevated-design.md` replaces emailed temporary passwords with
hashed, expiring reset-link tokens and never says whether a token can be used more than once. The prompt
gives the skill text and its base directory, says the design is written and approved section by section,
and asks for the next steps up to the user review, non-interactively. Sonnet, 3 runs per design.

Scoring (`score.py`, pinned by `test_score.py`). Only the top-level agent's `Agent`/`Task` calls count.
- Routine: pass when no subagent is dispatched. Any dispatch fails, since the step needs none.
- Elevated: pass when a dispatched subagent's prompt contains "plan to build" (the builder-check
  template's wording), and the final reply surfaces the single-use question: one sentence naming a token
  or link and single-use, one-time, reuse, replay, use more than once or twice, or invalidation after use.
- A run with no `result` event (crash or budget stop) is an error, not scored.

| Run | Design | Pass | Builder check dispatched | Single-use surfaced | Mean cost |
|---|---|---:|---:|---:|---:|
| RED (SKILL.md at fc673da) | routine | 3/3 | 0/3 | 0/3 | $0.056 |
| RED (SKILL.md at fc673da) | elevated | 0/3 | 0/3 | 3/3 | $0.063 |
| GREEN round 1 | routine | 3/3 | 0/3 | 0/3 | $0.054 |
| GREEN round 1 | elevated | 3/3 | 3/3 | 3/3 | $0.352 |

Per run:
- RED routine 1–3 ($0.056, $0.057, $0.055): no dispatch; self-review only. An earlier RED routine round
  ($0.065, $0.067, $0.068, also no dispatch) ran on a fixture whose doc named a button `id` the HTML
  lacks; every run flagged it, so the fixture was fixed and routine RED rerun.
- RED elevated 1–3 ($0.064, $0.063, $0.063): no dispatch. Each self-review found the reuse gap and
  decided it unasked: "A token is now single-use. Its row is deleted on success" (run 1), "each link
  works once" (runs 2, 3). Run 1 also closed the second-request gap.
- GREEN routine 1–3 ($0.057, $0.056, $0.048): no dispatch.
- GREEN elevated 1–3 ($0.363, $0.398, $0.295): one "Builder check of design" dispatch each, prompt
  rendered from the template with a filled-in domain ("backend/security", "authentication/backend").
  The builder returned 7, 5 and 8 questions; each reply listed single use first among the decisions
  folded into a "Decisions from builder check" section, and asked the user to check them.

RED behavior: the current skill never dispatched the old spec reviewer, on either design. On this
fixture the self-review alone already finds the single-use gap, so the "surfaced" criterion does not
separate RED from GREEN; only the dispatch does. What the builder check adds here is breadth (one live
token per user, storage, clock, email failure, out-of-scope pages), at about $0.29 more per elevated
design. Routine designs cost the same as before.

Limits: one fixture per design, one model, n=3. The builder raised 5–8 questions, not only the few that
change the plan; ranking quality and the "nothing important left" path are untested. The scorer's
single-use detector is a regex: unlisted phrasings can pass or fail wrongly. Raw outputs land under
`/tmp/bearpaws-tests/builder-eval/<timestamp>/` and are not committed.
