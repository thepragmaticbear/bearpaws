# Token measurement

`measure.sh` emits a JSON snapshot of bytes-on-disk for the bootstrap and the skills tree. Run before and after a change to see the delta.

## Usage

```bash
# Capture pre-change baseline
tests/token-measurement/measure.sh > /tmp/before.json

# (make changes)

# Capture post-change measurement
tests/token-measurement/measure.sh > /tmp/after.json

# Diff
diff <(jq -S . /tmp/before.json) <(jq -S . /tmp/after.json)
```

## What's measured

- `bootstrap_additional_context_bytes`: the actual `additionalContext` string injected by SessionStart, after JSON-escape. This is what every session pays.
- `skills_skill_md_total_bytes`: sum of all `skills/*/SKILL.md` files. Skills are loaded on demand via the `Skill` tool, so this is the *aggregate* a session could load if every skill were invoked.
- `skills_full_payload_bytes`: total bytes across the `skills/` tree (SKILL.md + supporting files); useful for tracking the fully-pulled checkout footprint.
- `per_skill_skill_md_bytes`: per-skill breakdown so reductions can be attributed.

## What's NOT measured

- Tokens. Token counts depend on the tokenizer; bytes are deterministic. As of v1.1.0 the README cross-checks byte deltas against `tiktoken` cl100k_base; if a skill uses unusual structure the ratio diverges from ~0.24 tok/byte.
- `<see>`-pointed references that load only when needed. Counted in `skills_full_payload_bytes` for completeness, not in the per-session targets.
