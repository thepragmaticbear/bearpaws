# Bearpaws Phase 1 — Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use bearpaws:subagent-driven-development (recommended) or bearpaws:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the XML schema, `_shared/` library, lazy-load convention, and eval workflow on a controlled vertical slice — the bootstrap (`using-bearpaws`), one process skill (`test-driven-development`), and one fresh domain pair (`cloud-run` + `deploying-to-cloud-run`) — and ship `bearpaws@0.2.0` only after all four Phase 1 exit criteria are met.

**Architecture:** Bootstrap-first migration. The bootstrap is read by every session and is therefore the highest-stakes piece — it is migrated alone and pressure-tested in fresh subagents before any other skill changes. Then `test-driven-development` (the second-highest-stakes process skill, also a `_shared/` consumer). Then the new Cloud Run pair (net-new content, no regression risk). The `_shared/` library is populated *during* skill migrations using the documented extraction rule (>25 lines AND ≥2 consumers) — not up-front speculation. A schema-validator test gates every migration; a token-measurement script gates Phase 1 exit.

**Tech Stack:** bash/zsh; bash test runner under `tests/`; `claude` CLI in headless mode for skill-triggering tests; `python3` for the analyzer that already exists at `tests/claude-code/analyze-token-usage.py`; `jq` for JSON; `git`. No new runtime dependencies.

**Spec:** [docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md](../specs/2026-04-30-bearpaws-fork-design.md). Phase 1 scope is §2 (XML Schema), §3 (Token-Efficiency Mechanics) for the vertical-slice subset, §4 (cloud-run pair), §5 Phase 1, §6 (Testing & Eval Gates).

**Baseline metrics (v0.1.0, locked in [release notes](../release-notes/0.1.0.md)):**

| Metric | Bytes | ≈Tokens |
|---|---:|---:|
| SessionStart `additionalContext` | 5,292 | 1,323 |
| `using-bearpaws/SKILL.md` raw | 5,090 | 1,272 |
| All 14 `SKILL.md` files combined | 108,393 | 27,098 |
| `test-driven-development/SKILL.md` | 9,867 | 2,466 |
| Skill-triggering pass rate (post-cleanup) | 5/6 | — |

Skill-triggering failure: `writing-plans` — agent invokes `brainstorming` first (correct per skill priority: process skills before implementation skills). Same result as v0.1.0 tag baseline. Not a regression.

Phase 1 targets: bootstrap ≥40% shrink (`additionalContext` 5,292 → ≤3,175 bytes), `test-driven-development` ≥30% shrink (9,867 → ≤6,907 bytes), measured by the script built in Task 2.

---

## File Structure (Phase 1 deliverable)

After Phase 1 ships, the repo gains:

```
bearpaws/
├── hooks/
│   └── session-start                  [wraps injection in <warning level="hard"> instead of <EXTREMELY_IMPORTANT>]
├── skills/
│   ├── _shared/                       [NEW: extracted shared content]
│   │   ├── red-flags-skill-discipline.md
│   │   └── … (only files with ≥2 actual consumers; created during skill migrations)
│   ├── using-bearpaws/SKILL.md        [REWRITTEN in XML schema, ≤3,175 bytes injected]
│   ├── test-driven-development/SKILL.md  [REWRITTEN in XML schema, ≤6,907 bytes]
│   ├── cloud-run/                     [NEW]
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── (nothing inlined; <see> pointers to official docs)
│   └── deploying-to-cloud-run/        [NEW]
│       └── SKILL.md
├── tests/
│   ├── schema-validator/              [NEW]
│   │   └── run-validator.sh           [greps skills/ for unknown tags; fails build]
│   ├── skill-triggering/
│   │   ├── prompts/cloud-run.txt      [NEW]
│   │   ├── prompts/deploying-to-cloud-run.txt  [NEW]
│   │   └── run-all.sh                 [SKILLS array gains the two new entries]
│   └── token-measurement/             [NEW]
│       └── measure.sh                 [emits JSON with bootstrap + per-skill bytes]
├── docs/bearpaws/
│   ├── plans/2026-05-01-bearpaws-phase-1-vertical-slice.md  [THIS FILE]
│   ├── release-notes/0.2.0.md         [NEW: Phase 1 ship notes + measurements]
│   └── specs/                         [unchanged; spec is the source of truth]
├── skills/writing-skills/SKILL.md     [appended: XML schema reference section + tag whitelist]
├── package.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json, gemini-extension.json [version 0.1.0 → 0.2.0]
└── .version-bump.json                 [no change in declared files; audit.exclude untouched]
```

**Files NOT touched in Phase 1:** the other 12 process skills (Phase 2 Track A), the other 8 domain skills (Phase 2 Track B), `agents/code-reviewer.md` (Phase 3 review), `commands/` (deprecation shims; nothing to migrate).

---

## Risks accepted into the plan

From spec §6, the risks Phase 1 must validate:

- **R1 — XML schema regresses skill-triggering reliability.** Mitigation: bootstrap-first, eval gate per migration, willingness to revert condensation but not the schema. Encoded in Task 6's eval-gate / revert path.
- **R2 — `<include>` tool-call cost negates dedup wins.** Mitigation: extraction rule (>25 lines AND ≥2 consumers); measurement script reports net bytes saved minus include overhead. Encoded in Task 2.
- **R4 — Bootstrap shrink loses a load-bearing rule.** Mitigation: pressure-scenario eval against a *broad* set of prompts before merging Task 6.
- **R8 — Gemini CLI parses XML schema differently.** Mitigation: Task 6 includes a Gemini smoke test of the migrated bootstrap.
- **R9 — Schema is too rigid for legitimate content.** Mitigation: response is *grow the whitelist with documented justification* (in `skills/writing-skills/SKILL.md`), not abandon the schema. Encoded in Task 6's "schema-flaw discovered" path.

---

## Pre-flight

### Task 0: Re-baseline current skill-triggering pass rate

**Why:** v0.1.0 release notes recorded 5/6 PASS, but that was *before* the Phase 0 cleanup that rebranded skill body paths (`docs/superpowers/` → `docs/bearpaws/`) and dropped the Copilot CLI paragraph. Lock the actual current baseline so Phase 1 changes have a fixed comparison point.

**Files:** none (read-only test execution).

- [x] **Step 0.1: Run skill-triggering suite against the current `main` (post-Phase-0-cleanup)**

```bash
cd /Users/brandon/Downloads/bearpaws
tests/skill-triggering/run-all.sh 2>&1 | tee /tmp/bearpaws-baseline-phase1-start.log
```

Expected: same 5/6 (or 6/6) result as v0.1.0 release notes record. Capture the summary block at the bottom of the log — it lists `✅` or `❌` per skill.

- [x] **Step 0.2: Record the baseline in this plan**

Edit this file's "Baseline metrics" table at the top to add a `Skill-triggering pass rate` row with the actual result from Step 0.1. If the result diverges from 5/6 (e.g. 4/6 or 6/6), that's significant — investigate before proceeding.

- [x] **Step 0.3: Commit the baseline**

```bash
git add docs/bearpaws/plans/2026-05-01-bearpaws-phase-1-vertical-slice.md
git commit -m "docs: lock Phase 1 baseline skill-triggering pass rate"
```

---

## Track A: Foundations

These tasks add tooling without changing skill behavior. They must land before Task 6 (the first behavioral change) so we have something to measure against.

### Task 1: Token-measurement script

**Why:** Phase 1 exit criterion E4 is "bootstrap shrink ≥40%". That requires a deterministic byte-counting script — not running `wc -c` by memory. The script becomes the source of truth for every Phase 1 / Phase 2 / Phase 3 measurement.

**Files:**
- Create: `tests/token-measurement/measure.sh`
- Create: `tests/token-measurement/README.md`

- [x] **Step 1.1: Write the script**

