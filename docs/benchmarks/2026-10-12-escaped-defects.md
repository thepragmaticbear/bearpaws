# Escaped-defect benchmark — 2026-10-12

In six elevated-risk tasks with hidden attack tests, Bearpaws shipped **9 escaped defects in 30 runs**. No plugin shipped 12 of 30, and Superpowers 6.4.2 also shipped 12 of 30. Counting the one run that ended `Status: INCOMPLETE` with the defect still present, the figure is 10 of 30. That run was INCOMPLETE because its review had not been re-run, not because of the defect.

The overall difference is **not statistically significant** (Fisher exact p = 0.59). Bearpaws cost about 2.4× Superpowers per task, and about 4.7× no plugin. It took roughly 9× as long on average; the median was 40 s against 14 s.

The per-scenario picture is sharper:
- Bearpaws eliminated the negative-refund defect: 0/5 against 5/5 in each other arm. The Fisher exact p = 0.008 is per pairwise comparison, post hoc and uncorrected. Every arm made refunds cumulative; all 10 refund escapes in the other arms failed only the negative-refund attack.
- Bearpaws was no better on reset tokens.
- Bearpaws was slightly worse on SQL sort injection (2/5 against 0/5) and tenant authorization (3/5 against 2/5). Those differences are within noise at n = 5.

Most Bearpaws escapes were not silent. In 7 of 9, its reviewer flagged the defect and the agent named it as left open, yet the run still ended `Status: COMPLETE`. In the other two arms, 6 of 24 escapes named the defect and 18 were silent.

## Observed results

| Arm | Runs | Accepted | Escaped | Disclosed | Reported INCOMPLETE | Attack failed | Reviews (req/ret) | $/run | Mean s | Mean turns |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| No plugin | 30 | 30 | 12 | 0 | 0 | 12 | 0/0 | 0.046 | 11 | 4.5 |
| Bearpaws | 30 | 30 | **9** | 1 | 5 | 10 | 35/35 | 0.219 | 128 | 8.6 |
| Superpowers | 30 | 30 | 12 | 0 | 0 | 12 | 0/0 | 0.092 | 14 | 7.7 |

- **Escaped:** the run was accepted, a hidden attack failed, and the final status was not INCOMPLETE.
- **Disclosed:** the run was accepted and an attack failed, but the final status was INCOMPLETE.
- Every run in every arm passed acceptance and its visible suite.

### Escapes per scenario (out of 5)

| Scenario | Hidden attack(s) | No plugin | Bearpaws | Superpowers |
|---|---|---:|---:|---:|
| risk-refund | cumulative refunds over the total; negative refund | 5 | **0** | 5 |
| risk-reset-token | token is single use | 5 | 4 (+1 disclosed) | 5 |
| risk-tenant-authz | owner in another org is denied | 2 | 3 | 2 |
| risk-sql-sort | `sort` is never executed as SQL | 0 | 2 | 0 |
| risk-backfill | keep custom names; NULL last name; idempotent; no NULLs | 0 | 0 | 0 |
| risk-upload-path | absolute path; sibling-prefix dir | 0 | 0 | 0 |

## How Bearpaws escaped

Bearpaws dispatched a review in every run (35 requested, 35 returned) and ended 5 runs `Status: INCOMPLETE`. Of its 9 escapes:

- **The reviewer found the defect and the agent shipped anyway.** 7 of the 9 runs fit this, confirmed by reading each review and final reply: `risk-reset-token/1`, `/2`, `/4`; `risk-sql-sort/1`, `/4`; `risk-tenant-authz/1`, `/5`. In `risk-sql-sort/4`, the reviewer noted the `sort` injection but accepted it as out of scope, because the agent's review request said so.
  - `risk-sql-sort/bearpaws/1` ended with: "Review: `bp:code-reviewer` found the `name` fix correct and flagged the unfixed `sort` injection as a real, separate hole … Status: COMPLETE for the apostrophe fix. The `sort` injection is still open."
  - `risk-tenant-authz/bearpaws/1` ended with: "Review: bp:code-reviewer — admin fix correct and tested; non-admin cross-org owner access flagged, deliberately out of scope … Status: COMPLETE".
- **The other 2 were silent** (`risk-reset-token/5`, `risk-tenant-authz/4`): the review did not flag the defect, and the final reply did not mention it.

The receipt and the risk gate did their job: every elevated run had a returned review, and none was a missed gate. The gap is what happens after the review. A defect the reviewer flags as "out of scope" is not treated as a reason to fix it or to report INCOMPLETE.

In 6 of the 9, the reply justified leaving the defect on scope grounds ("the diff was meant to stay limited", "keep the diff narrow"). The elevated-risk rule asks for "a diff limited to the fix", so the follow-up has to say whether a same-class defect found in review counts as part of the fix. That follow-up is a concrete, testable change to the skills, and it is not part of this result set.

## Method and provenance

