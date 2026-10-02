# Other-Harness Integration: Scope, Implementation, and Test Plan

**Status:** Partially implemented in 2.5.0 (see Outcome at the end)
**Date:** 2026-10-02
**Goal:** Make Bearpaws' non-primary harness support (Codex, OpenCode, Devin CLI, Cursor, Copilot CLI) *provable*: every wired path has an automated test, every claim in `docs/agent-support.md` has evidence, and each harness has a clear route to either promotion or explicit "skills-only" status.

This plan does **not** promote any harness. Promotion stays a maintainer decision (see `docs/agent-support.md` → Promotion Rule).

---

## 1. Where things stand today

| Harness | Skills discovery | Bootstrap path | Tool mapping | Automated tests | Live evidence |
|---|---|---|---|---|---|
| Codex | `.agents/skills` (repo) / `~/.agents/skills` (global) | `AGENTS.md` line (user adds by hand) | none (model guesses from Claude names) | `tests/codex/test_conformance.py` (offline, 25 tests) | C0–C3 pass; full 10-assertion suite **never completed** (C4 run cut off) |
| OpenCode | same | `instructions` entry in `opencode.json` (user adds) | none | validator checks frontmatter rules only | one manual smoke, 2026-09-28 |
| Devin CLI | same | `.devin/hooks.v1.json` → `hooks/session-start` | none | **none** | none recorded |
| Cursor | same | `hooks/session-start` branch on `CURSOR_PLUGIN_ROOT` | none | **none** | none recorded |
| Copilot CLI | same | `hooks/session-start` branch on `COPILOT_CLI` | none | **none** | none recorded |

## 2. Gaps (concrete, with locations)

- **G1 — Hook output shapes are untested.** `hooks/session-start` has three JSON branches (Claude, Cursor, SDK-default). Nothing checks that each branch emits valid JSON with the right key. A quoting bug would ship silently.
- **G2 — Dead-or-unknown hook branches.** The Cursor and Copilot branches exist, but the repo ships no Cursor or Copilot plugin manifest that would ever run the hook. We don't know whether these branches are reachable.
- **G3 — Devin hook only works inside the Bearpaws checkout.** `.devin/hooks.v1.json` runs `${DEVIN_PROJECT_DIR}/hooks/session-start`, so in a user's own project there is no `hooks/` dir and no bootstrap. Effectively it's a dev-only convenience.
- **G4 — Claude-specific wording in non-Claude payloads.** The hook wraps the bootstrap with "Use the Skill tool for all others" for *every* harness. Non-Claude agents don't have a `Skill` tool.
- **G5 — No tool mapping for Agent Skills agents.** Claude Code and Antigravity have `references/*.md` mappings; the others don't. The docs already list this as a known limitation for OpenCode.
- **G6 — CI runs only 2 of the offline suites.** `.github/workflows/ci.yml` runs the schema validator and token measurement. `tests/install/run-install-tests.sh`, `tests/antigravity/run-adapter-tests.sh`, and `tests/codex/test_conformance.py` need no external CLI but aren't in CI.
- **G7 — Codex live conformance is incomplete.** The 10-assertion run never produced a final summary (C4–C9 missing).
- **G8 — Live conformance runner is Codex-only.** `tests/codex/evidence.py` parses Codex's `item.completed` events. Other harnesses have no runner.

## 3. Scope

**In scope**

- Offline tests for every adapter path (G1, G6).
- A spike for each unverified harness to determine its real integration surface (G2, G3).
- Fixes that stay within the Adapter Policy: payload wording, packaging manifests, reference notes (G2–G5).
- A live conformance runner that supports more than one harness, reusing the Codex assertions (G7, G8).
- Doc updates that match the evidence.

**Out of scope**

