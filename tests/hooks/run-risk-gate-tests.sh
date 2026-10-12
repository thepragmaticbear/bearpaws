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
reset() { rm -f "$TMP_ROOT/data/risk-gate/$SID.log" "$TMP_ROOT/data/risk-gate/$SID".*.tree; }
logfile() { echo "$TMP_ROOT/data/risk-gate/$SID.log"; }
# The state file is per repo: <session>.<first 12 hex of sha1(toplevel)>.tree. treefile: the first one that exists.
treefile() { local f; for f in "$TMP_ROOT/data/risk-gate/$SID".*.tree; do [ -e "$f" ] && { echo "$f"; return; }; done; echo "$TMP_ROOT/data/risk-gate/$SID.none.tree"; }
treefor() { echo "$TMP_ROOT/data/risk-gate/$SID.$(printf '%s' "$(git -C "$1" rev-parse --show-toplevel)" | shasum | cut -c1-12).tree"; }
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
  elif jq -se --arg s "${3:-}" 'length == 1 and (.[0] | (has("decision") | not) and (keys == ["hookSpecificOutput"]) and .hookSpecificOutput.hookEventName == "Stop" and (.hookSpecificOutput.additionalContext | contains($s)))' "$TMP_ROOT/out" >/dev/null 2>&1; then
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
if jq -e '.hookSpecificOutput.additionalContext | contains("/Users/")' "$TMP_ROOT/out" >/dev/null; then
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
reset; edit src/authz.py; stop "${ELEVATED/Status: COMPLETE/Status: \`INCOMPLETE\`}"
expect "backticked 'Status: \`INCOMPLETE\`': allow" allow
reset; edit src/authz.py; stop "${ELEVATED/Status: COMPLETE/Status: \`COMPLETE\`}"
expect "backticked 'Status: \`COMPLETE\`': block" block "independent review"

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
rm -rf "$TMP_ROOT/data"; edit src/app.py
case "$(ls -ld "$TMP_ROOT/data/risk-gate")" in
  drwx------*) echo "OK: log dir is mode 700" ;;
  *) fail "log dir is not mode 700: $(ls -ld "$TMP_ROOT/data/risk-gate")" ;;
esac

# Edits stay pending until a receipt accepts them, across turns and background-agent report-backs.
reset; edit src/app.py; stop "dispatched"; expect "background gap: unrelated reply with pending edit needs a receipt" block "risk receipt"
stop "$ROUTINE"; expect "background gap: routine receipt accepts" allow
if [ -e "$(logfile)" ]; then fail "accepted stop left the log"; else echo "OK: accepted stop removes the log"; fi
stop "The answer is 42."; expect "background gap: nothing pending after acceptance" allow
reset; edit src/authz.py; stop "$ELEVATED"; expect "report-back: elevated COMPLETE without review blocks" block "independent review"
stop "$ELEVATED"; expect "report-back: elevated work stays pending across turns" block "independent review"
reset; edit src/authz.py; stop "$ELEVATED_INCOMPLETE"; expect "elevated INCOMPLETE unreviewed: allow" allow
if grep -qx 'edit src/authz.py' "$(logfile)" 2>/dev/null; then echo "OK: elevated INCOMPLETE unreviewed keeps the log"; else fail "elevated INCOMPLETE unreviewed cleared the log"; fi
stop "$ELEVATED"; expect "later COMPLETE still needs a review" block "independent review"
review; stop "$ELEVATED"; expect "later COMPLETE after review: allow" allow
if [ -e "$(logfile)" ]; then fail "reviewed COMPLETE left the log"; else echo "OK: reviewed COMPLETE removes the log"; fi
reset; edit src/authz.py; review; stop "$ELEVATED_INCOMPLETE"; expect "elevated INCOMPLETE reviewed: allow" allow
if [ -e "$(logfile)" ]; then fail "elevated INCOMPLETE reviewed left the log"; else echo "OK: elevated INCOMPLETE reviewed removes the log"; fi
reset; edit src/auth/login.py; stop "$ROUTINE"; stop "$ROUTINE" true; expect "nudged routine second stop: allow" allow
if [ -e "$(logfile)" ]; then fail "nudged second stop left the log"; else echo "OK: nudged second stop removes the log"; fi
reset; edit src/app.py; gate stop "$(jq -cn --arg s "$SID" '{session_id:$s,hook_event_name:"Stop"}')"
expect "missing message: allow" allow
if [ -e "$(logfile)" ]; then echo "OK: missing message keeps the log"; else fail "missing message cleared the log"; fi
reset; edit src/app.py; stop "Done."; expect "block keeps the log" block "risk receipt"
if [ -e "$(logfile)" ]; then echo "OK: block keeps the log"; else fail "block cleared the log"; fi

