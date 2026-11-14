# Token measurement

`measure.sh` emits a JSON snapshot of UTF-8 byte counts and approximate token estimates for the bootstrap and the skills tree. Run before and after a change to see the delta.

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

All size fields are measured in **UTF-8 bytes** (including `bootstrap_additional_context_bytes`, measured via UTF-8 encoding of the decoded `additionalContext` string, matching `wc -c` on UTF-8 skill files).

- `bootstrap_additional_context_bytes`: UTF-8 bytes of the `additionalContext` string injected by `SessionStart`. This is what every session pays up front.
- `skills_skill_md_total_bytes`: sum of UTF-8 bytes across all `skills/*/SKILL.md` files. Skills are loaded on demand via the `Skill` tool, so this is the *aggregate* a session could load if every skill were invoked.
- `skills_full_payload_bytes`: total UTF-8 bytes across the `skills/` tree (`SKILL.md` + supporting files); useful for tracking the fully-pulled checkout footprint.
- `typical_session_bytes`: `bootstrap_additional_context_bytes` plus the `SKILL.md` UTF-8 bytes of the skills loaded in a typical end-to-end feature workflow:
  - `onboarding-to-a-project`
  - `brainstorming`
  - `writing-plans`
  - `test-driven-development`
  - `requesting-code-review`
  - `verification-before-completion`
- `typical_session_skills`: the ordered list of skill names included in `typical_session_bytes`.
- `*_approx_tokens` (`bootstrap_additional_context_approx_tokens`, `skills_skill_md_total_approx_tokens`, `skills_full_payload_approx_tokens`, `typical_session_approx_tokens`): **approximate** token estimates computed as `(utf8_bytes + 2) // 4` (~4 UTF-8 bytes per token, rounded to nearest integer).
- `per_skill_skill_md_bytes`: per-skill UTF-8 byte breakdown so reductions can be attributed.

## What's NOT measured

- Exact tokenizer counts. Token counts depend on the model's tokenizer; UTF-8 bytes are deterministic, and the `*_approx_tokens` fields (`~bytes / 4`, i.e., `~0.25 tok/byte`) are heuristic approximations only. If a skill uses unusual structure or dense punctuation, the ratio can diverge from `~0.24–0.25 tok/byte`.
- `<see>`-pointed references that load only when needed. Counted in `skills_full_payload_bytes` for completeness, not in `typical_session_bytes` or `skills_skill_md_total_bytes`.
