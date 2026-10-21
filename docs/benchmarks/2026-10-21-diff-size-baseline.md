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