# M-1: a backticked Risk value is accepted, like the Status value.
reset; edit src/ui/button.py; stop $'Done.\n\nRisk: `routine`\nVerified: pytest — 3 passed\nStatus: COMPLETE'
expect "backticked Risk value: allow" allow
# M-2: the missing-receipt reason names the allowed values.
reset; edit src/app.py; stop "Done."; expect "reason names Risk: routine" block "Risk: routine or Risk: elevated (surface)"
reset; edit src/app.py; stop "Done."; expect "reason says edits are pending" block "Edits are pending without a risk receipt."
reset; edit src/app.py; stop "Done."
if grep -q "This turn" "$TMP_ROOT/out"; then fail "block reason still says This turn"; else echo "OK: block reason has no This turn"; fi
# M-3: Claude's own config, memory, and plan files are not edits.
reset; edit "$HOME/.claude/projects/x/memory/prefs.md"; stop "Saved."; expect "write under ~/.claude is not an edit" allow
H="$TMP_ROOT/home"
reset; edit "$H/.claude/projects/x/memory/m.md" HOME="$H"; stop "Saved."; expect "temp HOME: write under ~/.claude is not an edit" allow
reset; edit "$H/.claude.json" HOME="$H"; stop "Saved."; expect "temp HOME: ~/.claude.json is not an edit" allow
reset; edit "$H/.claude-work/app/src/billing.py" HOME="$H"; stop "Done."; expect "~/.claude-work project is an edit" block "risk receipt"
reset; edit "$H/.clauderc-project/main.py" HOME="$H"; stop "Done."; expect "~/.clauderc-project project is an edit" block "risk receipt"
reset; edit "$H/.claude-team/projects/x/m.md" HOME="$H" CLAUDE_CONFIG_DIR="$H/.claude-team"; stop "Saved."; expect "~/.claude-team with CLAUDE_CONFIG_DIR is not an edit" allow
reset; edit "$H/.claude-team/projects/x/m.md" HOME="$H"; stop "Done."; expect "~/.claude-team without CLAUDE_CONFIG_DIR is an edit" block "risk receipt"
reset; edit "/cfg/dir/plans/p.md" CLAUDE_CONFIG_DIR=/cfg/dir; stop "Saved."; expect "write under CLAUDE_CONFIG_DIR is not an edit" allow
reset; edit "$HOME/notes/.claude.md"; stop "Saved."; expect "other path under HOME is still an edit" block "risk receipt"
reset; edit "/cfg/dirx/a.md" CLAUDE_CONFIG_DIR=/cfg/dir; stop "Saved."; expect "CLAUDE_CONFIG_DIR prefix needs the slash" block "risk receipt"

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