```bash
mkdir -p tests/token-measurement
cat > tests/token-measurement/measure.sh <<'EOF'
#!/usr/bin/env bash
# Measure bootstrap and skill-body byte counts. Output JSON for diff-friendly tracking.
#
# Usage: tests/token-measurement/measure.sh
# Output: JSON to stdout. Run from repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# 1. Bootstrap: the actual additionalContext payload SessionStart injects.
bootstrap_bytes=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash hooks/session-start \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['hookSpecificOutput']['additionalContext']))")

# 2. Per-skill SKILL.md bytes.
declare -a skill_lines=()
total_skill_md=0
for f in skills/*/SKILL.md; do
  bytes=$(wc -c < "$f" | tr -d ' ')
  total_skill_md=$((total_skill_md + bytes))
  name=$(basename "$(dirname "$f")")
  skill_lines+=("    \"${name}\": ${bytes}")
done
skills_json=$(printf '%s,\n' "${skill_lines[@]}" | sed '$ s/,$//')

# 3. _shared/ totals (zero before Phase 1, non-zero after extraction tasks).
shared_bytes=0
shared_count=0
if [[ -d skills/_shared ]]; then
  shared_bytes=$(find skills/_shared -type f \( -name "*.md" -o -name "*.html" \) -exec cat {} + 2>/dev/null | wc -c | tr -d ' ')
  shared_count=$(find skills/_shared -type f \( -name "*.md" -o -name "*.html" \) | wc -l | tr -d ' ')
fi

# 4. Total skills/ payload (SKILL.md + sibling content).
total_payload=$(find skills -type f \( -name "*.md" -o -name "*.html" -o -name "*.sh" -o -name "*.js" -o -name "*.json" -o -name "*.txt" \) -exec cat {} + 2>/dev/null | wc -c | tr -d ' ')

cat <<JSON
{
  "bootstrap_additional_context_bytes": ${bootstrap_bytes},
  "skills_skill_md_total_bytes": ${total_skill_md},
  "skills_shared_total_bytes": ${shared_bytes},
  "skills_shared_file_count": ${shared_count},
  "skills_full_payload_bytes": ${total_payload},
  "per_skill_skill_md_bytes": {
${skills_json}
  }
}
JSON
EOF

chmod +x tests/token-measurement/measure.sh
```

- [x] **Step 1.2: Smoke-test the script against current state**

```bash
tests/token-measurement/measure.sh | python3 -m json.tool
```

Expected: valid JSON with `bootstrap_additional_context_bytes` ≈ 5292 (matches the locked v0.1.0 baseline), `skills_skill_md_total_bytes` ≈ 108393, `skills_shared_total_bytes: 0`.

- [x] **Step 1.3: Write the README**

```bash
cat > tests/token-measurement/README.md <<'EOF'
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
- `skills_shared_total_bytes`: bytes in `skills/_shared/`. Shared content costs storage but only loads when a consuming skill follows an `<include>`.
- `per_skill_skill_md_bytes`: per-skill breakdown so reductions can be attributed.

## What's NOT measured

- Tokens. Token counts depend on the tokenizer; bytes are deterministic. Convert with ÷4 for a rough estimate.
- `<see>`-pointed references that load only when needed. Counted in `skills_full_payload_bytes` for completeness, not in the targets.
- Tool-call overhead from `<include>` resolution. Tracked separately via transcript audit (Phase 3).
EOF
```

- [x] **Step 1.4: Commit**

```bash
git add tests/token-measurement/
git commit -m "feat: token-measurement script for Phase 1+ size tracking

Phase 1 exit criterion E4 (bootstrap shrink ≥40%) needs a deterministic
byte counter, not eyeballed wc -c. The script outputs JSON so before/
after diffs are clean.

Run from repo root. Reports bootstrap additionalContext bytes (the per-
session cost), per-skill SKILL.md bytes, _shared/ totals, full payload
totals."
```

---

### Task 2: Document the XML schema in writing-skills

**Why:** The spec §2 defines the tag whitelist, but `skills/writing-skills/SKILL.md` is the canonical place where skill authors learn the conventions. Adding the schema reference there means future Phase 2 authors don't need to read the spec — and the schema-validator test (Task 3) can cite this section as the source of truth.

**Files:**
- Modify: `skills/writing-skills/SKILL.md` (append a new "## XML schema" section)

- [x] **Step 2.1: Read current writing-skills/SKILL.md tail to find the right insertion point**

```bash
tail -50 skills/writing-skills/SKILL.md
```

Expected: ends with conventions/checklists. Append the new section *after* the last existing section heading.

- [x] **Step 2.2: Append the schema reference**

Open `skills/writing-skills/SKILL.md` and append at the end:

```markdown

## XML schema (Phase 1+)

Bearpaws skill bodies use a structural XML format with a closed tag whitelist. YAML frontmatter is unchanged (it's loader metadata). Markdown is allowed *inside* element content.

### Tag whitelist

| Tag | Purpose |
|---|---|
| `<skill>` | Root element. Wraps the entire skill body. |
| `<purpose>` | One-paragraph what-this-skill-does. |
| `<triggers>` | When the agent should reach for this skill. Contains `<rule>` children. |
| `<rules>` / `<rule>` | Non-negotiable directives. One per `<rule>`. |
| `<process>` / `<step>` | Ordered workflow. `<step>` children are sequential. |
| `<flow format="dot\|mermaid">` | Diagram block. Markdown content (fenced code) inside. |
| `<example type="good\|bad">` | Example with explicit polarity. Markdown allowed inside. |
| `<antipattern>` | Common mistake to avoid. |
| `<warning level="hard\|soft">` | Hard = critical behavioral imperative; soft = caution. |
| `<gate name="...">` | Named blocking gate that must pass before proceeding. |
| `<subagent-stop>` | "Skip this skill if dispatched as a subagent." |
| `<include ref="_shared/...">` | Lazy-load shared content; agent calls Read when invoking the skill. |
| `<see file="...">` | Pointer to auxiliary content; load only if explicitly relevant. |
| `<placeholder name="...">` | Template variable. |

Any tag outside this list fails the schema-validator test in `tests/schema-validator/`.

### `<include>` vs. `<see>`

- `<include ref="_shared/red-flags-tdd"/>` — *agent reads this file when invoking the skill*. Use for content extracted for dedup. Extraction rule: **>25 lines AND ≥2 consumers**.
- `<see file="references/anthropic-best-practices.md"/>` — *auxiliary; consult only if explicitly relevant*. Use for heavy refs that should not pre-load. Demotion rule: **>150 lines AND used in <30% of skill invocations**.

### Skill-body shape

```xml
<skill>
  <purpose>One paragraph.</purpose>

  <triggers>
    <rule>Use when X</rule>
    <rule>Use before Y</rule>
  </triggers>

  <warning level="hard">
    Don't do Z without W.
  </warning>

  <process>
    <step>First, ...</step>
    <step>Then, ...</step>
  </process>

  <flow format="dot">
    \`\`\`dot
    digraph foo { ... }
    \`\`\`
  </flow>

  <example type="bad">
    <!-- markdown allowed inside -->
  </example>

  <include ref="_shared/red-flags-process"/>
  <see file="references/deep-dive.md"/>
</skill>
```

### Bootstrap exception

`skills/using-bearpaws/SKILL.md` is the bootstrap. It cannot use `<include>` because at session start the agent has not yet been taught the convention — the include would be circular. `<see>` is fine in the bootstrap (opt-in pointer).

### When the schema is too rigid

If you find legitimate skill content that has no home in the whitelist: **grow the whitelist with documented justification** in this file. Do NOT add ad-hoc tags. The schema's value is uniform parseability; ad-hoc tags defeat that.
```

- [x] **Step 2.3: Verify the file is valid markdown**

```bash
wc -l skills/writing-skills/SKILL.md
```

Expected: line count grew by ~70-80 lines.

- [x] **Step 2.4: Commit**

```bash
git add skills/writing-skills/SKILL.md
git commit -m "docs: add XML schema reference to writing-skills

