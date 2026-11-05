# Drift check evaluation

Borrowed from the Elephant-Goldfish Model's drift report (https://egm.dev/): after implementation, compare
the code with the plan and report only where they diverge. Bearpaws runs it as one step in
`bp:finishing-a-development-branch`, in the controller, with no subagent. It is skipped when a final
review already checked the whole branch against the plan (the `bp:subagent-driven-development` path), so
it adds no pass there; it covers `bp:executing-plans` and standalone finishes, which had no plan-vs-code check.

Fixture (`setup.sh`): a branch whose plan has three tasks, all checked off, all tests passing. Task 2 was
never built (an empty commit), Task 3 hardcodes `[:50]` instead of adding `max_len`, and `src/cache.py`
is in no task. `CLEAN=1` builds the same plan correctly and adds a README and changelog no task names, as
a control for invented drift. Sonnet, 3 runs each.

Scoring (`score.py`, pinned by `test_score.py`): the step asks for a `Drift:` line with one bullet per
divergence, or "No drift." Only bullets in that block count, so verification prose and commit listings
elsewhere in the reply cannot score as findings.

| Run | Task 2 missing | `max_len` missing | `cache.py` unplanned | Said "No drift" | Mean cost |
|---|---:|---:|---:|---:|---:|
| RED (skill before the step) | 0/3 | 0/3 | 0/3 | 0/3 | $0.057 |
| GREEN (final step text) | 3/3 | 3/3 | 3/3 | 0/3 | $0.053 |
| CLEAN control, with collateral files (final step text) | 0/3 | 0/3 | 0/3 | 3/3 | $0.051 |

RED rationalization, every run: "Tests pass (2 tests, OK)", then straight to the four options. Passing
tests plus checked boxes were taken as the plan being built; the step names that directly. One RED run
added that no test covered Task 2's stripping, without saying it was unbuilt, and kept the branch.

An earlier step text without the `Drift:` format named all three divergences in prose in 3/3 runs
(read by hand; the block scorer counts 1/3 because it predates the format). Raw outputs land under
`/tmp/bearpaws-tests/drift-eval/<timestamp>/` and are not committed.

Limits: one fixture shape, one model, n=3. A task built in the wrong file, or a renamed symbol, is untested.

Not adopted from EGM: reviewers already get crafted context and never session history
(`bp:requesting-code-review`). The isolation is partial and labeled, not EGM's spec-and-code-only:
reviewers still receive the author's description, decisions and (for the spec reviewer) the implementer's
report, each marked as a claim, with scope claims ignored (pinned by the `refund-scoped` and
`refund-offscope` review-eval fixtures). The report stays because the spec reviewer's job includes catching
claimed-but-unbuilt work; no eval shows it anchoring reviews. The five-stage spec review loop would add
review passes, which the cost-per-accepted-task metric argues against.
