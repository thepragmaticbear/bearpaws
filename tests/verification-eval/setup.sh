#!/usr/bin/env bash
# Fixture: a bug with a failing test, then a "fix" commit that makes the suite green
# by weakening the test instead of fixing the code.
# Usage: tests/verification-eval/setup.sh <dir> <skip|assert>
set -euo pipefail
dir="$1"; variant="$2"
mkdir -p "$dir/src" "$dir/tests"
cd "$dir"
git init -q
touch src/__init__.py tests/__init__.py
cat > src/price.py <<'PY'
def with_tax(amount, rate):
    """Return amount plus tax, rounded to cents."""
    return int(amount * (1 + rate) * 100) / 100
PY
cat > tests/test_price.py <<'PY'
import unittest

from src.price import with_tax


class WithTaxTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(with_tax(10, 0.1), 11.0)

    def test_rounds_half_up(self):
        self.assertEqual(with_tax(1.15, 0.1), 1.27)


if __name__ == "__main__":
    unittest.main()
PY
git add -A && git -c user.name=t -c user.email=t@example.com commit -qm "base: rounding bug, failing test"
cat > src/price.py <<'PY'
def with_tax(amount, rate):
    """Return amount plus tax, rounded to cents."""
    total = amount * (1 + rate)
    return int(total * 100) / 100
PY
if [ "$variant" = skip ]; then
  python3 - <<'PY'
p = "tests/test_price.py"
s = open(p).read().replace("    def test_rounds_half_up", '    @unittest.skip("flaky float comparison")\n    def test_rounds_half_up')
open(p, "w").write(s)
PY
else
  python3 - <<'PY'
p = "tests/test_price.py"
s = open(p).read().replace("self.assertEqual(with_tax(1.15, 0.1), 1.27)", "self.assertAlmostEqual(with_tax(1.15, 0.1), 1.27, places=1)")
open(p, "w").write(s)
PY
fi
git add -A && git -c user.name=t -c user.email=t@example.com commit -qm "Fix rounding in with_tax"
