# Design: Cheaper Routine Path

Date: 2026-10-12
Status: Approved (brainstorming)
Branch: `feat/routine-path`, based on `feat/escaped-defects`. Model runs wait until the C benchmark finishes.

## Goal

Lower Bearpaws' cost on routine coding tasks, which today runs +41% over no plugin and level with Superpowers, without weakening the elevated-risk path.

## Evidence (from the 2026-09-30 three-way CSVs; research notes 2026-10-12)

- Routine scenarios (7): Bearpaws $0.0980 per run, Superpowers $0.0962, baseline $0.0695. The gap over baseline is about +1.2 turns and about +4.3k cache-write tokens per task.
- On "fix this small bug", the bootstrap pushes onboarding (5.9 KB, with a cold test run) and brainstorming ("This applies to EVERY project regardless of perceived simplicity"), then TDD and verification.
- Superpowers has no onboarding skill and routes "fix this bug" straight to debugging.

## Changes

1. **Light onboarding.** For a clear routine patch in a repo that has CLAUDE.md or AGENTS.md, onboarding reads that file, finds the test command, and runs it once. It skips the manifest sweep and file sampling. Elevated-risk work always gets full onboarding, because its baseline run feeds `Pinned:`.
2. **Routine fast path.** A fully specified routine patch skips brainstorming and goes to TDD and verification. "Fully specified" means the expected behavior is stated and no design choice is left. Vague or design-level requests still brainstorm, however small they sound. "Size never lowers risk" is unchanged.
3. **Skills in the summary.** The benchmark summary counts skill invocations per arm, so we can see whether routine runs still load onboarding in full and brainstorming.

Not changed: the risk gate, the sensitive-path nudge, the Red Flags table, and the elevated-risk paragraph.

## Evaluation

- **RED:** the routing eval (`tests/skill-triggering/routing/`), with a new "forbidden skill" check so `spec-bugfix` must not list `bp:brainstorming`. Run it with the current bootstrap, 3 runs per case.
- **GREEN:**
  - The same routing eval passes all 5 cases. `disguised-build` and `vague-feature` must still brainstorm, and `risky-oneliner` must still be elevated with review and verification.
  - `tests/risk-eval` (with `PLUGIN_DIR`, live gate) is no worse than its last live result: all 3/3.
- **Cost:** the routine benchmark scenarios × {baseline, bearpaws-before (an export of `feat/escaped-defects`), bearpaws, superpowers} × 5 reps. That is 140 runs, about $12–15.
- **Elevated regression:** if D changes skills, re-run `--suite risk` for the Bearpaws arm only (30 runs, about $5), then compare escapes against the C result.

## Success

- Routine Bearpaws cost goes down against bearpaws-before, and ideally falls below Superpowers.
- No routing or risk-eval regression.
- The risk-suite escape count is no worse than C's.

Results are published as measured.

## Results (2026-10-12): stopped after RED

- **Routing eval with the current bootstrap** (`/tmp/bearpaws-tests/routing-eval/routine-before`): all 5 cases 3/3, including `spec-bugfix` with the new `!bp:brainstorming` check. Today's wording already routes a fully specified bug fix to TDD and verification only. Lever 2 has no RED.
- **Live routine runs**, Bearpaws only, 7 scenarios × 3 (`/tmp/bearpaws-tests/benchmark/routine-red-80f56b7`): 21/21 accepted, $0.101 per task, 6.1 turns.
  - Brainstorming was invoked in **0/21** runs.
  - Onboarding was invoked in 8/21: `conventions` 3/3, `new-subsystem` 3/3, `simple-feature` 2/3. Two of those three are builds, where light mode would not apply.
  - The most expensive scenario, `multi-file-refactor` ($0.191), touches `money.py`. The elevated rule sends it to review, which is by design.
- **Decision:** with an expected saving of about $0.004 per task, changing tuned skill text is not justified. D stops here with no skill change. Two model-free improvements are kept for later use: per-arm skill counts in the benchmark summary, and forbidden-skill checks in the routing eval.
- **Next:** the escaped-defect benchmark (C) found a larger lever. Bearpaws' reviewer caught defects that the agent then shipped as "out of scope". See `docs/benchmarks/2026-10-12-escaped-defects.md`.
