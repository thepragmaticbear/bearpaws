#!/usr/bin/env bash
# Build the review fixture: a base commit and a head commit with planted defects.
# Usage: tests/review-eval/setup.sh <dir>
# Planted: (1) missing requirement: empty input must raise ValueError, returns 0;
# (2) unrequested scope: a "d" (days) unit; (3) bug: "1h1h" is accepted and double-counts;
# (4) quality: duplicated per-unit parsing branches.
set -euo pipefail
dir="$1"
mkdir -p "$dir/src" "$dir/tests"
cd "$dir"
git init -q
touch src/__init__.py tests/__init__.py
cat > src/duration.py <<'PY'
PY
cat > tests/test_duration.py <<'PY'
PY
if [ "${CONVENTION:-0}" = 1 ]; then
  # CONVENTION=1: a project-only rule (register public functions in __all__) that the head commit misses.
  printf '# Contributing\n\n- Every public function in src/ must be added to `__all__` in `src/__init__.py`. The plugin loader only exposes names listed there; anything else is invisible in production.\n' > CONTRIBUTING.md
  printf '__all__ = []\n' > src/__init__.py
fi
git add -A && git -c commit.gpgsign=false -c user.name=t -c user.email=t@example.com commit -qm base
cat > src/duration.py <<'PY'
import re


def parse_duration(text):
    """Parse strings like "1h30m" or "45s" into total seconds."""
    if not text:
        return 0
    total = 0
    for amount, unit in re.findall(r"(\d+)([dhms])", text):
        if unit == "d":
            total += int(amount) * 86400
        elif unit == "h":
            total += int(amount) * 3600
        elif unit == "m":
            total += int(amount) * 60
        elif unit == "s":
            total += int(amount)
    return total
PY

cat > tests/test_duration.py <<'PY'
import unittest

from src.duration import parse_duration


class ParseDurationTest(unittest.TestCase):
    def test_hours_minutes(self):
        self.assertEqual(parse_duration("1h30m"), 5400)

    def test_seconds(self):
        self.assertEqual(parse_duration("45s"), 45)


if __name__ == "__main__":
    unittest.main()
PY
git add -A && git -c commit.gpgsign=false -c user.name=t -c user.email=t@example.com commit -qm "Add parse_duration"