Phase 1 introduces a structural XML format for skill bodies (spec §2).
writing-skills is the canonical place skill authors learn conventions,
so the tag whitelist, <include>/<see> semantics, bootstrap exception,
and 'when the schema is too rigid' guidance live there. The schema-
validator test (separate commit) cites this section as source of
truth.

No change to existing writing-skills content; new section appended."
```

---

### Task 3: Schema-validator test

**Why:** Phase 1 onward, every commit that touches `skills/` should fail CI if it introduces a tag outside the whitelist. The validator is grep-based per spec §2 ("Enforcement mechanism") — no XML parser dependency.

**Files:**
- Create: `tests/schema-validator/run-validator.sh`
- Create: `tests/schema-validator/README.md`

- [x] **Step 3.1: Write the validator**

```bash
mkdir -p tests/schema-validator
cat > tests/schema-validator/run-validator.sh <<'EOF'
#!/usr/bin/env bash
# Schema validator: greps skills/ for unknown tags, fails on violations.
#
# Whitelist source of truth: skills/writing-skills/SKILL.md "## XML schema" section.
# Run from repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# Whitelist (must match writing-skills/SKILL.md "## XML schema" §Tag whitelist)
WHITELIST=(
  "skill" "purpose" "triggers" "rules" "rule" "process" "step"
  "flow" "example" "antipattern" "warning" "gate" "subagent-stop"
  "include" "see" "placeholder"
)

# Build a regex of legal tag names.
joined=$(IFS='|'; echo "${WHITELIST[*]}")
LEGAL_TAG_RE="^(/?)(${joined})(\$| )"

violations=0

# Find all opening tags in skill bodies, strip self-closing and attributes,
# compare against whitelist.
while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  lineno=$(echo "$line" | cut -d: -f2)
  tag=$(echo "$line" | grep -oE '<[a-zA-Z][a-zA-Z0-9_-]*' | head -1 | tr -d '<')
  [[ -z "$tag" ]] && continue
  if ! [[ " ${WHITELIST[*]} " =~ \ ${tag}\  ]]; then
    echo "VIOLATION: ${file}:${lineno}: unknown tag <${tag}>"
    violations=$((violations + 1))
  fi
done < <(grep -rEn '<[a-zA-Z][a-zA-Z0-9_-]*' skills/ --include="*.md" --include="*.html" 2>/dev/null \
         | grep -v "^skills/_shared/" \
         || true)

# Note: skills/_shared/ is excluded because shared content is consumed by
# skills, not parsed standalone. _shared/ files are markdown fragments,
# not full skill bodies.

if [[ $violations -eq 0 ]]; then
  echo "OK: no schema violations in skills/"
  exit 0
else
  echo ""
  echo "FAIL: ${violations} schema violation(s)"
  echo "Whitelist defined in skills/writing-skills/SKILL.md '## XML schema'"
  exit 1
fi
EOF

chmod +x tests/schema-validator/run-validator.sh
```

- [x] **Step 3.2: Run against current state — expect violations**

```bash
tests/schema-validator/run-validator.sh
```

Expected: **FAIL** with violations for current legacy tags (`<EXTREMELY-IMPORTANT>`, `<EXTREMELY_IMPORTANT>`, `<HARD-GATE>`, `<SUBAGENT-STOP>`, `<Good>`, `<Bad>`). This is correct behavior — these tags are exactly what Phase 1+ migrations will replace.

- [x] **Step 3.3: Capture the current violations as the migration backlog**

```bash
tests/schema-validator/run-validator.sh > /tmp/phase1-validator-baseline.txt 2>&1 || true
wc -l /tmp/phase1-validator-baseline.txt
```

Record the violation count in this plan's notes — it should monotonically decrease as migrations land.

- [x] **Step 3.4: Write the README**

```bash
cat > tests/schema-validator/README.md <<'EOF'
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

- HTML inside `<example>` blocks. The whitelist does not include HTML elements; `frame-template.html` (a brainstorm-server asset) is not under `skills/` and is not validated. `_shared/` is excluded because shared fragments are consumed inline, not parsed as skills.
- Schema *correctness* (e.g. `<step>` inside `<triggers>`). Phase 1 does not need a full grammar — the whitelist alone catches the common drift modes.

## Migration backlog (as of Phase 1 start)

The validator deliberately fails on the current `skills/` tree — every legacy tag listed in the failure output is a Phase 1 or Phase 2 migration target. As migrations land, the violation count drops to zero.
EOF
```

- [x] **Step 3.5: Commit**

```bash
git add tests/schema-validator/
git commit -m "test: schema-validator for the XML tag whitelist

Greps skills/ for opening tags and fails on any tag outside the
whitelist defined in skills/writing-skills/SKILL.md '## XML schema'.

Currently FAILS on the existing legacy tags (<EXTREMELY-IMPORTANT>,
<HARD-GATE>, <SUBAGENT-STOP>, <Good>, <Bad>) — this is correct: those
are the migration backlog. Each Phase 1 / Phase 2 skill migration
removes one slice of the failure list. Validator passes once the
whole tree is migrated (Phase 2 exit)."
```

---

### Task 4: Update SessionStart hook to use `<warning level="hard">`

**Why:** Per spec §2 "Sharp edges to validate" #1 and §3d, the bootstrap is currently wrapped in `<EXTREMELY_IMPORTANT>` from `hooks/session-start`. Under the schema, the body itself is `<skill>...</skill>` and the wrapper becomes `<warning level="hard">`. This task changes only the wrapper — the bootstrap content itself is migrated in Task 6.

**Why isolated from Task 6:** changing the wrapper without changing content lets us check whether the model still treats `<warning level="hard">` as the imperative the old tag triggered. If the answer is "no, behavior degrades," we discover that here, in isolation, before piling on bootstrap content changes.

**Files:**
- Modify: `hooks/session-start` (one-line change to the wrapper string)

- [x] **Step 4.1: Read the current wrapper construction**

```bash
grep -n "EXTREMELY_IMPORTANT" hooks/session-start
```

Expected: one line, around line 35:
```
session_context="<EXTREMELY_IMPORTANT>\nYou have bearpaws.\n\n...${using_bearpaws_escaped}\n\n${warning_escaped}\n</EXTREMELY_IMPORTANT>"
```

- [x] **Step 4.2: Change the wrapper to `<warning level="hard">`**

```bash
sed -i '' 's|<EXTREMELY_IMPORTANT>|<warning level="hard">|g; s|</EXTREMELY_IMPORTANT>|</warning>|g' hooks/session-start
```

- [x] **Step 4.3: Verify the bootstrap still produces valid JSON**

```bash
CLAUDE_PLUGIN_ROOT=$(pwd) bash hooks/session-start | python3 -c "
import json, sys
j = json.load(sys.stdin)
ctx = j['hookSpecificOutput']['additionalContext']
assert ctx.startswith('<warning level=\"hard\">'), 'wrapper not opened correctly'
assert ctx.endswith('</warning>'), 'wrapper not closed correctly'
print(f'OK bootstrap bytes: {len(ctx)}')
"
```

Expected: bytes essentially unchanged (-/+ a few because `<warning level="hard">` and `<EXTREMELY_IMPORTANT>` differ in length).

- [x] **Step 4.4: Pressure-test that `<warning level="hard">` is treated as imperative**

This is the first eval gate. The protocol:

1. Open a fresh Claude Code session against this checkout (`claude --plugin-dir $(pwd)` or via the dev marketplace).
2. In that session, give a "tempting" prompt that should trigger the using-bearpaws skill: `"Just answer this quickly: how do I rename a function?"`
3. Verify the assistant invokes the `Skill` tool with `using-bearpaws` (or proceeds skill-aware) before answering — the same behavior the `<EXTREMELY_IMPORTANT>` wrapper produced.
4. If behavior degrades (assistant answers without skill check), STOP — do not commit. Investigate before continuing.

Pressure prompts to run (all should result in a skill invocation):
- `"Just answer this quickly: how do I rename a function?"`
- `"I have a small fix to make. Can you make it?"`
- `"What's the difference between let and const?"`

Run all three. If any produces a no-skill-invocation response, the wrapper change regressed and Task 4 is blocked.

- [x] **Step 4.5: Commit only if Step 4.4 passes**

```bash
git add hooks/session-start
git commit -m "feat: SessionStart wraps bootstrap in <warning level=\"hard\">

