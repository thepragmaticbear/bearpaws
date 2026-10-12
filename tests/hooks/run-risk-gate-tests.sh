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
  local mode="$1" json="$2" rc=0; shift 2
  printf '%s' "$json" | env -u COPILOT_CLI -u CURSOR_PLUGIN_ROOT -u DEVIN_PROJECT_DIR \
    -u DEVIN_PLUGIN_ROOT -u BEARPAWS_ENFORCE \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" CLAUDE_PLUGIN_DATA="$TMP_ROOT/data" "$@" \
    bash "$GATE" "$mode" >"$TMP_ROOT/out" 2>"$TMP_ROOT/err" || rc=$?
  echo "$rc" >"$TMP_ROOT/rc"
}
reset() { gate reset "{\"session_id\":\"$SID\"}"; }
edit() { # <path> [VAR=value ...]
  local p="$1"; shift
  gate record "$(jq -cn --arg s "$SID" --arg p "$p" \
    '{session_id:$s,tool_name:"Edit",tool_input:{file_path:$p}}')" "$@"
}
editc() { # <cwd> <path>
  gate record "$(jq -cn --arg s "$SID" --arg c "$1" --arg p "$2" \
    '{session_id:$s,cwd:$c,tool_name:"Edit",tool_input:{file_path:$p}}')"
}
dispatch() { # <tool_name> <subagent_type> <description> [prompt]
  gate record "$(jq -cn --arg s "$SID" --arg t "$1" --arg st "$2" --arg d "$3" --arg p "${4:-}" \
    '{session_id:$s,tool_name:$t,tool_input:{subagent_type:$st,description:$d,prompt:$p}}')"
}
review() {
  gate record "$(jq -cn --arg s "$SID" \
    '{session_id:$s,tool_name:"Agent",tool_input:{subagent_type:"bp:code-reviewer",description:"Review authz fix",prompt:"Review the diff"}}')"
}
stop() { # <message> [stop_hook_active]
  gate stop "$(jq -cn --arg s "$SID" --arg m "$1" --argjson a "${2:-false}" \
    '{session_id:$s,hook_event_name:"Stop",stop_hook_active:$a,last_assistant_message:$m}')"
}
expect() { # <label> allow|block [reason substring]; a non-zero hook exit fails either way
  if [ "$(cat "$TMP_ROOT/rc")" != 0 ]; then
    fail "$1: hook exited $(cat "$TMP_ROOT/rc"), expected 0"
  elif [ "$2" = allow ]; then
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
reset; edit src/a.py; review; edit src/authz.py; stop "$ELEVATED"
expect "review between edits does not cover the last edit" block "independent review"
reset; edit "$(printf 'src/x.py\rreview')"
if grep -qv '^edit ' "$TMP_ROOT/data/risk-gate/$SID.log" || [ "$(grep -c "$(printf '\r')" "$TMP_ROOT/data/risk-gate/$SID.log")" != 0 ]; then
  fail "CR in path reached the log: $(od -c "$TMP_ROOT/data/risk-gate/$SID.log" | head -3)"
else
  echo "OK: CR in path is stripped from the log"
fi

# Only a reviewer subagent_type or a description that starts with "review" counts. Never the prompt.
reset; edit src/authz.py; dispatch Agent general-purpose "Implement Task 2" "Do the task. Self-review before reporting."; stop "$ELEVATED"
expect "implementer dispatch is not a review" block "independent review"
reset; edit src/authz.py; dispatch Task bp:code-reviewer "Review authz fix"; stop "$ELEVATED"
expect "review dispatched via Task counts" allow
for row in "yes|bp:code-reviewer|Implement Task 3" \
           "yes|bp:code-reviewer|Do the task" \
           "yes|pr-review-toolkit:code-reviewer|Do the task" \
           "no|preview-builder|Do the task" \
           "yes|general-purpose|Review spec compliance for Task 3" \
           "yes|general-purpose|Code review of authz fix" \
           "yes|general-purpose|Final review" \
           "yes|general-purpose|Reviewing task 2" \
           "yes|general-purpose|Security review of authz" \
           "yes|general-purpose|Final code review" \
           "yes|general-purpose|Independent code review" \
           "yes|general-purpose|Re-review Task 3" \
           "yes|general-purpose|Spec review for Task 3" \
           "no|general-purpose|Implement Task 2" \
           "no|general-purpose|Fix the issues the reviewer found" \
           "no|general-purpose|Fix reviewer findings" \
           "no|general-purpose|Fix review comments" \
           "no|general-purpose|Address review feedback" \
           "no|general-purpose|Apply review fixes" \
           "no|general-purpose|Handle review findings for Task 3" \
           "no|general-purpose|Skip review, just implement" \
           "no|general-purpose|Implement review queue" \
           "no|general-purpose|Respond to review" \
           "no|general-purpose|Code review fixes" \
           "no|general-purpose|Final review feedback for Task 3" \
           "no|general-purpose|Preview the page" \
           "no|general-purpose|Previewing the page" \
           "no|general-purpose|Reviewer follow-ups for Task 2"; do
  IFS='|' read -r want st desc <<<"$row"
  reset; edit src/authz.py; dispatch Agent "$st" "$desc" "Self-review before reporting"; stop "$ELEVATED"
  if [ "$want" = yes ]; then expect "matcher: '$st' / '$desc' counts" allow
  else expect "matcher: '$st' / '$desc' does not count" block "independent review"; fi
done

# A missing or non-string last_assistant_message fails open.
reset; edit src/authz.py; gate stop "$(jq -cn --arg s "$SID" '{session_id:$s,hook_event_name:"Stop"}')"
expect "missing last_assistant_message: allow" allow
reset; edit src/authz.py; gate stop "$(jq -cn --arg s "$SID" '{session_id:$s,last_assistant_message:42}')"
expect "non-string last_assistant_message: allow" allow

# Paths are logged relative to cwd, so a sensitive-looking project dir does not nudge.
CWD=/Users/maclean/repos/oauth-proxy
reset; editc "$CWD" "$CWD/src/ui/button.py"; stop "$ROUTINE"; expect "sensitive project dir, routine path: allow" allow
reset; editc "$CWD" "$CWD/src/auth/login.py"; stop "$ROUTINE"; expect "sensitive path under cwd still nudges" block "src/auth/login.py"
if jq -e '.reason | contains("/Users/")' "$TMP_ROOT/out" >/dev/null; then
  fail "nudge reason leaks the absolute path: $(cat "$TMP_ROOT/out")"
else
  echo "OK: nudge reason shows the relative path"
fi

# INCOMPLETE must be the Status value, not a word elsewhere on the line.
reset; edit src/authz.py; stop "${ELEVATED/Status: COMPLETE/Status: COMPLETE | INCOMPLETE}"
expect "template line 'COMPLETE | INCOMPLETE': block" block "independent review"
reset; edit src/authz.py; stop "${ELEVATED/Status: COMPLETE/Status: COMPLETE (nothing left INCOMPLETE)}"
expect "'COMPLETE (nothing left INCOMPLETE)': block" block "independent review"
reset; edit src/authz.py; stop "${ELEVATED/Status: COMPLETE/**Status:** INCOMPLETE}"
expect "markdown-bold '**Status:** INCOMPLETE': allow" allow
reset; edit src/authz.py; stop "${ELEVATED_INCOMPLETE//$'\n'/$'\r\n'}"$'\r'
expect "CRLF message ending 'Status: INCOMPLETE': allow" allow

# Only the last Status line decides.
QUOTED=$'The reviewer said:\n> Status: INCOMPLETE\n\n'
reset; edit src/authz.py; stop "$QUOTED$ELEVATED"; expect "quoted INCOMPLETE then final COMPLETE: block" block "independent review"
reset; edit src/authz.py; stop $'> Status: COMPLETE\n\n'"$ELEVATED_INCOMPLETE"; expect "quoted COMPLETE then final INCOMPLETE: allow" allow

# Receipt line variants: heading, list item, code span.
for r in '## Risk: routine' '1. Risk: routine' '`Risk: routine`'; do
  reset; edit src/ui/button.py
  stop "$(printf 'Done.\n\n%s\nVerified: pytest — 3 passed\nStatus: COMPLETE' "$r")"
  expect "receipt variant '$r': allow" allow
done

# Every edit tool is recorded.
reset; gate record "$(jq -cn --arg s "$SID" '{session_id:$s,tool_name:"MultiEdit",tool_input:{file_path:"src/app.py"}}')"
stop "Done."; expect "MultiEdit is recorded as an edit" block "risk receipt"
reset; gate record "$(jq -cn --arg s "$SID" '{session_id:$s,tool_name:"NotebookEdit",tool_input:{notebook_path:"nb/a.ipynb"}}')"
stop "Done."; expect "NotebookEdit notebook_path is recorded as an edit" block "risk receipt"

# Subagent edits carry agent_id and still count.
reset
gate record "$(jq -cn --arg s "$SID" '{session_id:$s,agent_id:"a1",agent_type:"general-purpose",tool_name:"Write",tool_input:{file_path:"src/app.py"}}')"
stop "Done."; expect "subagent edit counts" block "risk receipt"

# Malformed session_id: no decision, nothing written outside the data dir.
for bad in "../evil" "a/b" "" "$(printf 'x%.0s' {1..129})"; do
  printf '%s' "$(jq -cn --arg s "$bad" '{session_id:$s,tool_name:"Edit",tool_input:{file_path:"src/app.py"}}')" \
    | env -u COPILOT_CLI -u CURSOR_PLUGIN_ROOT -u DEVIN_PROJECT_DIR -u DEVIN_PLUGIN_ROOT -u BEARPAWS_ENFORCE \
      CLAUDE_PLUGIN_ROOT="$REPO_ROOT" CLAUDE_PLUGIN_DATA="$TMP_ROOT/bad/data" bash "$GATE" record >"$TMP_ROOT/out" 2>&1 || fail "bad session_id '$bad': non-zero exit"
done
if [ -e "$TMP_ROOT/bad/evil.log" ] || [ -n "$(find "$TMP_ROOT/bad" -type f 2>/dev/null)" ]; then
  fail "malformed session_id wrote a file"
else
  echo "OK: malformed session_id writes nothing"
fi

# A symlinked log is refused: nothing is written through it.
mkdir -p "$TMP_ROOT/sym/data/risk-gate"
ln -s "$TMP_ROOT/sym/target" "$TMP_ROOT/sym/data/risk-gate/$SID.log"
edit src/app.py "CLAUDE_PLUGIN_DATA=$TMP_ROOT/sym/data"
if [ "$(cat "$TMP_ROOT/rc")" != 0 ]; then
  fail "symlinked log: hook exited $(cat "$TMP_ROOT/rc"), expected 0"
elif [ -s "$TMP_ROOT/sym/target" ]; then
  fail "symlinked log: hook wrote through the symlink"
else
  echo "OK: symlinked log is refused"
fi

# A symlinked log dir is refused too.
mkdir -p "$TMP_ROOT/symdir/data" "$TMP_ROOT/symdir/target"
ln -s "$TMP_ROOT/symdir/target" "$TMP_ROOT/symdir/data/risk-gate"
edit src/app.py "CLAUDE_PLUGIN_DATA=$TMP_ROOT/symdir/data"
if [ "$(cat "$TMP_ROOT/rc")" != 0 ]; then
  fail "symlinked log dir: hook exited $(cat "$TMP_ROOT/rc"), expected 0"
elif [ -n "$(find "$TMP_ROOT/symdir/target" -type f)" ]; then
  fail "symlinked log dir: hook wrote through the symlink"
else
  echo "OK: symlinked log dir is refused"
fi

# The log dir is owner-only. (A dir owned by someone else cannot be simulated without root.)
rm -rf "$TMP_ROOT/data"; reset
case "$(ls -ld "$TMP_ROOT/data/risk-gate")" in
  drwx------*) echo "OK: log dir is mode 700" ;;
  *) fail "log dir is not mode 700: $(ls -ld "$TMP_ROOT/data/risk-gate")" ;;
