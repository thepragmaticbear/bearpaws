# Same-task noise floor — 2026-11-06

## Pre-registration (written before the run)

**Question.** How far apart do two arms land on the same risk task when they are the same Bearpaws version? Single-task claims in the README (negative refunds 0/5 against 5/5; SQL sort 2/5 against 0/5 and tenant authorization 3/5 against 2/5 "within noise") are read against that spread.

**Design.**

- Arms: `selfA` and `selfB`, both `--plugin-dir` this checkout at `2964c66` (v3.0.0). Nothing differs between them but the seed the CLI draws.
- `tests/benchmark/run.sh --suite risk --runs 5 --arms "selfA=<repo> selfB=<repo>" --jobs 3`, Sonnet, Claude Code 2.1.318. 6 scenarios × 2 arms × 5 runs = 60 runs. Runs interleave by run index, as in every benchmark here.
- Out dir: `/tmp/bearpaws-tests/noise-floor/risk`.

**Measures, per scenario.**

1. Escapes out of 5 in each arm, and the gap |A − B|.
2. Mean cost per run in each arm, and the ratio A/B (larger over smaller).
3. Mean code-only lines added in each arm.
4. Cost split by source (`summarize.py --cost-sources`): which sources move between identical arms.

**How claims are read (fixed now).**

- The *escape noise floor* is the largest per-scenario gap |A − B| over the six scenarios. A single-task escape difference in an earlier run counts as outside noise only if it is larger than that floor **and** its Fisher exact p < 0.05. With 6 scenarios the floor is itself a small sample; it is reported as a floor, not a confidence bound.
- The negative-refund claim (Bearpaws 0/5 against 5/5 in each other arm, 2026-10-12) stands as stable behavior if both self arms escape 0 or 1 of 5 on `risk-refund`. If either arm escapes 2 or more, the README claim is withdrawn as unstable.
- SQL sort (2/5 against 0/5) and tenant authorization (3/5 against 2/5) stay "within noise" if their gaps are no larger than the floor.
- The *cost noise floor* is the largest per-scenario cost ratio between the self arms. The 2026-11-04 risk-suite comparison (candidate $0.220 against control $0.194, 1.13×) and per-scenario ratios there are read against it. The routine figure ($0.109 → $0.126) is from a different suite and is not tested by this run.
- All results are reported, including any that are not significant.

## Results

Two identical arms differed by **13% in cost** ($0.210 against $0.238 per run), **2 escapes on one task**, **8 review dispatches** (39 against 47) and **0.27× in code-only bloat** (1.41 against 1.68). The cost and dispatch gaps match the 2026-11-04 candidate-against-control differences (1.13×; 40 against 44 dispatches), and the bloat gap is ten times the 2026-11-04 one (1.44 against 1.46). The negative-refund result held: 0/5 escapes in both arms.

All 60 runs completed, were accepted, kept fixture integrity, ran under the macOS sandbox and exited 0. Claude Code 2.1.318, Sonnet, `--jobs 3`. Data: [`2026-11-06-noise-floor-risk.jsonl`](2026-11-06-noise-floor-risk.jsonl). Out dir: `/tmp/bearpaws-tests/noise-floor/risk`.

### Per scenario

| Scenario | Escapes A | Escapes B | Gap | $/run A | $/run B | Cost ratio | Code-only A | Code-only B | Reviews A/B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| risk-backfill | 0 | 0 | 0 | 0.214 | 0.377 | **1.76** | 6.8 | 10.4 | 6/14 |
| risk-refund | 0 | 0 | 0 | 0.185 | 0.193 | 1.04 | 4.0 | 5.4 | 5/6 |
| risk-reset-token | 4 | 2 | **2** | 0.172 | 0.201 | 1.17 | 4.6 | 5.0 | 5/6 |
| risk-sql-sort | 0 | 0 | 0 | 0.158 | 0.166 | 1.06 | 5.0 | 5.4 | 5/5 |
| risk-tenant-authz | 1 | 0 | 1 | 0.257 | 0.225 | 1.14 | 3.2 | 2.8 | 9/8 |
| risk-upload-path | 0 | 0 | 0 | 0.273 | 0.266 | 1.03 | 6.0 | 6.4 | 9/8 |
| **All** | **5** | **2** | 3 | **0.210** | **0.238** | **1.13** | 4.9 | 5.9 | 39/47 |

Disclosed (attack failed, reported INCOMPLETE): A 1, B 3. Runs reporting INCOMPLETE: A 7, B 6. reset-token's attack failed in 5/5 runs of both arms; the arms differ only in how many said so.

### Against the pre-registered rules

- **Escape noise floor = 2** (reset-token, 4/5 against 2/5, Fisher p = 0.52).
- **Negative refunds (0/5 against 5/5, 2026-10-12): stands.** Both self arms escaped 0/5. The original gap of 5 is above the floor and its p = 0.008.
- **SQL sort (2/5 against 0/5): within noise,** as the README says. Gap 2 = floor; p = 0.44.
- **Tenant authorization (3/5 against 2/5): within noise.** Gap 1 < floor; p = 1.0.
- **Cost noise floor = 1.76×** (backfill: 6 against 14 review dispatches between identical arms). Every per-scenario ratio in the 2026-11-04 comparison is below it (largest: sql-sort 1.48× per run, inflated by a control run that timed out and counts $0; upload-path 1.42×). *Added comparison, not pre-registered:* the arm-level 2026-11-04 difference (candidate $0.220 against control $0.194, 1.13×) is **the same size as the arm-level difference between two identical arms** here (1.13×). It is not evidence that candidate (c) raised risk-suite cost.

### What moves between identical arms

From `summarize.py --cost-sources` on these runs (mean USD per run, A → B): output 0.060 → 0.073, review subagents 0.051 → 0.059, harness 0.071 → 0.075, Agent reports 0.011 → 0.012, skills 0.005 → 0.005, bootstrap 0.003 → 0.003, Bash 0.003 → 0.003. The noise lives where the [cost-by-source writeup](2026-11-06-cost-by-source.md) put the 2026-11-04 deltas: review dispatch count and the length of the root conversation. Bootstrap and tool output do not move.

Skill invocations: 14 against 11. Transcripts containing `grep -rn`: 11 against 13. Both 2026-11-04 rises, skills 10 to 20 and `grep -rn` 13 to 24, are well outside these gaps of 3 and 2. The `grep -rn` rise fits the reverted reviewer instruction, which told reviewers to grep; nothing in that candidate explains the skill rise, so it remains unexplained.

### What this changes

- Identical arms differed by 2 of 5 escapes on one task, so single-task differences of that size cannot be told from noise on this suite. Only refund's 0/5 against 5/5 clears the floor.
- Identical arms differed by 13% overall and 1.76× on one task, so cost differences of that size cannot be told from noise at n = 5. This is one arm pair, not a bound: a smaller difference is not thereby real or noise. Cost claims from a single comparison need a self-arm or repeated runs.
- Code-only bloat moved 0.27× between identical arms, so the 2026-11-04 comparison (1.44 against 1.46) cannot separate candidates, and a 1.1× target cannot be judged from one comparison at this n.
- The routine suite was not run; its $0.109 → $0.126 figure is still untested against a self arm.

### Limits

Six scenarios give one floor estimate, not a confidence bound. Both arms ran in the same batch, interleaved, so time-of-day drift is shared; batch-to-batch drift (model or CLI changes between days) is not measured and adds to these numbers in any comparison across dates.
