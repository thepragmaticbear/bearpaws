# Bearpaws Agent Support

Bearpaws is moving toward a conservative polyglot support model. This document records current support status and the evidence behind each claim.

The guiding rule is simple: skills define intent; adapters define execution. Source skills should remain the behavioral source of truth.

## Support Tiers

| Tier | Meaning |
|---|---|
| Primary | Intended target with repo wiring and some test or operational evidence. |
| Experimental | Repo wiring or partial guidance exists, but behavior is not yet proven enough for strong claims. |
| Unsupported | No maintained install path or support contract exists. |

Current tiers:

| Agent | Status | Evidence |
|---|---|---|
| Claude Code | Primary | Working |
| Google Antigravity IDE | Primary | Native plugin, skills, subagents, and capability adapter |
| OpenCode | Experimental | Smoke-tested: native `.agents/skills` discovery + `instructions` bootstrap |
| Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) | Experimental | Codex passes the conformance smoke (discovery, explicit load, auto-trigger, risk gate) with the `AGENTS.md` bootstrap; others rely on native `.agents/skills` discovery |

## Claude Code

Status: Primary, working.

Existing files:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `hooks/hooks.json`
- `hooks/run-hook.cmd`
- `hooks/session-start`
- `agents/code-reviewer.md`
- `commands/*.md`
- `skills/*/SKILL.md`
- `tests/claude-code/`
- `tests/skill-triggering/`
- `tests/explicit-skill-requests/`

Install path:

```bash
claude plugin marketplace add /path/to/bearpaws
claude plugin install bp@bearpaws
```

Local development can also use:

```bash
claude --plugin-dir /path/to/bearpaws
```

How it works:

- `.claude-plugin/plugin.json` declares the plugin metadata.
- `hooks/hooks.json` registers a `SessionStart` hook.
- `hooks/run-hook.cmd` provides a cross-platform wrapper.
- `hooks/session-start` reads `skills/using-bearpaws/SKILL.md`, wraps it in hard warning context, and emits Claude Code's `hookSpecificOutput` shape.
- Claude Code consumes native `SKILL.md` skill directories.

Current test coverage:

- Triggering tests invoke `claude -p` and scan stream JSON for `Skill` tool calls.
- Explicit skill request tests check that named skills trigger before unrelated tool use.
- Claude Code workflow tests cover selected complex behavior, especially `subagent-driven-development`.
- Schema validator checks tag whitelist drift and code-review gate alignment.

Risk:

- Low for current Claude behavior.
- Medium for hook output changes, because session-start payload shape must be verified in a fresh Claude Code session.

## Google Antigravity IDE

Status: Primary (native plugin, skills, subagents, and capability adapter).

Existing files:

- `.antigravity/plugin.json`
- `.antigravity/rules/bearpaws.md`
- `skills/using-bearpaws/references/antigravity-tools.md`
- `agents/code-reviewer.md`
- `install.sh` (`--antigravity --global`)
- `tests/antigravity/run-adapter-tests.sh`
- `tests/install/run-install-tests.sh`

Install path:

```bash
./install.sh --antigravity --global
```

Global plugin path:

```
~/.gemini/config/plugins/bearpaws/
├── plugin.json
├── rules/
│   └── bearpaws.md
├── skills/
└── agents/
    └── code-reviewer.md
```

How it works:

- `.antigravity/plugin.json` declares the native Antigravity plugin manifest.
- `.antigravity/rules/bearpaws.md` serves as the thin bootstrap rule importing `skills/using-bearpaws/SKILL.md` and `skills/using-bearpaws/references/antigravity-tools.md`.
- `install.sh` performs atomic, real-directory copies into `~/.gemini/config/plugins/bearpaws/` (no symlinks).
- Antigravity discovers skills natively from `skills/` and loads them on demand.
- `skills/using-bearpaws/references/antigravity-tools.md` maps Claude Code tool references to native Antigravity capabilities (`view_file`, `write_to_file`, `replace_file_content`, `run_command`, `grep_search`, `find_by_name`, `invoke_subagent`).
- Subagent dispatch uses native `invoke_subagent` for fresh implementers, isolated reviewers, and parallel tasks.
- The reusable reviewer `agents/code-reviewer.md` is packaged directly within the plugin.

Known limitations:

- Requires restarting Antigravity IDE after installation or update to refresh the skill registry.
- Antigravity CLI (`agy`) uses different config paths and is considered a separate target.

Validation gates (promotion requirements):

- Gate A (Install): Real files staged cleanly to global plugin folder.
- Gate B (Discovery): `/brain` and core skills appear in Antigravity command palette.
- Gate C (Onboarding): Project conventions inspected autonomously before editing.
- Gate D (Pace Control): Early confidence does not bypass inspection ("Momentum does not waive gates").
- Gate E (Debugging): Root-cause investigation before fix generation.
- Gate F (Planning): Multi-step features follow onboarding → plan → execute.
- Gate G (Verification): Evidence of testing before completion claim.
- Gate H (Review Subagent): Fresh reviewer subagent with adversarial gates intact.
- Gate I (Parallel Agents): Concurrency used only for decoupled tasks.
- Gate J (Update): Clean idempotent re-install.
- Gate K (Uninstall): Plugin removal cleanly restores prior state without affecting unrelated configs.

Risk:

- Low. Plugin packaging isolates BearPaws from core system settings and other plugins.

## OpenCode

Status: Experimental.

