# Bearpaws

A Claude Code (and Gemini CLI) plugin that ships a library of behavior-shaping skills — TDD, debugging, planning, code review — plus domain-knowledge skills for Google Cloud, Google ADK, Vite, JS/TypeScript, and Cloud Run.

> **Status:** v0.1.0. Phase 0 of a four-phase fork program (see [docs/bearpaws/specs/](docs/bearpaws/specs/)). Skill bodies are still in legacy markdown form; XML-schema migration arrives in Phase 1, domain skills in Phase 2.

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

## Attribution

Bearpaws is a hard fork of **[superpowers](https://github.com/obra/superpowers)** at v5.0.7 by Jesse Vincent and contributors, released under the MIT license. The Bearpaws fork preserves the same license and credits the original authors. Subsequent changes (token-efficiency pass, XML schema migration, domain-knowledge skills, Cursor/Codex platform drop) are documented in [docs/bearpaws/specs/](docs/bearpaws/specs/).

## License

MIT — see [LICENSE](LICENSE).
