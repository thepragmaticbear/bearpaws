# Roadmap Evaluation — 2026-09-29

Evaluates the "competitive roadmap" proposals against v2.3.0, in the recommended order. Each skill change followed `bp:writing-skills`: a failing baseline first, then the smallest change, then a re-test. A proposal with no failing baseline got no skill change.

Model for all runs: Claude Sonnet via `claude -p`, isolated with `--setting-sources project,local --strict-mcp-config`. Raw runs are under `/tmp/bearpaws-tests/`.

## Results

| Step | Proposal | Baseline (RED) | Change | Result (GREEN) |
|---|---|---|---|---|
| 1 | Benchmark before changing anything | n/a | Added `tests/benchmark/` | v2.3.0: $0.146 per accepted task vs $0.120 with no plugin (+22%); 9/9 accepted per arm |
| 2 | One review for routine work; label break attempts | One code reviewer caught all 4 planted defects 3/3; the separate spec reviewer added $0.10/task and caught fewer (2/3 on one defect). Reviews wrote 6–9 "Tried:" lines but executed code 1–2 times, with nothing distinguishing the two | Routine tasks: one combined review. Elevated-risk: spec then quality, as before. "Tried:" lines carry `[executed]` or `[reasoned]`. Reviewer template treats the implementer report as a claim | Risk routing 9/9 under pressure (one-line auth change and "trivial" migration stayed two-stage). Labels on 24/24 lines and honest; defect detection unchanged |
| 3 | Test-tampering check in verification | Current skill caught a skipped test and a loosened assertion 6/6, including with a justifying report and a waiting user. No benchmark agent removed test lines | None | Eval kept as a regression guard |
| 4 | Scope and risk router | Classification was already correct when asked (15/15). In real runs Bearpaws did nothing extra on a security fix: 0/6 reviews | Elevated-risk rule in the bootstrap (objective list; test first, review, evidence). No Probe/Patch/Build routes: no measured benefit for their per-session cost | Security fix reviewed 5/5 after closing one loophole ("I'll note that I skipped the review"), with the failing test written first 4/5. Security-fix cost $0.107 → $0.209 per accepted task; small-bug unchanged |
| 5 | Resume from interruption | Agent reconciled plan checkboxes with git 6/6, including from a stale compaction summary | None | Eval kept |
| 6 | Project context map | Controller already passed onboarding findings to implementers 3/3 | None | Eval kept |
| 7 | Codex adapter conformance | n/a | Added `tests/codex/run-conformance.sh` (discovery, explicit load, auto-trigger, risk gate) | codex-cli 0.156.1, repo-level `.agents/skills`: discovery 15/15, explicit `$skill` load, and auto-trigger of systematic-debugging pass. Risk gate fails: on the security fix Codex read no Bearpaws skill and ran no review, though its fix passed the held-out acceptance tests. Codex has no automatic bootstrap, so the elevated-risk rule never reaches it. Follow-up: an `AGENTS.md` bootstrap line (printed by the installer) turned C4 green 2/2 vs 0/1 without it; both runs wrote the failing test first, used an independent reviewer that found real symlink-swap races, and passed acceptance. Global install path then passed 4/4 (`GLOBAL=1`, 2026-09-30) with acceptance passing; security fixes took several review rounds, about 14 minutes. Promotion is a maintainer decision |

## Costs of the changes

- Bootstrap: 3,193 → 3,960 bytes (about +185 tokens every session).
- Elevated-risk tasks roughly double in cost (the independent review). Routine tasks in SDD save one reviewer dispatch per task.

## Also fixed

- `requesting-code-review/code-reviewer.md` used `{PLAN_REFERENCE}` while the skill tells callers to fill `{PLAN_OR_REQUIREMENTS}`; the requirements section rendered empty.

## Open

- Scenarios are easy: every run in both arms was accepted, so the benchmark currently discriminates on cost only. Add harder scenarios (new subsystem, multi-file refactor, forced compaction).
- Superpowers comparison needs a local checkout (`SUPERPOWERS_DIR`).
- n=3–5 per cell; repeat before publishing any comparative claim.
- Codex: the global path passes conformance (n=1 complete, n=2 cut off after meeting all checks). Repeat before promoting, and watch cost: security fixes ran several review rounds.
