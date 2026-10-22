#!/usr/bin/env bash
# Git gate tests. No agent CLI needed: each case stages files in a temp repo, writes a
# commit message file, runs hooks/git-commit-msg on it, and checks the exit code and stderr.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATE="$REPO_ROOT/hooks/git-commit-msg"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
failures=0
R="$TMP_ROOT/repo"

fail() { echo "FAIL: $1"; failures=$((failures + 1)); }

git init -q "$R"
git -C "$R" config user.email t@example.com
git -C "$R" config user.name t
git -C "$R" config commit.gpgsign false
echo one >"$R/README.md"; git -C "$R" add README.md; git -C "$R" commit -qm init --no-verify

# reset: unstage and drop everything since the initial commit.
reset() { git -C "$R" reset -q --hard; git -C "$R" clean -qfdx; rm -f "$(git -C "$R" rev-parse --path-format=absolute --git-path MERGE_HEAD)"; }
stage() { local p; for p in "$@"; do mkdir -p "$R/$(dirname "$p")"; echo "$RANDOM" >>"$R/$p"; git -C "$R" add -- "$p"; done; }
# gate <message> [VAR=value ...]: run the hook from the repo root under a clean environment.
gate() {
  local m="$1" rc=0; shift
  printf '%s\n' "$m" >"$TMP_ROOT/msg"
  (cd "$R" && env -u BEARPAWS_ENFORCE "$@" bash "$GATE" "$TMP_ROOT/msg") >"$TMP_ROOT/out" 2>"$TMP_ROOT/err" || rc=$?
  echo "$rc" >"$TMP_ROOT/rc"
}
expect() { # <label> pass|block|warn [stderr substring]
  local rc; rc="$(cat "$TMP_ROOT/rc")"
  case "$2" in
    pass) [ "$rc" = 0 ] && [ ! -s "$TMP_ROOT/err" ] && echo "OK: $1" || fail "$1: expected silent pass, got rc=$rc err='$(cat "$TMP_ROOT/err")'" ;;
    warn) [ "$rc" = 0 ] && grep -qF -- "$3" "$TMP_ROOT/err" && [ "$(wc -l <"$TMP_ROOT/err")" -eq 1 ] && echo "OK: $1" \
            || fail "$1: expected one-line warning containing '$3', got rc=$rc err='$(cat "$TMP_ROOT/err")'" ;;
    block) [ "$rc" = 1 ] && grep -qF -- "$3" "$TMP_ROOT/err" && echo "OK: $1" \
            || fail "$1: expected block containing '$3', got rc=$rc err='$(cat "$TMP_ROOT/err")'" ;;
  esac
}

ROUTINE=$'Fix button label\n\nRisk: routine\nVerified: pytest — 12 passed\nStatus: COMPLETE'
ELEVATED=$'Deny cross-org access\n\nRisk: elevated (authorization)\nPinned: test_owner_allowed passed before edit\nFailing first: test_cross_org_denied failed, then passed\nReview: bp:code-reviewer — Ready to merge: Yes\nAssumptions: org_id is never null\nVerified: pytest — 14 passed\nStatus: COMPLETE'
NO_REVIEW="$(grep -v '^Review:' <<<"$ELEVATED")"

reset; stage src/ui/button.py; gate "$ROUTINE"; expect "routine with receipt passes" pass
reset; stage src/ui/button.py; gate "Fix button label"; expect "no receipt blocks" block "Risk:"
reset; stage src/ui/button.py; gate $'Fix\n\nVerified: ok\nStatus: COMPLETE'; expect "Verified and Status without Risk blocks" block "Risk:"
reset; stage src/ui/button.py; gate $'Fix\n\nRisk: medium\nStatus: COMPLETE'; expect "unknown risk level blocks" block "Risk:"
reset; stage src/authz.py; gate "$NO_REVIEW"; expect "elevated without Review blocks" block "Review"
reset; stage src/authz.py; gate "${NO_REVIEW/Status: COMPLETE/Status: INCOMPLETE}"; expect "elevated INCOMPLETE without Review passes" pass
reset; stage src/authz.py; gate "${ELEVATED/Status: COMPLETE/Status: INCOMPLETE}"; expect "elevated INCOMPLETE with Review passes" pass
reset; stage src/authz.py; gate "$ELEVATED"; expect "elevated with Review passes" pass
reset; stage src/authz.py; gate "${ELEVATED/Review: bp:code-reviewer — Ready to merge: Yes/Review:}"
expect "empty Review line does not count" block "Review"
reset; stage src/authz.py; gate $'x\n\nRisk: elevated (authz)\nStatus: INCOMPLETE\nVerified: ok\nStatus: COMPLETE'
expect "only the last Status line counts" block "Review"

