# Roadmap continuation — 2026-09-30

Branch: `feat/pull-main-2ace29`. Continue the evidence-driven evaluation recorded in `2026-09-29-roadmap-evaluation.md`; preserve the existing uncommitted work. PR #11 has already merged, so this work is a follow-up rather than a merge gate for that PR.

## Execution checklist

- [x] Publish the completed nine-scenario, three-arm benchmark and its limits under `docs/benchmarks/`.
- [x] Repair benchmark integrity and scoring with failing offline checks first; preserve original observations.
- [x] Complete the adapter conformance surfaces, rejecting incomplete runs and unsupported review claims.
- [x] Refresh README positioning, support evidence, and new release notes without rewriting historical notes.
- [x] Run skill, triggering, static, and integration checks; resolve independent review findings and record remaining limits.

## Scope decisions inherited from the handoff

The router, context map, and persistent state proposals had passing baselines and were deliberately not added. Completion behavior already failed closed in the unavailable-integration scenario (5/5). Those outcomes justify retaining existing behavior, not claiming the proposed artifacts exist. The seeded recovery scenario is not a live forced-compaction test. No experimental platform is promoted automatically.

## Evidence states for this continuation

Observed means a transcript reports an action. Checks Passed requires recorded successful commands. Independently Verified requires the required independent review and verification. Approved requires explicit authorization for that action; implementation approval does not approve publication or merging. A missing required check or review keeps the corresponding item incomplete.

## Current observations

The inherited three-way run contains 81 rows: nine scenarios × three arms × three repetitions. All original acceptance and visible suites passed. Rescoring removed duplicate cumulative session cost: mean cost per originally accepted task is $0.065 for baseline, $0.113 for Bearpaws, and $0.098 for Superpowers. Two Bearpaws security runs missed the review gate. Saved worktrees are being checked against strengthened acceptance definitions separately.

The inherited expanded Codex run completed C1–C3 and was still running C4 during this continuation; there was no final completion for C4–C7 when inspected. Earlier four-check results do not establish all eight roadmap conformance surfaces.

## Roadmap disposition

| Original item | Implementation or evidence | Status |
|---|---|---|
| Scope and risk routing | Elevated-risk bootstrap rule; scope classification baseline 15/15 | Risk rule implemented; route labels deliberately omitted |
| Proportional brainstorming | Existing project-first workflow retained | Interactive design overhead remains unmeasured |
| Project Context Map | Context handoff baseline 3/3 already passed | Proposed map deliberately omitted; no map trust boundary claimed |
| Persistent run state | Git reconciliation baseline 6/6; seeded recovery fixture | Proposed files deliberately omitted; actual compaction still untested |
| Adaptive review | Routine combined review; elevated-risk spec then quality; executed/reasoned labels | Implemented in subagent-driven-development |
| Compact review packages | Conventions baseline 0/3, supplied/fallback green 3/3 each; evidence/decisions/concerns package extension | Extension awaiting pressure RED/GREEN |
| Completion and verifier trust | Unavailable mandatory integration checks baseline INCOMPLETE 5/5; bootstrap review fail-closed A/B; integrity regressions | Existing behavior retained; four named states documented here, not mandatory output labels |
| External verification | Native macOS checker protection and snapshots | Enforcement and unsupported-host behavior under test; old runs were not isolated |
| Metrics and comparative benchmark | Nine scenarios, three arms, numerical artifacts, corrected cost, tokens, duration, regression and process fields | Published smoke evidence; test coverage is a proxy, not full requirement coverage |
| Adapter conformance | Completed-action checks, review correlation, tool mapping and completion checks | Fresh suite pending; no support-tier promotion |
| Release structure | Manifests synchronized by bump-version script to proposed 2.3.1; new notes | Local proposal; no release published |
| Product positioning | README now says “Less context. Deliberate execution. Evidence at every gate.” and discloses benchmark limits | Implemented |
| Existing strengths and boundaries | Canonical skills, thin adapters, lazy loading, pace control, adversarial gates, project-first work | Preserved; Antigravity live behavioral parity remains unverified |

## Verification and review

Fresh offline verification runs completed on 2026-09-30:
- `tests/schema-validator/run-validator.sh`: PASSED (XML tag whitelist, Agent Skills frontmatter, .agents/skills links, adversarial gates)
- `tests/install/run-install-tests.sh`: PASSED (Antigravity and --agents global installers)
- `tests/antigravity/run-adapter-tests.sh`: PASSED (all 7 Antigravity adapter static assertions)
- `python3 tests/benchmark/test_integrity.py`: PASSED (30 tests: fixture integrity, runner isolation, score calculation)
- `python3 tests/review-eval/test_render.py`: PASSED (2 tests: review package rendering and diff inclusion)
- `python3 tests/codex/test_conformance.py`: PASSED (25 tests: all 8 roadmap surfaces and turn-status states)
- `scripts/bump-version.sh --check`: PASSED (manifests synchronized at 2.3.1)
- `scripts/bump-version.sh --audit`: PASSED (0 undeclared files)