# Bash edits: a per-repo git tree fingerprint, compared with the one stored in <session>.<repo>.tree.
mkrepo() { # <name> [--empty]: temp git repo (one commit unless --empty); prints its path
  local r="$TMP_ROOT/repo-$1"; mkdir -p "$r"
  git -C "$r" init -q && git -C "$r" config user.email t@t && git -C "$r" config user.name t
  [ "${2:-}" = --empty ] || { echo one >"$r/a.py"; git -C "$r" add a.py && git -C "$r" commit -qm init; }
  echo "$r"
}
bashc() { # <cwd>
  gate record "$(jq -cn --arg s "$SID" --arg c "$1" \
    '{session_id:$s,cwd:$c,tool_name:"Bash",tool_input:{command:"x"}}')"
}
prec() { # <cwd>: PreToolUse Bash, handled by `baseline` mode
  gate baseline "$(jq -cn --arg s "$SID" --arg c "$1" \
    '{session_id:$s,cwd:$c,hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:"x"}}')"
}
nbash() { [ -f "$(logfile)" ] || { echo 0; return; }; grep -cxF 'edit (bash)' "$(logfile)" || true; }
expect_bash_edits() { # <label> <count>
  if [ "$(nbash)" = "$2" ]; then echo "OK: $1"; else fail "$1: expected $2 'edit (bash)' line(s), got $(nbash): $(cat "$(logfile)" 2>/dev/null)"; fi
}

R="$(mkrepo 1)"
reset; bashc "$R"; expect "bash baseline: allow" allow; expect_bash_edits "first Bash call is a baseline, not an edit" 0
[ -s "$(treefile)" ] && echo "OK: baseline stores the fingerprint in the .tree file" || fail "baseline wrote no .tree file"
grep -q '^tree ' "$(logfile)" 2>/dev/null && fail "tree line leaked into the log" || echo "OK: log holds no tree lines"
cat >"$R/new.py" <<'EOT'
print("written by heredoc")
EOT
bashc "$R"; expect_bash_edits "Bash heredoc write is an edit" 1
stop "Done."; expect "Bash edit without receipt: block" block "risk receipt"
bashc "$R"; expect_bash_edits "unchanged tree adds no second edit" 1
reset; bashc "$R"; stop "Done."; expect "tree lines alone are not edits: allow" allow

R="$(mkrepo 2)"
reset; bashc "$R"
mkdir -p "$R/__pycache__" "$R/.pytest_cache" "$R/node_modules/p" "$R/.venv/lib" "$R/pkg/__pycache__"
echo x >"$R/__pycache__/x.pyc"; echo x >"$R/.pytest_cache/v"; echo x >"$R/node_modules/p/i.js"
echo x >"$R/.venv/lib/z"; echo x >"$R/pkg/__pycache__/y.cpython.pyc"; echo x >"$R/stray.pyc"
bashc "$R"; expect_bash_edits "cache dirs and .pyc are not edits" 0
echo real >"$R/real.py"; bashc "$R"; expect_bash_edits "a real new file next to caches is an edit" 1

R="$(mkrepo 3)"
reset; echo two >"$R/a.py"; editc "$R" a.py; review; bashc "$R"
stop "$ELEVATED"; expect "Edit, review, Bash with no change (pytest): allow" allow

R="$(mkrepo 4)"
reset; echo two >"$R/a.py"; editc "$R" a.py; review; echo fixed >"$R/a.py"; bashc "$R"
stop "$ELEVATED"; expect "Edit, review, Bash sed -i, COMPLETE: block" block "independent review"
review; stop "$ELEVATED"; expect "re-review after the Bash fix: allow" allow

R="$(mkrepo 4b)"
reset; echo two >"$R/a.py"; editc "$R" a.py
[ -s "$(treefile)" ] && echo "OK: Edit refreshes the .tree file" || fail "Edit did not write the .tree file"
bashc "$R"; expect_bash_edits "Bash right after Edit: tree already fresh, no edit" 0

R="$(mkrepo 4c)"
reset; bashc "$R"; echo y >"$R/n.py"; bashc "$R"; stop "$ROUTINE"; expect "'edit (bash)' with a routine receipt: no nudge" allow

PLAIN="$TMP_ROOT/plain"; mkdir -p "$PLAIN"
reset; bashc "$PLAIN"; echo x >"$PLAIN/f"; bashc "$PLAIN"
expect "non-git cwd: rc 0, no output" allow; expect_bash_edits "non-git cwd never records edit (bash)" 0
[ -e "$(logfile)" ] || [ -e "$(treefile)" ] && fail "non-git cwd wrote state" || echo "OK: non-git cwd writes no state"

