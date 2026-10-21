# Diff-size baseline — 2026-10-21

This is the RED measurement for over-building: how many source lines each arm writes for the same task, before any skill text changes. It is not a claim that Bearpaws is wrong to write them; read it next to the escape counts.

On the six elevated-risk tasks, **Bearpaws wrote about 1.9× the code of a careful reference fix, no plugin wrote 0.8×**. Bearpaws let 5 of 32 defects escape against 15 of 32 for no plugin (Fisher exact p = 0.014). The extra Bearpaws lines are partly the defenses the hidden attacks test for and partly guards against inputs the code cannot receive, race hardening the task did not ask for, and comments explaining both.

On the nine routine tasks the arms are level, except where the task touches security: there Bearpaws wrote 2 to 11 times the lines of no plugin for the same accepted fix.

## Method

- Runner: `tests/benchmark/run.sh` at `f97bb03` (rows rescored with the `197a0d0` summarizer), Claude Code 2.1.300, Sonnet, `--jobs 3`. Both arms got the same prompt and non-interactive suffix.
- `src_added`: source lines added between `scenarios/<name>/repo/` and the final work tree (difflib; tests, docs, caches, dotfiles and `.md`/`.txt` excluded). Added tests do not count.
- `bloat`: mean over runs of `src_added / ref_src_added`, where the reference is the scenario's `hidden/reference/` overlay (the careful fix that passes the attacks). Only the risk suite has one.
- *Code-only* columns drop blank lines, comments and docstrings. They were computed after the fact with a one-off script, not by the summarizer, so they are indicative.
- Data: [`2026-10-21-diff-size-risk.jsonl`](2026-10-21-diff-size-risk.jsonl) (64 rows) and [`2026-10-21-diff-size-routine.jsonl`](2026-10-21-diff-size-routine.jsonl) (54 rows). The `source` field marks re-run rows.

## Risk suite

| Arm | Runs | Accepted | Escaped | Disclosed | Added lines | Code-only | Bloat | Code-only bloat | Reviews req/ret | $/run |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| No plugin | 32 | 32 | 15 | 0 | 5.5 | 2.9 | 1.39 | 0.81 | 0/0 | 0.057 |
| Bearpaws | 32 | 32 | **5** | 5 | 9.3 | 6.7 | **2.54** | **1.93** | 68/68 | 0.297 |

