# Skill Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use bp:subagent-driven-development (recommended) or bp:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Apply the five approved audit findings (2026-09-29) to skill content, each backed by before/after evidence, as required by `bp:writing-skills` and CLAUDE.md "When editing skills".

**Architecture:** Measure first (baseline), edit the skill text, re-measure with the same harness. The harnesses are `tests/skill-triggering/` (does a naive prompt trigger the right skill), `tests/explicit-skill-requests/run-all.sh`, `tests/claude-code/run-skill-tests.sh` (fast), and `tests/token-measurement/measure.sh`. Evidence goes in the "Evidence log" at the bottom of this file.

**Tech Stack:** Markdown skills, bash test harnesses, `claude -p` (stream-json).

**Findings in scope:**
1. Five descriptions summarize workflow instead of triggering conditions: brainstorming, finishing-a-development-branch, receiving-code-review, using-git-worktrees, verification-before-completion.
2. The bootstrap `skills/using-bearpaws/SKILL.md` is 911 words and is injected into every session; the guideline for frequently loaded skills is under 200 words.
3. The bootstrap uses aggressive emphasis ("1% chance", "ABSOLUTELY MUST", "YOU DO NOT HAVE A CHOICE"). Current Claude models over-trigger on this; Anthropic's Claude 4+ prompting guidance recommends calm "Use X when…" phrasing.
4. The brainstorming description does not start with "Use when".
5. Brainstorming's "Write design doc… Commit" step conflicts with current agent harnesses that commit only when the user asks.

**Rules for every task:**
- Never edit a skill before its baseline is recorded.
- Tuned content (Red Flags tables, rationalization tables, "your human partner") stays unless evidence supports a change.
- Commits have no attribution trailers.

---

### Task 1: Harness integrity and baseline

**Files:**
- Create: `tests/skill-triggering/prompts/{finishing-a-development-branch,receiving-code-review,using-git-worktrees,verification-before-completion}.txt`
- Modify: `tests/skill-triggering/run-all.sh` (SKILLS list)

- [x] **Step 1: Confirm which plugin copy the harness exercises.** The user also has `bp` 2.2.0 installed globally with the same skill names. Run one triggering test (`tests/skill-triggering/run-test.sh brainstorming tests/skill-triggering/prompts/brainstorming.txt`) and inspect the `system`/`init` event in `/tmp/bearpaws-tests/<ts>/skill-triggering/brainstorming/claude-output.json` for plugin paths. If the installed 2.2.0 copy is loaded alongside or instead of `--plugin-dir`, isolate the harness: pass `--setting-sources project,local` or an equivalent documented `claude` flag that excludes user-installed plugins (check `claude --help`). Apply the fix in `tests/skill-triggering/run-test.sh` and `tests/explicit-skill-requests/run-test.sh`, then re-run to prove only this checkout's skills load. Record the evidence.
- [x] **Step 2: Add naive prompts** for the four uncovered skills. Each is 1–3 sentences a real user would type, and none names the skill:
  - `finishing-a-development-branch.txt`: "All the tasks on my feature branch are done and the tests pass. What should I do with the branch now?"
  - `receiving-code-review.txt`: "My reviewer left these comments on my PR: 'Extract the retry logic into a helper' and 'This null check is unnecessary, remove it.' Can you address them?"
  - `using-git-worktrees.txt`: "I want to start a new feature but keep my current work untouched in this checkout. Set me up an isolated workspace for it."
  - `verification-before-completion.txt`: "I think I fixed the login bug. Can you confirm it's done so I can open the PR?"
