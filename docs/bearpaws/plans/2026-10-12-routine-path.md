# Cheaper Routine Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use bp:subagent-driven-development (recommended) or bp:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Status:** Approved
**Design:** [2026-10-12-routine-path-design.md](2026-10-12-routine-path-design.md)

**Goal:** Cut Bearpaws' routine-task cost with light onboarding and a fully specified patch path, while leaving the elevated path unchanged.

**Architecture:** This is a skill-text change in three files (bootstrap priority, onboarding, brainstorming), driven by a RED/GREEN routing eval. The routing eval gains forbidden-skill checks. The benchmark summary gains per-arm skill counts. Cost is measured on the routine benchmark scenarios.

**Tech Stack:** bash, Python stdlib, `claude -p` evals.

**Risk:** Routine tooling, plus behavior-shaping skill text that touches the routing of elevated work. The routing and risk evals guard that routing.

**Branch:** `feat/routine-path` in `.worktrees/routine-path`. Commits carry no co-author trailers. **No model runs until `/tmp/bearpaws-tests/benchmark/risk-prereg-8ba4601/results.jsonl` has 90 lines.**

---

### Task 1: Skills counts in the benchmark summary (model-free)

**Files:** `tests/benchmark/summarize.py`, `tests/benchmark/test_integrity.py`

- [ ] **Failing test.** Write a `summarize()` over rows whose `skills` lists include `bp:onboarding-to-a-project` and `bp:brainstorming`. It should print a `Skills by arm` section with one line per arm, giving each skill's count over n runs. A row's `skills` may repeat a name; count runs that invoked the skill, not invocations.
- [ ] **Implement.** After the token table, print `\nSkills by arm (runs that invoked each skill / n)` and, per arm, `  <arm>: <skill> a/n, ...`, sorted by skill name. Print nothing when no row has a skill.
- [ ] Run `python3 tests/benchmark/test_integrity.py` and confirm it passes.
- [ ] Commit: `feat(benchmark): per-arm skill counts in the summary`.

### Task 2: Routing eval forbids skills (model-free part)

**Files:** `tests/skill-triggering/routing/run.sh`, `tests/skill-triggering/routing/cases.txt`

- [ ] In the scoring block, the `must` field gains forbidden entries prefixed with `!`, for example `bp:test-driven-development+!bp:brainstorming`. Required entries must appear in `skills`; forbidden ones must not.
  ```python
  need = [s for s in must.split("+") if s and not s.startswith("!")]
  banned = [s[1:] for s in must.split("+") if s.startswith("!")]
  good = r["route"] == exp_route and r["risk"] == exp_risk and all(s in r["skills"] for s in need) and not any(s in r["skills"] for s in banned)
  ```
- [ ] In `cases.txt`, change `spec-bugfix` to `patch,routine,bp:test-driven-development+!bp:brainstorming`. Leave the other cases unchanged.
- [ ] Verify without a model: feed the scoring block a hand-made `scores.jsonl`. Use one row listing brainstorming and one not, and confirm `ok 1/2`. The block can be extracted with `sed`, or reproduced in a scratch script that copies it verbatim; report which.
- [ ] Commit: `test(routing): forbidden-skill checks; spec-bugfix must not brainstorm`.

### Task 3: RED baseline (model runs, about $0.50)

- [ ] Run `tests/skill-triggering/routing/run.sh skills/using-bearpaws/SKILL.md before 3` and record every case line.
- [ ] Expected: `spec-bugfix` below 3/3, because brainstorming gets listed. If it is already 3/3, record that; lever 2 then has no routing RED and rests on cost evidence alone.
- [ ] Record whether `bp:onboarding-to-a-project` is listed for `spec-bugfix`. The text eval can't show "light" mode, so the benchmark measures the cost.

### Task 4: Wording (GREEN)

**Files:** `skills/using-bearpaws/SKILL.md`, `skills/onboarding-to-a-project/SKILL.md`, `skills/brainstorming/SKILL.md`. Change only these lines; tuned text (Red Flags, rationalizations, gate and antipattern wording) stays as is.

- [ ] In `using-bearpaws/SKILL.md`, replace the two Skill priority items 1–2:
  ```
  1. **`bp:onboarding-to-a-project`** first for projects; skip only for abstract design with no project involved.
  2. **`bp:brainstorming`** next for design, using project conventions.
  ```
  with:
  ```
  1. **`bp:onboarding-to-a-project`** first for projects (light mode for a clear routine patch); skip only for abstract design with no project involved.
  2. **`bp:brainstorming`** next for design, using project conventions. A fully specified routine patch (expected behavior stated, no design choice left) has nothing to design: go to TDD and verification.
  ```
- [ ] In `onboarding-to-a-project/SKILL.md`, inside `<triggers>`, after the "already onboarded" rule, add:
  ```
  <rule>**Light mode** for a clear routine patch when CLAUDE.md or AGENTS.md exists: read it, find the test command, run it once, then proceed. Elevated-risk work always gets full onboarding.</rule>
  ```
- [ ] In `brainstorming/SKILL.md`, inside `<triggers>`, after the first rule, add:
  ```
  <rule>Skip for a fully specified routine patch (expected behavior stated, no design choice left): use `bp:test-driven-development`. A vague, design-level, or elevated-risk request still comes here, however small it sounds.</rule>
  ```
- [ ] Run `tests/schema-validator/run-validator.sh && tests/hooks/run-hook-tests.sh && tests/token-measurement/measure.sh`. Report the bootstrap byte delta (it should be under +200).
- [ ] Commit: `feat(skills): light onboarding and a fully specified patch path`.

### Task 5: GREEN evals (model runs)

- [ ] Routing: run `tests/skill-triggering/routing/run.sh skills/using-bearpaws/SKILL.md after 3`. All 5 cases should reach 3/3. `disguised-build` and `vague-feature` must still list brainstorming, and `risky-oneliner` must stay elevated with review and verification. If a guard case regresses, revise only the new sentences and re-run, at most twice.
- [ ] Risk-eval with the live gate: run `PLUGIN_DIR="$PWD" tests/risk-eval/run.sh skills/using-bearpaws/SKILL.md after-live 3`. Every column should be 3/3 (the last live result).
- [ ] Commit the eval summaries into the design doc's Results.

### Task 6: Cost measurement (about $12–15)

- [ ] Before export: run `git archive feat/escaped-defects | tar -x -C <scratch>/bp-before`. Exclude `tests/benchmark/scenarios` by deleting it after extraction.
- [ ] Run, in the background:
  ```
  SUPERPOWERS_DIR=~/repos/superpowers tests/benchmark/run.sh --scenarios "small-bug simple-feature broken-test-config conventions multi-file-refactor new-subsystem resume-after-context-loss" --arms "baseline before=<scratch>/bp-before bearpaws superpowers" --runs 5 --jobs 3 --budget 3 --out /tmp/bearpaws-tests/benchmark/routine-<sha>
  ```
- [ ] Run `summarize.py` and report $/accepted per arm, mean turns, and the skills section.
- [ ] Elevated regression: run `tests/benchmark/run.sh --suite risk --arms bearpaws --runs 5 --jobs 3 --out /tmp/bearpaws-tests/benchmark/risk-after-<sha>`. Compare escaped, disclosed, and accepted counts against the C bearpaws arm.

### Task 7: Results, review, finish

- [ ] Add a Results section to the design doc covering routing before and after, risk-eval, the routine cost table, and risk-suite escapes before and after. State plainly whether the goal was met.
- [ ] Final review via bp:requesting-code-review over `feat/escaped-defects..feat/routine-path`.
