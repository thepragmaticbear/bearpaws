# Bearpaws

A Claude Code (and Gemini CLI) skills plugin focused on **token-efficiency** — delivering the same behavioral performance as [superpowers](https://github.com/obra/superpowers) while significantly reducing per-session token consumption.

**24 skills** covering TDD, debugging, planning, code review, parallel execution, and domain knowledge for Google Cloud, Google ADK, Vite, JS/TypeScript, and Cloud Run. All skill bodies use a structured XML schema with lazy-loaded references.

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

Bearpaws ships a `gemini-extension.json` for use as a Gemini CLI extension:

```bash
gemini extensions link /path/to/bearpaws
```

## Skills

### Process skills (14)

| Skill | Purpose |
|---|---|
| `bp:brainstorming` | Structured brainstorming before creative work |
| `bp:writing-plans` | Write implementation plans from specs |
| `bp:executing-plans` | Execute implementation plans step by step |
| `bp:test-driven-development` | TDD workflow: RED → GREEN → REFACTOR |
| `bp:systematic-debugging` | Root-cause debugging methodology |
| `bp:verification-before-completion` | Verify work before claiming completion |
| `bp:requesting-code-review` | Request code review from the reviewer agent |
| `bp:receiving-code-review` | Process and apply code review feedback |
| `bp:finishing-a-development-branch` | Ship a branch: rebase, squash, PR |
| `bp:subagent-driven-development` | Multi-agent development with spec/impl/review |
| `bp:dispatching-parallel-agents` | Run independent tasks via parallel subagents |
| `bp:using-git-worktrees` | Isolate feature work in git worktrees |
| `bp:writing-skills` | Author and test new skills (meta) |

### Domain skills (10)

| Skill | Type | Technology |
|---|---|---|
| `bp:google-cloud` | reference | Google Cloud Platform |
| `bp:working-on-google-cloud` | workflow | Google Cloud Platform |
| `bp:google-adk` | reference | Google Agent Development Kit |
| `bp:building-with-adk` | workflow | Google Agent Development Kit |
| `bp:vite` | reference | Vite |
| `bp:working-with-vite` | workflow | Vite |
| `bp:javascript-typescript` | reference | JavaScript / TypeScript |
| `bp:writing-typescript` | workflow | TypeScript |
| `bp:cloud-run` | reference | Cloud Run |
| `bp:deploying-to-cloud-run` | workflow | Cloud Run |

## Token efficiency

Bearpaws delivers the same skill-triggering reliability as superpowers with significantly less context:

| Metric | superpowers v5.0.7 | Bearpaws v1.0.0 | Delta |
|---|---:|---:|---|
| Bootstrap injected per session | 5,292 bytes | 2,907 bytes | -45% |
| Process skill bodies | 108,393 bytes | 53,477 bytes | -51% |
| Average bytes per skill | 7,742 | 3,748 | -52% |
| Skills | 14 | 24 | +71% |

## Tests

```bash
tests/skill-triggering/run-all.sh                     # ~2 min — naive-prompt triggering
tests/claude-code/run-skill-tests.sh                   # ~2 min — fast skill-content tests
tests/claude-code/run-skill-tests.sh --integration     # 10–30 min — full integration suite
tests/schema-validator/run-validator.sh                # <1 sec — XML tag whitelist enforcement
tests/token-measurement/measure.sh                     # <1 sec — byte counts (JSON output)
```

## Attribution

Bearpaws is a hard fork of **[superpowers](https://github.com/obra/superpowers)** at v5.0.7 by Jesse Vincent and contributors, released under the MIT license. The Bearpaws fork preserves the same license and credits the original authors. Design spec and release history are in [docs/bearpaws/](docs/bearpaws/).

## License

MIT — see [LICENSE](LICENSE).