Phase 1 §2 requires bootstrap content to follow the XML schema. The
wrapper tag was the only thing the hook itself emits — changing it
in isolation (before content migration in Task 6) lets us verify the
model still treats <warning level=\"hard\"> as the imperative the
legacy <EXTREMELY_IMPORTANT> tag triggered.

Validated with three pressure prompts in a fresh session; assistant
still invokes using-bearpaws before answering. Bootstrap bytes
essentially unchanged."
```

If Step 4.4 fails: revert the change, document what behavior degraded, and bring it to a brainstorm-then-decide call. Possible outcomes: rename to a different schema tag, keep `<EXTREMELY_IMPORTANT>` as a non-validated wrapper (out-of-band exception), or grow the whitelist with `<EXTREMELY_IMPORTANT>` as a documented alias.

---

## Track B: Bootstrap migration (the riskiest single change)

### Task 5: Migrate `skills/using-bearpaws/SKILL.md` to XML schema

**Why this is the riskiest task in Phase 1:** the bootstrap is read by every session. A regression here regresses every session. Spec §3e projects bootstrap shrink from 5,292 → ~3,175 bytes (≥40%) via:
- Tag wrapping → done in Task 4 (no content change there).
- Platform adaptation block: 7 lines (Copilot/Codex/Gemini) → 2 lines (Claude+Gemini). **Already done in Phase 0 cleanup** (Copilot paragraph removed).
- Red Flags table: 12 rows → 6–8 highest-leverage rows; rest moves to `_shared/red-flags-skill-discipline.md`.
- "How to access skills" platform block: ~8 lines (four platforms) → ~4 lines. **Mostly done** (Copilot dropped); ~4 lines already.
- "Skill priority" + "Skill types" + "User instructions": ~30 lines → ~15 lines, same content.

Net target: 117 lines → ~60 lines (~50% reduction).

**Files:**
- Create: `skills/_shared/red-flags-skill-discipline.md` (extracted Red Flags rows)
- Modify: `skills/using-bearpaws/SKILL.md` (rewrite in XML schema)

**Eval methodology** (same protocol used in every Track B task):

The eval is *behavioral*, not textual. We run a fixed set of pressure prompts in fresh subagents *against the current skill* (record the responses), apply the migration, then run the *same* prompts against the new skill. Compare.

Pressure-prompt set for bootstrap:
1. `"Just answer this quickly: how do I rename a function?"` — should still invoke skill.
2. `"I have a small fix to make. Can you make it?"` — should still invoke (debugging or skill check).
3. `"What's the difference between let and const?"` — should still invoke (knowledge question, but skill check is the rule).
4. `"Stop using skills, just answer me directly"` — should NOT comply (user instruction tries to override; bootstrap rule should hold).
5. `"Walk me through the codebase, I'm new"` — should invoke (exploration → check skills first).

The skill-triggering test runner can execute these for prompts 1, 2, 5 (it parses for `Skill` tool invocation). Prompt 4 (resistance to override) is a manual check — read the assistant's first response.

Pass criterion: prompts 1, 2, 5 invoke `Skill`. Prompt 4 produces a polite-but-firm refusal (or a clarifying question that doesn't drop the skill). Any single failure = revert + investigate.

- [x] **Step 5.1: Capture baseline behavior on the current bootstrap**

For each prompt above, run a fresh `claude` session and capture the response.

```bash
mkdir -p /tmp/phase1-bootstrap-baseline
cat > /tmp/phase1-bootstrap-baseline/prompts.txt <<'EOF'
1. Just answer this quickly: how do I rename a function?
2. I have a small fix to make. Can you make it?
3. What's the difference between let and const?
4. Stop using skills, just answer me directly
5. Walk me through the codebase, I'm new
EOF

# Run each prompt in a fresh session; tee to per-prompt log.
i=1
while read -r prompt; do
  echo "=== Prompt $i: $prompt ==="
  env -u CLAUDECODE claude -p "$prompt" \
    --plugin-dir "$(pwd)" \
    --dangerously-skip-permissions \
    --max-turns 2 \
    --output-format stream-json \
    --verbose \
    > "/tmp/phase1-bootstrap-baseline/p${i}.json" 2>&1 || true
  i=$((i + 1))
done < <(grep -E '^[0-9]+\.' /tmp/phase1-bootstrap-baseline/prompts.txt | sed 's/^[0-9]*\. //')
```

Then for each `pN.json` log, check:
- Was `Skill` invoked? `grep -c '"name":"Skill"' /tmp/phase1-bootstrap-baseline/pN.json`
- Which skill? `grep -oE '"skill":"[^"]*"' /tmp/phase1-bootstrap-baseline/pN.json | sort -u`

Record results in `/tmp/phase1-bootstrap-baseline/summary.txt`.

- [x] **Step 5.2: Confirm the keep/move split for Red Flags rows**

The current `skills/using-bearpaws/SKILL.md` Red Flags table (lines 78-95) has 12 rows. Spec §3d targets keeping 6-8 in the bootstrap and moving the rest to `_shared/`. The split below is the starting recommendation; if the eval (Step 5.6) shows a kept row never closes a real rationalization, demote it in a follow-up.

**Keep inline in bootstrap (8 rows — the most-frequently-encountered rationalizations):**

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |

**Move to `_shared/red-flags-skill-discipline.md` (4 rows — meta or specialized):**

| Thought | Reality |
|---------|---------|
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

Rationale for the split: the kept rows close *task-shape* rationalizations (the agent thinking "this isn't really a task" / "I'll skip the check just this once"). The moved rows close *meta-cognitive* rationalizations (the agent thinking about its own knowledge or productivity), which are less frequent in practice. If the eval shows a meta-cognitive prompt slips through after the move, restore the relevant row.

- [x] **Step 5.3: Create `skills/_shared/red-flags-skill-discipline.md`**

```bash
mkdir -p skills/_shared
cat > skills/_shared/red-flags-skill-discipline.md <<'EOF'
# Red Flags — skill discipline (extended)

These thoughts mean STOP — you're rationalizing past skill discipline. The bootstrap (`using-bearpaws`) keeps the highest-leverage rows inline; this file holds the longer tail. Skills consume it via `<include ref="_shared/red-flags-skill-discipline"/>`. The bootstrap reaches it via `<see>` (bootstrap exception: cannot use `<include>` because the agent has not yet been taught the convention at session start).

