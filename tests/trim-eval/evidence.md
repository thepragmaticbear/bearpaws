# Trim duplicated skill text: evidence

Old means origin/main at 2d1f174. New means branch `chore/trim-skills` with its final text. The result
below is that no regression was observed on these fixtures, which does not prove behavior is preserved
everywhere.

## Cuts

1. **`skills/brainstorming/SKILL.md`**: removed the `dot` graph, which repeats the `<process>` steps (−824 B
   net). Two clauses keep its two loops in the steps:
   - "Ask after each section if it looks right; revise until it does."
   - "Wait for approval; if they request changes, update the spec and self-review again."
2. **`skills/subagent-driven-development/SKILL.md`**: removed the `when_to_use` graph. Its routing was partly
   wrong for the toolkit:
   - it sent "no plan" to brainstorming, even when a design was already agreed;
   - it sent tightly coupled plans to brainstorming, though executing-plans takes them.

   A new trigger rule follows the other skills' triggers instead: "A plan comes first: no agreed design →
   bp:brainstorming; agreed design, no plan → bp:writing-plans. A plan with tightly coupled tasks, or run in
   a separate session → bp:executing-plans." Net change: −506 B.
3. **`skills/test-driven-development/testing-anti-patterns.md`**: removed Anti-Pattern 5 ("Can't claim complete
   without tests"), its Quick Reference row, and "TDD Prevents These Anti-Patterns" (−938 B).
   - Anti-Pattern 5 requires a test for every change, which conflicts with the scoped test exemption.
   - The other section repeats the TDD cycle in SKILL.md.

## Token measurement (`tests/token-measurement/measure.sh`)

| Metric | origin/main | branch | Δ |
|---|---:|---:|---:|
| SKILL.md total bytes | 76,362 | 75,032 | −1,330 |
| Full skill payload bytes | 203,270 | 201,002 | −2,268 |
| Typical session bytes (includes brainstorming) | 33,772 | 32,948 | −824 |
| Bootstrap bytes | 5,381 | 5,381 | 0 |

## Runs

Each cell is passes/runs, with 3 runs per case. Every run listed was executed. Models were chosen with
`BENCH_MODEL`.

### Brainstorming (final text; no brainstorming change after round 1)

| Eval | Model | Old | New |
|---|---|---:|---:|
| builder-eval DESIGN=elevated | sonnet | 3/3 | 3/3 |
| builder-eval DESIGN=elevated | opus | 3/3 | 3/3 |
| builder-eval DESIGN=routine | sonnet | 3/3 | 3/3 |
| builder-eval DESIGN=routine | opus | 3/3 | 3/3 |

builder-eval covers the builder-check dispatch only. The two revision loops have no eval: none of these
runs requests a change.

### SDD routing: `tests/trim-eval/run.sh` (committed, cases in `cases.txt`)

The expected answers follow the toolkit's triggers, not the old graph:
- `nodesign` → brainstorming;
- `noplan` (approved design) → writing-plans;
- `coupled` → executing-plans;
- `separate` → executing-plans;
- `fit` → subagent-driven-development, or using-git-worktrees, because SDD's Setup step sets up the
  workspace first.

| Model | Old | New |
|---|---:|---:|
| sonnet | 15/15 | 15/15 |
| opus | 15/15 | 15/15 |

Even with the old graph in context, both models answered executing-plans for the coupled plan and
writing-plans for the agreed design. They followed the toolkit, not the graph. An earlier ad hoc probe
(round 1, not committed) scored against the graph's routing and so measured obedience to the graph. Its
numbers are dropped.

### SDD review routing and fix loop

The final SDD text was re-run after the trigger fix:

| Eval | Model | Old | New |
|---|---|---:|---:|
| review-eval/routing.sh (auth, migration, routine × 3) | sonnet | 9/9 | 9/9 |
| review-eval/routing.sh | opus | 9/9 | 9/9 |
| fixloop-eval | sonnet | 3/3 | 3/3 |
| fixloop-eval | opus | 3/3 | 2/3 (see below) |

routing.sh has no scorer. I read every row: auth and migration were classed elevated (spec reviewer, then
code-quality reviewer), and routine was classed routine (code-quality reviewer only).

The fixloop-eval Opus FAIL (run 2) is a scorer miss on a correct reply:
- the reply stops after round 5, offers no round 6, and ends `Status: INCOMPLETE`;
- its `Open:` entry reads "Two requests at the same moment can both redeem the same reset token";
- the scorer's race words (`concurrent`, `race`, `twice`, `double`, `atomic`, `toctou`) miss "at the same
  moment", so the run failed.

The scorer was not changed here. With the intermediate round-1 SDD text, the same eval scored Opus 3/3, and
old Opus 3/3.

## `testing-anti-patterns.md`

No eval loads this file. `grep -rn testing-anti-patterns tests/` finds nothing, and the only reference is
the `<see>` in `test-driven-development/SKILL.md`. Nothing in the repo refers to Anti-Pattern 5 or the
removed section by name. The cut rests on reference analysis, with no model run behind it.

## Not run

- `tests/skill-triggering/run-all.sh`: no frontmatter `description` changed, and those tests only check that
  the Skill tool fires.
- The bootstrap routing eval: it reads only `using-bearpaws/SKILL.md`, which did not change.

## Limits

- 3 runs per case and one fixture per eval.
- Raw outputs went to `/tmp` and are not committed.
