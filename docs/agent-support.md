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
| Gemini CLI | Primary | Mostly working, needs lightweight validation |
| Codex | Experimental | No maintained install flow yet |
| Devin for Terminal | Experimental | Partial repo-local symlink and hook wiring |
| Windsurf Cascade | Experimental | Partial repo-local symlink and rule wiring |

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

## Gemini CLI

Status: Primary, mostly working with lightweight validation still needed.

Existing files:

- `gemini-extension.json`
- `GEMINI.md`
- `skills/using-bearpaws/SKILL.md`
- `skills/using-bearpaws/references/gemini-tools.md`

Install path:

```bash
gemini extensions install /path/to/bearpaws
```

Local development can also use:

```bash
gemini extensions link /path/to/bearpaws
```

How it works:

- `gemini-extension.json` declares the extension and points Gemini at `GEMINI.md`.
- `GEMINI.md` includes the Bearpaws bootstrap and the Gemini tool mapping reference.
- `skills/using-bearpaws/references/gemini-tools.md` maps Claude Code tool names to Gemini CLI equivalents.

Known limitations:

- Gemini CLI has no equivalent to Claude Code's `Task` tool.
- Skills that depend on subagent dispatch cannot have exact behavior parity.
- The Gemini reference says subagent-heavy workflows should fall back to single-session execution via `executing-plans`.
- The repo does not currently include automated Gemini trigger tests.

Minimum useful validation:

- Confirm Gemini installs or links the extension.
- Confirm `GEMINI.md` context loads.
- Confirm `activate_skill` can load at least `using-bearpaws`, `onboarding-to-a-project`, and one process skill.
- Confirm subagent-dependent skills either fall back or are clearly documented as limited.

Risk:

- Medium until a lightweight Gemini smoke test or repeatable manual validation is documented.

## Codex

Status: Experimental, currently no install flow.

Existing files:

- Incidental reference in `skills/brainstorming/visual-companion.md`
- Incidental reference in `skills/writing-skills/SKILL.md`

Current install behavior:

- None.

Current support reality:

- There is no Codex manifest, adapter, installer flag, or test suite.
- The current skills may be useful to Codex as human-readable process docs, but Bearpaws does not currently provide a maintained Codex integration.

Minimum work before stronger claims:

- Decide where Bearpaws skills should live for Codex.
- Document activation behavior.
- Add a minimal placement or wrapper flow.
- Validate at least bootstrap discovery and one non-bootstrap skill.

Risk:

- Medium to high if promoted prematurely, because no current support surface exists.

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
| Gemini CLI | Extension/context smoke test plus one or two skill activation checks. |
| Codex | None until an integration is added. |
| Devin for Terminal | Symlink install test plus manual or automated activation proof before promotion. |
| Windsurf Cascade | Symlink install test plus manual or automated include/activation proof before promotion. |

Do not add a full per-agent trigger matrix unless the maintenance cost is explicitly accepted.

## Support Claim Guidance

Recommended public posture:

- Claude Code and Gemini CLI are primary supported targets.
- Codex, Devin for Terminal, and Windsurf Cascade are experimental unless and until validated.
- Bearpaws began as a hard fork of superpowers v5.0.7 and now evolves independently.
- Attribution and MIT license compliance remain.

Avoid claiming:

- Full behavioral parity with superpowers.
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
