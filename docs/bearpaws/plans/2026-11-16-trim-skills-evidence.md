# Trim duplicated skill text: evidence

Cuts, each checked against origin/main at 2d1f174 ("old") with the same eval:

1. `skills/brainstorming/SKILL.md`: removed the `dot` graph. It repeats the `<process>` steps. Its two
   loops are now in the steps: "Ask after each section if it looks right; revise until it does." and "Wait
   for approval; if they request changes, update the spec and self-review again." −824 B.
2. `skills/subagent-driven-development/SKILL.md`: removed the `when_to_use` graph. It held the routing
   that the triggers did not: no plan or tightly coupled tasks go to brainstorming, and a separate session
   goes to executing-plans. That routing is now a trigger rule: "No plan, or tightly coupled tasks: use
   bp:brainstorming first. Executing in a separate session: use bp:executing-plans." −578 B.
3. `skills/test-driven-development/testing-anti-patterns.md`: removed Anti-Pattern 5 ("Can't claim
   complete without tests"), its Quick Reference row, and "TDD Prevents These Anti-Patterns". Anti-Pattern 5
   requires a test for every change, which conflicts with the scoped test exemption. The other section
   repeats the TDD cycle in SKILL.md. −938 B.

Token measurement (`tests/token-measurement/measure.sh`):

| Metric | origin/main | this branch | Δ |
|---|---:|---:|---:|
| SKILL.md total bytes | 76,362 | 74,960 | −1,402 |
| Full skill payload bytes | 203,270 | 200,930 | −2,340 |
| Typical session bytes (includes brainstorming) | 33,772 | 32,948 | −824 |
| Bootstrap bytes | 5,381 | 5,381 | 0 |

## Runs

Each cell is passes/runs. Every run in the table was executed, with 3 runs per cell. The old text ran from
a detached origin/main worktree and the new text from this branch. Models were chosen with `BENCH_MODEL`.

| Eval | Model | Old | New | Mean cost old / new |
|---|---|---:|---:|---|
| builder-eval DESIGN=elevated | sonnet | 3/3 | 3/3 | $0.100 / $0.107 |
| builder-eval DESIGN=elevated | opus | 3/3 | 3/3 | $0.218 / $0.214 |
| builder-eval DESIGN=routine | sonnet | 3/3 | 3/3 | $0.031 / $0.031 |
| builder-eval DESIGN=routine | opus | 3/3 | 3/3 | $0.085 / $0.078 |
| fixloop-eval | sonnet | 3/3 | 3/3 | $0.034 / $0.033 |
| fixloop-eval | opus | 3/3 | 3/3 | $0.076 / $0.080 |
| review-eval/routing.sh (auth, migration, routine × 3) | sonnet | 9/9 | 9/9 | — |
| review-eval/routing.sh (auth, migration, routine × 3) | opus | 9/9 | 9/9 | — |
| SDD routing probe (ad hoc, 4 cases × 3) | sonnet | 6/12 | 9/12 | — |
| SDD routing probe (ad hoc, 4 cases × 3) | opus | 12/12 | 12/12 | — |

How each eval was scored:
- builder-eval: `score.py`. Elevated designs dispatch the builder check and surface its question; routine
  designs dispatch nothing.
- fixloop-eval: `score.py`. The run must stop after round 5 with `Status: INCOMPLETE`, list the open finding,
  and propose no round 6.
- routing.sh: no scorer. The expected answers are elevated, then spec reviewer and code-quality reviewer, for
  auth and migration, and routine, then code-quality reviewer only, for the routine case. I read every row,
  and all match in both versions.

The SDD routing probe is ad hoc and not committed. None of the existing evals covers the routing the
removed graph encoded. The probe is a text-only `claude -p` call: the SDD skill text plus a situation, and
the agent answers `NEXT: bp:<name>`. Cases and expected answers:
- `noplan` → brainstorming;
- `coupled` (a plan exists but its tasks are tightly coupled) → brainstorming;
- `separate` (the user will run the plan in another session) → executing-plans;
- `fit` (an independent plan, run in this session) → subagent-driven-development.

Probe results by case:
- Sonnet failed `fit` 3/3 in both versions by answering bp:using-git-worktrees. That answer is defensible,
  since the Setup step says to set up the workspace first, so the miss comes from the probe, not the skill.
- Old Sonnet failed `coupled` 3/3 by answering executing-plans.
- New Sonnet passed `coupled` 3/3.
- Opus passed every case in both versions.

`tests/skill-triggering/run-all.sh` and the bootstrap routing eval were not run. Neither one tests these
cuts:
- the triggering tests check only that the Skill tool fires, which depends on the frontmatter
  `description`, and no description changed;
- the routing eval reads only `using-bearpaws/SKILL.md`, which did not change.

`testing-anti-patterns.md`: no eval loads it. `grep -rn testing-anti-patterns tests/` finds nothing, and
the only reference anywhere is the `<see>` in `test-driven-development/SKILL.md`. Nothing in the repo
refers to Anti-Pattern 5 or the removed section by name. The cut rests on that reference analysis, and no
model run backs it.

Limits:
- 3 runs per cell and one fixture per eval.
- The probe adds one more scenario of its own.
- Raw outputs were under `/tmp/trim-eval/out/` and are not committed.