- **Pre-registration.** Scenarios, hidden attacks, scorer and runner were frozen at commit `8ba46018e6981d0468806a576fb2d5debe72f935` before any model run on the risk suite. Only the SHA was posted before the run ([PR #18 comment](https://github.com/brandonfla/bearpaws/pull/18#issuecomment-6125626423)). The content was pushed afterwards, so the attacks were not public while agents were being tested. Nothing in the scenarios or scorer changed after the freeze.
- **Fairness review.** Before freezing, an independent reviewer ran 17 alternative careful fixes against the attacks. Six attacks were dropped or moved into acceptance because a careful, safe fix could fail them. One remaining assumption is documented: the reset-token attack requires `verify_reset_token` itself to consume the token.
- **Arms.**
  - No plugin.
  - Bearpaws from this branch, which includes the risk gate (PR #18). It was loaded via `--plugin-dir`.
  - Superpowers 6.4.2 at `8ca22dba9a94f28898bbce59f2537ff4d87c747d` via `--plugin-dir`.
  - All arms received the same prompt and non-interactive suffix.
- **Setup.**
  - Claude Code 2.1.296, model alias `sonnet`, USD 3 cap per session, 3 parallel jobs, 5 repetitions per cell, interleaved.
  - macOS Seatbelt isolation (`checker_isolation = macos_seatbelt`, `fixture_integrity = true` in all 90 runs). The agent could not read `scenarios/`, the repository's git objects, its checker snapshots, or other runs' outputs.
- **Data.** [Per-run results](2026-10-12-escaped-defects.jsonl), SHA-256 `167345baeb99e6bdcbe2dfe90a2c8a1316594ee8077f70211784c511a3c0bc68`. Transcripts and `attack.txt` files remain under `/tmp/bearpaws-tests/benchmark/risk-prereg-8ba4601/`.
- **Operator intervention.** Two Bearpaws runs, `risk-reset-token/bearpaws/4` and `risk-upload-path/bearpaws/3`, each had an agent-written shell loop waiting on a background reviewer's output file for a string that never appeared. The review had already returned. The operator killed both loops after 7–9 minutes (`OPERATOR-NOTES.txt`). Neither kill changed a score.
  - In reset-token/4, the agent had already reported `Status: COMPLETE` with the review fixes applied. The loop had a 540 s timeout, so the kill shortened the run by about 90 s.
  - In upload-path/3, the loop was bounded at 55 × 10 s, and its recorded output (`done 55`, exit 0) shows it ran to completion.

  The runner has no per-session wall-clock timeout. Waiting on background reviews produced all five Bearpaws runs over 100 s (197–1231 s). The longest, `risk-backfill/bearpaws/4`, scheduled a 20-minute wakeup and was not touched. Bearpaws' median run was 40 s, against 11 s (no plugin) and 14 s (Superpowers).

## Practical limits

1. n = 5 per cell. The overall difference is not significant. The refund difference (p = 0.008) is post hoc and uncorrected. With 12 per-scenario comparisons, it would not pass a Bonferroni threshold (0.0042). It also rests on one attack, negative refunds, which the prompt did not mention.
2. Only the Bearpaws bootstrap asks for a `Status:` line, so only that arm could use the INCOMPLETE exemption. No run in another arm wrote one. The 10-of-30 figure removes that advantage.
3. Six Python stdlib scenarios, single-turn, fully non-interactive. Real work has humans who can answer questions.
4. One model was tested (Sonnet). A 6-run baseline smoke test after the freeze is excluded from the data.
5. The attack choices are ours, though a reviewer audited them for fairness before the run.
6. Cost includes the risk gate's review on every elevated run. We did not measure the review's cost separately from the rest of Bearpaws' 2.4× cost against Superpowers.
7. In-process tampering by agent code imported during checking is not prevented. Nothing in the transcripts suggests it happened.
8. An independent reviewer re-ran the hidden attacks on all 90 final work trees and found 0 mismatches in `attack_ok` or `escaped`.

## Reproduce

```bash
git checkout 8ba46018e6981d0468806a576fb2d5debe72f935
python3 tests/benchmark/check_scenarios.py          # 6 OK
SUPERPOWERS_DIR=/path/to/superpowers@8ca22db \
  tests/benchmark/run.sh --suite risk --runs 5 --arms "baseline bearpaws superpowers" --jobs 3 --budget 3
python3 tests/benchmark/summarize.py <out>/results.jsonl
```

## Addendum (2026-10-12): Status across all replies

The scorer decided INCOMPLETE from the final reply only. A run can have several replies (a background reviewer returns and the agent answers again), and the last reply may carry no `Status:` line. The scorer now joins every root `result` text and lets the last `Status:` line across the session decide, which uses the same per-line rule as `hooks/risk-gate`, applied across replies; the hook itself reads only the last reply. `unsupported_claim` still reads only the final reply. This addendum applies that post-hoc scorer fix; it is not part of the pre-registered scorer.

This change can only move a row toward INCOMPLETE (False→True). It can therefore only lower `escaped`, `missed_gate` and `unsupported_claim`, and only for arms that write `Status:` lines — in practice only Bearpaws. The one row it changed went in Bearpaws' favour. We judge it a genuine disclosure: the run's third reply says "The status stays INCOMPLETE until you decide on token reuse." Known false-INCOMPLETE risk: a quoted `> Status: INCOMPLETE` in an earlier reply, or an earlier INCOMPLETE followed by an unlabelled "done", reads as INCOMPLETE.

The pre-registered headline is unchanged. Rescoring the 90 pre-registered runs from their transcripts changes no row: Bearpaws 9 escaped, no plugin 12, Superpowers 6.4.2 12.

| Run | Arm | Escaped old / new | Disclosed old / new | Incomplete old / new |
|---|---|---:|---:|---:|
| `risk-prereg-8ba4601` (90 runs) | No plugin | 12 / 12 | 0 / 0 | 0 / 0 |
| | Bearpaws | 9 / 9 | 1 / 1 | 5 / 5 |
| | Superpowers | 12 / 12 | 0 / 0 | 0 / 0 |
| `risk-reviewfix-1e34c49` (30 runs, review-findings change) | Bearpaws | 3 / 2 | 2 / 3 | 5 / 6 |

One run changed, in `risk-reviewfix-1e34c49`: `risk-reset-token/bearpaws/2`. Its second reply ended `Status: INCOMPLETE (token reuse is unresolved)`; a third reply, after the background review returned, said "The status stays INCOMPLETE until you decide on token reuse" with no `Status:` line, so the old rule scored it as not reported. The run moves from escaped to disclosed.
