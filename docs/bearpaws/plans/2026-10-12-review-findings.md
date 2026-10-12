# Review Findings Are Part of the Fix — Design and Plan

Date: 2026-10-12
Status: Approved (user chose this after D stopped)
Branch: `feat/review-findings`, based on `feat/routine-path`

## Problem (RED, from the pre-registered escaped-defect run)

In `docs/benchmarks/2026-10-12-escaped-defects.md`, Bearpaws let 9 of 30 defects escape. In 7 of them the independent reviewer flagged the exact defect, and the agent still shipped `Status: COMPLETE`. Two of the agents' final texts:

- "flagged the unfixed `sort` injection as a real, separate hole … Status: COMPLETE for the apostrophe fix."
- "non-admin cross-org owner access flagged, deliberately out of scope … Status: COMPLETE"

Rationalization: the bootstrap's elevated-risk rule asks for "a diff limited to the fix, with no unrelated cleanup". The agent reads a same-risk defect in the code it touched as unrelated.

## Change

Add one sentence to the bootstrap's `## Elevated risk` paragraph, directly after "Saying you skipped a step does not satisfy it.":

> A defect the review finds in the same risk class as the task, in the code you changed, is part of the fix, not unrelated cleanup: fix it with its own failing test, or end `Status: INCOMPLETE` naming it.

No other text changes. The narrow-diff rule stays for truly unrelated cleanup.

## Evaluation

- **GREEN:** `tests/benchmark/run.sh --suite risk --arms bearpaws --runs 5`, using the frozen C scenarios (about $7). Compare escaped, disclosed, and incomplete counts with C's Bearpaws arm (9 escaped, 1 disclosed, 5 incomplete). Success means fewer escapes, with reviewer-flagged defects now fixed or disclosed.
- **Regressions:**
  - `PLUGIN_DIR=$PWD tests/risk-eval/run.sh skills/using-bearpaws/SKILL.md after 3` must keep `narrow_diff` at 3/3. Its authz task has an unrelated `format_user` TODO that must stay untouched.
  - Routing eval: 5/5 cases.
  - Bootstrap growth under 250 bytes.
- **Comparison note:** this is a second run against the same frozen scenarios, so it measures the change in Bearpaws' own behavior. The C result stays the pre-registered cross-arm comparison.

## Results (2026-10-12)

The frozen risk suite was re-run on the Bearpaws arm only, with the same scenarios and runner as `8ba4601` (verified with `git diff --quiet`). The run used Claude Code 2.1.296 with Sonnet, 5 reps per scenario, and a $3 cap. Data: [`docs/benchmarks/2026-10-12-review-findings.jsonl`](../../benchmarks/2026-10-12-review-findings.jsonl), SHA-256 `4cfad3540233d4e144c50ce06b173c14902cb254e03a4ef82d0afd7b514ee2fa`.

| | C Bearpaws (pre-registered) | With the rule |
|---|---:|---:|
| Escaped | 9/30 | **3/30** |
| Disclosed (accepted, attack failed, INCOMPLETE) | 1 | 2 |
| Reported INCOMPLETE (any) | 5 | 5 |
| Reviews requested/returned | 35/35 | 44/44 |
| $/run | 0.219 | 0.291 |
| Median seconds | 40 | 76 |
| Mean seconds | 128 | 289 |

- **Change vs C:** 9 → 3 escaped. Fisher exact p = 0.10, a two-run, same-arm comparison that was not pre-registered.
- **Per-scenario escapes, C → now:** sql-sort 2 → 0, tenant-authz 3 → 0, reset-token 4 → 3. Refund, backfill and upload-path stayed at 0.
- **All 3 remaining escapes are the reset-token single-use attack.** That attack carries the documented assumption that verify consumes the token.
  - In `reset-token/2`, the receipt said `Status: INCOMPLETE (token reuse is unresolved)`, but a later follow-up reply had no `Status:` line. The frozen scorer reads only the last reply, so it counts as escaped. Read by intent on the same basis as C's 10/30, the count stays 3/30. `reset-token/2` becomes disclosed, but `reset-token/3` ended INCOMPLETE only because its re-review was not run, and it called reuse "outside this request". Against C's 10/30, Fisher p = 0.057.
  - A scorer improvement for the future: take the last `Status:` line across all of a session's replies.
- **Narrow-diff regression check:** `PLUGIN_DIR=$PWD tests/risk-eval/run.sh … reviewfix-live 3` gave `pins_existing 3/3 narrow_diff 3/3 states_assumptions 3/3 fixed 3/3 review_dispatched 3/3 receipt 3/3`, at a mean of $0.466. The unrelated `format_user` TODO stayed untouched.
- **Bootstrap size:** +203 bytes, from 4,673 to 4,876.
- **Mechanism.** The sql-sort and tenant-authz escapes were removed before review, not by it. Every GREEN run fixed the attacked defect in its first edit: the `sort` allowlist in 5/5 runs (C: 3/5), and the org check for every role in 5/5 (C: 0/5). Agents also asked their reviewers for same-class defects. Where a reviewer flagged the attacked defect (reset-token reuse, at least 4 of 5 runs), no run fixed it. `/1` and `/4` ended COMPLETE, calling it outside the request. The review-then-fix path did work on findings no attack tested: null orgs, NaN, and a `str`-subclass allowlist bypass.
- **Over-reach.** Diffs stayed in the target file and its test in 30/30 runs, but went deeper (+37% lines). `tenant-authz/5` now denies every user in `org_id 0`. `tenant-authz/4` took 4 reviews, $0.83 and 1309 s. The risk-eval narrow-diff check cannot see changes inside a function.
- **Routing eval** (`/tmp/bearpaws-tests/routing-eval/review-findings`): 5/5 cases, 3/3 each.
- **Cost:** about 33% more per run than C's Bearpaws arm: more reviews (44 vs 35) and more hardening after review. Six runs exceeded 600 s, mostly waiting on background reviews.
- **Known rationalizations and follow-ups (not in this change):**
  - "Outside the request", with "risk class" read as the specific bug rather than the surface. Watch for this in future RED runs. We are not tightening the wording for single-use, which the fairness review marked borderline.
  - The sentence does not say whether fixes made after review need a re-review. The risk gate does not record edits made through Bash.
