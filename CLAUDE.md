# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bearpaws is a Claude Code (and Gemini CLI) skills plugin that is a hard fork of [superpowers](https://github.com/obra/superpowers) v5.0.7 — credit to Jesse Vincent and contributors for the original. The fork's primary goal is **token-efficiency**: delivering the same behavioral performance (skill triggering, compliance, code quality) while significantly reducing per-session token consumption through structured compression, deferred loading, and tighter prompt engineering.

Skills cover TDD, debugging, planning, code review, and parallel execution, plus domain-knowledge for Google Cloud, Google ADK, Vite, JS/TypeScript, and Cloud Run. The plugin's job is to inject the `using-bearpaws` bootstrap at session start so the agent learns to discover and invoke the rest of the skills via the `Skill` tool.

## Repository layout

- [skills/](skills/) — one directory per skill, each with a `SKILL.md` and optional `references/`, `examples/`, `scripts/`. Flat namespace.
- [commands/](commands/) — slash commands. The current files are deprecation shims pointing users at the equivalent skills.
- [agents/](agents/) — subagent definitions (e.g. `code-reviewer`).
- [hooks/](hooks/) — `SessionStart` hook that injects the bootstrap.
- [.claude-plugin/](.claude-plugin/) — Claude Code plugin manifest and dev marketplace.
- [gemini-extension.json](gemini-extension.json) — Gemini CLI extension manifest.
- [scripts/](scripts/) — version-bump tooling.
- [tests/claude-code/](tests/claude-code/) — behavioral tests that shell out to the `claude` CLI.
- [tests/skill-triggering/](tests/skill-triggering/) — naive-prompt tests that verify skills auto-trigger.
- [docs/bearpaws/specs/](docs/bearpaws/specs/) — design specs.
- [docs/bearpaws/plans/](docs/bearpaws/plans/) — implementation plans.

## How the bootstrap works

The plugin manifest [.claude-plugin/plugin.json](.claude-plugin/plugin.json) registers the [hooks/hooks.json](hooks/hooks.json) `SessionStart` hook (matchers: `startup|clear|compact`). That hook calls [hooks/run-hook.cmd](hooks/run-hook.cmd) → [hooks/session-start](hooks/session-start), which:

1. Reads [skills/using-bearpaws/SKILL.md](skills/using-bearpaws/SKILL.md).
2. Wraps it in an `<EXTREMELY_IMPORTANT>` block (Phase 0; replaced with `<warning level="hard">` in Phase 1 per the XML-schema spec).
3. Emits JSON in the shape Claude Code expects: `{ "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "..." } }`.

[hooks/run-hook.cmd](hooks/run-hook.cmd) is a bash/cmd polyglot so the same file works on macOS/Linux and Windows. Hook scripts under [hooks/](hooks/) are intentionally **extensionless** — Claude Code's Windows auto-detection prepends `bash` to anything ending in `.sh`, which would double-wrap the call.

If you change the bootstrap shape or the JSON output, run a fresh Claude Code session against this checkout (registered via `--plugin-dir` or the dev marketplace) and confirm the `using-bearpaws` content arrives in the first turn.

## Version management

The plugin version is duplicated across four manifest fields. They are kept in sync by [scripts/bump-version.sh](scripts/bump-version.sh), driven by [.version-bump.json](.version-bump.json):

```bash
scripts/bump-version.sh --check       # report current versions, detect drift
scripts/bump-version.sh --audit       # check + grep repo for stray version strings
scripts/bump-version.sh 0.2.0         # bump every declared file
```

Never hand-edit a version in one manifest — `--check` will flag the drift and `--audit` will surface any undeclared file that mentions the old version.

## Tests

Tests are behavioral, not unit — they invoke the `claude` CLI in headless mode and assert against transcripts. Requires the local plugin to be registered (e.g. `"bp@bearpaws-dev": true` in `~/.claude/settings.json`, or pass `--plugin-dir` explicitly).

```bash
tests/claude-code/run-skill-tests.sh                                          # fast skill-content tests (~2 min)
tests/claude-code/run-skill-tests.sh --integration                            # full subagent-driven-dev run (10–30 min)
tests/claude-code/run-skill-tests.sh -t test-subagent-driven-development.sh   # single test
tests/claude-code/run-skill-tests.sh --verbose                                # stream Claude output
tests/skill-triggering/run-all.sh                                             # verify naive prompts trigger the right skill
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

See [skills/writing-skills/SKILL.md](skills/writing-skills/SKILL.md) and [skills/writing-skills/anthropic-best-practices.md](skills/writing-skills/anthropic-best-practices.md) for the full conventions. The XML-schema migration described in [docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md](docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md) §2 lands in Phase 1; until then, skill bodies remain in the legacy markdown-with-ad-hoc-tags form inherited from superpowers.

## Commit conventions

Do not include `Co-Authored-By` lines or any AI/LLM attribution in commit messages. Commits should be clean with no co-author trailers.
