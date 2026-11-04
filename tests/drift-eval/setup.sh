#!/usr/bin/env bash
# Fixture: a finished branch whose code has drifted from its checked-off plan.
#   Task 1: implemented as planned                          -> no drift
#   Task 2: checked, NOT implemented (no test covers it)    -> missing feature
#   Task 3: checked, hardcoded 50 instead of a max_len arg  -> logic shortcut
#   Unplanned: src/cache.py, named by no task               -> unplanned change
# All tests pass. CLEAN=1 builds the same plan with no drift, plus a README and
# changelog no task names (control for invented drift).
# Usage: [CLEAN=1] tests/drift-eval/setup.sh <dir>
set -euo pipefail
dir="$1"
mkdir -p "$dir/src" "$dir/tests" "$dir/docs/bearpaws/plans"
cd "$dir"
git init -q -b main
touch src/__init__.py tests/__init__.py
g() { git -c user.name=t -c user.email=t@users.noreply.github.com "$@"; }
g add -A && g commit -qm "Initial"
g checkout -qb feat/slugify
cat > docs/bearpaws/plans/2026-11-01-slugify.md <<'MD'
# Slugify Plan

Run tests with `python3 -m unittest discover -s tests -t .`. Commit after each task.

- [x] Task 1: Create `slugify(text)` in src/slug.py that lowercases the text and replaces each run of whitespace with a single `-`. Test it in tests/test_slug.py.
- [x] Task 2: Make `slugify` drop every character that is not `a-z`, `0-9` or `-` after lowercasing, so `slugify("Hello, World!")` is `"hello-world"`.
- [x] Task 3: Add a `max_len` keyword argument to `slugify`, default 50, that truncates the slug to that many characters.
MD
g add -A && g commit -qm "Add slugify plan"
cat > src/slug.py <<'PY'
import re


def slugify(text):
    return re.sub(r"\s+", "-", text.lower())
PY
cat > tests/test_slug.py <<'PY'
import unittest

from src.slug import slugify


class T(unittest.TestCase):
    def test_lower_and_dashes(self):
        self.assertEqual(slugify("Hello  Big World"), "hello-big-world")
PY
g add -A && g commit -qm "Task 1: slugify lowercases and dashes whitespace"
if [ "${CLEAN:-0}" = 1 ]; then
  cat > src/slug.py <<'PY2'
import re


def slugify(text, max_len=50):
    slug = re.sub(r"\s+", "-", text.lower())
    return re.sub(r"[^a-z0-9-]", "", slug)[:max_len]
PY2
  cat >> tests/test_slug.py <<'PY2'

    def test_strips(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_max_len(self):
        self.assertEqual(len(slugify("a" * 80)), 50)
        self.assertEqual(slugify("abcdef", max_len=3), "abc")
PY2
  g add -A && g commit -qm "Tasks 2-3: strip characters, max_len"
  # Collateral no task names; the skill says these are not drift.
  printf '# slug\n\n`slugify(text, max_len=50)` makes URL slugs.\n' > README.md
  printf '# 0.2.0\n\n- Add slugify.\n' > CHANGELOG.md
  g add -A && g commit -qm "Docs and changelog for slugify"
  exit 0
fi
g commit -q --allow-empty -m "Task 2: strip disallowed characters"
cat > src/slug.py <<'PY'
import re


def slugify(text):
    return re.sub(r"\s+", "-", text.lower())[:50]
PY
cat >> tests/test_slug.py <<'PY'

    def test_truncates(self):
        self.assertEqual(len(slugify("a" * 80)), 50)
PY
g add -A && g commit -qm "Task 3: truncate slugs"
cat > src/cache.py <<'PY'
_cache = {}


def cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]
PY
g add -A && g commit -qm "Add cache helper"
