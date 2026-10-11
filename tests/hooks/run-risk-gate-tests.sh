#!/usr/bin/env bash
# Risk gate tests. No agent CLI needed: each case feeds hook-input JSON on stdin
# to hooks/risk-gate and checks the decision it prints. An empty stdout means allow.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATE="$REPO_ROOT/hooks/risk-gate"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
failures=0
SID=test-session

fail() { echo "FAIL: $1"; failures=$((failures + 1)); }

# gate <mode> <json> [VAR=value ...]: run under a clean Claude Code environment.
gate() {
  local mode="$1" json="$2"; shift 2
  printf '%s' "$json" | env -u COPILOT_CLI -u CURSOR_PLUGIN_ROOT -u DEVIN_PROJECT_DIR \
    -u DEVIN_PLUGIN_ROOT -u BEARPAWS_ENFORCE \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" CLAUDE_PLUGIN_DATA="$TMP_ROOT/data" "$@" \
    bash "$GATE" "$mode" >"$TMP_ROOT/out" 2>"$TMP_ROOT/err" || true
}
reset() { gate reset "{\"session_id\":\"$SID\"}"; }
edit() {
  gate record "$(jq -cn --arg s "$SID" --arg p "$1" \
    '{session_id:$s,tool_name:"Edit",tool_input:{file_path:$p}}')"
}
review() {
  gate record "$(jq -cn --arg s "$SID" \
    '{session_id:$s,tool_name:"Agent",tool_input:{subagent_type:"bp:code-reviewer",description:"Review authz fix",prompt:"Review the diff"}}')"
}
stop() { # <message> [stop_hook_active]
  gate stop "$(jq -cn --arg s "$SID" --arg m "$1" --argjson a "${2:-false}" \
    '{session_id:$s,hook_event_name:"Stop",stop_hook_active:$a,last_assistant_message:$m}')"
}
expect() { # <label> allow|block [reason substring]
  if [ "$2" = allow ]; then
    if [ -s "$TMP_ROOT/out" ]; then fail "$1: expected allow, got $(cat "$TMP_ROOT/out")"; else echo "OK: $1"; fi
  elif jq -e --arg s "${3:-}" '.decision == "block" and (.reason | contains($s))' "$TMP_ROOT/out" >/dev/null 2>&1; then
    echo "OK: $1"
  else
    fail "$1: expected block containing '${3:-}', got '$(cat "$TMP_ROOT/out")'"
  fi
}

ROUTINE=$'Done.\n\nRisk: routine\nVerified: pytest — 12 passed\nStatus: COMPLETE'
ELEVATED=$'Fixed.\n\nRisk: elevated (authorization)\nPinned: test_owner_allowed passed before edit\nFailing first: test_cross_org_denied failed, then passed\nReview: bp:code-reviewer — Ready to merge: Yes\nAssumptions: org_id is never null\nVerified: pytest — 14 passed\nStatus: COMPLETE'
ELEVATED_INCOMPLETE="${ELEVATED/Status: COMPLETE/Status: INCOMPLETE}"

reset; stop "The answer is 42."; expect "no edits: allow" allow
reset; edit src/app.py; stop "Done, looks good."; expect "edit without receipt: block" block "risk receipt"
reset; edit src/ui/button.py; stop "$ROUTINE"; expect "routine receipt: allow" allow
reset; edit src/ui/button.py; stop $'Done.\n\n**Risk:** routine\n**Verified:** pytest — 3 passed\n**Status:** COMPLETE'
expect "markdown-bold receipt: allow" allow
reset; edit src/authz.py; stop "$ELEVATED"; expect "elevated without review: block" block "independent review"
reset; review; edit src/authz.py; stop "$ELEVATED"; expect "review before last edit does not count" block "independent review"
reset; edit src/authz.py; review; stop "$ELEVATED"; expect "elevated with review after edit: allow" allow
reset; edit src/authz.py; stop "$ELEVATED_INCOMPLETE"; expect "elevated INCOMPLETE without review: allow" allow
reset; edit src/authz.py; stop "$ELEVATED"; stop "$ELEVATED" true
expect "repeat stop while unmet still blocks" block "independent review"
reset; edit src/auth/login.py; stop "$ROUTINE"; expect "routine on sensitive path: nudge" block "look elevated-risk"
stop "$ROUTINE" true; expect "second routine stop after nudge: allow" allow
reset; edit src/app.py; reset; stop "Answer only."; expect "reset clears the previous turn" allow
reset; edit "$(printf 'src/x.py\nreview')"; stop "$ELEVATED"
expect "newline in path cannot forge a review" block "independent review"

# Subagent edits carry agent_id and still count.
reset
gate record "$(jq -cn --arg s "$SID" '{session_id:$s,agent_id:"a1",agent_type:"general-purpose",tool_name:"Write",tool_input:{file_path:"src/app.py"}}')"
stop "Done."; expect "subagent edit counts" block "risk receipt"

# Malformed session_id: no decision, nothing written outside the data dir.
for bad in "../evil" "a/b" "" "$(printf 'x%.0s' {1..129})"; do
  printf '%s' "$(jq -cn --arg s "$bad" '{session_id:$s,tool_name:"Edit",tool_input:{file_path:"src/app.py"}}')" \
    | env CLAUDE_PLUGIN_ROOT="$REPO_ROOT" CLAUDE_PLUGIN_DATA="$TMP_ROOT/bad/data" bash "$GATE" record >"$TMP_ROOT/out" 2>&1 || fail "bad session_id '$bad': non-zero exit"
done
if [ -e "$TMP_ROOT/bad/evil.log" ] || [ -n "$(find "$TMP_ROOT/bad" -type f 2>/dev/null)" ]; then
  fail "malformed session_id wrote a file"
else
  echo "OK: malformed session_id writes nothing"
fi

# Opt-out and other harnesses: always allow.
reset; edit src/app.py; stop "Done." false
gate stop "$(jq -cn --arg s "$SID" '{session_id:$s,last_assistant_message:"Done."}')" BEARPAWS_ENFORCE=0
expect "BEARPAWS_ENFORCE=0: allow" allow
gate stop "$(jq -cn --arg s "$SID" '{session_id:$s,last_assistant_message:"Done."}')" COPILOT_CLI=1
expect "Copilot CLI env: allow" allow
printf '{}' | env -u CLAUDE_PLUGIN_ROOT bash "$GATE" stop >"$TMP_ROOT/out" 2>&1
expect "no CLAUDE_PLUGIN_ROOT: allow" allow

# Missing jq: allow, and say why on stderr.
mkdir -p "$TMP_ROOT/nojq"
if printf '{}' | env PATH="$TMP_ROOT/nojq" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$BASH" "$GATE" stop >"$TMP_ROOT/out" 2>"$TMP_ROOT/err" \
   && [ ! -s "$TMP_ROOT/out" ] && grep -q "jq not found" "$TMP_ROOT/err"; then
  echo "OK: missing jq allows with a stderr note"
else
  fail "missing jq: expected exit 0, empty stdout, stderr note"
fi

if [ "$failures" -ne 0 ]; then
  echo "$failures risk-gate test(s) failed"
  exit 1
fi
echo "ALL RISK-GATE TESTS PASSED"
