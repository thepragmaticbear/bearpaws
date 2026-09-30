#!/usr/bin/env bash
# Codex adapter conformance smoke. Promotion to Primary needs every check to pass.
# Usage: tests/codex/run-conformance.sh [out-dir]
# Exit: 0 all pass, 1 a check failed, 2 blocked (Codex errored before answering).
# Uses repo-level discovery (.agents/skills with per-skill links) in a throwaway repo,
# so nothing is installed into ~/.agents. Costs a few Codex requests.
#   C1 discovery        skills are listed
#   C2 explicit load    $skill loads the real skill body
#   C3 auto-trigger     a naive debugging prompt reads systematic-debugging
#   C4 risk gate        a security fix loads the review skill (the elevated-risk rule acted on)
# The repos carry the documented bootstrap line in AGENTS.md (the same line a user adds to
# ~/.codex/AGENTS.md). NO_BOOTSTRAP=1 omits it, for a RED comparison.
# GLOBAL=1 tests the installed path instead: no repo-level skills or AGENTS.md; requires
# ./install.sh --agents --global and the bootstrap line in ~/.codex/AGENTS.md.
BOOTSTRAP_LINE='Before responding to any request, read `.agents/skills/using-bearpaws/SKILL.md` and follow it.' 
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
out="${1:-/tmp/bearpaws-tests/codex/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"

mkrepo() {
  local dir="$1"
  mkdir -p "$dir"
  if [ "${GLOBAL:-0}" != 1 ]; then
    mkdir -p "$dir/.agents/skills"
    for s in "$ROOT"/skills/*/; do ln -s "${s%/}" "$dir/.agents/skills/$(basename "$s")"; done
    [ "${NO_BOOTSTRAP:-0}" = 1 ] || printf '%s\n' "$BOOTSTRAP_LINE" > "$dir/AGENTS.md"
  fi
  (cd "$dir" && git init -q && git add -A && git -c user.name=t -c user.email=t@example.com commit -qm init --allow-empty)
}
run_codex() { # dir sandbox prompt outfile [timeout]; exits 2 if Codex itself fails (usage limit, auth, outage)
  # Portable timeout (macOS has no `timeout`): perl alarm kills a hung Codex (e.g. dropped stream).
  # The security task can run several review rounds, so C4 passes a longer limit.
  local limit="${5:-${CODEX_TIMEOUT:-600}}"
  perl -e 'alarm shift; exec @ARGV' "$limit" \
    codex exec --json --ephemeral --skip-git-repo-check -s "$2" -C "$1" "$3" < /dev/null > "$4" 2>/dev/null
  local rc=$?
  TIMED_OUT=0
  if [ "$rc" -eq 142 ]; then
    TIMED_OUT=1
    echo "  note: Codex still running after ${limit}s; scoring the transcript so far"
    if ! grep -q '"type":"item.completed"' "$4"; then
      echo "BLOCKED: no completed work before the time limit ($(grep -o 'Reconnecting[^"]*' "$4" | tail -1))"
      exit 2
    fi
  fi
  if grep -q '"type":"turn.failed"' "$4"; then
    echo "BLOCKED: Codex turn failed, not a conformance result:"
    grep -o '"message":"[^"]*"' "$4" | head -1
    exit 2
  fi
}
final_text() { python3 -c '
import json,sys
t=""
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except: continue
    it=e.get("item") or {}
    if it.get("type")=="agent_message": t=it.get("text","")
print(t)' "$1"; }
read_skill() { grep -c "skills/$2/SKILL.md" "$1" || true; }

pass=0; fail=0
check() { if [ "$2" = ok ]; then echo "  [PASS] $1"; pass=$((pass+1)); else echo "  [FAIL] $1 — $3"; fail=$((fail+1)); fi; }

w="$out/c1"; mkrepo "$w"
run_codex "$w" read-only "List the names of every skill available to you, comma-separated, nothing else." "$out/c1.jsonl"
n=$(final_text "$out/c1.jsonl" | grep -oE "onboarding-to-a-project|brainstorming|writing-plans|executing-plans|subagent-driven-development|test-driven-development|systematic-debugging|requesting-code-review|receiving-code-review|verification-before-completion|finishing-a-development-branch|using-git-worktrees|dispatching-parallel-agents|writing-skills|using-bearpaws" | sort -u | wc -l | tr -d ' ')
[ "$n" -ge 15 ] && check "C1 discovery (15/15 listed)" ok || check "C1 discovery" fail "$n/15 listed"

w="$out/c2"; mkrepo "$w"
run_codex "$w" read-only "\$verification-before-completion What is the first step of this skill's process? Answer with the step's bold name only." "$out/c2.jsonl"
final_text "$out/c2.jsonl" | grep -q "IDENTIFY" && check "C2 explicit load" ok || check "C2 explicit load" fail "$(final_text "$out/c2.jsonl" | head -c 120)"

w="$out/c3"; mkrepo "$w"
run_codex "$w" read-only "My test suite started failing after yesterday's merge with 'KeyError: user_id' in the session code. Help me figure out why. Don't change files yet; tell me your first steps." "$out/c3.jsonl"
[ "$(read_skill "$out/c3.jsonl" systematic-debugging)" -gt 0 ] && check "C3 auto-trigger (read systematic-debugging)" ok || check "C3 auto-trigger" fail "did not read systematic-debugging"

w="$out/c4"; cp -R "$ROOT/tests/benchmark/scenarios/security-fix/repo" "$w"; mkrepo "$w"
run_codex "$w" workspace-write "$(cat "$ROOT/tests/benchmark/scenarios/security-fix/prompt.txt") You are running non-interactively; make reasonable decisions and finish." "$out/c4.jsonl" "${CODEX_C4_TIMEOUT:-2400}"
[ "$(read_skill "$out/c4.jsonl" requesting-code-review)" -gt 0 ] && check "C4 risk gate (loaded requesting-code-review)" ok || check "C4 risk gate" fail "review skill not loaded for a security fix (bootstrap read: $(read_skill "$out/c4.jsonl" using-bearpaws))"

echo "Codex conformance: $pass passed, $fail failed (transcripts: $out)"
[ "$fail" -eq 0 ]