reset; stage src/auth/login.py src/ui/a.py; gate "$ROUTINE"; expect "routine on sensitive path warns and passes" warn "src/auth/login.py"
grep -qF src/ui/a.py "$TMP_ROOT/err" && fail "warning lists a non-sensitive path" || echo "OK: warning lists only sensitive paths"
reset; stage a/token1 a/token2 a/token3 a/token4 a/token5 a/token6; gate "$ROUTINE"; expect "warning on many sensitive paths" warn "a/token1"
[ "$(grep -o 'a/token[0-9]' "$TMP_ROOT/err" | wc -l)" -eq 5 ] && echo "OK: warning lists at most 5 paths" || fail "warning should list 5 paths: $(cat "$TMP_ROOT/err")"
reset; stage src/authz.py; gate "$ELEVATED"; expect "elevated on sensitive path does not warn" pass
# Matched relative to the repo root: a checkout under an auth-looking directory is not sensitive.
reset; stage src/ui/button.py; R2="$TMP_ROOT/oauth-proxy"; git clone -q "$R" "$R2"; stage_in() { echo x >"$R2/$1"; git -C "$R2" add "$1"; }
stage_in b.py; printf '%s\n' "$ROUTINE" >"$TMP_ROOT/msg"; rc=0; (cd "$R2" && bash "$GATE" "$TMP_ROOT/msg") 2>"$TMP_ROOT/err" || rc=$?
[ "$rc" = 0 ] && [ ! -s "$TMP_ROOT/err" ] && echo "OK: paths matched relative to repo root" || fail "repo dir name triggered warning: $(cat "$TMP_ROOT/err")"
# Run from a subdirectory: paths are still repo-relative.
reset; stage src/auth/login.py; printf '%s\n' "$ROUTINE" >"$TMP_ROOT/msg"; rc=0; (cd "$R/src" && bash "$GATE" "$TMP_ROOT/msg") 2>"$TMP_ROOT/err" || rc=$?
[ "$rc" = 0 ] && grep -qF src/auth/login.py "$TMP_ROOT/err" && echo "OK: warning from a subdirectory" || fail "subdir run: rc=$rc err=$(cat "$TMP_ROOT/err")"

# Skips.
reset; stage src/x.py; : >"$(git -C "$R" rev-parse --path-format=absolute --git-path MERGE_HEAD)"; gate "Resolve conflicts"; expect "merge in progress skips" pass
reset; stage src/x.py; gate "Merge branch 'feature'"; expect "Merge subject skips" pass
reset; stage src/x.py; gate "fixup! Fix button label"; expect "fixup skips" pass
reset; stage src/x.py; gate "squash! Fix button label"; expect "squash skips" pass
reset; gate "Empty commit"; expect "no staged paths skips" pass
reset; stage src/x.py; gate $'\n# Please enter the commit message\n'; expect "empty message skips" pass
reset; stage src/x.py; gate "No receipt" BEARPAWS_ENFORCE=0; expect "BEARPAWS_ENFORCE=0 skips" pass

# Field matching is the risk-gate format: case-insensitive, markdown bold, backticks, bullets.
reset; stage src/x.py; gate $'Fix\n\n**Risk:** routine\n**Verified:** ok\n**Status:** COMPLETE'; expect "markdown-bold receipt passes" pass
reset; stage src/x.py; gate $'Fix\n\nrisk: ROUTINE\nstatus: complete'; expect "case-insensitive receipt passes" pass
reset; stage src/x.py; gate $'Fix\n\n- `Risk:` `routine`\n- `Status:` COMPLETE'; expect "backticked bullet receipt passes" pass
reset; stage src/authz.py; gate $'Fix\n\n**Risk:** elevated (authz)\n**review:** bp:code-reviewer — Yes\n**Status:** COMPLETE'; expect "bold elevated with bold Review passes" pass
reset; stage src/x.py; gate $'Fix\n\nNo Risk: routine here'; expect "mid-line Risk does not count" block "Risk:"