R="$(mkrepo 6)"
reset; bashc "$R"; rm -rf "$R"; bashc "$R"
expect "cwd removed between calls: rc 0, no output" allow; expect_bash_edits "cwd removed: no edit" 0
R="$(mkrepo 6b)"
reset; bashc "$R"; echo garbage >"$R/.git/HEAD"; echo y >"$R/n.py"; bashc "$R"
expect "corrupted .git: rc 0, no output" allow; expect_bash_edits "corrupted .git: no edit" 0

R="$(mkrepo 7 --empty)"
reset; bashc "$R"; expect_bash_edits "no-commit repo: baseline is not an edit" 0
echo x >"$R/f.py"; bashc "$R"; expect_bash_edits "no-commit repo: new file is an edit" 1
git -C "$R" add f.py; bashc "$R"; expect_bash_edits "no-commit repo: git add is not an edit" 1
bashc "$R"; expect_bash_edits "no-commit repo: unchanged adds nothing" 1

R="$(mkrepo 8)"
printf 'aaaa' >"$R/u.txt"; reset; bashc "$R"
printf 'bbbb' >"$R/u.txt"; touch -t 203001010000 "$R/u.txt"; bashc "$R"
expect_bash_edits "untracked same-size change with a new mtime is an edit" 1
# Known limit: untracked content is not hashed, only size and mtime, so a same-size change in the same second is missed.
touch -t 203001010001 "$R/u.txt"; bashc "$R"; n=$(nbash)
printf 'cccc' >"$R/u.txt"; touch -t 203001010001 "$R/u.txt"; bashc "$R"
expect_bash_edits "known limit: same-size, same-mtime untracked change is missed" "$n"

# Index- and HEAD-independent fingerprint: git add / git commit are not edits; content, size-preserving and delete edits are.
R="$(mkrepo 10)"
reset; bashc "$R"; echo n >"$R/new.py"; bashc "$R"; git -C "$R" add -A; bashc "$R"
expect_bash_edits "Bash git add -A after an edit adds no edit" 1
R="$(mkrepo 11)"
reset; echo two >"$R/a.py"; editc "$R" a.py; git -C "$R" add -A; bashc "$R"
expect_bash_edits "Edit then Bash git add -A: no edit (bash)" 0
R="$(mkrepo 12)"
reset; echo two >"$R/a.py"; editc "$R" a.py; review; git -C "$R" commit -qam x; bashc "$R"
stop "$ELEVATED"; expect "Edit, review, Bash git commit -am, COMPLETE: allow" allow
R="$(mkrepo 13)"
reset; bashc "$R"; echo two >"$R/a.py"; bashc "$R"
expect_bash_edits "same-size rewrite of a tracked file is detected via mtime" 1
R="$(mkrepo 14)"
reset; bashc "$R"; rm "$R/a.py"; bashc "$R"
expect_bash_edits "deleting a tracked file is an edit" 1

# The fingerprint survives an accepted stop (which removes the log), so the next turn's first Bash call is not just a baseline.
R="$(mkrepo 15)"
reset; echo two >"$R/a.py"; editc "$R" a.py; stop "$ROUTINE"; expect "gap: routine receipt accepts" allow
[ -e "$(logfile)" ] && fail "gap: accepted stop left the log" || echo "OK: gap: accepted stop removed the log"
[ -s "$(treefile)" ] && echo "OK: accepted stop keeps the .tree file" || fail "accepted stop removed the .tree file"
echo heredoc >"$R/b.py"; bashc "$R"; expect_bash_edits "gap: first Bash call of the next turn detects the edit" 1
stop "Done."; expect "gap: Bash edit in a later turn needs a receipt" block "risk receipt"