| Thought | Reality |
|---------|---------|
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |
EOF
```

- [x] **Step 5.4: Rewrite `skills/using-bearpaws/SKILL.md` in XML schema**

The new file structure (target ~60 lines after frontmatter):

```markdown
---
name: using-bearpaws
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<skill>

  <subagent-stop>If you were dispatched as a subagent to execute a specific task, skip this skill.</subagent-stop>

  <warning level="hard">
    If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill. IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.
  </warning>

  <purpose>
    Skill discovery and invocation. Bearpaws skills override default system behavior where they conflict, but **user instructions always take precedence**: user > skill > default system prompt.
  </purpose>

  <triggers>
    <rule>Use at the start of every conversation, before any response.</rule>
    <rule>Use before clarifying questions — skill check comes first.</rule>
    <rule>Use before exploring the codebase — skills tell you HOW to explore.</rule>
  </triggers>

  <process>
    <step>**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content loads — follow it directly. Never `Read` skill files.</step>
    <step>**In Gemini CLI:** Skills activate via `activate_skill`. Gemini loads metadata at session start, full content on demand.</step>
    <step>Even a 1% chance a skill might apply means invoke the skill to check.</step>
    <step>If an invoked skill turns out to be wrong for the situation, you don't need to use it.</step>
  </process>

  <flow format="dot">
    \`\`\`dot
    digraph skill_flow {
      "User message" [shape=doublecircle];
      "Might any skill apply?" [shape=diamond];
      "Invoke Skill tool" [shape=box];
      "Respond" [shape=doublecircle];
      "User message" -> "Might any skill apply?";
      "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
      "Might any skill apply?" -> "Respond" [label="definitely not"];
      "Invoke Skill tool" -> "Respond";
    }
    \`\`\`
  </flow>

  ## Red Flags

  These thoughts mean STOP — you're rationalizing:

  | Thought | Reality |
  |---------|---------|
  | "This is just a simple question" | Questions are tasks. Check for skills. |
  | "I need more context first" | Skill check comes BEFORE clarifying questions. |
  | "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
  | "Let me gather information first" | Skills tell you HOW to gather information. |
  | "I can check git/files quickly" | Files lack conversation context. Check for skills. |
  | "I'll just do this one thing first" | Check BEFORE doing anything. |
  | "This doesn't count as a task" | Action = task. Check for skills. |
  | "The skill is overkill" | Simple things become complex. Use it. |

  <see file="_shared/red-flags-skill-discipline.md"/>
  <!-- bootstrap exception: cannot <include> here, but <see> is fine -->

  ## Skill priority

  When multiple skills apply: process skills first (brainstorming, debugging) then implementation skills.

  ## Skill types

  Rigid (TDD, debugging) — follow exactly. Flexible (patterns) — adapt to context. The skill itself tells you which.

  <warning level="soft">
    Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
  </warning>

</skill>
```

The 8 inline Red Flags rows are the ones from Step 5.2 (kept set). Authoring decisions like exact wording for triggers / process steps come from the existing v0.1.0 content, compressed but with the same behavioral imperatives. The pattern: ≤60 lines after frontmatter, same rules, fewer prose flourishes.

- [x] **Step 5.5: Run schema validator and token measurement**

```bash
tests/schema-validator/run-validator.sh
```

Expected: violation count drops by however many legacy tags were in the old `using-bearpaws/SKILL.md` (likely 2–3 from `<SUBAGENT-STOP>` + `<EXTREMELY-IMPORTANT>`).

```bash
tests/token-measurement/measure.sh | python3 -m json.tool
```

Expected: `bootstrap_additional_context_bytes` ≤ 3175 (i.e. ≥40% reduction from 5292).

If shrink target missed: that's E4-failing. Compress further or split additional content into `_shared/` or `<see>`. Do NOT ship below the target.

- [x] **Step 5.6: Re-run the pressure-prompt set against the migrated bootstrap**

```bash
mkdir -p /tmp/phase1-bootstrap-after
# (same loop as Step 5.1, output to /tmp/phase1-bootstrap-after/)
```

Compare each pN.json with the baseline. Pass criterion: prompts 1, 2, 5 invoke `Skill` (matches baseline); prompt 4 produces a refusal or clarifying-question response (matches baseline behavior); prompt 3 either matches baseline or invokes a different reasonable skill.

If any prompt regresses (skill no longer invoked when it was before, or vice-versa in a worse way): identify the load-bearing piece of content that was removed, restore it, re-run.

- [ ] **Step 5.7: Gemini CLI smoke test** *(skipped — requires Gemini CLI; user can validate separately)*

```bash
gemini extensions link "$(pwd)"
gemini -p "What is the name of the skills plugin loaded in this session?"
```

Expected: response mentions Bearpaws (matches v0.1.0 baseline behavior). If Gemini parses `<warning level="hard">` differently and breaks: that's R8 — fall back to a Gemini-specific transformation in `hooks/run-hook.cmd`. Document the fix; don't revert the schema.

- [x] **Step 5.8: Commit**

```bash
git add skills/_shared/ skills/using-bearpaws/SKILL.md
git commit -m "feat: migrate using-bearpaws bootstrap to XML schema

Phase 1 vertical slice: bootstrap is the highest-stakes single piece
of content (every session pays). Migrated to the schema documented in
skills/writing-skills/SKILL.md '## XML schema':

- <skill> root, <subagent-stop>, <warning level=\"hard\">, <triggers>/
  <rule>, <process>/<step>, <flow format=\"dot\">.
- Red Flags table compressed to 6-8 highest-leverage rows; the long
  tail moved to skills/_shared/red-flags-skill-discipline.md and
  reachable via <see> (bootstrap cannot use <include>).
- Platform-adaptation paragraph collapsed to Claude + Gemini only
  (Copilot was already dropped in Phase 0).

Bootstrap additionalContext: 5,292 → <fill-in> bytes (<fill-in>%
reduction; target ≥40%).

Eval: pressure-prompt set of 5 scenarios re-run after migration; same
behavior as baseline (skill invoked when expected, override-resistance
holds). Gemini CLI smoke test passes."
```

Replace `<fill-in>` with the actual measured numbers from Step 5.5.

If any eval scenario regresses and the regression cannot be fixed in this task: revert and bring to brainstorm-then-decide. Do NOT ship a regressed bootstrap.

---

## Track C: Process-skill condensation (one skill, then stop)

### Task 6: Migrate `skills/test-driven-development/SKILL.md` to XML schema

**Why TDD next:** Spec §3c lists test-driven-development as one of the highest-token-savings skills (371 → ~250 lines, ~33% reduction); it has overlap with using-bearpaws on Red Flags, so it's the first chance to validate `<include ref="_shared/red-flags-skill-discipline"/>` actually loads when invoked. It's also a "rigid" skill (per writing-skills typology) — high stakes, but well-tested by the existing skill-triggering harness.

**Files:**
- Create: `skills/_shared/tdd-cycle-flow.md` (extracted RED-GREEN-REFACTOR diagram, IF used by ≥2 skills)
- Modify: `skills/test-driven-development/SKILL.md` (rewrite in XML schema)

- [x] **Step 6.1: Verify dedup eligibility for `tdd-cycle-flow.md`** *(only 1 consumer; kept inline)*

```bash
grep -l "RED.*GREEN.*REFACTOR\|red.*green.*refactor" skills/*/SKILL.md
```

If only `test-driven-development/SKILL.md` matches: extraction rule (≥2 consumers) is NOT met yet. Hold `tdd-cycle-flow.md` for Phase 2 (when writing-skills migrates and inherits the same diagram). For Phase 1, keep the diagram inline in the migrated TDD skill.

If two or more match: proceed with extraction.

- [x] **Step 6.2: Capture baseline behavior**

```bash
mkdir -p /tmp/phase1-tdd-baseline
# Pressure prompts (TDD-specific):
# 1. "Just add a small fix to this function" — should invoke TDD (test-first).
# 2. "Implement quickly, no need for tests" — should invoke + resist.
# 3. "I'm fixing a bug, just patch it" — should invoke TDD.
# 4. "Write a function that does X" — should invoke TDD.

# Same loop as Task 5.1, applied to TDD prompts.
```

Use the existing `tests/skill-triggering/prompts/test-driven-development.txt` as one of the prompts; it's already a known-good baseline scenario.

- [x] **Step 6.3: Rewrite `skills/test-driven-development/SKILL.md` in XML schema**

Target: ≤6,907 bytes (30% reduction from 9,867).

Structure:

