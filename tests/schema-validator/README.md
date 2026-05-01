# Schema validator

Greps `skills/` for any opening XML tag and fails if the tag is outside the whitelist defined in `skills/writing-skills/SKILL.md` `## XML schema`.

## Usage

```bash
tests/schema-validator/run-validator.sh
```

Exit 0 = pass. Exit 1 = at least one violation; first lines of output identify file/line/tag.

## What's checked

- Every `*.md` and `*.html` under `skills/` (excluding `skills/_shared/`).
- Opening tags only (e.g. `<warning level="hard">`); attributes ignored.
- Self-closing tags (`<see file="..."/>`) treated like opening tags.

## What's NOT checked

- Schema *correctness* (e.g. `<step>` inside `<triggers>`). Phase 1 does not need a full grammar — the whitelist alone catches the common drift modes.

## Migration backlog (as of Phase 1 start)

The validator deliberately fails on the current `skills/` tree — every legacy tag listed in the failure output is a Phase 1 or Phase 2 migration target. As migrations land, the violation count drops to zero.

Current baseline: 121 violations. Most are from HTML in reference files (`visual-companion.md`, `frame-template.html`, `anthropic-best-practices.md`); the SKILL.md-specific legacy tags (`<SUBAGENT-STOP>`, `<EXTREMELY-IMPORTANT>`, `<HARD-GATE>`, `<Good>`, `<Bad>`) are the primary migration targets.