# Comment lines and the verbose diff are not the message.
reset; stage src/x.py; gate $'Fix\n# Risk: routine'; expect "commented receipt does not count" block "Risk:"
reset; stage src/x.py
gate $'Fix\n# ------------------------ >8 ------------------------\n+Risk: routine\nRisk: routine'
expect "receipt below the scissors line does not count" block "Risk:"

# End to end through git commit, including -v (the staged diff is appended to the message file).
reset; mkdir -p "$TMP_ROOT/hooks"; printf '#!/usr/bin/env bash\nexec bash %q "$@"\n' "$GATE" >"$TMP_ROOT/hooks/commit-msg"; chmod +x "$TMP_ROOT/hooks/commit-msg"
commit() { (cd "$R" && env -u BEARPAWS_ENFORCE GIT_EDITOR=true git -c core.hooksPath="$TMP_ROOT/hooks" commit -q "$@") >/dev/null 2>"$TMP_ROOT/err"; }
# forge: HEAD has a "Risk: routine" line and the staged change removes it. The diff then shows
# "-Risk: routine", which the receipt regex would accept if the diff counted as message.
forge() { printf 'Risk: routine\n' >"$R/notes.txt"; git -C "$R" add notes.txt; git -C "$R" diff --cached --quiet || commit --no-verify -m "Add notes"
  echo "other $RANDOM" >"$R/notes.txt"; git -C "$R" add notes.txt; }
forge; commit -v -e -m "Rewrite notes" && fail "git commit -v: receipt in the staged diff passed" || echo "OK: git commit -v: receipt in the staged diff does not count"
forge; git -C "$R" config core.commentString //; rc=0; commit -v -e -m "Rewrite notes" || rc=$?; git -C "$R" config --unset core.commentString
[ "$rc" = 0 ] && fail "commentString=//: receipt in the staged diff passed" || echo "OK: commentString=//: receipt in the staged diff does not count"
# Backslashes are literal, not awk escapes.
forge; git -C "$R" config core.commentString 'a\b'; rc=0; commit -v -e -m "Rewrite notes" || rc=$?; git -C "$R" config --unset core.commentString
[ "$rc" = 0 ] && fail "commentString=a\\b: receipt in the staged diff passed" || echo "OK: commentString with a backslash: receipt in the staged diff does not count"
# Git reads both names as one setting, last one wins: global commentString, repo commentChar.
forge; printf '[core]\n\tcommentString = //\n' >"$TMP_ROOT/global.gitconfig"; git -C "$R" config core.commentChar ';'
rc=0; GIT_CONFIG_GLOBAL="$TMP_ROOT/global.gitconfig" commit -v -e -m "Rewrite notes" || rc=$?; git -C "$R" config --unset core.commentChar
[ "$rc" = 0 ] && fail "global commentString, repo commentChar: receipt in the staged diff passed" || echo "OK: comment settings follow git's last-one-wins order"
# With auto, git strips a commented receipt, so it does not count.
forge; git -C "$R" config core.commentChar auto; rc=0; commit -e -m $'Rewrite notes\n# Risk: routine\n# Status: COMPLETE' || rc=$?; git -C "$R" config --unset core.commentChar
[ "$rc" = 0 ] && fail "commentChar=auto: commented receipt passed" || echo "OK: commentChar=auto: commented receipt does not count"
forge; commit -m "$ROUTINE" && echo "OK: git commit with receipt succeeds" || fail "git commit with receipt failed: $(cat "$TMP_ROOT/err")"
echo more >>"$R/notes.txt"; git -C "$R" add notes.txt
commit -m "No receipt" && fail "git commit without receipt succeeded" || echo "OK: git commit without receipt is refused"
commit --no-verify -m "No receipt" && echo "OK: --no-verify bypasses" || fail "--no-verify did not bypass"

if [ "$failures" -gt 0 ]; then echo "$failures GIT-GATE TEST(S) FAILED"; exit 1; fi
echo "ALL GIT-GATE TESTS PASSED"