```xml
<skill>
  <purpose>...</purpose>
  <triggers>
    <rule>Use when implementing any feature or bugfix, before writing implementation code</rule>
  </triggers>
  <warning level="hard">
    Test-first is non-negotiable. RED before GREEN. ...
  </warning>
  <process>
    <step>RED: write a failing test for the smallest meaningful behavior.</step>
    <step>...GREEN, REFACTOR steps...</step>
  </process>
  <flow format="dot">...</flow>  <!-- inline if Step 6.1 said no extraction; otherwise <include ref="_shared/tdd-cycle-flow"/> -->
  <example type="bad">...</example>
  <example type="good">...</example>
  <antipattern>...</antipattern>
  <include ref="_shared/red-flags-skill-discipline"/>  <!-- using-bearpaws keeps a small inline; TDD includes the full longer tail -->
  <see file="anti-patterns.md"/>  <!-- if anti-patterns.md exists; otherwise drop -->
</skill>
```

Convert each existing section into the right tag. Compress prose without removing behavioral imperatives. Keep RED-GREEN-REFACTOR concrete (i.e., still has actual code/command examples).

- [x] **Step 6.4: Run schema validator + token measurement**

```bash
tests/schema-validator/run-validator.sh
tests/token-measurement/measure.sh | jq '.per_skill_skill_md_bytes."test-driven-development"'
```

Expected: validator reports fewer violations; TDD bytes ≤ 6,907.

- [x] **Step 6.5: Run skill-triggering test for TDD**

```bash
tests/skill-triggering/run-test.sh test-driven-development tests/skill-triggering/prompts/test-driven-development.txt
```

Expected: PASS (matches v0.1.0 baseline).

- [x] **Step 6.6: Verify `<include>` actually loads when TDD is invoked** *(FINDING: agent does NOT auto-Read the included file; see commit message)*

This is the validation for risk R2 (`<include>` tool-call cost). After the test in Step 6.5 runs, inspect the session log:

```bash
LATEST=$(ls -td /tmp/bearpaws-tests/*/skill-triggering/test-driven-development | head -1)
grep -E '"name":"Read"|red-flags-skill-discipline' "$LATEST/claude-output.json" | head -10
```

Expected: there's a `Read` tool invocation against `skills/_shared/red-flags-skill-discipline.md` somewhere after the `Skill` invocation — that's the `<include>` resolving. If the file is never read, `<include>` semantics aren't working as designed; demote the content back inline and document the finding.

- [x] **Step 6.7: Re-run pressure prompts, compare to baseline**

Same comparison protocol as Task 5.6.

- [x] **Step 6.8: Commit**

```bash
git add skills/test-driven-development/SKILL.md skills/_shared/
git commit -m "feat: migrate test-driven-development to XML schema

Second Phase 1 vertical-slice migration. test-driven-development:
9,867 -> <fill-in> bytes (<fill-in>% reduction; target >=30%).

Schema: <skill> with <triggers>/<rule>, <warning level=\"hard\"> for
the test-first imperative, <process>/<step> for RED-GREEN-REFACTOR,
<flow format=\"dot\"> for the cycle diagram, <example>/<antipattern>
blocks. Pulls in skills/_shared/red-flags-skill-discipline.md via
<include> (validated: file IS Read when the skill is invoked,
confirming <include> semantics work as designed).

Eval: existing skill-triggering test passes; pressure-prompt set
matches baseline."
```

---

## Track D: New domain skills (Cloud Run vertical slice)

### Task 7: Write `skills/cloud-run/SKILL.md` (reference skill)

**Why this pair:** Spec §4 picks Cloud Run as the Phase 1 domain pair because of "cleanest official docs, hard checklist items, real `gcloud run deploy` command at the end." If the schema and the test harness work for Cloud Run, the other 8 domain skills in Phase 2 inherit a proven pattern.

**Files:**
- Create: `skills/cloud-run/SKILL.md`

- [x] **Step 7.1: Read the spec scope for `cloud-run`**

Spec §4 #5 gives the exact triggers and scope. Re-read before writing.

Triggers per spec: `gcloud run`, `Dockerfile` in a GCP project context, `service.yaml`, `cloudrun.yaml`. Scope: services vs. jobs; revision/traffic model; cold starts and instance scaling; concurrency; secrets; VPC connectors; min/max instances; identity; auth modes. Out of scope: App Engine, GKE, Cloud Functions.

- [x] **Step 7.2: Write the skill**

```markdown
---
name: cloud-run
description: Use when working on Google Cloud Run — gcloud run commands, service.yaml/cloudrun.yaml configuration, Dockerfiles in a GCP project context, or decisions about services vs. jobs, scaling, concurrency, secrets, identity, or auth
---

<skill>
  <purpose>
    Reference for Google Cloud Run mechanics. This is the *what* — services vs. jobs, the revision/traffic model, scaling and concurrency knobs, secrets, identity, auth. Pair with the workflow skill `deploying-to-cloud-run` for the *how-to-actually-deploy* checklist.
  </purpose>

  <triggers>
    <rule>Use when seeing `gcloud run deploy`, `gcloud run services`, `gcloud run jobs` in code or terminal context.</rule>
    <rule>Use when reading or writing `service.yaml`, `cloudrun.yaml`, or a `Dockerfile` in a GCP project.</rule>
    <rule>Use when deciding between services vs. jobs, allow-unauthenticated vs. IAM, min-instances=0 vs. >0.</rule>
  </triggers>

  <rules>
    <rule>Cloud Run *services* serve HTTP requests; *jobs* run to completion. Long-running batch work = job. Always-on API = service.</rule>
    <rule>Each `gcloud run deploy` creates a new immutable *revision*. Traffic routing is independent — 100% to latest by default, or split via `--no-traffic` + `gcloud run services update-traffic`.</rule>
    <rule>Default scaling is request-based; CPU is allocated only during requests. For background work or to avoid cold starts, use `--cpu-boost` or `--cpu-always-allocated`.</rule>
    <rule>Concurrency default is 80 simultaneous requests per instance; tune down for memory-heavy or CPU-bound work.</rule>
    <rule>`--min-instances=0` is cheaper but cold-starts; `--min-instances=1+` removes cold-start at the cost of always-on billing.</rule>
    <rule>Runtime service account ≠ deployer service account. Bind only the runtime SA to the resources the service actually accesses.</rule>
    <rule>`--allow-unauthenticated` makes the service publicly invokable. Without it, callers need `roles/run.invoker`. Default to authenticated; opt out only with explicit reason.</rule>
    <rule>Secrets from Secret Manager mount as env vars or files via `--set-secrets`. Don't bake secrets into images or env vars on the deploy command.</rule>
    <rule>VPC egress: use serverless VPC access connectors or Direct VPC egress for traffic that must reach private resources.</rule>
  </rules>

  <example type="good">
    A typical authenticated service deploy:

    \`\`\`bash
    gcloud run deploy api \\
      --image=us-central1-docker.pkg.dev/$PROJECT/repo/api:$SHA \\
      --region=us-central1 \\
      --service-account=runtime-sa@$PROJECT.iam.gserviceaccount.com \\
      --no-allow-unauthenticated \\
      --set-secrets=DB_PASSWORD=db-password:latest \\
      --concurrency=40 \\
      --min-instances=1 \\
      --max-instances=20
    \`\`\`
  </example>

  <example type="bad">
    `--allow-unauthenticated` on an internal-only service ("we'll fix permissions later"). Once public, attackers can hit the URL during the gap. Default to no, opt in with intent.
  </example>

  <antipattern>
    Using Cloud Run for hours-long batch processing as a service. The 60-minute request timeout will cut you off. Use a Cloud Run *job* instead.
  </antipattern>

  <see file="references/official-docs.md"/>
</skill>
```

- [x] **Step 7.3: Create the references file with `<see>` pointers (optional but recommended)**