- [x] **Step 3: Add the four skills** to the `SKILLS` array in `run-all.sh`.
- [x] **Step 4: Baseline.** Run `tests/skill-triggering/run-all.sh`, `tests/explicit-skill-requests/run-all.sh`, and `tests/claude-code/run-skill-tests.sh`. Record per-skill PASS/FAIL, the bootstrap word count (`wc -w skills/using-bearpaws/SKILL.md`), and the `measure.sh` bootstrap token figure in the Evidence log.
- [x] **Step 5: Over-trigger baseline.** Run `claude -p "What is 17 * 23? Reply with the number only." --plugin-dir <repo> --output-format stream-json --verbose --max-turns 2` (with the same isolation as Step 1) and count `"name":"Skill"` invocations. Repeat with "What does the acronym HTTP stand for?". Record both counts.
- [x] **Step 6: Commit:** `test(triggering): cover four more skills; isolate from installed plugin; record baseline`

### Task 2: Descriptions (findings 1 and 4)

**Files:** frontmatter only in `skills/{brainstorming,finishing-a-development-branch,receiving-code-review,using-git-worktrees,verification-before-completion}/SKILL.md`

- [x] **Step 1: Rewrite each `description`** to triggering conditions only: third person, starting "Use when…", no workflow summary. Keep the trigger keywords.
  - brainstorming: `Use when about to create or change features, components, or behavior and the design has not been agreed yet`
  - finishing-a-development-branch: `Use when implementation on a branch is complete, tests pass, and it's time to decide how to integrate the work (merge, PR, keep, or discard)`
  - receiving-code-review: `Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable`
  - using-git-worktrees: `Use when starting feature work that needs isolation from the current workspace, or before executing an implementation plan`
  - verification-before-completion: `Use when about to claim work is complete, fixed, or passing, or before committing or opening a PR`
- [x] **Step 2: Run the validator** (`tests/schema-validator/run-validator.sh`, expect 4 OK).
- [ ] **Step 3: Re-run triggering** for these 5 skills plus `run-all.sh` for regressions. Each must pass at least as often as the baseline. If one regresses, adjust its keywords (not a workflow summary) and re-run, at most 2 iterations; if it still regresses, revert that description and log why.
- [x] **Step 4: Commit:** `feat(skills): trigger-only descriptions for five skills` (`e2bfbc8`)

### Task 3: Bootstrap trim and de-escalation (findings 2 and 3)

**Files:** `skills/using-bearpaws/SKILL.md`, plus `tests/antigravity/run-adapter-tests.sh` only if its asserted strings move

- [x] **Step 1: Draft the trimmed bootstrap.** Target ≤450 words (roughly half) as a first step toward the 200-word guideline. Keep, in this order: the subagent-stop line; the core rule; the per-agent process lines (Claude Code, Antigravity, other Agent Skills agents); the Red Flags table (tuned, keep verbatim); Pace Control ending in "**Momentum does not waive gates.**" (the adapter test asserts it); skill priority; and the lazy-load contract. Condense the Brevity Policy to at most 4 bullets, keeping its "Never compress" items. Drop the "Skill types" section only if its content lives in the process skills. Replace shouting with calm directives, for example: "If a skill might apply, invoke it before responding — including before clarifying questions. Skills override default behavior; user instructions override skills." Keep `<warning level="hard">` semantics, but without all-caps.
- [x] **Step 2: Verify static checks:** validator (4 OK), `tests/antigravity/run-adapter-tests.sh` (Pace Control, Red Flag, Antigravity step, no `activate_skill`), and `CLAUDE_PLUGIN_ROOT=$PWD hooks/session-start | python3 -m json.tool`.
- [ ] **Step 3: Re-run every harness** from Task 1 Steps 4–5 under the same isolation. Acceptance:
  - Triggering and explicit-request pass counts are ≥ the Task 1 baseline.
  - The fast test passes.
  - Over-trigger counts are ≤ the baseline.
  - The word count is ≤450.
  - Judge dispatching-parallel-agents (flaky at baseline) over ≥3 runs.
  
  If triggering regresses, restore the specific removed element that plausibly caused it (not all of them) and re-run, at most 2 iterations. If it still regresses, report BLOCKED with the evidence.
- [x] **Step 4: Commit:** `feat(bootstrap): halve using-bearpaws and drop aggressive emphasis` (`bdeb875`)

