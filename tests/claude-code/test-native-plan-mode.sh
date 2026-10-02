#!/usr/bin/env bash
# Test: writing-plans inside Claude Code native Plan Mode
# Runs a headless session with --permission-mode plan against a disposable
# fixture repo and asserts that planning happens without project mutation:
# writing-plans triggers, no project write/edit is attempted, no commit,
# worktree, or install command runs, and the git tree is unchanged.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: writing-plans in native Plan Mode ==="
echo ""

TEST_PROJECT=$(create_test_project)
LOG_DIR="${BEARPAWS_TEST_LOG_DIR:-/tmp/bearpaws-tests/$(date +%Y%m%d-%H%M%S)}/native-plan-mode"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/stream.jsonl"
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
git init -q
git config user.email "test@example.com"
git config user.name "Test"
git add .
git commit -qm "fixture"

head_before=$(git rev-parse HEAD)
worktrees_before=$(git worktree list --porcelain | grep -c '^worktree ' || true)

PROMPT='The spec below is approved; do not brainstorm further. Plan the implementation.

Spec: add discount codes to the cart. New module src/discounts.js exports
applyDiscount(totalCents, code). Codes: SAVE10 takes 10% off (rounded down to
whole cents), FIVEOFF takes 500 cents off but never below zero, unknown codes
throw an Error. cartTotal(cart, code) in src/cart.js applies the code when one
is given. Add tests in test/discounts.test.js and extend test/cart.test.js.'

echo "Running Claude in plan mode (log: $LOG_FILE)..."
portable_timeout 600 claude -p "$PROMPT" \
    --permission-mode plan \
    --plugin-dir "$REPO_ROOT" \
    --output-format stream-json --verbose \
    > "$LOG_FILE" 2>&1 || true

failed=0

if python3 - "$LOG_FILE" "$TEST_PROJECT" <<'PY'
import json, os, re, sys
log, project = sys.argv[1], os.path.realpath(sys.argv[2])
uses = []
for line in open(log, errors="replace"):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    if ev.get("type") != "assistant":
        continue
    for block in ev.get("message", {}).get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            uses.append((block.get("name"), block.get("input") or {}))

ok = True
def check(cond, label, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f": {detail}" if detail and not cond else ""))
    ok = ok and cond

skills = [i.get("skill", "") for n, i in uses if n == "Skill"]
check(any(s.endswith("writing-plans") for s in skills), "writing-plans skill invoked", f"skills={skills}")

def in_project(path):
    if not path:
        return False
    p = path if os.path.isabs(path) else os.path.join(project, path)
    p = os.path.realpath(p)
    return p == project or p.startswith(project + os.sep)

writes = [(n, i.get("file_path") or i.get("notebook_path"))
          for n, i in uses if n in ("Write", "Edit", "MultiEdit", "NotebookEdit")]
project_writes = [w for w in writes if in_project(w[1])]
check(not project_writes, "no write/edit attempted on project files", f"{project_writes}")

mutating = re.compile(r"git\s+(commit|worktree\s+add|checkout\s+-b|switch\s+-c|add\b)|npm\s+(install|i\b)|mkdir|(?<![0-9&])>>?\s*(?!/dev/null)[^\s&|;]")
bash = [i.get("command", "") for n, i in uses if n == "Bash"]
bad = [c for c in bash if mutating.search(c)]
check(not bad, "no mutating shell command attempted", f"{bad}")

sys.exit(0 if ok else 1)
PY
then :; else failed=1; fi

if [ -z "$(git status --porcelain)" ]; then
    echo "  [PASS] git working tree unchanged"
else
    echo "  [FAIL] git working tree changed:"; git status --porcelain | sed 's/^/    /'; failed=1
fi
if [ "$(git rev-parse HEAD)" = "$head_before" ]; then
    echo "  [PASS] no commits created"
else
    echo "  [FAIL] HEAD moved"; failed=1
fi
worktrees_after=$(git worktree list --porcelain | grep -c '^worktree ' || true)
if [ "$worktrees_after" = "$worktrees_before" ]; then
    echo "  [PASS] no worktree created"
else
    echo "  [FAIL] worktree count changed ($worktrees_before -> $worktrees_after)"; failed=1
fi

echo ""
if [ "$failed" -eq 0 ]; then
    echo "=== native Plan Mode test PASSED ==="
else
    echo "=== native Plan Mode test FAILED (log: $LOG_FILE) ==="
    exit 1
fi
