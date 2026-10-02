#!/usr/bin/env bash
# Integration test: native Plan Mode -> approval -> execution handoff.
#
# Phase A plans in --permission-mode plan (default model: opusplan, override with
# BEARPAWS_PLAN_MODEL). Phase B resumes the same session with the approval
# message and a writable permission mode. Assertions are behavioral:
#   - planning left the git tree untouched
#   - the session continued (same session id) instead of restarting
#   - after approval, no second "start?" / "which execution mode?" question
#   - the approved plan was persisted under docs/bearpaws/plans/ before the
#     first src/ or test/ write
#   - the work continued into bp:subagent-driven-development or bp:executing-plans
# Model identity is reported when the stream exposes it but never fails the test.
#
# Slow and uses premium models. Run via: run-skill-tests.sh --integration
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

MODEL="${BEARPAWS_PLAN_MODEL:-opusplan}"
EXEC_TURNS="${BEARPAWS_EXEC_MAX_TURNS:-40}"

echo "=== Integration Test: native Plan Mode -> execution (model: $MODEL) ==="
echo ""

TEST_PROJECT=$(create_test_project)
LOG_DIR="${BEARPAWS_TEST_LOG_DIR:-/tmp/bearpaws-tests/$(date +%Y%m%d-%H%M%S)}/opusplan-integration"
mkdir -p "$LOG_DIR"
PLAN_LOG="$LOG_DIR/plan.jsonl"
EXEC_LOG="$LOG_DIR/exec.jsonl"
trap 'cleanup_test_project "$TEST_PROJECT"' EXIT

cd "$TEST_PROJECT"
mkdir -p src test
cat > package.json <<'EOF'
{ "name": "cart-fixture", "version": "1.0.0", "type": "module", "scripts": { "test": "node --test" } }
EOF
cat > src/cart.js <<'EOF'
export function createCart() {
  return { items: [] };
}

export function addItem(cart, name, priceCents, qty = 1) {
  cart.items.push({ name, priceCents, qty });
  return cart;
}

export function cartTotal(cart) {
  return cart.items.reduce((sum, i) => sum + i.priceCents * i.qty, 0);
}
EOF
cat > test/cart.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createCart, addItem, cartTotal } from '../src/cart.js';

test('total sums price times quantity', () => {
  const cart = addItem(addItem(createCart(), 'a', 250, 2), 'b', 100);
  assert.equal(cartTotal(cart), 600);
});
EOF
cat > CLAUDE.md <<'EOF'
Work directly on the current feature branch; no worktree is needed for this repo.
EOF
git init -q -b main
git config user.email "test@example.com"
git config user.name "Test"
git add .
git commit -qm "fixture"
# A feature branch so the main/master consent rule is not what this test measures.
git checkout -qb feature/discounts

PROMPT='The spec below is approved; do not brainstorm further. Plan the implementation.

Spec: add discount codes to the cart. New module src/discounts.js exports
applyDiscount(totalCents, code). Codes: SAVE10 takes 10% off the total, with the
discount rounded down to whole cents; FIVEOFF takes 500 cents off but never
below zero; unknown codes throw an Error. cartTotal(cart, code) in src/cart.js
applies the code when one is given. Add tests in test/discounts.test.js and
extend test/cart.test.js.'

echo "Phase A: planning in native Plan Mode (log: $PLAN_LOG)..."
portable_timeout 900 claude -p "$PROMPT" \
    --model "$MODEL" \
    --permission-mode plan \
    --plugin-dir "$REPO_ROOT" \
    --output-format stream-json --verbose \
    > "$PLAN_LOG" 2>&1 || true

failed=0
if [ -z "$(git status --porcelain)" ]; then
    echo "  [PASS] Phase A: git working tree unchanged during planning"
else
    echo "  [FAIL] Phase A: planning changed the tree:"; git status --porcelain | sed 's/^/    /'; failed=1
fi