# The .tree file gets the same no-symlink treatment as the log: the planted link survives, still points at its
# original target, and the target is untouched. (Without the guard, mv -f would replace the link with a file.)
R="$(mkrepo 16)"
mkdir -p "$TMP_ROOT/symtree/data/risk-gate"
echo original >"$TMP_ROOT/symtree/target"
SYMTREE="$TMP_ROOT/symtree/data/risk-gate/$(basename "$(treefor "$R")")"
ln -s "$TMP_ROOT/symtree/target" "$SYMTREE"
for m in baseline record; do
  if [ $m = baseline ]; then gate baseline "$(jq -cn --arg s "$SID" --arg c "$R" '{session_id:$s,cwd:$c,tool_name:"Bash"}')" "CLAUDE_PLUGIN_DATA=$TMP_ROOT/symtree/data"
  else gate record "$(jq -cn --arg s "$SID" --arg c "$R" '{session_id:$s,cwd:$c,tool_name:"Bash",tool_input:{command:"x"}}')" "CLAUDE_PLUGIN_DATA=$TMP_ROOT/symtree/data"; fi
  if [ "$(cat "$TMP_ROOT/rc")" != 0 ]; then fail "symlinked .tree ($m): hook exited $(cat "$TMP_ROOT/rc")"
  elif [ ! -L "$SYMTREE" ] || [ "$(readlink "$SYMTREE")" != "$TMP_ROOT/symtree/target" ]; then fail "symlinked .tree ($m): the planted link was replaced"
  elif [ "$(cat "$TMP_ROOT/symtree/target")" != original ]; then fail "symlinked .tree ($m): hook wrote through the symlink"
  else echo "OK: symlinked .tree is refused ($m)"; fi
done

# PreToolUse `baseline`: take the fingerprint before the first Bash call, so a first-ever heredoc write is seen.
R="$(mkrepo 18)"
reset; prec "$R"; expect "baseline mode prints nothing" allow
[ -s "$(treefile)" ] && echo "OK: baseline writes the .tree file" || fail "baseline wrote no .tree file"
[ -e "$(logfile)" ] && fail "baseline wrote the log" || echo "OK: baseline does not touch the log"
echo heredoc >"$R/first.py"; bashc "$R"
expect_bash_edits "first-ever Bash call that writes a file is an edit" 1
stop "Done."; expect "first-call Bash heredoc without receipt: block" block "risk receipt"

R="$(mkrepo 19)"
reset; bashc "$R"; touch -t 200001010000 "$(treefile)"
before="$(cat "$(treefile)")|$(ls -lT "$(treefile)" 2>/dev/null || ls -l --time-style=full-iso "$(treefile)")"
echo changed >"$R/a.py"; prec "$R"
after="$(cat "$(treefile)")|$(ls -lT "$(treefile)" 2>/dev/null || ls -l --time-style=full-iso "$(treefile)")"
[ "$before" = "$after" ] && echo "OK: baseline leaves an existing .tree untouched" || fail "baseline rewrote an existing .tree"
bashc "$R"; expect_bash_edits "baseline did not absorb the edit: next record sees it" 1

PLAIN2="$TMP_ROOT/plain2"; mkdir -p "$PLAIN2"
reset; prec "$PLAIN2"; expect "baseline, non-git cwd: rc 0, no output" allow
[ -e "$(treefile)" ] && fail "baseline wrote .tree outside git" || echo "OK: baseline outside git writes nothing"
reset; prec "$TMP_ROOT/does-not-exist"; expect "baseline, missing cwd: rc 0, no output" allow
reset; gate baseline "$(jq -cn --arg s "$SID" '{session_id:$s,tool_name:"Bash"}')"; expect "baseline, no cwd: rc 0, no output" allow
R="$(mkrepo 20)"; reset; echo garbage >"$R/.git/HEAD"; prec "$R"; expect "baseline, corrupted .git: rc 0, no output" allow
for bad in "../evil" "a/b" "" "$(printf 'x%.0s' {1..129})"; do
  rc=0; printf '%s' "$(jq -cn --arg s "$bad" --arg c "$(mkrepo 21)" '{session_id:$s,cwd:$c,tool_name:"Bash"}')" \
    | env -u COPILOT_CLI -u CURSOR_PLUGIN_ROOT -u DEVIN_PROJECT_DIR -u DEVIN_PLUGIN_ROOT -u BEARPAWS_ENFORCE \
      CLAUDE_PLUGIN_ROOT="$REPO_ROOT" CLAUDE_PLUGIN_DATA="$TMP_ROOT/bad2/data" bash "$GATE" baseline >"$TMP_ROOT/out" 2>&1 || rc=$?
  if [ "$rc" != 0 ] || [ -s "$TMP_ROOT/out" ]; then fail "baseline, bad session_id '$bad': rc=$rc out=$(cat "$TMP_ROOT/out")"; fi
