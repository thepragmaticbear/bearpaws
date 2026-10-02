#!/usr/bin/env bash
# SessionStart hook payload tests. No agent CLI needed.
# Checks each harness gets exactly one context key in the shape it consumes,
# that the bootstrap survives JSON escaping, and that bad input fails loudly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$REPO_ROOT/hooks/session-start"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
failures=0

fail() { echo "FAIL: $1"; failures=$((failures + 1)); }

# Run the hook with a clean harness environment plus the given VAR=value pairs.
run_hook() { # hook-path out-file [VAR=value ...]
  local hook="$1" out="$2"; shift 2
  env -u CLAUDE_PLUGIN_ROOT -u CURSOR_PLUGIN_ROOT -u COPILOT_CLI \
      -u DEVIN_PROJECT_DIR -u DEVIN_PLUGIN_ROOT "$@" bash "$hook" >"$out" 2>"$out.err"
}

# check_shape <label> <expected key path> [VAR=value ...]
# Key paths: hookSpecificOutput | additional_context | additionalContext
check_shape() {
  local label="$1" expected="$2"; shift 2
  local out="$TMP_ROOT/$label.json"
  if ! run_hook "$HOOK" "$out" "$@"; then
    fail "$label: hook exited non-zero ($(cat "$out.err"))"
    return
  fi
  if ! python3 - "$out" "$expected" "$REPO_ROOT/skills/using-bearpaws/SKILL.md" <<'PY'
import json, sys
out, expected, skill = sys.argv[1:]
data = json.load(open(out))
keys = set(data)
want = {"hookSpecificOutput"} if expected == "hookSpecificOutput" else {expected}
assert keys == want, f"top-level keys {sorted(keys)} != {sorted(want)}"
if expected == "hookSpecificOutput":
    inner = data["hookSpecificOutput"]
    assert inner.get("hookEventName") == "SessionStart", inner.get("hookEventName")
    assert set(inner) == {"hookEventName", "additionalContext"}, sorted(inner)
    ctx = inner["additionalContext"]
else:
    ctx = data[expected]
assert ctx.startswith('<warning level="hard">'), ctx[:40]
assert ctx.rstrip().endswith("</warning>"), ctx[-40:]
assert open(skill, encoding="utf-8").read() in ctx, "bootstrap body not embedded verbatim"
PY
  then
    fail "$label: expected $expected shape"
  else
    echo "OK: $label emits $expected"
  fi
}

check_shape claude-code    hookSpecificOutput CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
check_shape cursor         additional_context CURSOR_PLUGIN_ROOT="$REPO_ROOT"
check_shape cursor+claude  additional_context CURSOR_PLUGIN_ROOT="$REPO_ROOT" CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
check_shape copilot-cli    additionalContext  CLAUDE_PLUGIN_ROOT="$REPO_ROOT" COPILOT_CLI=1
check_shape devin-project  hookSpecificOutput DEVIN_PROJECT_DIR="$REPO_ROOT"
check_shape devin-plugin   hookSpecificOutput DEVIN_PLUGIN_ROOT="$REPO_ROOT"
check_shape unknown-sdk    additionalContext

# Claude Code payload is release-blocking: lock the wrapper text so a change to
# shared wording is a deliberate, reviewed edit.
claude_out="$TMP_ROOT/claude-code.json"
if python3 - "$claude_out" <<'PY'
import json, sys
ctx = json.load(open(sys.argv[1]))["hookSpecificOutput"]["additionalContext"]
head = '<warning level="hard">\nYou have bearpaws.\n\n**Your bootstrap skill (bp:using-bearpaws). Use the Skill tool for all others:**\n\n'
assert ctx.startswith(head), repr(ctx[:len(head)])
assert ctx.endswith("\n</warning>"), repr(ctx[-20:])
PY
then echo "OK: Claude Code wrapper text unchanged"; else fail "Claude Code wrapper text changed"; fi

# Escaping: quotes, backslashes, tabs, CRLF and non-ASCII must round-trip.
FAKE="$TMP_ROOT/fake-plugin"
mkdir -p "$FAKE/hooks" "$FAKE/skills/using-bearpaws"
cp "$HOOK" "$FAKE/hooks/session-start"
printf -- '---\nname: using-bearpaws\n---\nquote " back \\ tab\there\r\ncrlf line\nunicode — ✓\n' \
  > "$FAKE/skills/using-bearpaws/SKILL.md"
esc_out="$TMP_ROOT/escape.json"
if run_hook "$FAKE/hooks/session-start" "$esc_out" CLAUDE_PLUGIN_ROOT="$FAKE" && python3 - "$esc_out" "$FAKE/skills/using-bearpaws/SKILL.md" <<'PY'
import json, sys
ctx = json.load(open(sys.argv[1]))["hookSpecificOutput"]["additionalContext"]
body = open(sys.argv[2], encoding="utf-8", newline="").read()
assert body in ctx, "special characters did not round-trip"
PY
then echo "OK: special characters round-trip through JSON"; else fail "escaping broke JSON or content"; fi

# Missing or empty bootstrap must fail loudly with nothing on stdout.
for case in missing empty; do
  if [ "$case" = missing ]; then rm -f "$FAKE/skills/using-bearpaws/SKILL.md"; else : > "$FAKE/skills/using-bearpaws/SKILL.md"; fi
  bad_out="$TMP_ROOT/$case.json"
  if run_hook "$FAKE/hooks/session-start" "$bad_out" CLAUDE_PLUGIN_ROOT="$FAKE"; then
    fail "$case bootstrap: hook should exit non-zero"
  elif [ -s "$bad_out" ]; then
    fail "$case bootstrap: stdout should be empty"
  elif ! grep -q "missing, empty, or unreadable" "$bad_out.err"; then
    fail "$case bootstrap: stderr should explain the failure"
  else
    echo "OK: $case bootstrap fails loudly"
  fi
done

# Packaging: every hook config points at a script that exists.
python3 - "$REPO_ROOT" <<'PY' && echo "OK: hook configs reference existing scripts" || fail "hook config references a missing script"
import json, os, sys
root = sys.argv[1]
claude = json.load(open(f"{root}/hooks/hooks.json"))
cmd = claude["hooks"]["SessionStart"][0]["hooks"][0]["command"]
assert "run-hook.cmd\" session-start" in cmd, cmd
cursor = json.load(open(f"{root}/hooks/hooks-cursor.json"))
assert cursor["version"] == 1
assert cursor["hooks"]["sessionStart"][0]["command"] == "./hooks/run-hook.cmd session-start"
manifest = json.load(open(f"{root}/.cursor-plugin/plugin.json"))
assert manifest["hooks"] == "./hooks/hooks-cursor.json" and manifest["skills"] == "./skills/"
devin = json.load(open(f"{root}/.devin/hooks.v1.json"))
assert "hooks/session-start" in devin["SessionStart"][0]["hooks"][0]["command"]
for script in ("run-hook.cmd", "session-start"):
    path = f"{root}/hooks/{script}"
    assert os.access(path, os.X_OK), f"{path} not executable"
PY

if [ "$failures" -ne 0 ]; then
  echo "$failures hook test(s) failed"
  exit 1
fi
echo "ALL HOOK TESTS PASSED"