### Task 4: Brainstorming commit step (finding 5)

**Files:** `skills/brainstorming/SKILL.md` (the "Write design doc" step only)

- [ ] **Step 1: RED.** In a temp git repo with one file, run `claude -p` (isolated, with `--plugin-dir`) with a prompt that completes a tiny brainstorm in one turn: "Design is approved as-is: a CLI flag --quiet that suppresses stdout. Write the design doc now." Use `--max-turns 6`. Check the stream-json for a `git commit` Bash call made without the user asking. Record it.
- [x] **Step 2: Edit the step** to: `**Write design doc** — save to docs/bearpaws/plans/YYYY-MM-DD-{topic}-design.md (user prefs override). Commit it if the user or project allows commits without asking; otherwise leave it uncommitted and say so.`
- [ ] **Step 3: GREEN.** Re-run the Step 1 scenario and record whether an unrequested commit still happens. Also re-run the brainstorming triggering test.
- [x] **Step 4: Commit:** `fix(brainstorming): respect commit policy for design docs` (`a2bf8ee`)

### Task 5: Release notes and final verification

- [x] **Step 1: Append to `docs/bearpaws/release-notes/2.3.0.md`** a "Skill content" section. List the five findings, with before/after numbers from the Evidence log (bootstrap words and tokens, triggering pass counts, over-trigger counts). Post-trim behavioral counts are explicitly unavailable because Claude usage is exhausted.
- [ ] **Step 2: Run** the validator, the install tests, the adapter tests (`PATH=/usr/bin:/bin` if node is broken), `measure.sh`, `bump-version.sh --check`, and the fast Claude test.
- [x] **Step 3: Commit:** `docs(release-notes): skill content enhancements with eval evidence`

---

## Evidence log

### Baseline (2026-09-29, claude 2.1.281)

**Isolation finding.** The init event of the first run lists exactly one `bp` plugin: `{"name":"bp","path":"<this checkout>","source":"bp@inline","version":"2.3.0"}`. The globally installed `bp@bearpaws` 2.2.0 (enabled in user settings) is not loaded: `--plugin-dir` registers the checkout as `bp@inline`, which shadows the same-named installed plugin. All 15 `bp:*` skills in the init event come from the checkout, and the SessionStart stream contains the checkout-only phrase "Load one with your native skill tool". No extra flags (`--setting-sources`, `--bare`) were needed, so `--bare` was never tried (it would skip the bootstrap hook). Auth works with the existing flags. Other plugins' node SessionStart hooks fail with `dyld ... libsimdjson.29.dylib` (exit 1, 5 of 6 hooks); the bp hook exits 0.

Changes: `run-test.sh` in `skill-triggering` and `explicit-skill-requests` now read only the init event line and warn (without failing) when it is missing ("no init event; isolation unverified") or when any `bp` plugin entry has a source other than `bp@inline`, including when both bp@bearpaws and bp@inline are present; whitespace after colons is tolerated. Verified with synthetic lines (inline only, installed only, both, spaced JSON, empty log). `tests/claude-code/test-helpers.sh` `run_claude` previously passed NO `--plugin-dir` (the fast test exercised the installed 2.2.0), so it now passes `--plugin-dir <repo>`. The two other `claude -p` callers, `test-document-review-system.sh` and `test-subagent-driven-development-integration.sh`, were fixed the same way.

| Suite | Result |
|---|---|
| skill-triggering run 1 (13 skills) | 12/13; FAIL: dispatching-parallel-agents |
| skill-triggering run 2 (13 skills) | 13/13 |
| explicit-skill-requests (4) | 4/4 (subagent-driven-development-please, use-systematic-debugging, please-use-brainstorming, mid-conversation-execute-plan) |
| claude-code fast (test-subagent-driven-development.sh) | PASS (with `--plugin-dir`; also PASS before the fix, against installed 2.2.0) |