SESSION_ID=$(python3 -c '
import json, sys
for line in open(sys.argv[1], errors="replace"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if ev.get("session_id"):
        print(ev["session_id"]); break
' "$PLAN_LOG")
if [ -z "$SESSION_ID" ]; then
    echo "  [FAIL] Phase A: no session id in stream"; exit 1
fi

# Phase B: the approval message mirrors what Claude Code sends when the user
# approves a native plan; headless sessions cannot click the approval UI.
APPROVAL='User has approved your plan. You can now start coding.'

echo "Phase B/C: approval and execution in session $SESSION_ID (log: $EXEC_LOG)..."
portable_timeout 1800 claude -p "$APPROVAL" \
    --resume "$SESSION_ID" \
    --model "$MODEL" \
    --permission-mode bypassPermissions \
    --max-turns "$EXEC_TURNS" \
    --plugin-dir "$REPO_ROOT" \
    --output-format stream-json --verbose \
    > "$EXEC_LOG" 2>&1 || true

if python3 - "$PLAN_LOG" "$EXEC_LOG" "$TEST_PROJECT" "$SESSION_ID" <<'PY'
import json, os, re, sys
plan_log, exec_log, project, session = sys.argv[1], sys.argv[2], os.path.realpath(sys.argv[3]), sys.argv[4]

def events(path):
    for line in open(path, errors="replace"):
        try:
            yield json.loads(line)
        except ValueError:
            pass

def tool_uses(path):
    out = []
    for ev in events(path):
        if ev.get("type") != "assistant":
            continue
        for b in ev.get("message", {}).get("content", []) or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                out.append((b.get("name"), b.get("input") or {}))
    return out

def models(path):
    return sorted({ev.get("message", {}).get("model") for ev in events(path)
                   if ev.get("type") == "assistant" and ev.get("message", {}).get("model")})

ok = True
def check(cond, label, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f": {detail}" if detail and not cond else ""))
    ok = ok and cond

plan_uses = tool_uses(plan_log)
exec_uses = tool_uses(exec_log)
exec_events = list(events(exec_log))

check(any(i.get("skill", "").endswith("writing-plans") for n, i in plan_uses if n == "Skill"),
      "Phase A: writing-plans invoked")

sessions = {ev.get("session_id") for ev in exec_events if ev.get("session_id")}
check(session in sessions, "Phase B: execution continued the planning session", f"sessions={sessions}")

def rel(path):
    if not path:
        return None
    p = os.path.realpath(path if os.path.isabs(path) else os.path.join(project, path))
    return os.path.relpath(p, project) if p.startswith(project + os.sep) else None

# Worktrees under the project (e.g. .worktrees/x/) count: strip that prefix.
def norm(r):
    return re.sub(r"^\.?worktrees/[^/]+/", "", r) if r else r

# Shell writes count too (heredocs, sed -i, scripts): any Bash command with a
# write marker contributes the plan/src/test paths it names, in textual order.
WRITE_MARKER = re.compile(r">|\btee\b|\bcp\b|\bmv\b|sed\s+-i|open\(|writeFile|python3?\s+-")
PATH_RE = re.compile(r"(docs/bearpaws/plans/[^\s'\"]+\.md|(?<![\w/])(?:src|test)/[^\s'\"]+)")
writes = []
for n, i in exec_uses:
    if n in ("Write", "Edit", "MultiEdit"):
        writes.append(norm(rel(i.get("file_path"))))
    elif n == "Bash":
        cmd = i.get("command", "")
        if WRITE_MARKER.search(cmd):
            writes.extend(PATH_RE.findall(cmd))

plan_idx = next((k for k, w in enumerate(writes) if w and w.startswith("docs/bearpaws/plans/")), None)
code_idx = next((k for k, w in enumerate(writes) if w and re.match(r"(src|test)/", w)), None)

check(plan_idx is not None, "Phase C: approved plan persisted under docs/bearpaws/plans/", f"writes={writes[:12]}")
check(code_idx is not None, "Phase C: implementation began without a second approval",
      f"writes={writes[:12]}; final={[e.get('result') for e in exec_events if e.get('type')=='result'][-1:]}")
if plan_idx is not None and code_idx is not None:
    check(plan_idx < code_idx, "Phase C: plan persisted before first src/ or test/ write",
          f"plan at {plan_idx}, code at {code_idx}")

exec_skills = [i.get("skill", "") for n, i in exec_uses if n == "Skill"]
check(any(s.endswith(("subagent-driven-development", "executing-plans")) for s in exec_skills),
      "Phase D: execution skill invoked", f"skills={exec_skills}")

print(f"  [INFO] planning models: {models(plan_log) or 'not exposed'}")
print(f"  [INFO] execution models: {models(exec_log) or 'not exposed'}")
sys.exit(0 if ok else 1)
PY
then :; else failed=1; fi

echo ""
if [ "$failed" -eq 0 ]; then
    echo "=== native Plan Mode integration test PASSED ==="
else
    echo "=== native Plan Mode integration test FAILED (logs: $LOG_DIR) ==="
    exit 1
fi