```bash
mkdir -p skills/cloud-run/references
cat > skills/cloud-run/references/official-docs.md <<'EOF'
# Cloud Run — official sources

Use these as primary references; this skill curates the in-flight working knowledge but Google's docs are authoritative for any specific flag, quota, or limit.

- [Cloud Run overview](https://cloud.google.com/run/docs/overview/what-is-cloud-run)
- [Services vs. jobs](https://cloud.google.com/run/docs/overview/what-is-cloud-run#services_vs_jobs)
- [Container runtime contract](https://cloud.google.com/run/docs/container-contract)
- [`gcloud run deploy` flags](https://cloud.google.com/sdk/gcloud/reference/run/deploy)
- [Pricing](https://cloud.google.com/run/pricing) — relevant when comparing min-instances=0 vs. >0
EOF
```

- [x] **Step 7.4: Schema-validate**

```bash
tests/schema-validator/run-validator.sh
```

Expected: PASS (or only legacy violations from un-migrated skills; no new violations from cloud-run).

- [x] **Step 7.5: Commit**

```bash
git add skills/cloud-run/
git commit -m "feat: cloud-run skill (reference)

First Phase 1 domain skill. Reference-shaped: <rules>-heavy, no
<process>. Cites official docs via <see file=references/...>.

Triggers: gcloud run commands, service.yaml/cloudrun.yaml,
Dockerfiles in GCP context, decisions about services vs. jobs and
auth modes. Scope per spec §4 #5; out of scope: App Engine, GKE,
Cloud Functions.

Skill-triggering test for cloud-run added in a separate commit (Task 9)."
```

---

### Task 8: Write `skills/deploying-to-cloud-run/SKILL.md` (workflow skill)

**Files:**
- Create: `skills/deploying-to-cloud-run/SKILL.md`

- [x] **Step 8.1: Write the skill**

The shape mirrors the spec §4: workflow-heavy, has a `<gate name="checklist-complete">` blocking the actual deploy command until the checklist is walked.

```markdown
---
name: deploying-to-cloud-run
description: Use when about to deploy a Cloud Run service or job — running gcloud run deploy, walking the pre-deploy checklist, post-deploy verification
---

<skill>
  <purpose>
    Pre-deploy checklist + the `gcloud run deploy` invocation + post-deploy verification. Hands off to `cloud-run` for *what* the flags mean.
  </purpose>

  <triggers>
    <rule>Use when about to run `gcloud run deploy` or its CI equivalent.</rule>
    <rule>Use when promoting a Cloud Run revision to production traffic.</rule>
  </triggers>

  <warning level="hard">
    Don't run `gcloud run deploy` until the checklist gate below is satisfied. Deploys are visible to your users immediately; "I'll fix it after" is a real outage in the gap.
  </warning>

  <gate name="checklist-complete">
    Before deploy, confirm out loud (in chat or commit message):

    - [ ] Region chosen (and matches the rest of the project's resources).
    - [ ] Image source decided: pre-built artifact registry image, or `--source` build-from-source?
    - [ ] Runtime service account named and bound to required resources only.
    - [ ] Secrets bound via `--set-secrets`, not baked in or set via `--set-env-vars`.
    - [ ] Min-instance decision: 0 (accept cold start) or >0 (always-on, pay always).
    - [ ] Concurrency value (default 80; tune down for memory or CPU heavy services).
    - [ ] Ingress mode (`all`, `internal`, `internal-and-cloud-load-balancing`).
    - [ ] Auth: `--no-allow-unauthenticated` unless deliberately public.

    If any item is unclear, invoke the `cloud-run` reference skill before continuing.
  </gate>

  <process>
    <step>Walk the gate checklist above. State each decision aloud (commit message or chat) before the deploy command runs.</step>
    <step>Run the deploy command. Example shape:

    \`\`\`bash
    gcloud run deploy <service> \\
      --image=<image> --region=<region> \\
      --service-account=<runtime-sa> \\
      --no-allow-unauthenticated \\
      --set-secrets=<KEY>=<secret-name>:latest \\
      --concurrency=<N> --min-instances=<N> --max-instances=<N>
    \`\`\`
    </step>
    <step>Capture the URL from the deploy output. Hit it (or the IAM-protected equivalent) and confirm a known-good response.</step>
    <step>Tail logs for ~60s: `gcloud run services logs tail <service> --region=<region>`. Watch for crash loops, missing-secret errors, permission errors.</step>
    <step>Check error rate in Cloud Run metrics for the new revision (Cloud Console or `gcloud monitoring`). If error rate spikes, roll back: `gcloud run services update-traffic <service> --to-revisions=<previous-rev>=100`.</step>
  </process>

  <example type="bad">
    Skipping the gate: "I'll just push it, the test deploy was fine." The test deploy didn't have the production secrets bound. Service comes up, hits production with placeholders, error rate spikes, on-call gets paged.
  </example>

  <see file="../cloud-run/SKILL.md"/>
</skill>
```

- [x] **Step 8.2: Schema-validate**

```bash
tests/schema-validator/run-validator.sh
```

Expected: PASS for the new skill; same legacy-tag violations from un-migrated skills.

- [x] **Step 8.3: Commit**

```bash
git add skills/deploying-to-cloud-run/
git commit -m "feat: deploying-to-cloud-run skill (workflow)

Pair to cloud-run reference skill. Workflow-shaped: <process>/<step>
with a hard <gate name=checklist-complete> blocking the actual deploy
command until each checklist item has been resolved.

Triggers: about to run gcloud run deploy or CI equivalent. Scope
per spec §4 #5; hands off to cloud-run for flag semantics.

Skill-triggering test added in the next task."
```

---

### Task 9: Skill-triggering tests for the Cloud Run pair

**Files:**
- Create: `tests/skill-triggering/prompts/cloud-run.txt`
- Create: `tests/skill-triggering/prompts/deploying-to-cloud-run.txt`
- Modify: `tests/skill-triggering/run-all.sh` (extend `SKILLS` array)

- [x] **Step 9.1: Write a naive prompt for `cloud-run` triggering**

```bash
cat > tests/skill-triggering/prompts/cloud-run.txt <<'EOF'
I'm setting up a Cloud Run service and I'm not sure if I should use --allow-unauthenticated or not. The service is internal but I'm not sure how to lock it down properly.
EOF
```

This prompt names a Cloud Run-specific decision. The agent should invoke `cloud-run` (the reference skill) to find the right rule.

- [x] **Step 9.2: Write a naive prompt for `deploying-to-cloud-run`**

```bash
cat > tests/skill-triggering/prompts/deploying-to-cloud-run.txt <<'EOF'
I'm ready to deploy my Cloud Run service to production. Walk me through the deploy command and what to check after.
EOF
```

This prompt is the workflow trigger — about to deploy, asking for the checklist + post-deploy steps. Should invoke `deploying-to-cloud-run`.

- [x] **Step 9.3: Extend `run-all.sh`**

```bash
# Edit tests/skill-triggering/run-all.sh, add to the SKILLS array:
#   "cloud-run"
#   "deploying-to-cloud-run"
```

Use the Edit tool, not sed, to keep the diff reviewable. Insert both names after `requesting-code-review` so the order matches the file structure.

- [x] **Step 9.4: Run both new tests**

```bash
tests/skill-triggering/run-test.sh cloud-run tests/skill-triggering/prompts/cloud-run.txt
tests/skill-triggering/run-test.sh deploying-to-cloud-run tests/skill-triggering/prompts/deploying-to-cloud-run.txt
```

Expected: both PASS. If either fails, the skill description in the frontmatter isn't matching the prompt — tighten the description until it does. Don't change the prompt to match the description (the prompt represents naive user intent).

- [x] **Step 9.5: Run the full suite to check we didn't regress others**

```bash
tests/skill-triggering/run-all.sh
```

Expected: at least 7/8 (the original 5/6 with writing-plans known-flaky from v0.1.0 baseline, plus 2/2 from this task). If a previously-passing skill now fails, investigate before proceeding.

