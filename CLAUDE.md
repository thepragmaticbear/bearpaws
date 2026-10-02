# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bearpaws is an independent, low-token skills toolkit for AI coding agents, with a focus on portability, simplicity, and practical agent support.

Claude Code and Google Antigravity IDE are the primary supported targets. OpenCode, Grok Build, and other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) are experimental unless a specific workflow has been validated. Avoid adding language that implies ongoing upstream tracking, upstream behavioral parity, or guaranteed support across every agent.

Skills cover TDD, debugging, planning, code review, and parallel execution, plus a stack-agnostic onboarding skill. The plugin's job is to get the `using-bearpaws` bootstrap into the agent context so the agent learns to discover and invoke the rest of the skills.

## Repository layout

- [skills/](skills/) — one directory per skill, each with a `SKILL.md` and optional `references/`, `examples/`, `scripts/`. Flat namespace.
- [commands/](commands/) — slash commands. The current files are deprecation shims pointing users at the equivalent skills.
- [agents/](agents/) — subagent definitions (e.g. `code-reviewer`).
- [hooks/](hooks/) — `SessionStart` hook that injects the bootstrap for Claude Code plus detected SDK-style contexts (Cursor, Devin CLI, Copilot CLI, or unknown SDK callers); [tests/hooks/](tests/hooks/) pins each payload shape. `hooks-cursor.json` is the Cursor hook config. Hook compatibility does not imply support-tier promotion.
- [.claude-plugin/](.claude-plugin/) — Claude Code plugin manifest and dev marketplace. Copilot CLI installs from the same marketplace; Devin falls back to this manifest.
- [.cursor-plugin/](.cursor-plugin/) — Cursor plugin manifest (skills + `hooks/hooks-cursor.json`).
- [.antigravity/](.antigravity/) — Google Antigravity IDE plugin manifest (`plugin.json`) and rules (`bearpaws.md`).
- [.devin/](.devin/) — Devin CLI `hooks.v1.json` (SessionStart hook). Skills come from `.agents/skills`.
- [.agents/skills](.agents/skills) — repo-level Agent Skills discovery: a real directory of per-skill links into `skills/` (Codex ignores a symlinked skills directory, so per-skill links; verified with Codex in a plain repo). The validator keeps it in sync; a new skill needs `ln -s ../../skills/<name> .agents/skills/<name>`. `install.sh --agents --global` links skills into `~/.agents/skills/` for Codex, Devin, OpenCode, Cursor, Copilot, and others; `install.sh --grok --global` adds a Grok Build bootstrap rule in `~/.grok/rules/`.
- [scripts/](scripts/) — version-bump tooling.
- [tests/antigravity/](tests/antigravity/) — static adapter tests for Antigravity plugin integrity.
- [tests/install/](tests/install/) — installer tests for Antigravity, Agent Skills (`--agents`), and Grok (`--grok`).
- [tests/hooks/](tests/hooks/) — SessionStart payload shape per harness, escaping, and loud failure.
- [tests/harness-wiring/](tests/harness-wiring/) — model-free checks that Codex, OpenCode, Copilot CLI, and Grok Build load the installed skills and bootstrap.
- [tests/claude-code/](tests/claude-code/) — behavioral tests that shell out to the `claude` CLI.
- [tests/skill-triggering/](tests/skill-triggering/) — naive-prompt tests that verify skills auto-trigger.
- [tests/benchmark/](tests/benchmark/) — full-session benchmark; primary metric is cost per accepted task, scored by held-out acceptance tests.
- `tests/*-eval/`, [tests/codex/](tests/codex/) — RED/GREEN behavior evals for skill changes, and the Codex conformance smoke.
- [docs/skill-structure.md](docs/skill-structure.md) — descriptive contract for current skill shape.
- [docs/agent-support.md](docs/agent-support.md) — current support tiers and evidence by agent.
- [docs/bearpaws/release-notes/](docs/bearpaws/release-notes/) — release notes, starting with the v1.0.0 public baseline; new positioning changes belong in new release-note files, not retroactive edits to historical notes.

## Support posture

