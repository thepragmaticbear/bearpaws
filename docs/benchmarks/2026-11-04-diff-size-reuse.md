# Diff size, reuse first — 2026-11-04

This tested whether a reuse-first, scoped-simplification change could cut Bearpaws' over-building on the six elevated-risk tasks without letting more defects escape. **It did not cut diff size.** Code-only bloat was 1.44× for the candidate against 1.46× for a concurrent control arm on `main`, short of the 1.1× bar. Escapes held at 5 of 30, with risk-refund at 0. Routine cost rose about 15%. Of the three candidate edits, only the reviewer reimplementation finding moved its own eval. It ships; the other two were dropped or reverted.

## Success criteria (fixed before the run)

| # | Criterion | Result | Pass |
|---|---|---|---|
| 1 | Code-only bloat on the six risk tasks ≤ 1.1× (candidate arm, n=5 per task; control arm in the same batch is the baseline) | Candidate **1.44×**, control 1.46× | **Miss** |
| 2 | Escapes ≤ 5/30; `risk-refund` escapes 0/5; `refund-narrow` review fixture rejected 3/3 with the negative amount blocking | 5/30 (control 4/30); refund 0/5; `refund-narrow` 3/3, negative blocking 3/3 | Pass |
| 3 | Routine cost no higher than the control arm (9 scenarios, n=3) | Candidate **$0.126**/run, control $0.109 | **Miss** |
| 4 | Bootstrap ≤ 5300 bytes | 5285 (unchanged) | Pass |

The plan's floor estimate held. risk-refund stays at 2.0×: every run in both arms adds 4 code lines where the reference adds 2 (the 10-21 runs wrote two `if`s for the reference's one compound condition). backfill (2.1×) and reset-token (1.3–1.5×) are the other scenarios above the bar.

## Candidates

| Candidate | Change | Eval before → after | Kept |
|---|---|---|---|
| (a) Bootstrap reuse clause | Not written | reuse-eval RED: `reused_helper` 3/3, `reimplemented` 0/3. The bootstrap already gets reuse right on this task. | Dropped; the fixture stays as a regression guard |
| (b) TDD GREEN "reuse first", REFACTOR "simplify only the changed lines, drop checks for inputs no caller passes" | `skills/test-driven-development/SKILL.md`, two sentences | reuse-eval `guards_types` 1/3 → 2/3, code added [3,3,5] → [5,3,5] | **Reverted** |
| (c) Reviewer: a reimplementation of an existing function is Important; grep the whole source tree, not only the diff | `agents/code-reviewer.md`, `skills/requesting-code-review/code-reviewer.md` | `FIXTURE=reimplemented` blocking and rejected 3/9 → 7/9; the plan's 3/3 pin was **not met** | Kept: detection moved 3/9 → 7/9 and no other fixture regressed |
| (d) Same-class rule limited to reachable defects | Already shipped in `e9657dc` | — | — |
| (e) Receipt line for deliberate shortcuts | Skipped as planned | — | — |

**Why (b) failed.** The extra guards in reuse-eval do not come from refactoring. The agent classes the money task as elevated and dispatches a review. Because reuse-eval runs without `PLUGIN_DIR`, that review is a general-purpose subagent with a prompt the agent wrote itself; the plugin's reviewer templates are not loaded. That ad-hoc reviewer files "a bare string passed as `amounts`" as Important, and the agent adds a `TypeError` guard test-first. A TDD sentence cannot reach that path.

**What (c) costs.** In the benchmark the word "reimplement" appears in 1 of 57 candidate transcripts and none of the control ones. Transcripts containing `grep -rn` (implementer or reviewer) rose from 13 to 24 on the risk suite and from 7 to 13 on routine, which suggests reviewers ran the new search. If so, that is review work with no diff-size return on these tasks. It may account for part of the cost rise, but the run cannot separate it from dispatch noise. On routine, `multi-file-refactor` dispatched review in 3/3 candidate runs against 0/3 control, at $0.179 against $0.075; the reviewer text cannot change that decision, which is made before the reviewer loads. Excluding that scenario, routine cost is $0.119 against $0.114. Keeping (c) is a judgment call: it closes a real reviewer gap on the fixture built for it and costs review time everywhere.

## Benchmark

- Runner: `tests/benchmark/run.sh` with the `7913275` summarizer (new `code_added`, `ref_code_added`, `code bloat`), Claude Code 2.1.316, Sonnet, `--jobs 3`. Arms in one invocation: `control` = worktree at `2bfe625` (`main`), `bearpaws` = this branch at `73915b0`.
- Data: [`2026-11-04-diff-size-reuse-risk.jsonl`](2026-11-04-diff-size-reuse-risk.jsonl) (60 rows) and [`2026-11-04-diff-size-reuse-routine.jsonl`](2026-11-04-diff-size-reuse-routine.jsonl) (54 rows). Out dirs: `/tmp/bearpaws-tests/reduce-size/bench/{risk,routine}`.

