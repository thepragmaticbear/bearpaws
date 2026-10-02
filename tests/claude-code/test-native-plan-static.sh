#!/usr/bin/env bash
# Static checks for the Claude Code native planning adapter (no claude CLI needed).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Test: native planning static contract ==="

failed=0
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; failed=1; }
has() { grep -qF -- "$2" "$1"; }

adapter="skills/using-bearpaws/references/claude-code.md"
plans="skills/writing-plans/SKILL.md"
bootstrap="skills/using-bearpaws/SKILL.md"

# 1. writing-plans carries the native planning contract and keeps the repo path.
if has "$plans" "native planning mode" \
   && has "$plans" "Do not leave native planning mode to save the plan" \
   && has "$plans" "docs/bearpaws/plans/YYYY-MM-DD-{feature-name}.md" \
   && has "$plans" "Native plan approval is the go-ahead"; then
    pass "writing-plans contains the native planning contract"
else
    fail "writing-plans missing native planning contract text"
fi

# 2. Execution skills persist a session-only plan before implementation.
for f in skills/subagent-driven-development/SKILL.md skills/executing-plans/SKILL.md; do
    if has "$f" "exists only in the session"; then
        pass "$(basename "$(dirname "$f")") persists a session-only plan first"
    else
        fail "$f missing approved-plan persistence precondition"
    fi
done

# 3. Claude adapter exists and is referenced from the bootstrap.
if [[ -f "$adapter" ]] && has "$adapter" "Plan Mode" && has "$adapter" "opusplan"; then
    pass "Claude Code adapter exists with Plan Mode and opusplan guidance"
else
    fail "$adapter missing or incomplete"
fi
if has "$bootstrap" '<see file="references/claude-code.md"/>'; then
    pass "using-bearpaws references the Claude Code adapter"
else
    fail "$bootstrap does not reference references/claude-code.md"
fi
if grep -qiE "plan mode|opusplan" "$bootstrap"; then
    fail "$bootstrap inlines Plan Mode policy; keep it in the adapter"
else
    pass "bootstrap stays small (no Plan Mode policy inline)"
fi

# 4. Claude-specific text does not leak into other adapters.
for f in skills/using-bearpaws/references/antigravity-tools.md .antigravity/rules/bearpaws.md; do
    if grep -qiE "plan mode|opusplan|ExitPlanMode|claude-code\.md" "$f"; then
        fail "$f contains Claude Code planning text"
    else
        pass "$f free of Claude Code planning text"
    fi
done

# 5. Portable skill content stays model-neutral. Allowed: the Claude adapter and
#    writing-skills' Anthropic best-practices reference (multi-model testing advice).
leaks=$(grep -rliE "\b(opus|sonnet|haiku|opusplan)\b" skills \
    | grep -vxF "$adapter" \
    | grep -vxF "skills/writing-skills/anthropic-best-practices.md" || true)
if [[ -z "$leaks" ]]; then
    pass "portable skills contain no Claude model names"
else
    fail "model names found in portable skills: $leaks"
fi

# 6. No phase-routing hook: SessionStart stays the only Claude hook event.
events=$(python3 -c 'import json; print(" ".join(sorted(json.load(open("hooks/hooks.json"))["hooks"].keys())))')
if [[ "$events" == "SessionStart" ]]; then
    pass "hooks.json registers only SessionStart"
else
    fail "hooks.json registers extra events: $events"
fi

echo ""
if [[ "$failed" -eq 0 ]]; then
    echo "=== native planning static contract PASSED ==="
else
    echo "=== native planning static contract FAILED ==="
    exit 1
fi