| Agent | Status | Evidence |
|---|---|---|
| Claude Code | Primary | Working |
| Google Antigravity IDE | Primary | Native plugin, skills, subagents, and capability adapter |
| OpenCode | Experimental | Wiring checked in CI: repo-level and global `.agents/skills` discovery, `instructions` bootstrap resolves; live bootstrap smoke-tested |
| Grok Build | Experimental | `./install.sh --grok --global`; `grok inspect` lists the bootstrap rule and all skills (1.0.45, built from source); no live session run |
| Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) | Experimental | Codex skills and `AGENTS.md` bootstrap checked in CI, activation smoke-tested; Copilot CLI installs the plugin (CI); Devin and Cursor hook payloads follow their docs, unverified live. Expanded conformance requires completed-action evidence. |

## How the bootstrap works

### Claude Code and SDK callers

The plugin manifest [.claude-plugin/plugin.json](.claude-plugin/plugin.json) registers the [hooks/hooks.json](hooks/hooks.json) `SessionStart` hook (matchers: `startup|clear`). That hook calls [hooks/run-hook.cmd](hooks/run-hook.cmd) → [hooks/session-start](hooks/session-start), which:

1. Reads [skills/using-bearpaws/SKILL.md](skills/using-bearpaws/SKILL.md). Fails loudly (exit 1, stderr) if the file is missing/empty/unreadable rather than emitting a garbage bootstrap silently.
2. Wraps it in a `<warning level="hard">` block (per the current XML-like skill structure convention).
3. Emits JSON in the platform-appropriate shape — Claude Code: `{ "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "..." } }`; Devin CLI (`DEVIN_PROJECT_DIR` or `DEVIN_PLUGIN_ROOT`): the same nested `hookSpecificOutput` shape; Cursor: top-level `additional_context`; Copilot CLI and unknown SDK-style callers: top-level `additionalContext`. [tests/hooks/run-hook-tests.sh](tests/hooks/run-hook-tests.sh) pins each shape.

[hooks/run-hook.cmd](hooks/run-hook.cmd) is a bash/cmd polyglot so the same file works on macOS/Linux and Windows. Hook scripts under [hooks/](hooks/) are intentionally **extensionless** — Claude Code's Windows auto-detection prepends `bash` to anything ending in `.sh`, which would double-wrap the call.

If you change the bootstrap shape or the JSON output, run a fresh Claude Code session against this checkout (registered via `--plugin-dir` or the dev marketplace) and confirm the `using-bearpaws` content arrives in the first turn.

### Google Antigravity IDE

The Antigravity plugin manifest [.antigravity/plugin.json](.antigravity/plugin.json) and rule [.antigravity/rules/bearpaws.md](.antigravity/rules/bearpaws.md) import [skills/using-bearpaws/SKILL.md](skills/using-bearpaws/SKILL.md) and [skills/using-bearpaws/references/antigravity-tools.md](skills/using-bearpaws/references/antigravity-tools.md).

Installation copies real files (no symlinks) into `~/.gemini/config/plugins/bearpaws/`:
```bash
./install.sh --antigravity --global
```
Antigravity discovers skills natively from `skills/`, loads them on demand, maps actions to native capabilities via `antigravity-tools.md`, and runs isolated subagents via `invoke_subagent`.

### Other harnesses

- **Codex, OpenCode:** skills from `.agents/skills`; the bootstrap is a line the user adds (`~/.codex/AGENTS.md`, or `instructions` in `opencode.json`). The installer prints both and never edits agent config.
- **Grok Build:** ignores SessionStart hook output, so `install.sh --grok --global` writes an owned rule, `~/.grok/rules/bearpaws.md`, that Grok loads in every project. It refuses to overwrite a `bearpaws.md` it did not create.
- **Copilot CLI, Cursor, Devin CLI:** run `hooks/session-start` from their plugin or hook config and get the payload shape each documents (see the table in `tests/hooks/run-hook-tests.sh`).

`tests/harness-wiring/run.sh` proves discovery and bootstrap wiring without a model; behavior still needs live conformance (`tests/codex/run-conformance.sh`).

## Version management

The plugin version is duplicated across three manifest fields. They are kept in sync by [scripts/bump-version.sh](scripts/bump-version.sh), driven by [.version-bump.json](.version-bump.json):

```bash
scripts/bump-version.sh --check       # report current versions, detect drift
scripts/bump-version.sh --audit       # check + grep repo for stray version strings
scripts/bump-version.sh 0.2.0         # bump every declared file
```

Never hand-edit a version in one manifest — `--check` will flag the drift and `--audit` will surface any undeclared file that mentions the old version.

## Tests

