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
reset; stage src/x.py; gate "Merge tool rewrite"; expect "Merge subject without MERGE_HEAD is checked" block "Risk:"
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
# A real merge runs commit-msg with MERGE_HEAD present and needs no receipt.
git -C "$R" checkout -qb side; echo s >"$R/side.txt"; git -C "$R" add side.txt; commit --no-verify -m side; git -C "$R" checkout -q -
(cd "$R" && GIT_EDITOR=true git -c core.hooksPath="$TMP_ROOT/hooks" merge -q --no-ff --edit side) >/dev/null 2>"$TMP_ROOT/err" \
  && echo "OK: git merge --no-ff passes without a receipt" || fail "git merge --no-ff was refused: $(cat "$TMP_ROOT/err")"

# Pre-push identity check: commit emails outside *@users.noreply.github.com, noreply@github.com
# and the project's "Allowed commit emails:" line are flagged once per branch.
PRE="$REPO_ROOT/hooks/git-pre-push"
P="$TMP_ROOT/push"
Z=0000000000000000000000000000000000000000
git init -q "$P"
git -C "$P" config commit.gpgsign false
pc() { # <author email> <committer email> <message>: an empty commit in P
  GIT_AUTHOR_NAME=a GIT_AUTHOR_EMAIL="$1" GIT_COMMITTER_NAME=c GIT_COMMITTER_EMAIL="$2" \
    git -C "$P" commit -q --allow-empty --no-verify -m "$3"
}
pc 1+t@users.noreply.github.com 1+t@users.noreply.github.com init
BASE="$(git -C "$P" rev-parse HEAD)"
prepush() { # <stdin line> [VAR=value ...]
  local line="$1" rc=0; shift
  (cd "$P" && printf '%s\n' "$line" | env -u BEARPAWS_ENFORCE "$@" bash "$PRE" origin https://example.invalid/r.git) >"$TMP_ROOT/out" 2>"$TMP_ROOT/err" || rc=$?
  echo "$rc" >"$TMP_ROOT/rc"
}
preset() { git -C "$P" checkout -q --detach "$BASE"; rm -f "$(git -C "$P" rev-parse --path-format=absolute --git-path bearpaws-identity-flagged)" "$P/CLAUDE.md"; }
tip() { git -C "$P" rev-parse HEAD; }

preset; pc dana.kowalski82@gmail.com 1+t@users.noreply.github.com "feat: x"
prepush "refs/heads/f1 $(tip) refs/heads/f1 $Z"
expect "pre-push: gmail.com author is flagged" block "dana.kowalski82@gmail.com"
grep -qF "git rebase -r" "$TMP_ROOT/err" && grep -qF -- "--reset-author" "$TMP_ROOT/err" && grep -qF "$(git -C "$P" rev-parse --short HEAD)" "$TMP_ROOT/err" \
  && echo "OK: pre-push: flag names the commit and offers the rewrite" || fail "pre-push flag lacks sha or rewrite command: $(cat "$TMP_ROOT/err")"
prepush "refs/heads/f1 $(tip) refs/heads/f1 $Z"; expect "pre-push: second push of a flagged branch proceeds" pass
prepush "refs/heads/f2 $(tip) refs/heads/f2 $Z"; expect "pre-push: flag is per branch" block "dana.kowalski82@gmail.com"
preset; pc 1+T@Users.Noreply.GitHub.com noreply@github.com "web merge"
prepush "refs/heads/ok $(tip) refs/heads/ok $Z"; expect "pre-push: noreply author (any case) and GitHub committer pass" pass
preset; pc 1+t@users.noreply.github.com dana@corp.example "x"
prepush "refs/heads/c $(tip) refs/heads/c $Z"; expect "pre-push: committer email is checked" block "dana@corp.example"
preset; pc 1+t@users.noreply.github.com 1+t@users.noreply.github.com $'x\n\nCo-authored-by: Dana <dana.kowalski82@gmail.com>'
prepush "refs/heads/t $(tip) refs/heads/t $Z"; expect "pre-push: Co-authored-by trailer is checked" block "dana.kowalski82@gmail.com"
preset; printf '# Rules\n\n- **Allowed commit emails:** *@corp.example, ops@other.example\n' >"$P/CLAUDE.md"
pc dana@corp.example ops@other.example "allowed"
prepush "refs/heads/a $(tip) refs/heads/a $Z"; expect "pre-push: project allowed list passes" pass
pc dana.kowalski82@gmail.com dana@corp.example "not allowed"
prepush "refs/heads/a2 $(tip) refs/heads/a2 $Z"; expect "pre-push: allowed list does not admit gmail.com" block "dana.kowalski82@gmail.com"
preset; pc dana.kowalski82@gmail.com dana.kowalski82@gmail.com "old"; OLD="$(tip)"; pc 1+t@users.noreply.github.com 1+t@users.noreply.github.com "new"
prepush "refs/heads/u $(tip) refs/heads/u $OLD"; expect "pre-push: only commits new to the remote are checked" pass
prepush "(delete) $Z refs/heads/gone $OLD"; expect "pre-push: branch deletion passes" pass
prepush "refs/heads/same $OLD refs/heads/same $OLD"; expect "pre-push: a push with no new commits passes" pass
preset; pc dana.kowalski82@gmail.com dana.kowalski82@gmail.com "x"
prepush "refs/heads/e $(tip) refs/heads/e $Z" BEARPAWS_ENFORCE=0; expect "pre-push: BEARPAWS_ENFORCE=0 bypasses" pass
# A remote tip this clone never fetched (a force-push over it) falls back to "not on any remote".
preset; pc dana.kowalski82@gmail.com dana.kowalski82@gmail.com "x"
prepush "refs/heads/k $(tip) refs/heads/k 1111111111111111111111111111111111111111"; expect "pre-push: unknown remote sha still checks the new commits" block "dana.kowalski82@gmail.com"
prepush "refs/heads/k2 0123456789abcdef refs/heads/k2 $Z"; expect "pre-push: a local sha git cannot read fails loudly" block "could not list commits"
# Allowed-list entries are patterns, never expanded against files in the repo.
preset; printf 'Allowed commit emails: *\n' >"$P/CLAUDE.md"; touch "$P/evil@acme.dev"
pc dana.kowalski82@gmail.com dana.kowalski82@gmail.com "x"
prepush "refs/heads/g $(tip) refs/heads/g $Z"; expect "pre-push: allow-all * is not glob-expanded" pass
printf 'Allowed commit emails: *@acme.dev\n' >"$P/CLAUDE.md"; pc me@acme.dev me@acme.dev "y"
prepush "refs/heads/g2 $(tip) refs/heads/g2 $Z"; expect "pre-push: a file named like an email does not shadow the pattern" block "dana.kowalski82@gmail.com"
grep -qF "me@acme.dev" "$TMP_ROOT/err" && fail "pre-push: me@acme.dev wrongly flagged" || echo "OK: pre-push: me@acme.dev matches *@acme.dev despite the file"
rm -f "$P/evil@acme.dev"
preset; pc 1+t@users.noreply.github.com 1+t@users.noreply.github.com $'x\n\nCo-authored-by: dana.kowalski82@gmail.com'
prepush "refs/heads/b $(tip) refs/heads/b $Z"; expect "pre-push: a bare Co-authored-by email is checked" block "dana.kowalski82@gmail.com"
# Two flagged refs in one push: each names its own rewrite base.
preset; pc dana.kowalski82@gmail.com dana.kowalski82@gmail.com "one"; ONE="$(tip)"; pc dana.kowalski82@gmail.com dana.kowalski82@gmail.com "two"
prepush "$(printf 'refs/heads/m1 %s refs/heads/m1 %s\nrefs/heads/m2 %s refs/heads/m2 %s' "$(tip)" "$ONE" "$(tip)" "$Z")"
grep -qF "git rebase -r $ONE" "$TMP_ROOT/err" && grep -qF "m2" "$TMP_ROOT/err" \
  && echo "OK: pre-push: each flagged ref gets its own rewrite base" || fail "pre-push: per-ref rewrite base missing: $(cat "$TMP_ROOT/err")"

if [ "$failures" -gt 0 ]; then echo "$failures GIT-GATE TEST(S) FAILED"; exit 1; fi
echo "ALL GIT-GATE TESTS PASSED"
