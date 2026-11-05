# Scoped re-review evidence (v3 Task 3)

Fixture `FIXTURE=rereview` (`setup.sh`): three commits on `src/billing.py`.

- base: `refund()` with no checks, and a pre-existing `report()` that builds SQL by string concatenation.
- A, the head the previous review saw: caps each refund at the order total. Two open findings, verbatim in `report-rereview.txt`: F1 accepts a negative amount; F2 ignores the cumulative cap.
- B, the fix (HEAD): rejects `amount_cents < 0`. F1 is addressed, F2 is untouched, and zero is still accepted although `task-rereview.txt` says amounts must be positive.

Rendering (`render.py`):

- RED, the full template re-run the way the SDD loop did before this change: `BASE_SHA` is the commit before A, so the reviewer sees the whole task diff. `DESCRIPTION` is `report-rereview.txt`, which names the open findings and the implementer's DONE claim, as a controller re-dispatching the full template would pass them.
- GREEN: `[FIX_BASE_SHA]` is A, `[HEAD_SHA]` is B, and `[FINDINGS]` is the report's two bullets, without the DONE claim.

Both arms ran on the same model (`BENCH_MODEL` default, sonnet), so the cost difference comes from the prompt and its scope, not from model choice. The skill tells the controller to use the cheapest model that handles review, which would widen the gap.

Scorer: `score.py` adds a `rereview` key when `FIXTURE=rereview`. It is pinned by `test_score.py` (`RereviewTest`).

## RED: full review as re-review (2026-11-05)

`FIXTURE=rereview AGENT_PROMPT=agents/code-reviewer.md tests/review-eval/run.sh skills/requesting-code-review/code-reviewer.md rereview-red 3`

| Run | F1 / F2 verdict | F2 raised as blocking | Zero bug | SQL | Cost |
|---|---|---|---|---|---|
| 1 | none / none | yes | Issues, Important | Minor, in Issues | $0.0787 |
| 2 | none / none | yes | Issues, Important | Minor, in Issues | $0.0795 |
| 3 | none / none | yes | Issues, Important | Minor, in Issues | $0.0796 |

Mean cost: **$0.0793**.

What RED did well: all three runs caught F2 as still open and the zero-amount bug as Important, and none made the SQL issue blocking. The plan expected the SQL issue to block; it did not.

What RED got wrong:

- There is no per-finding verdict. F1's status appears only in a Break Attempt or under Strengths, so the controller has to infer which findings are closed.
- The SQL issue sits in the Issues list (Minor). It is not separated from the task's findings.
- The review re-opened code the fix round did not touch. All three runs added an Important "missing tests" item covering commit A's `test_over_total_raises` (it does not assert that the order is unchanged), plus an exact-total boundary test. These items were not in the open findings or the fix diff, but as Important items they extend the loop. Blocking bullet lines (Critical plus Important, sub-bullets included): 13, 15, 8.
- It costs a full review: all four gates, failure-mode enumeration, strengths and recommendations.

## GREEN round 1: `re-review-prompt.md` (2026-11-05)

`FIXTURE=rereview tests/review-eval/run.sh skills/subagent-driven-development/re-review-prompt.md rereview-green 3`

| Run | F1 / F2 verdict | Zero bug | SQL | Pass | Cost |
|---|---|---|---|---|---|
| 1 | ADDRESSED / NOT ADDRESSED | New Breakage, Important | Out-of-Scope only | yes | $0.0513 |
| 2 | ADDRESSED / NOT ADDRESSED | New Breakage, Important | Out-of-Scope only | yes | $0.0486 |
| 3 | ADDRESSED / NOT ADDRESSED | New Breakage, Important | Out-of-Scope only | yes | $0.0506 |

Mean cost: **$0.0502**, 37% below RED. All runs gave 3 or 4 `Tried:` lines, every one labelled. All three verdicts read "Findings remain open". Result: **3/3 pass on round 1**, so the prompt was not tightened.

Observations, which do not block:

- Run 1 also listed F2 under New Breakage as "the same defect as Finding 2". It is a duplicate, not a new item, and adds no extra loop work.
- No run executed code. Every break attempt was `[reasoned]`, which the prompt allows ("only when reading leaves a specific doubt").
- No run raised commit A's test gaps as blocking. Run 1 put a docstring note and an int-type note under Out-of-Scope.

## Routing check

`tests/review-eval/routing.sh 3` after the SKILL.md wiring: auth and migration came back elevated, with spec review then code quality, 3/3 each. Routine came back routine, with code quality only, 3/3. The routing is unchanged.