done
[ -n "$(find "$TMP_ROOT/bad2" -type f 2>/dev/null)" ] && fail "baseline with a malformed session_id wrote a file" || echo "OK: baseline with a malformed session_id writes nothing"
R="$(mkrepo 22)"; reset
gate baseline "$(jq -cn --arg s "$SID" --arg c "$R" '{session_id:$s,cwd:$c,tool_name:"Bash"}')" BEARPAWS_ENFORCE=0
[ -e "$(treefile)" ] && fail "baseline ignored BEARPAWS_ENFORCE=0" || echo "OK: BEARPAWS_ENFORCE=0 disables baseline"

# C1: the fingerprint is toplevel-relative and keyed per repo, so cd and worktrees are not edits.
R="$(mkrepo 30)"; mkdir -p "$R/sub/deep"
reset; bashc "$R"; bashc "$R/sub"; bashc "$R/sub/deep"; bashc "$R"
expect_bash_edits "cd into a subdir with no change is not an edit" 0
R="$(mkrepo 31)"; mkdir -p "$R/sub"
reset; bashc "$R"; echo n >"$R/top.py"; bashc "$R/sub"
expect_bash_edits "an edit at the root seen from a subdir cwd is an edit" 1
R="$(mkrepo 32)"; WT="$TMP_ROOT/wt-32"
git -C "$R" worktree add -q "$WT" -b wt32 2>/dev/null
reset; bashc "$R"; bashc "$WT"; bashc "$R"; bashc "$WT"; bashc "$R"
expect_bash_edits "alternating main checkout and worktree with no change: no edit" 0
[ "$(ls "$TMP_ROOT/data/risk-gate/$SID".*.tree | wc -l | tr -d ' ')" = 2 ] && echo "OK: one state file per repo" || fail "expected 2 .tree files"
prec "$R"; prec "$WT"; echo w >"$WT/only-in-wt.py"; bashc "$WT"
expect_bash_edits "worktree edit after its own baseline is detected" 1
R="$(mkrepo 33)"; WT="$TMP_ROOT/wt-33"; git -C "$R" worktree add -q "$WT" -b wt33 2>/dev/null
reset; bashc "$R"; echo w >"$WT/first.py"; bashc "$WT"
expect_bash_edits "known limit: a worktree's first Bash call with no baseline only baselines" 0
# Another repo's state does not leak: the edit at B is not an edit in A.
R="$(mkrepo 34)"; R2="$(mkrepo 35)"
reset; bashc "$R"; bashc "$R2"; echo z >"$R2/z.py"; bashc "$R"
expect_bash_edits "an edit in repo B is not seen from repo A" 0
bashc "$R2"; expect_bash_edits "the same edit is seen from repo B" 1

