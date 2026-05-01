# Bearpaws

A Claude Code (and Gemini CLI) skills plugin focused on **token-efficiency** — delivering the same behavioral performance as [superpowers](https://github.com/obra/superpowers) while significantly reducing per-session token consumption. Skills cover TDD, debugging, planning, code review, and parallel execution, plus domain-knowledge for Google Cloud, Google ADK, Vite, JS/TypeScript, and Cloud Run.

> **Status:** v0.1.0. Phase 0 of a four-phase fork program (see [docs/bearpaws/specs/](docs/bearpaws/specs/)). Skill bodies are still in legacy markdown form; XML-schema migration and token-budget optimizations arrive in Phase 1, domain skills in Phase 2.

## Install (Claude Code)

Register the plugin via the dev marketplace in `~/.claude/settings.json`:

```json
{
  "plugins": {
    "bearpaws@bearpaws-dev": true
  },
  "marketplaces": {
    "bearpaws-dev": "/path/to/bearpaws"
  }
}
```

Or pass it on the command line: `claude --plugin-dir /path/to/bearpaws`.

## Install (Gemini CLI)

Bearpaws ships a `gemini-extension.json` so it can also be loaded as a Gemini CLI extension. Refer to the Gemini CLI documentation for extension installation.

## Tests

```bash
tests/skill-triggering/run-all.sh           # ~2 min — verifies skills auto-trigger on naive prompts
tests/claude-code/run-skill-tests.sh        # ~2 min — fast skill-content tests
tests/claude-code/run-skill-tests.sh --integration   # 10–30 min — full integration suite
```

## Why fork?

Superpowers is excellent at shaping agent behavior, but its skill payloads are verbose — every session pays a high token cost for context that could be expressed more concisely. Bearpaws aims to preserve the same pass rate on skill-triggering and behavioral compliance tests while cutting token overhead through structured compression, deferred loading, and tighter prompt engineering. The goal is **same performance, fewer tokens**.

## Attribution

Bearpaws is a hard fork of **[superpowers](https://github.com/obra/superpowers)** at v5.0.7 by Jesse Vincent and contributors, released under the MIT license. The Bearpaws fork preserves the same license and credits the original authors. Subsequent changes (token-efficiency pass, XML schema migration, domain-knowledge skills, Cursor/Codex platform drop) are documented in [docs/bearpaws/specs/](docs/bearpaws/specs/).

## License

MIT — see [LICENSE](LICENSE).