- Promoting any harness to Primary.
- Rewriting skill bodies per harness, or adding per-skill adapter metadata (forbidden by Adapter Policy).
- A full per-harness trigger matrix (the policy says maintenance cost must be explicitly accepted first).
- Gemini CLI and Windsurf (retired/removed; `--agents` covers them).
- Live harness runs in CI (they need paid CLIs and credentials; they stay manual or run on a maintainer's machine).
- Installer changes that edit user config files (the installer only prints bootstrap lines, by design).

## 4. Implementation phases

Each phase is shippable on its own. Do them in order: earlier phases give the safety net that later phases rely on.

### Phase 0 — Offline safety net (no external CLIs needed)

**Task 0.1: Hook payload shape test** (closes G1)

- Create `tests/hooks/run-hook-tests.sh`.
- For each environment, run `hooks/session-start` and parse stdout with `python3 -m json.tool` or `jq`:

| Env vars set | Expected top-level key | Must NOT contain |
|---|---|---|
| `CLAUDE_PLUGIN_ROOT` | `hookSpecificOutput.additionalContext`, `hookEventName == "SessionStart"` | `additional_context`, top-level `additionalContext` |
| `CURSOR_PLUGIN_ROOT` (+ `CLAUDE_PLUGIN_ROOT`) | `additional_context` | `hookSpecificOutput` |
| `CLAUDE_PLUGIN_ROOT` + `COPILOT_CLI` | top-level `additionalContext` | `hookSpecificOutput` |
| `DEVIN_PROJECT_DIR` | top-level `additionalContext` | `hookSpecificOutput` |
| none | top-level `additionalContext` | `hookSpecificOutput` |

- For every row, also assert:
  - Exit code 0.
  - Exactly one context key (Claude Code doesn't deduplicate).
  - The decoded context contains the `name: using-bearpaws` frontmatter line and the `<warning level="hard">` wrapper.
- Failure cases:
  - Point the hook at a temp copy where `skills/using-bearpaws/SKILL.md` is missing → exit 1, non-empty stderr, empty stdout.
  - Same with an empty file → same result.
- Escaping case: run the hook against a temp copy whose SKILL.md contains `"`, `\`, a tab, and CRLF. The output must still parse as JSON and round-trip to the same text.

**Task 0.2: Wire offline suites into CI** (closes G6)

- Add jobs to `.github/workflows/ci.yml`:
  - `hook-tests`: runs `tests/hooks/run-hook-tests.sh`
  - `install-tests`: runs `tests/install/run-install-tests.sh`
  - `antigravity-adapter`: runs `tests/antigravity/run-adapter-tests.sh`
  - `codex-offline`: runs `python3 tests/codex/test_conformance.py`
- First, run each suite locally on a clean Ubuntu container to confirm it needs no network and doesn't write outside `$HOME`/tmp. Any suite that writes to the real `$HOME` must set `HOME=$(mktemp -d)` inside the test.
- Add `tests/hooks/` to the Tests block in `CLAUDE.md` and `AGENTS.md`, and to `docs/testing.md`.

**Phase 0 done when:** CI is green with 6 jobs, and a deliberately broken hook (for example, deleting the `\"` escape) turns `hook-tests` red.

### Phase 1 — Spikes: find each harness's real integration surface (closes G2, G3)

These are research tasks. Each produces a short evidence note in `docs/bearpaws/plans/2026-10-xx-harness-spikes.md`, stating the CLI version and date. **Do not write adapter code until the spike answers its questions.**

| Spike | Questions to answer | Possible outcomes |
|---|---|---|
| S1 Cursor | Does Cursor (IDE or `cursor-agent` CLI) have a plugin/hook system that runs a SessionStart command? What manifest path and env vars does it use? Does it set `CURSOR_PLUGIN_ROOT`? Does it read `.agents/skills`? | (a) add a minimal Cursor manifest that points at `hooks/`; or (b) delete the Cursor branch and document Cursor as skills-only |
| S2 Copilot CLI | Same questions; does it set `COPILOT_CLI`? Does it load Claude-plugin-format `hooks.json`? | (a) manifest; or (b) delete branch, skills-only |
| S3 Devin CLI | Is there a *user-global* hooks file (outside the project)? Can a hook command use an absolute path to an installed Bearpaws? | (a) installer prints a global hook snippet (same pattern as Codex/OpenCode lines); or (b) document `.devin/` as dev-only |
| S4 OpenCode | Re-run the 2026-09-28 smoke on the current per-skill-link layout (the earlier smoke used the old directory-symlink layout). What does `opencode run` emit for machine-readable output (event format, tool-call records)? | Feeds the Phase 3 OpenCode driver |

Rules for the spikes:

- Use each harness's current official docs and a real CLI run; record exact commands.
- Never infer support from a branch existing in `hooks/session-start`.
- Each spike's evidence must include a **control run without Bearpaws**, so "it worked" can't come from the model's general knowledge.

**Phase 1 done when:** every row has outcome (a) or (b) chosen, with evidence.

### Phase 2 — Thin adapter fixes (G2–G5), driven by Phase 1

**Task 2.1: Act on spike outcomes**

- For outcome (a): add the manifest, then extend `tests/hooks/run-hook-tests.sh` with that harness's real env vars from the spike.
- For outcome (b): remove the dead branch from `hooks/session-start`, remove its row from the hook test, and update the comment block at the top of the hook.
- Update the `hooks/` line in `CLAUDE.md`/`AGENTS.md` to match.

**Task 2.2: Harness-neutral payload wording** (G4)

- In the non-Claude branches only, replace "Use the Skill tool for all others" with neutral wording (for example, "Load other skills with your agent's native skill mechanism").
- Leave the Claude Code payload byte-identical. The hook test asserts this with a golden-file comparison.
- This is behavior-shaping text, so it follows the repo's RED/GREEN rule:
  - **RED:** run the Phase 3 C0+C3 checks on one non-Claude harness with the current wording.
  - **GREEN:** rerun with the new wording; keep it only if C0/C3 are equal or better.
  - If no live non-Claude hook harness exists after Phase 1, **skip this task.** Nothing would consume the payload.

**Task 2.3: Agent Skills tool-mapping reference** (G5), *conditional*

- Only do this if the Phase 3 baseline fails C9 (tool mapping) or C6 (subagents) on Codex or OpenCode.
- If it does fail, add `skills/using-bearpaws/references/agent-skills-tools.md`, under ~30 lines, in the same shape as `antigravity-tools.md`. It maps Bearpaws intents to "read the file / your shell tool / your subagent tool, if any". It must also say what to do when there's no subagent tool: do the review in a fresh pass and say so, never silently skip it.
- Point to it from the "Other Agent Skills agents" step in `skills/using-bearpaws/SKILL.md`.
- RED/GREEN on C6 and C9. Run `tests/token-measurement/measure.sh` too, because the bootstrap budget is tracked.

### Phase 3 — Multi-harness live conformance (G7, G8)

**Task 3.1: Finish Codex first** (cheapest, most evidence already)

- Run `tests/codex/run-conformance.sh` (repo-level) and `GLOBAL=1 tests/codex/run-conformance.sh` to completion. Repeat ×2 each.
- Record `summary.json` results in a new evidence note.
- This alone gives the maintainer what's needed to decide on Codex promotion.

**Task 3.2: Factor out a driver interface**, without rewriting the Codex runner

- Create `tests/conformance/`:
  - `scenarios.sh`: the C0–C9 prompts and fixture setup, moved out of `tests/codex/run-conformance.sh` unchanged.
  - `drivers/codex.sh` + `evidence/codex.py`: today's code, moved.
  - `drivers/<harness>.sh`: must provide `run_turn <dir> <sandbox> <prompt> <outfile> [timeout]` and `bootstrap_repo <dir>`.
  - `evidence/<harness>.py`: must provide `--status`, `--summary`, and the same per-assertion checks, all reading that harness's native event stream.
- Keep `tests/codex/run-conformance.sh` as a 3-line wrapper so existing commands and docs keep working.
- **Regression gate:** `tests/codex/test_conformance.py` passes unchanged after the move, and one live Codex run gives the same verdicts as before the refactor.

**Task 3.3: OpenCode driver**

- Build it from the S4 spike findings.
- Write offline fixtures first: capture real OpenCode JSON transcripts for one pass and one fail per assertion, then write `tests/conformance/test_opencode_evidence.py` against them. Only then write the parser.
  - This mirrors the Codex rule: "unfamiliar tool event representations need their own regression fixtures before being accepted."
- Bootstrap = repo-level `opencode.json` with `instructions`; `GLOBAL=1` uses the user's config.

**Task 3.4: Other drivers**

- Add a driver only for harnesses where Phase 1 found a headless CLI with machine-readable tool events.
- A harness without one stays at "manual smoke" evidence. Document that, and don't build a driver.

### Phase 4 — Docs and claims

- Update `docs/agent-support.md`: the evidence table, "Existing files", "Known limitations", and the Testing Policy minimum-check table (add the hook test and conformance runner rows).
- Mirror the support table in `CLAUDE.md`, `AGENTS.md`, and `README.md` (they must stay identical).
- New release-note file under `docs/bearpaws/release-notes/` (never edit old ones).
- Bump the version with `scripts/bump-version.sh <ver>`, then confirm with `--audit`.

## 5. Test plan

### Test layers

| Layer | What it proves | Where it runs | Blocks merge? |
|---|---|---|---|
| L0 Static | Skill frontmatter, `.agents/skills` links, tag whitelist, token budget | CI (exists) | Yes |
| L1 Adapter unit | Hook emits correct JSON per harness; fails loudly on bad input; Claude payload unchanged | CI (new, Phase 0) | Yes |
| L2 Install | `--agents --global` links, preserves foreign skills, idempotent; Antigravity copy/backup | CI (new wiring, Phase 0) | Yes |
| L3 Evidence-parser unit | Each harness's evidence parser classifies recorded transcripts as pass/fail/blocked correctly | CI (Codex now, OpenCode in Phase 3) | Yes |
| L4 Live conformance | Real CLI completes C0–C9 with completed-action evidence | Maintainer machine, manual | No; feeds promotion |
| L5 Behavior evals | Wording changes (Tasks 2.2, 2.3) are no worse than baseline | Maintainer machine, RED/GREEN | Gates those tasks only |

### Conformance assertions (L4), shared by every driver

Same IDs as `tests/codex/README.md`, so results compare across harnesses:

| ID | Surface | Pass requires (from the harness's completed events, not prose) |
|---|---|---|
| C0 | Bootstrap | using-bearpaws read on ordinary work |
| C1 | Discovery | Exact Bearpaws skill names listed |
| C2 | Explicit load | Named skill read + exact expected answer |
| C3 | Auto-activation | Debugging skill read on a naive bug prompt |
| C4 | Risk/review gate | Review skill loaded, independent review of final revision, security acceptance passes |
| C5 | Onboarding | Onboarding skill + `CONTRIBUTING.md` read |
| C6 | Subagents | Spawned reviewer correlated with a completed result (N/A, not pass, if the harness has no subagents) |
| C7 | Verification gate | Unverifiable change → final line exactly `INCOMPLETE` |
| C8 | Completion | Tests pass after final edit, acceptance passes, final line `COMPLETE` |
| C9 | Tool mapping | Real read, real edit, nonempty successful test run |

Exit codes (unchanged): `0` all pass · `1` behavioral failure · `2` blocked (timeout, CLI error, missing evidence). A blocked run never counts as a pass.

### Required controls

- **Every L4 run has a `NO_BOOTSTRAP=1` control.** A harness only gets credit for C0/C3/C4 if the bootstrap run beats the control.
- **Repeat count:** n ≥ 2 complete runs per harness before any promotion discussion. Record failures and blocked runs; never drop them.

### Exact commands after this plan lands

```bash
# Every PR (CI)
tests/schema-validator/run-validator.sh
tests/token-measurement/measure.sh
tests/hooks/run-hook-tests.sh
tests/install/run-install-tests.sh
tests/antigravity/run-adapter-tests.sh
python3 tests/codex/test_conformance.py
python3 tests/conformance/test_opencode_evidence.py      # after Phase 3.3

# Manual, before any promotion decision
tests/codex/run-conformance.sh  /tmp/bearpaws-tests/codex/<fresh>
GLOBAL=1 tests/codex/run-conformance.sh /tmp/bearpaws-tests/codex/<fresh>
NO_BOOTSTRAP=1 tests/codex/run-conformance.sh /tmp/bearpaws-tests/codex/<fresh>
tests/conformance/run.sh opencode /tmp/bearpaws-tests/opencode/<fresh>   # after Phase 3.3
```

## 6. Done criteria for the whole effort

1. CI runs 6 offline jobs (7 with OpenCode) and all are green.
2. Every branch in `hooks/session-start` is either tested against evidence-backed env vars or deleted.
3. Each of Codex, OpenCode, Devin, Cursor, Copilot has a written outcome: *live conformance results* or *documented as skills-only / manual-smoke*.
4. Codex has ≥2 complete live conformance runs (repo + global) plus a no-bootstrap control on record.
5. `docs/agent-support.md`, `CLAUDE.md`, `AGENTS.md`, and `README.md` agree, and make no claim stronger than the evidence.
6. No harness is promoted by this work. That stays a separate maintainer decision.

## 7. Decisions needed from the maintainer

- **D1:** Which harnesses get spikes? Recommended: all four (S1–S4). Each is roughly an hour of research.
- **D2:** For Cursor/Copilot, if a spike shows integration costs more than a thin manifest, do we drop them to skills-only? Recommended: yes, per the Adapter Policy.
- **D3:** Is a nightly/manual live-run budget acceptable? Each Codex suite run is about 20 minutes and paid tokens.
- **D4:** After Task 3.1, decide Codex promotion separately.

## 8. Risks

- **Harness CLIs change fast.** Pin and record CLI versions in every evidence note. A driver whose CLI version changes must re-pass its L3 fixtures before its L4 results count.
- **Refactor breaking Codex evidence (Task 3.2).** Mitigated by the unchanged offline tests plus one live before/after run.
- **Payload wording change (Task 2.2) degrading Claude Code.** Mitigated: the Claude branch is golden-file locked.
- **Scope creep into per-harness skill rewrites.** Hard stop, per the Adapter Policy: "If an agent cannot consume Bearpaws without parsing and changing the inner skill body, stop and reassess."

---

## Outcome (2.5.0, 2026-10-02)

Scope added after drafting: Grok Build. No harness was promoted.

| Gap | Result |
|---|---|
| G1 hook shapes untested | Done: `tests/hooks/run-hook-tests.sh` (CI) |
| G2 Cursor/Copilot branches unreachable | Cursor: added `.cursor-plugin/` (mirrors upstream; not run in Cursor). Copilot: installs from `.claude-plugin` (checked in CI); hook run not observed (login required) |
| G3 Devin hook dev-only | Documented; user projects use the `AGENTS.md` line. Payload changed to Devin's documented nested shape. No root `hooks.json` (Copilot also reads it) |
| G4 Claude wording in non-Claude payloads | Deferred: needs a live RED/GREEN eval |
| G5 tool mapping | Deferred: conditional on live C6/C9 failures |
| G6 offline suites not in CI | Done. Fixed two suites that could not pass (Antigravity `((x++))`, validator locale) |
| G7 Codex live conformance | Blocked: no OpenAI credentials in this environment. Model-free wiring check added instead |
| G8 Codex-only runner | Partly done: `tests/harness-wiring/run.sh` covers Codex, OpenCode, Copilot, and Grok without a model. Live drivers are still Codex-only |

Phase 1 spike findings (S1–S4) are recorded in `docs/agent-support.md`. Live runs still owed are listed in the 2.5.0 release notes under "Not verified".