The four new skills (finishing-a-development-branch, receiving-code-review, using-git-worktrees, verification-before-completion) triggered in both runs. dispatching-parallel-agents is flaky (1 of 2).

**Size.** `wc -w skills/using-bearpaws/SKILL.md`: 911 words. `measure.sh`: bootstrap `additionalContext` 6334 bytes (about 1520 tokens at the ~0.24 tok/byte ratio in `tests/token-measurement/README.md`; `measure.sh` reports bytes only).

**Over-trigger** (isolated, `--max-turns 2`, temp dir, `"name":"Skill"` count):

| Prompt | Run 1 | Run 2 |
|---|---|---|
| What is 17 * 23? Reply with the number only. | 0 | 0 |
| What does the acronym HTTP stand for? | 0 | 0 |

### Resumption (2026-09-29, behavioral checks pending)

The five Task 2 descriptions are edited but uncommitted. The validator passes all four checks, and a direct frontmatter check confirms each starts with `Use when`. The Task 3 bootstrap draft is also uncommitted: 911 → 440 words; injected `additionalContext` 6334 → 3161 bytes. The validator, Antigravity adapter tests, installer tests, version check, hook JSON parse, and `git diff --check` pass. A follow-up plan check restored the rigid/flexible skill distinction and placed skill priority before lazy-load guidance.

The triggering harness produced 0/13 because `claude auth status` reports `loggedIn: false`; each agent response was `Not logged in · Please run /login`. These are invalid behavioral results, not regressions. Explicit-request, fast Claude, over-trigger, and the Claude CLI version of Task 4 still require sign-in. The Homebrew Node binary remains broken (`libsimdjson.29.dylib` missing), but the bundled Node v24.19.0 at `/Users/brandon/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node` runs and can be placed first on `PATH` for the integration test.

**Task 4 Codex pressure scenario.** In fresh, isolated temp repos with only a README and an initial commit, two fresh agents read the brainstorming skill and received the same request: “Design is approved as-is: a CLI flag --quiet that suppresses stdout. Write the design doc now.” RED (old `Commit.` step): the agent committed the design doc as `777d704` without a commit request. GREEN (conditional commit step): the agent wrote and self-reviewed the design doc, ran `git diff --check`, and left it uncommitted because neither the request nor project allowed commits without asking. This tests the behavior on Codex; the planned Claude CLI scenario remains pending.

**Recovered Task 2 Claude results.** Saved stream-json logs from 12:43–12:45 EDT ran after the five description files were edited at 12:43:31. Each of the five skills triggered in two runs (10/10), and each init event listed exactly the checkout's `bp@inline` plugin. A subsequent `run-all.sh` began with six passes, then the CLI hit its session limit at 12:50 (the remaining seven results are invalid). The full post-change triggering suite and Task 3 bootstrap checks therefore remain pending.

### Closeout decision and static verification (2026-09-29)

The user clarified that Claude usage is exhausted and asked to continue based on the existing Bearpaws usage and evidence. The original plan's live Claude re-runs remain unchecked and **not run**: the full Task 2 suite, Task 3 triggering/explicit/over-trigger/fast checks, the Claude CLI Task 4 RED/GREEN scenario, and the Task 5 fast Claude check. The earlier valid 10/10 targeted description triggers and the fresh Codex RED/GREEN design-doc scenario are the behavioral evidence available for these edits. No post-trim Claude behavior claim is made. The long subagent-driven-development integration test also remains unverified in this environment.

Final static checks passed: schema validator (4 checks), installer tests, Antigravity adapter tests (with bundled Node v24.19.0 first on PATH), token measurement (440 bootstrap words and 3161 injected-context bytes), version check (2.3.0), hook JSON parse, and git diff --check. The Red Flags table is byte-for-byte unchanged from pre-enhancement commit `30ab1bc`.

Skill changes were committed separately as `e2bfbc8`, `bdeb875`, and `a2bf8ee`. The unchecked live-test steps above remain a recorded verification limit, not passing results.