Per scenario, code-only lines added (the reference fix's count in brackets) and escapes out of 5 or 6:

| Scenario | Reference | No plugin | Bearpaws | Escapes: no plugin | Escapes: Bearpaws |
|---|---:|---:|---:|---:|---:|
| risk-backfill | 5 | 3.2 | 8.0 | 0 | 0 |
| risk-refund | 2 | 2.0 | 6.0 | 5 | 0 |
| risk-reset-token | 3 | 3.0 | 7.6 | 5 | 5 |
| risk-sql-sort | 4 | 4.4 | 5.0 | 1 | 0 |
| risk-tenant-authz | 4 | 1.2 | 4.3 | 4 | 0 |
| risk-upload-path | 4 | 3.3 | 9.0 | 0 | 0 |

How to read it:

- **No plugin's low count is partly under-fixing.** On tenant-authz it wrote 1.2 lines and let 4 of 5 defects through; the reference needs 4. On refund it wrote exactly the 2 lines asked for and shipped the negative-refund defect every time.
- **Bearpaws's extra lines split three ways.** Refund is the cleanest case: the reference is 2 lines, Bearpaws wrote 6. Two are the attack-tested `amount_cents <= 0` guard. Two more reject a `bool` or non-`int` amount, which no caller passes. On reset-token, Bearpaws wrote 7.6 lines against 3: a named constant, a guard for a `created_at` that is a `bool` or non-numeric, and a comparison written to fail on NaN and infinity, with a comment saying so. All 5 Bearpaws reset-token runs still shipped the single-use defect, so the extra lines bought nothing the attacks measure.
- **Where both arms are safe, Bearpaws still writes more.** Upload-path: 0 escapes in both arms, 3.3 lines against 9.0. Two Bearpaws runs added an `O_NOFOLLOW` open with `errno.ELOOP` handling to close a check-then-open race, after a reviewer raised it. The task was a path-traversal fix.
- **Backfill: both arms clear the attacks, at 3.2 and 8.0 code lines against a 5-line reference.** All-lines bloat is above 2 in both arms because both write docstrings and multi-line SQL; compare the arms there, not the absolute ratio.

## Routine scenarios

27 runs per arm, 9 scenarios × 3. Every run was accepted and passed its visible suite.

| Arm | Added lines | Code-only | New files | Reviews req/ret | $/run |
|---|---:|---:|---:|---:|---:|
| No plugin | 15.2 | 12.7 | 0.8 | 0/0 | 0.061 |
| Bearpaws | 16.9 | 13.9 | 0.8 | 14/14 | 0.143 |

Per scenario, mean lines added:

| Scenario | No plugin | Bearpaws |
|---|---:|---:|
| broken-test-config | 5.0 | 5.0 |
| conventions | 16.0 | 16.0 |
| multi-file-refactor | 12.0 | 12.0 |
| new-subsystem | 67.0 | 61.0 |
| resume-after-context-loss | 16.0 | 16.3 |
| simple-feature | 12.0 | 12.0 |
| small-bug | 1.0 | 1.0 |
| security-fix | 4.0 | **19.3** |
| security-fix-injected | 4.0 | **9.3** |

Seven of nine scenarios are identical or within a line. On new-subsystem, Bearpaws wrote less. The whole gap is the two security scenarios, where the elevated-risk rule applies: the same `read_user_file` traversal fix that no plugin made in 4 lines every time took Bearpaws 6, 8 and 44 lines. The 44-line run had four reviews ($0.62, 188 s). The reviewers raised a directory-swap race, FIFO targets and descriptor leaks; the agent answered with an `O_NOFOLLOW` component walk, `fstat` regular-file checks and errno mapping, then reported that a 20,000-iteration race stress test never leaked a file. The prompt asked that reads outside `base_dir` raise `PermissionError`.

## What this does and does not show

- The over-building Bearpaws adds is concentrated on elevated-risk work and is driven by the review loop: reviewers enumerate failure modes, and `requesting-code-review` says fix Important findings before proceeding. On routine work with no security surface the two arms write the same code.
- Some of the extra lines are the point. Refund's `<= 0` guard and tenant-authz's org check are why Bearpaws escaped 5 and no plugin 15. A change that cuts lines must keep escapes at or below 5 of 32 on this suite.
- The rest is speculative: type guards on trusted internal values, NaN handling on a timestamp, TOCTOU hardening nobody asked for, and comments defending each. That is the target.

## Limits

- n is 5 or 6 per cell, one model, Python stdlib scenarios.
- The machine lost its network overnight during the first pass (`ENOTFOUND`). Reps 4 and 5 of both arms and two Bearpaws rep-3 cells failed with one turn and no edits and were dropped; those 26 cells were re-run the next morning into separate output directories and merged (`source` field). Four cells therefore have 6 runs instead of 5. Wall-clock seconds for the surviving first-pass rep-3 runs include the outage and are not comparable; `$/run` is.
- The reference fix is one careful answer, not a minimum. Bloat above 1 in both arms (backfill) means the reference is lean, not that both arms over-built.
- `src_added` counts docstrings, comments and blank lines. The code-only numbers correct for that but come from a post-hoc script; if they matter for a decision, move the filter into the summarizer first.
- The diff is against the pristine repo, so it cannot see churn inside a function that nets to the same line count.

## After the reviewer change (2026-10-21, `a7b3187`)

The reviewer templates were changed so that severity follows the requirements and the enumerated failure modes (RED/GREEN in [`tests/review-eval/overbuild-evidence.md`](../../tests/review-eval/overbuild-evidence.md)). The Bearpaws arm was re-run on the risk suite (5 reps) and the two routine security scenarios (3 reps). Data: [`2026-10-21-diff-size-reviewfix.jsonl`](2026-10-21-diff-size-reviewfix.jsonl).

| | Before (`f97bb03`) | After (`a7b3187`) |
|---|---:|---:|
| Escaped | 5/32 | **4/30** (+1 disclosed) |
| Accepted | 32/32 | 28/30 (2 sessions hit the 900 s timeout) |
| Added lines | 9.3 | 10.6 |
| Code-only added | 6.6 | 7.7 |
| Code-only bloat | 1.92 | 2.28 |
| $/run | 0.297 | 0.306 |

The escape gate holds. Lines did not fall, so the review loop is not where this suite's extra code comes from: it is written in the first implementation. The fix in `risk-refund/1` guards the order's own `total_cents` for type and sign, a value no caller of `refund` sets. On the routine security pair, security-fix went from 19.3 to 8.7 lines (the 44-line run did not recur) and security-fix-injected from 9.3 to 13.0; both are n=3.

## After the bootstrap change (2026-10-21, `f01eb55` then `e9657dc`)

The transcripts showed where the extra lines came from. In every refund and reset-token run the first fix was minimal; the agent then asked its reviewer for "same risk class" gaps, naming non-int amounts, the reviewer executed `refund(order, float('nan'))` and filed it as Important ("a reachable failure from the function's own inputs"), and the agent added the guard under the bootstrap's same-class rule. Across the two earlier runs, 19 of 32 and 15 of 28 final sources carried NaN, bool or None guards, and 22 of 32 and 20 of 28 dispatch prompts asked for them.

`f01eb55` added one sentence pair to the bootstrap's elevated-risk paragraph: a defect is behavior a caller or an untrusted input can reach, and a guard for a value no caller produces is not one. The reviewer templates defined "reachable" the same way. `e9657dc` tightened it after one escape (below): a negative or oversized amount is a defect; only a type no caller passes (NaN, bool, a string where a number goes) is exempt.

Bearpaws arm, risk suite, 5 reps each. Code-only columns come from the post-hoc script:

| | Before (`f97bb03`) | Reviewer (`a7b3187`) | Bootstrap v1 (`f01eb55`) | Bootstrap v2 (`e9657dc`) |
|---|---:|---:|---:|---:|
| Escaped | 5/32 | 4/30 | 5/30 | **5/30** |
| of which refund | 0 | 0 | **1** | 0 |
| Accepted | 32/32 | 28/30 | 29/30 | 30/30 |
| Code-only lines added | 6.6 | 7.7 | 4.7 | **4.9** |
| Code-only bloat | 1.92 | 2.28 | 1.31 | **1.38** |
| Sources with type/None guards | 19/32 | 15/28 | 9/29 | 9/30 |
| Reviews dispatched | 68 | 68 | 47 | 48 |
| $/run | 0.297 | 0.306 | 0.227 | 0.257 |

- All 5 remaining escapes are the reset-token single-use attack, as in every earlier run.
- The 9 remaining guards are the `None` org checks in tenant-authz, which the hidden attack requires, and a bounded age in reset-token. The NaN, bool and float guards on refund amounts are gone: refund settled at 4 code lines in 5 of 5 runs (reference 2; the extra 2 are the attack-tested non-positive check).
- **The v1 regression.** In `f01eb55` refund run 5 the agent dropped the negative-amount check, wrote "Callers outside this repo don't pass negative amounts" in its assumptions, and the reviewer approved, having "found no defect reachable from this repo". The attack caught it. The v1 sentence said "a value no caller produces" and the agent read a value support staff can type as one. v2 names negative and oversized amounts as defects and limits the exemption to types. A review-eval fixture (`refund-narrow`: the cap with no sign check) now pins it: rejected 3/3 with the negative amount as a blocking finding.
- Routine security pair after v2: security-fix 5.7 lines (19.3 at baseline), security-fix-injected 8.0 (9.3).

Data: [`2026-10-21-diff-size-bootstrap-v1.jsonl`](2026-10-21-diff-size-bootstrap-v1.jsonl), [`2026-10-21-diff-size-bootstrap-v2.jsonl`](2026-10-21-diff-size-bootstrap-v2.jsonl). Same limits as above: n=5 per cell, one model, and v1 against v2 is a one-escape difference that n=5 cannot resolve; the fixture, not the benchmark, is the evidence for the v2 wording.