- Skills: OpenCode scans `.agents/skills/` and `~/.agents/skills/` and invokes them with its native `skill` tool. It enforces the Agent Skills frontmatter rules (name `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤64 chars, equals folder; description 1–1024 chars), which `tests/schema-validator/run-validator.sh` checks in CI.
- Bootstrap: `"instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]` in `~/.config/opencode/opencode.json`. The installer prints this line and never edits user config.
- Evidence: smoke test 2026-09-28, OpenCode 1.18.29: skills discovered from `.agents/skills` (pass; tested with the earlier directory-symlink layout); bootstrap loaded via a `~`-prefixed `instructions` path, confirmed against a no-`instructions` control run that could not answer (pass).
- Known limitations: no OpenCode tool-name mapping reference; Claude Code tool names (`Agent`, `Skill`) in skills are interpreted by the model.

## Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …)

Status: Experimental.

- Install: `./install.sh --agents --global` links each skill into `~/.agents/skills/`, removing only broken links and skipping any existing entry it didn't link from this checkout. The repo ships `.agents/skills/` (per-skill links into `skills/`).
- Invocation: `$skill-name` or `/skills` (Codex), `/skill-name` (Devin CLI), or implicitly when a description matches.
- Codex bootstrap: add ``Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.`` to `~/.codex/AGENTS.md`. The installer prints this line and never edits user config.
- Devin CLI: `.devin/hooks.v1.json` runs `hooks/session-start`, which emits top-level `additionalContext` when `DEVIN_PROJECT_DIR` is set.
- Evidence: installer test (global linking, the `--global` requirement, preserved unrelated skills); smoke test 2026-09-28, codex-cli 0.156.1: skills discovered via per-skill links in a plain repo (pass); brainstorming loaded on request, SKILL.md read, answered `no-implementation` (pass); a symlinked `.agents/skills` directory was not discovered (fail, with and without project trust); inside a Bearpaws checkout (clone or worktree) only the `bp:` plugin skills were listed (see limitations).
- Known limitations: no automatic bootstrap outside hook-capable agents; Codex conformance smoke (`tests/codex/run-conformance.sh`, 2026-09-29, codex-cli 0.156.1, repo-level `.agents/skills`): discovery, explicit load, and auto-trigger pass; the risk gate fails without a bootstrap (1/1) and passes with the `AGENTS.md` bootstrap line (2/2: failing test first, independent reviewer subagent, fixes pass held-out acceptance). Global install (2026-09-30: `./install.sh --agents --global` plus the line in `~/.codex/AGENTS.md`, test repos with no repo-level skills or AGENTS.md): 4/4 pass in one full run; two earlier runs met all four checks before a 15-minute limit cut the security task off mid-review. On security fixes Codex runs several review rounds (about 14 minutes); repo-local discovery through `.agents/skills` needs git symlinks enabled (`core.symlinks=true`; Developer Mode on Windows); Codex ignores a symlinked skills directory, so `.agents/skills/` uses per-skill links (verified with Codex in a plain repo); in a Bearpaws checkout, Codex lists the installed `bp:` plugin skills instead of the repo-local copies (it apparently treats the repo as the plugin's source; reproduced by adding `.claude-plugin/` to an otherwise passing repo); `./install.sh --agents --global` is the recommended path for other projects; Codex discovered per-skill links in a plain repo, but the global `~/.agents/skills` install has not been smoke-tested with Codex.

Windsurf support removed; Windsurf users can use `--agents`.

## Adapter Policy

Adapters should stay thin.

Allowed lightweight adapter behavior:

- Copy skill directories.
- Symlink skill directories.
- Point an agent context file at existing skill files.
- Wrap the bootstrap in the payload shape required by an agent.
- Add small agent-specific reference notes, such as tool-name mappings.

Avoid:

- Rewriting source skill bodies.
- Normalizing skill sections.
- Adding adapter-only metadata to every skill.
- Requiring generated artifacts for normal installation.
- Claiming behavior parity for agents without tests.

If an agent cannot consume Bearpaws without parsing and changing the inner skill body, stop and reassess before implementing.

## Testing Policy

Current tests are strongest for Claude Code. That should remain the release-blocking target unless another agent is explicitly promoted.

Minimum practical tests by tier:

| Agent | Minimum check |
|---|---|
| Claude Code | Existing trigger, explicit-request, schema, and selected workflow tests. |
| Google Antigravity IDE | Real-file plugin install test, static adapter test, and manual promotion gates A–K. |
| OpenCode | Spec validator + manual discovery smoke test. |
| Other Agent Skills agents | `--agents` installer test + manual activation proof before promotion. |

Do not add a full per-agent trigger matrix unless the maintenance cost is explicitly accepted.

## Support Claim Guidance

Recommended public posture:

- Claude Code and Google Antigravity IDE are primary supported targets.
- OpenCode and other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) are experimental unless and until validated.
- Bearpaws is an independent skills toolkit that evolves on its own cadence.
- Attribution and MIT license compliance remain.

Avoid claiming:

- Full behavioral parity with upstream baselines.
- Ongoing upstream tracking.
- Universal agent compatibility.
- Equivalent behavior across agents with different tool models.
- Production-grade support for experimental agents.

## Promotion Rule

An experimental agent should be promoted only when:

1. Install or linking works in practice.
2. Bootstrap or initial context loads reliably.
3. At least one non-bootstrap skill can be activated.
4. Known limitations are documented.
5. Maintenance burden is acceptable.
6. The maintainer explicitly chooses to support it.
