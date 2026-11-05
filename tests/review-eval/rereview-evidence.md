# Scoped re-review evidence (v3 Task 3)

Fixture `FIXTURE=rereview` (`setup.sh`): three commits on `src/billing.py`.

- base: `refund()` with no checks, and a pre-existing `report()` that builds SQL by string concatenation.
- A, the head the previous review saw: caps each refund at the order total. Two open findings, verbatim in `report-rereview.txt`: F1 accepts a negative amount; F2 ignores the cumulative cap.
- B, the fix (HEAD): rejects `amount_cents < 0`. F1 is addressed, F2 is untouched, and zero is still accepted although `task-rereview.txt` says amounts must be positive.

Rendering (`render.py`):

- RED, the full template re-run the way the SDD loop did before this change: `BASE_SHA` is the commit before A, so the reviewer sees the whole task diff. `DESCRIPTION` is `report-rereview.txt`, which names the open findings and the implementer's DONE claim, as a controller re-dispatching the full template would pass them.
- GREEN: `[FIX_BASE_SHA]` is A, `[HEAD_SHA]` is B, and `[FINDINGS]` is the report's two bullets, without the DONE claim.

Both arms ran on the same model (`BENCH_MODEL` default, sonnet), so the cost difference comes from the prompt and its scope, not from model choice. The skill tells the controller to use the cheapest model that handles review, which would widen the gap.

Scorer: `score.py` adds a `rereview` key when `FIXTURE=rereview`. It is pinned by `test_score.py` (`RereviewTest`). A pass requires all of the following:

- F1 is ADDRESSED and F2 is NOT ADDRESSED, read from the first verdict token.
- The zero item sits under New Breakage at Important or higher, and it names a zero amount.
  - Zero-amount wording that counts: `refund(…, 0)`, an amount of zero, or the `< 0`/`<= 0` check on the amount.
  - Wording that does not count: "below zero" or "total - 600 - 600 < 0".
  - Severity, in order of preference:
    1. An explicit `Severity: X`.
    2. A leading label.
    3. A label after a `file:line` prefix, either parenthesised or after a dash or colon.
    4. A closing severity word, unless "not" precedes it.
    5. The heading.
- The SQL issue appears only under Out-of-Scope.
- The Verdict says a finding remains open, or findings remain open. The Verdict text can sit on the `### Verdict` heading line or on a `**Verdict:**` line.
- There is at least one `Tried:` line under Break Attempts.

## RED: full review as re-review (2026-11-05)

`FIXTURE=rereview AGENT_PROMPT=agents/code-reviewer.md tests/review-eval/run.sh skills/requesting-code-review/code-reviewer.md rereview-red 3`

| Run | F1 / F2 verdict | F2 raised as blocking | Zero bug | SQL | Cost |
|---|---|---|---|---|---|
| 1 | none / none | yes | Issues, Important | Minor, in Issues | $0.0787 |
| 2 | none / none | yes | Issues, Important | Minor, in Issues | $0.0795 |
| 3 | none / none | yes | Issues, Important | Minor, in Issues | $0.0796 |

Mean cost: **$0.0793**.

What RED did well: all three runs caught F2 as still open and the zero-amount bug as Important, and none made the SQL issue blocking. The plan expected the SQL issue to block; it did not. RED also executed code: each run has 2 or 3 `[executed]` break attempts (2, 3, 3).

What RED did not give:

- There is no per-finding verdict. F1's status appears only in a Break Attempt or under Strengths, so the controller has to infer which findings are closed.
- The SQL issue sits in the Issues list (Minor), not in a section separated from the task's findings.
- Each run added a third Important "missing tests" item. Most of it is in scope: tests for F2 and for zero. It also flags that `test_over_total_raises` does not assert that the order is unchanged. That is a real task requirement ("before the order changes"), not unrelated code. Runs 1 and 2 also ask for an exact-total boundary test; run 3 does not. Blocking bullet lines (Critical plus Important, sub-bullets included): 13, 15, 8.
- It costs a full review: all four gates, failure-mode enumeration, strengths and recommendations.

RED's 0/3 on `rereview_pass` is partly by construction: the full template has no Finding Verdicts or Out-of-Scope section and no "Findings remain open" verdict, so those criteria cannot pass. The real deltas are three. GREEN gives per-finding verdicts. It costs 37% less. It raises no extra test items.

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
- No GREEN run executed code. Every break attempt was `[reasoned]`, which the prompt allows ("only when reading leaves a specific doubt"). RED ran 2–3 `[executed]` attempts per run, so part of the cost cut is execution GREEN skipped.
- No run raised commit A's test gaps as blocking. Run 1 put a docstring note and an int-type note under Out-of-Scope.

## Routing check

`tests/review-eval/routing.sh 3` after the SKILL.md wiring: auth and migration came back elevated, with spec review then code quality, 3/3 each. Routine came back routine, with code quality only, 3/3. The routing is unchanged.

## Scorer fix round (2026-11-05)

A review of the first scorer found two false passes:

- Severity came from the first severity word anywhere in an item, so "Not critical: … Severity: Minor" scored Critical.
- The zero pattern matched "0 cents" and "non-positive", so an F2 duplicate could stand in for the zero bug.

It also found two gaps and one false fail:

- `rereview_pass` did not check the Verdict.
- `rereview_pass` did not check Break Attempts.
- "ADDRESSED … not addressed here" read as NOT ADDRESSED.

Each case is now a failing reply in `RereviewTest`. All five fail against the old scorer and pass against the new one.

The six saved transcripts were re-scored with the new scorer:

- RED: 0/3 pass, unchanged. The zero bug is in Issues at Important, the SQL issue is not blocking, and 5, 6 and 6 `Tried:` lines sit under Break Attempts.
- GREEN: 3/3 pass, unchanged. 4, 3 and 4 `Tried:` lines sit under Break Attempts, and every Verdict reads "Findings remain open".

## Scorer fix round 2 (2026-11-05)

The review of fix round 1 found three problems:

- Severity read only from a leading label. Three legitimate forms false-failed: "file:line (Important):", "**file:line** — Important:", and a closing "Important.".
- The verdict check missed three forms: "### Verdict: Findings remain open", "**Verdict:** …", and "remains open".
- The zero pattern still matched F2 duplicates worded "below zero" or "total - 600 - 600 < 0".

Fixes:

- The scorer accepts those forms, and all are pinned as passing.
- The F2 duplicates are pinned as failing.
- A real zero item that also mentions "cumulative" still counts.
- The earlier failing vectors still fail.

`re-review-prompt.md` now tells the reviewer to start each New Breakage item with its severity ("- Important: file:line — what breaks").

Re-scoring the six saved transcripts gave the same numbers: RED 0/3, GREEN round 1 3/3.

Because the prompt changed, GREEN was re-run as `rereview-green2` (3 runs):

| Run | F1 / F2 | Zero bug | SQL | Pass | Cost |
|---|---|---|---|---|---|
| 1 | ADDRESSED / NOT ADDRESSED | New Breakage, Important | Out-of-Scope only | yes | $0.0507 |
| 2 | ADDRESSED / NOT ADDRESSED | New Breakage, Important | Out-of-Scope only | yes | $0.0501 |
| 3 | ADDRESSED / NOT ADDRESSED | New Breakage, Important | Out-of-Scope only | yes | $0.0495 |

Mean cost: **$0.0501**. Every New Breakage item opened with "Important:" or "Minor:".

Two runs added a second item:

- Run 1 restated the open F2 as an Important item.
- Run 2 flagged missing tests for zero and the cumulative cap as Important. Both cases are in the task, so the item is in scope.

No run executed code.