### Risk suite

| Arm | Runs | Accepted | Escaped | Disclosed | Added lines | Code-only | Bloat | Code-only bloat | Reviews req/ret | $/run |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Control (`main`) | 30 | 29 | 4 | 2 | 7.4 | 5.3 | 1.96 | 1.46 | 40/40 | 0.194 |
| Candidate | 30 | 30 | 5 | 0 | 7.7 | 5.2 | 2.00 | **1.44** | 44/44 | 0.220 |

Per scenario, mean code-only lines added (the reference fix's count in brackets) and escapes out of 5:

| Scenario | Reference | Control | Candidate | Escapes: control | Escapes: candidate |
|---|---:|---:|---:|---:|---:|
| risk-backfill | 5 | 10.8 | 10.4 | 0 | 0 |
| risk-refund | 2 | 4.0 | 4.0 | 0 | 0 |
| risk-reset-token | 3 | 4.6 | 3.8 | 3 (+2 disclosed) | 5 |
| risk-sql-sort | 4 | 5.0 | 5.0 | 0 | 0 |
| risk-tenant-authz | 4 | 2.8 | 2.8 | 1 | 0 |
| risk-upload-path | 4 | 4.4 | 5.4 | 0 | 0 |

reset-token escapes in every run of both arms; the control arm disclosed two of them as INCOMPLETE. The one control sql-sort run not accepted timed out.

### Routine suite

| Arm | Runs | Accepted | Added lines | Code-only | Reviews | $/run |
|---|---:|---:|---:|---:|---:|---:|
| Control (`main`) | 27 | 27 | 16.4 | 13.4 | 8 | 0.109 |
| Candidate | 27 | 27 | 17.0 | 13.6 | 11 | **0.126** |

`bp:test-driven-development` loaded in 0/27 routine runs in both arms, and in 7/30 (candidate) and 3/30 (control) risk runs. That is why a TDD-text change could only ever reach a minority of runs.

## Evals (Sonnet, n=3 unless noted; out dirs under `/tmp/bearpaws-tests/reduce-size/`)

| Eval | RED (`main` skills) | Final |
|---|---|---|
| reuse-eval (new): fixed / reused / reimplemented / type guards / narrow diff | 3/3, 3/3, 0/3, 1/3, 3/3; code added [3,3,5]; $0.304 | 3/3, 3/3, 0/3, 1/3, 3/3; code added [3,5,3]; $0.314 |
| risk-eval: all gates | 3/3; code added [1,1,3]; type guards 1/3 | 3/3; code added [1,1,1]; type guards 0/3 |
| review `reimplemented` (new): reuse finding blocking, rejected | 3/9 | 7/9 (plan pin 3/3: **not met**) |
| review `minimal`: approved | 2/3 | 3/3 |
| review `refund-narrow`: rejected, negative blocking | 3/3, 3/3 | 3/3, 3/3 |
| review `refund`, `traversal`: approved | 3/3, 3/3 | 3/3, 3/3 |
| review `overbuilt`, planted: rejected | 3/3, 3/3 | 3/3, 3/3 |
| routing | 5/5 scenarios 3/3 | 5/5 scenarios 3/3 |

reuse-eval, risk-eval and routing do not load the reviewer templates, so their final runs (on the first wording of (c)) stand for the final wording. The first wording of (c) and three tuned wordings each scored 2/3 on `reimplemented` (out dirs `green-c`, `green-c2`, `green-c3`, `green-c4`). The last, which adds the grep, was confirmed with six more runs per side (RED 2/6 on the control checkout's templates, final 5/6). Every other review fixture was re-run on the final wording. The first `reimplemented` RED reported "7 tests" against 10 in the file, and reviewers flagged the mismatch. It was discarded and the fixture's report corrected.

## Limits

- n=5 per risk task and n=3 per routine task, one model, one CLI version. A 0.02× difference in bloat and a $0.017 difference in routine cost are both inside run-to-run noise at this n. The criteria are stated as bars, so they are reported as missed rather than re-tested.
- The control arm defines the baseline. The 2026-10-21 1.38× code-only figure came from a one-off script on work trees that no longer exist; this run's control measures 1.46× with the summarizer's own `code_lines()`.
- reuse-eval runs without `PLUGIN_DIR` and with `--setting-sources project,local`, so no Bearpaws plugin loads, and a review the agent dispatches uses its own prompt rather than the plugin's reviewer templates. It cannot exercise the templated review path. `PLUGIN_DIR=<checkout>` makes that path available, but the agent may still write its own review prompt.
- `code_lines()` is a line heuristic. A single-line `"""docstring"""` counts as code, and a lone `"""` inside a string literal toggles docstring state, which drops the rest of that file from the count. Both arms are measured the same way.
- reuse-eval has one fixture. On it the bootstrap already reuses the helper, so it cannot show whether a reuse clause would help in a case where the helper is harder to find.