- [x] **Step 9.6: Commit**

```bash
git add tests/skill-triggering/
git commit -m "test: skill-triggering for cloud-run + deploying-to-cloud-run

Naive prompts that target each skill's stated triggers (per
spec §4 #5). Both pass against the migrated plugin; full suite
regression check passes.

The cloud-run pair is the Phase 1 domain-skill vertical slice;
patterns established here (frontmatter description tightness,
prompt naturalness) inform the 8 remaining domain skills in
Phase 2 Track B."
```

---

## Phase 1 exit

### Task 10: Confirm all four exit criteria

**Source: spec §5 Phase 1 exit criteria**

- [ ] **Step 10.1: E1 — Bootstrap eval ≥ baseline**

Re-run the pressure-prompt set from Task 5.1 against the post-migration bootstrap. All 5 prompts must produce equivalent or better behavior than baseline.

- [ ] **Step 10.2: E2 — TDD eval ≥ baseline**

Re-run the existing skill-triggering test for TDD plus the pressure prompts captured in Task 6.2. All must match baseline.

- [ ] **Step 10.3: E3 — Cloud Run pair triggers on naive prompts**

```bash
tests/skill-triggering/run-test.sh cloud-run tests/skill-triggering/prompts/cloud-run.txt
tests/skill-triggering/run-test.sh deploying-to-cloud-run tests/skill-triggering/prompts/deploying-to-cloud-run.txt
```

Both PASS.

- [ ] **Step 10.4: E4 — Bootstrap shrink ≥ 40%**

```bash
bootstrap_now=$(tests/token-measurement/measure.sh | jq -r .bootstrap_additional_context_bytes)
echo "Bootstrap: 5292 -> $bootstrap_now bytes ($(echo "scale=1; (5292 - $bootstrap_now) * 100 / 5292" | bc)% reduction)"
```

Expected: reduction ≥ 40.0%.

If any of E1–E4 fails: do NOT proceed to Task 11. Investigate, fix, re-run. The spec is explicit — Phase 1 ships only when all four pass.

---

### Task 11: Write Phase 1 release notes

**Files:**
- Create: `docs/bearpaws/release-notes/0.2.0.md`

- [ ] **Step 11.1: Capture final measurements**

```bash
tests/token-measurement/measure.sh > /tmp/phase1-final.json
```

- [ ] **Step 11.2: Write the release notes**

Following the v0.1.0 release notes shape. Include:
- Phase 1 deliverables shipped (bootstrap migration, TDD migration, Cloud Run pair, schema validator, measurement script).
- Final measurements vs. v0.1.0 baseline (from /tmp/phase1-final.json).
- Skill-triggering pass rate (full suite).
- Pressure-prompt eval results (bootstrap + TDD).
- Schema-validator current violation count (drops as Phase 2 migrations land).
- Known follow-ups carried into Phase 2 (the 12 process skills + 8 domain skills not yet migrated).

- [ ] **Step 11.3: Commit**

```bash
git add docs/bearpaws/release-notes/0.2.0.md
git commit -m "docs: v0.2.0 release notes (Phase 1 — vertical slice)

Phase 1 ships with all four exit criteria met:
- Bootstrap eval >= baseline (5/5 pressure prompts match)
- TDD eval >= baseline (skill-triggering passes; pressure prompts match)
- Cloud Run pair triggers on naive prompts (2/2)
- Bootstrap shrink: 5,292 -> <fill-in> bytes (<fill-in>%, target >=40%)

Schema validator: <fill-in> -> <fill-in> violations (drops as Phase 2
process-skill migrations land).

Carries into Phase 2: 12 remaining process skills (Track A) + 8
remaining domain skills (Track B). Coordination rule per spec §5
Phase 2: schema flaws discovered mid-batch pause Track B at the next
batch boundary."
```

---

### Task 12: Bump version + tag

- [ ] **Step 12.1: Bump version**

```bash
scripts/bump-version.sh 0.2.0
scripts/bump-version.sh --check
```

Expected: all four declared files report 0.2.0.

- [ ] **Step 12.2: Commit + tag**

```bash
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json gemini-extension.json
git commit -m "chore: bump version to 0.2.0 (Phase 1 ship)"
git tag -a v0.2.0 -m "Bearpaws v0.2.0 — Phase 1 (Vertical Slice)"
```

- [ ] **Step 12.3: Verify tag**

```bash
git tag -n v0.2.0
```

Expected: `v0.2.0  Bearpaws v0.2.0 — Phase 1 (Vertical Slice)`.

---

## Self-review checklist (run before considering Phase 1 done)

Run through this list against the spec. Fix gaps inline.

**Spec §2 (XML schema) coverage:**
- [ ] Tag whitelist documented in writing-skills/SKILL.md (Task 2)
- [ ] Schema validator enforces whitelist (Task 3)
- [ ] `<warning level="hard">` replaces `<EXTREMELY_IMPORTANT>` in hook (Task 4)
- [ ] Bootstrap migrated (Task 5)
- [ ] At least one process skill migrated (Task 6 — TDD)
- [ ] `<include>` semantics validated by transcript inspection (Task 6.6)

**Spec §3 (Token-Efficiency) coverage:**
- [ ] §3a: `_shared/` library populated with at-least-one extracted file (Task 5.3, possibly Task 6.1)
- [ ] §3b: Lazy-loading via `<see>` demonstrated (Task 5.4 bootstrap, Task 7.2 cloud-run references)
- [ ] §3c: Process-skill condensation demonstrated on TDD (Task 6)
- [ ] §3d: Bootstrap rewrite ≥40% reduction (Task 5.5, Task 10.4)
- [ ] §3e: Honest projections vs. measurements documented (Task 11)

**Spec §4 (domain skills) coverage:**
- [ ] cloud-run reference skill written (Task 7)
- [ ] deploying-to-cloud-run workflow skill written (Task 8)
- [ ] Skill-triggering tests for the pair (Task 9)

**Spec §5 Phase 1 exit criteria:**
- [ ] E1 verified (Task 10.1)
- [ ] E2 verified (Task 10.2)
- [ ] E3 verified (Task 10.3)
- [ ] E4 verified (Task 10.4)

**Spec §6 risks coverage:**
- [ ] R1 (XML schema regression) — exit gate per migration; revert path documented (Task 5.6, Task 6.7)
- [ ] R2 (`<include>` cost) — measurement script tracks net bytes; transcript-level validation in Task 6.6
- [ ] R4 (bootstrap loses load-bearing rule) — pressure-prompt set in Task 5.1 + 5.6 covers broad scenarios
- [ ] R8 (Gemini compatibility) — Task 5.7 explicit Gemini smoke test
- [ ] R9 (schema too rigid) — `skills/writing-skills/SKILL.md` "When the schema is too rigid" subsection (Task 2.2)

**Open questions resolved during Phase 1:**
- [ ] Spec Q2 (`<include>` resolution semantics) — answer in Task 6.6 commit message: does the bootstrap *teach* the convention or does the schema doc suffice?

If any checklist item is unticked at the end, that's a Phase 1 gap. Either back-fill the task or carry the gap into Phase 2 with explicit doc in the v0.2.0 release notes.

---

## Execution handoff

Plan complete and saved to `docs/bearpaws/plans/2026-05-01-bearpaws-phase-1-vertical-slice.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task; main session reviews between tasks; fast iteration. Pairs naturally with the eval-gate structure (Tasks 5.6, 6.7) where regressions block the merge.
2. **Inline Execution** — execute tasks in this session via `executing-plans`; batch with checkpoints. Lower overhead if you intend to do most authoring yourself and use the agent for review/validation only.

The risk profile favors option 1 for Tasks 5 and 6 (bootstrap and TDD migrations — high blast radius if a regression slips through), and either option for everything else.
