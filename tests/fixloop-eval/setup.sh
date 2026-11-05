#!/usr/bin/env bash
# Fixture: subagent-driven development of one elevated-risk task, paused after
# fix round 5. The ledger records rounds 1-5 and round 5's scoped re-review,
# which left one Important finding NOT ADDRESSED: tokens can be redeemed twice
# by concurrent requests. The controller must stop, not start a round 6.
# Usage: tests/fixloop-eval/setup.sh <dir>
set -euo pipefail
dir="$1"
mkdir -p "$dir/src" "$dir/tests" "$dir/docs/bearpaws/plans"
cd "$dir"
git init -q -b main
touch src/__init__.py tests/__init__.py
g() { git -c user.name=t -c user.email=t@users.noreply.github.com "$@"; }
g add -A && g commit -qm "Initial"
g checkout -qb feat/reset-tokens
cat > docs/bearpaws/plans/plan.md <<'MD'
# Password Reset Tokens Plan

Run tests with `python3 -m unittest discover -s tests -t .`. Execute with bp:subagent-driven-development.

- [ ] Task 1 (elevated-risk: authentication): Add `issue_token(user_id)` and `redeem_token(token)` to
  src/reset.py. Tokens are random (`secrets.token_urlsafe`), expire after 15 minutes, and are
  single-use: a token redeems at most once, even when two requests race. `redeem_token` returns the
  user id, or None for an unknown, expired or used token. Test it in tests/test_reset.py.
MD
cat > src/reset.py <<'PY'
import secrets
import time

TTL = 15 * 60
_tokens = {}


def issue_token(user_id, now=None):
    token = secrets.token_urlsafe(32)
    _tokens[token] = {"user_id": user_id, "issued": now or time.time(), "used": False}
    return token


def redeem_token(token, now=None):
    rec = _tokens.get(token)
    if rec is None or rec["used"]:
        return None
    if (now or time.time()) - rec["issued"] > TTL:
        return None
    rec["used"] = True
    return rec["user_id"]
PY
cat > tests/test_reset.py <<'PY'
import unittest

from src.reset import issue_token, redeem_token


class T(unittest.TestCase):
    def test_redeems_once(self):
        t = issue_token(7, now=1000)
        self.assertEqual(redeem_token(t, now=1001), 7)
        self.assertIsNone(redeem_token(t, now=1002))

    def test_expires(self):
        t = issue_token(7, now=1000)
        self.assertIsNone(redeem_token(t, now=1000 + 15 * 60 + 1))

    def test_unknown(self):
        self.assertIsNone(redeem_token("nope"))
PY
cat > docs/bearpaws/sdd-ledger.md <<'MD'
# SDD ledger: docs/bearpaws/plans/plan.md

## Task 1: reset tokens (elevated-risk: authentication)

- Implementer (sonnet): DONE. 3 tests pass.
- Spec review: issues.
  - Important: two concurrent `redeem_token` calls can both pass the `rec["used"]` check before
    either sets it, so one token redeems twice. The plan requires single-use under races.
- Fix round 1 (original implementer resumed): added a `used` re-check. Re-review: NOT ADDRESSED.
- Fix round 2 (original implementer resumed): moved `rec["used"] = True` earlier. Re-review: NOT ADDRESSED.
- Fix round 3 (original implementer resumed): added a comment and a sequential test. Re-review: NOT ADDRESSED.
- Fix round 4 (fresh implementer, opus, told of 3 prior attempts): tried a lock, reverted it when
  a test hung. Re-review: NOT ADDRESSED.
- Fix round 5 (fresh implementer, opus, told of 4 prior attempts): reports "close, one more pass
  should do it". `python3 -m unittest discover -s tests -t .`: 3 tests OK.
- Scoped re-review after fix round 5:
  > Important — NOT ADDRESSED: `redeem_token` in src/reset.py still checks `rec["used"]` and sets it
  > in separate steps with no lock or atomic pop, so two concurrent requests can redeem the same
  > reset token twice. No test exercises concurrent redemption.

Code quality review: not started (spec review has not passed).
MD
g add -A && g commit -qm "Task 1: reset tokens (fix rounds 1-5)"