# I1: file names that look like stat options must not blind the fingerprint.
R="$(mkrepo 36)"
for n in -f -n --help "with space"; do echo one >"$R/$n"; done
reset; bashc "$R"; touch -t 203001010000 "$R/-f"; bashc "$R"
expect_bash_edits "a file named -f does not blind detection" 1
touch -t 203001010001 "$R/--help"; bashc "$R"; expect_bash_edits "a file named --help changes are detected" 2
touch -t 203001010002 "$R/with space"; bashc "$R"; expect_bash_edits "a file name with a space is detected" 3
touch -t 203001010003 "$R/-n"; bashc "$R"; expect_bash_edits "a file named -n is detected" 4
R="$(mkrepo 37)"; echo n >"$R/-f"; reset; bashc "$R"; echo new >"$R/real.py"; bashc "$R"
expect_bash_edits "a new file next to a file named -f is detected" 1

# I2: unambiguous test artifacts are not edits; dist/, build/, coverage/ are.
R="$(mkrepo 38)"
reset; echo two >"$R/a.py"; editc "$R" a.py; review
mkdir -p "$R/htmlcov" "$R/.hypothesis" "$R/.tox/x" "$R/.nox" "$R/pkg.egg-info"
echo x >"$R/.coverage"; echo x >"$R/.coverage.host.123"; echo x >"$R/htmlcov/x.html"; echo x >"$R/.hypothesis/h"
echo x >"$R/.tox/x/y"; echo x >"$R/.nox/n"; echo x >"$R/.eslintcache"; echo x >"$R/pkg.egg-info/PKG-INFO"
bashc "$R"; stop "$ELEVATED"; expect "coverage, hypothesis, tox, nox, eslintcache, egg-info after a review: allow" allow
for d in dist build coverage; do
  R="$(mkrepo 39-$d)"; reset; echo two >"$R/a.py"; editc "$R" a.py; review; mkdir -p "$R/$d"; echo x >"$R/$d/o"; bashc "$R"
  stop "$ELEVATED"; expect "$d/ output counts as an edit (no .gitignore)" block "independent review"
done

# M2: no temp files are left next to the state file.
R="$(mkrepo 40)"; reset; bashc "$R"; echo y >"$R/n.py"; bashc "$R"
[ -z "$(ls "$TMP_ROOT/data/risk-gate" | grep -E '\.tree\.[0-9]+$' || true)" ] && echo "OK: no temp files left by the atomic .tree write" || fail "temp file left: $(ls "$TMP_ROOT/data/risk-gate")"

# M4: a git failure after rev-parse works is a failure, not an empty list.
R="$(mkrepo 41)"; reset; bashc "$R"; echo garbage >"$R/.git/index"; echo y >"$R/n.py"; bashc "$R"
expect "corrupt index: rc 0, no output" allow; expect_bash_edits "ls-files failure is not hashed as an empty tree" 0

# Performance (reported, not asserted): 20 Bash record calls on a repo with 200 files.
R="$(mkrepo 9)"
for i in $(seq 1 200); do echo "$i" >"$R/f$i.txt"; done
git -C "$R" add -A f1*.txt 2>/dev/null; git -C "$R" commit -qm many
for i in $(seq 1 100); do echo "$i" >"$R/u$i.txt"; done
reset; bashc "$R"
t0=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)
for i in $(seq 1 20); do bashc "$R"; done
t1=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)
echo "PERF: 20 Bash record calls, 200 files: mean $(( (t1 - t0) / 20 )) ms"
R="$(mkrepo 17)"
for i in $(seq 1 5000); do echo "$i" >"$R/f$i.txt"; done
git -C "$R" add -A; git -C "$R" commit -qm many
reset; bashc "$R"
t0=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)
for i in $(seq 1 20); do bashc "$R"; done
t1=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)
echo "PERF: 20 Bash record calls, 5000 files: mean $(( (t1 - t0) / 20 )) ms"
t0=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)
for i in $(seq 1 20); do prec "$R"; done
t1=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)
echo "PERF: 20 baseline calls with .tree present, 5000 files: mean $(( (t1 - t0) / 20 )) ms"

if [ "$failures" -ne 0 ]; then
  echo "$failures risk-gate test(s) failed"
  exit 1
fi
echo "ALL RISK-GATE TESTS PASSED"