esac

# Opt-out and other harnesses: always allow.
reset; edit src/app.py; stop "Done."; expect "edited log blocks without an opt-out" block "risk receipt"
DONE_JSON="$(jq -cn --arg s "$SID" '{session_id:$s,last_assistant_message:"Done."}')"
gate stop "$DONE_JSON" BEARPAWS_ENFORCE=0; expect "BEARPAWS_ENFORCE=0: allow" allow
for v in COPILOT_CLI CURSOR_PLUGIN_ROOT DEVIN_PROJECT_DIR DEVIN_PLUGIN_ROOT; do
  gate stop "$DONE_JSON" "$v=1"; expect "$v set: allow" allow
done
# Valid session and an edited log, so only the missing CLAUDE_PLUGIN_ROOT can explain the allow.
rc=0; printf '%s' "$DONE_JSON" | env -u CLAUDE_PLUGIN_ROOT -u COPILOT_CLI -u CURSOR_PLUGIN_ROOT -u DEVIN_PROJECT_DIR \
  -u DEVIN_PLUGIN_ROOT -u BEARPAWS_ENFORCE CLAUDE_PLUGIN_DATA="$TMP_ROOT/data" bash "$GATE" stop >"$TMP_ROOT/out" 2>&1 || rc=$?; echo "$rc" >"$TMP_ROOT/rc"
expect "no CLAUDE_PLUGIN_ROOT: allow" allow

# Missing jq: allow, and say why on stderr.
mkdir -p "$TMP_ROOT/nojq"
if printf '{}' | env -u COPILOT_CLI -u CURSOR_PLUGIN_ROOT -u DEVIN_PROJECT_DIR -u DEVIN_PLUGIN_ROOT -u BEARPAWS_ENFORCE \
     PATH="$TMP_ROOT/nojq" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$BASH" "$GATE" stop >"$TMP_ROOT/out" 2>"$TMP_ROOT/err" \
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
