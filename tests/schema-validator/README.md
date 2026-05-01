# Schema validator

Greps `skills/` for any opening XML tag and fails if the tag is outside the whitelist defined in `skills/writing-skills/SKILL.md` `## XML schema`.

## Usage

```bash
tests/schema-validator/run-validator.sh
```

Exit 0 = pass. Exit 1 = at least one violation; first lines of output identify file/line/tag.

## What's checked

- Every `skills/*/SKILL.md`. Supporting files (HTML templates, external Anthropic docs, code examples) are intentionally excluded since they may legitimately contain non-schema tags.
- Opening tags only (e.g. `<warning level="hard">`); attributes ignored.
- Self-closing tags (`<see file="..."/>`) treated like opening tags.

## What's NOT checked

- Schema *correctness* (e.g. `<step>` inside `<triggers>`). The whitelist alone catches the common drift modes; a full grammar is out of scope for v1.x.
- Files outside `skills/*/SKILL.md` — supporting files in `skills/<name>/references/`, `examples/`, or `scripts/` may contain HTML, code, or external-doc tags that aren't part of the schema.

## Status

Pass at v1.0.0 and v1.1.0: 0 violations across all 25 SKILL.md files.