```bash
tests/schema-validator/run-validator.sh                                       # verify XML tag whitelist, Agent Skills frontmatter, .agents/skills links, and adversarial gates
tests/install/run-install-tests.sh                                            # verify Antigravity, --agents, and --grok installer
tests/hooks/run-hook-tests.sh                                                 # SessionStart payload shape per harness (no CLI)
tests/harness-wiring/run.sh                                                   # model-free discovery/bootstrap checks for installed codex, opencode, copilot, grok
tests/antigravity/run-adapter-tests.sh                                        # verify Antigravity adapter static assertions
tests/claude-code/run-skill-tests.sh                                          # fast Claude skill-content tests (~2 min)
tests/claude-code/run-skill-tests.sh --integration                            # full subagent-driven-dev run (10–30 min)
tests/claude-code/run-skill-tests.sh -t test-subagent-driven-development.sh   # single test
bash tests/claude-code/test-native-plan-static.sh                             # native Plan Mode contract (static, no CLI)
tests/claude-code/run-skill-tests.sh --verbose                                # stream Claude output
tests/skill-triggering/run-all.sh                                             # verify naive prompts trigger the right skill
tests/benchmark/run.sh                                                        # cost per accepted task: bearpaws vs no plugin (see tests/benchmark/README.md)
tests/review-eval/run.sh <template> <label>                                   # reviewer catches planted defects; labels break attempts honestly
tests/review-eval/routing.sh                                                  # SDD routes review by risk under pressure
tests/skill-triggering/routing/run.sh skills/using-bearpaws/SKILL.md <label>              # bootstrap classifies scope and risk
tests/verification-eval/run.sh skills/verification-before-completion/SKILL.md <label>  # weakened tests are caught
tests/risk-eval/run.sh skills/using-bearpaws/SKILL.md <label>                 # elevated-risk floor: pin behavior, narrow diff, assumptions
tests/resume-eval/run.sh skills/executing-plans/SKILL.md <label>              # resume reconciles plan checkboxes with git
tests/context-eval/run.sh <label>                                             # controller passes onboarding facts to implementers
tests/codex/run-conformance.sh                                                # Codex adapter conformance, repo-level (exit 2 = blocked, not failed)
GLOBAL=1 tests/codex/run-conformance.sh                                       # same, against ./install.sh --agents --global + ~/.codex/AGENTS.md line
```

[tests/skill-triggering/run-test.sh](tests/skill-triggering/run-test.sh) parses `stream-json` output for `"name":"Skill"` plus a matching `"skill":"..."` value — that's how it decides a skill triggered. Logs land under `/tmp/bearpaws-tests/<timestamp>/`.

## When editing skills

Skills are behavior-shaping code, not prose. Use the `bp:writing-skills` skill — it applies TDD to skill content:

1. Run a baseline pressure scenario in a fresh subagent (RED).
2. Capture the exact rationalization the agent uses to skip the right behavior.
3. Write the minimum skill text that closes that loophole (GREEN).
4. Re-run the scenario in a fresh subagent and confirm compliance.
5. Probe for new rationalizations and repeat.

The Red Flags tables, rationalization lists, and the deliberate "your human partner" phrasing in existing skills are tuned content — change them only with eval evidence that the new wording works better, not because the prose reads cleaner.

## Skill structure

Each skill is a directory under [skills/](skills/) containing `SKILL.md` with YAML frontmatter:

```markdown
---
name: skill-name-with-hyphens
description: Use when [specific triggering conditions and symptoms]
---
```

Constraints worth knowing before editing frontmatter:

- `description` is third-person and describes **when** to use the skill, not what it does. The matcher uses it to decide whether to load.
- Frontmatter total ≤ 1024 chars; `name` is letters/numbers/hyphens only.
- Heavy reference material (>100 lines) and reusable scripts go in sibling files; keep `SKILL.md` focused on the rule.

See [docs/skill-structure.md](docs/skill-structure.md), [skills/writing-skills/SKILL.md](skills/writing-skills/SKILL.md), and [skills/writing-skills/anthropic-best-practices.md](skills/writing-skills/anthropic-best-practices.md) for the full conventions. All skill bodies use a compact XML-like structure — the validator at [tests/schema-validator/run-validator.sh](tests/schema-validator/run-validator.sh) enforces the tag whitelist, frontmatter spec, and `.agents/skills` layout on every commit.

## Commit conventions

Do not include `Co-Authored-By` lines or any AI/LLM attribution in commit messages. Commits should be clean with no co-author trailers.
