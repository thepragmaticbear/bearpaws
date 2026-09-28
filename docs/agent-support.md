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
| Devin for Terminal | Experimental | Partial repo-local symlink and hook wiring |
| Windsurf Cascade | Experimental | Partial repo-local symlink and rule wiring |
| Codex | Experimental | Partial `.agents/skills` symlink wiring; no behavior test yet |

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
- `hooks/hooks.json` registers a `SessionStart` hook for `startup`, `clear`, and `compact` (so the bootstrap survives context compaction).
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

## Codex

Status: Experimental, partial.

Existing files:

- `.agents/skills/` symlinks into `skills/`
- `install.sh` (`--codex`, optional `--global`)
- `skills/using-bearpaws/SKILL.md` (Codex activation line)
- `tests/install/run-install-tests.sh`

Install path:

```bash
./install.sh --codex            # repo-local .agents/skills
./install.sh --codex --global   # also ~/.agents/skills
```

How it works:

- Codex discovers Agent Skills (`SKILL.md` directories) from `.agents/skills/` between the working directory and the repo root, and from `~/.agents/skills/`.
- `install.sh` symlinks each `skills/<name>/` directory into those locations. Reinstalls prune only broken links that pointed into this repo's `skills/`, and skip any colliding entry that is not a Bearpaws link (a real directory or the user's own symlink), so the user's other skills in the shared global directory are untouched.
- Codex selects a skill by matching its `description`, or when the user mentions it as `$skill-name`. Skill names carry no `bp:` prefix in Codex.
- The bootstrap relies on `using-bearpaws` being selected by its description. For reliable loading, add `Use the using-bearpaws skill at the start of every task.` to the project's `AGENTS.md`.

Known limitations:

- No SessionStart hook: Codex currently rejects `additionalContext` in SessionStart hook output (openai/codex#45999), so the bootstrap cannot be injected the way it is for Claude Code.
- `~/.agents/skills` is also read by other Agent Skills clients; the links may surface there too. That is incidental and not a support claim.
- The repo does not include a real Codex behavior test.

Evidence:

- The repo has an install reconciliation test covering repo-local and global links and preservation of unrelated global skills.

Minimum work before promotion:

- Verify `using-bearpaws` loads at session start (implicitly or via `AGENTS.md`).
- Verify at least one non-bootstrap skill activates.

Risk:

- Medium until real Codex activation is verified.

## Devin for Terminal

Status: Experimental, partial.

Existing files:

- `.devin/hooks.v1.json`
- `.devin/skills/` symlinks into `skills/`
- `install.sh`
- `hooks/session-start`

Install path:

```bash
./install.sh --devin
```

Optional global install:

```bash
./install.sh --devin --global
```

How it works:

- `install.sh` symlinks each `skills/<name>/` directory into `.devin/skills/`.
- `.devin/hooks.v1.json` runs `hooks/session-start` through bash.
- `hooks/session-start` detects `DEVIN_PROJECT_DIR` and emits SDK-standard top-level `additionalContext`.

Evidence:

- The repo has an install reconciliation test for symlink creation.

Known limitations:

- The repo does not include a real Devin behavior test.
- The bootstrap currently instructs Devin to use the `skill` tool or slash command `/skill-name`; real activation should be verified before primary support is claimed.

Risk:

- Medium until real Devin activation is verified.

## Windsurf Cascade

Status: Experimental, partial.

Existing files:

- `.windsurf/rules/bearpaws.md`
- `.windsurf/skills/` symlinks into `skills/`
- `install.sh`

Install path:

```bash
./install.sh --windsurf
```

How it works:

- `install.sh` symlinks each `skills/<name>/` directory into `.windsurf/skills/`.
- `.windsurf/rules/bearpaws.md` is an always-on rule file with a commented `@include` reference to `../skills/using-bearpaws/SKILL.md`; real include expansion has not been verified.

Evidence:

- The repo has an install reconciliation test for symlink creation.

Known limitations:

- The repo does not include a real Windsurf behavior test.
- The always-on rule and commented include behavior should be verified in Windsurf before stronger support claims are made.

Risk:

- Medium until real Windsurf activation is verified.

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
| Codex | Symlink install test plus manual or automated activation proof before promotion. |
| Devin for Terminal | Symlink install test plus manual or automated activation proof before promotion. |
| Windsurf Cascade | Symlink install test plus manual or automated include/activation proof before promotion. |

Do not add a full per-agent trigger matrix unless the maintenance cost is explicitly accepted.

## Support Claim Guidance

Recommended public posture:

- Claude Code and Google Antigravity IDE are primary supported targets.
- Codex, Devin for Terminal, and Windsurf Cascade are experimental unless and until validated.
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
