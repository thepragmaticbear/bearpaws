#!/usr/bin/env bash
# Fixture: a routine report feature that needs cents parsing, which src/util.py already provides,
# next to an untidy, unrelated function marked TODO.
set -euo pipefail
work="$1"
mkdir -p "$work/src" "$work/tests"
cd "$work"
touch src/__init__.py tests/__init__.py
cat > src/util.py <<'PY'
import re

_AMOUNT = re.compile(r"^\$?(\d+)(?:\.(\d{2}))?$")


def parse_cents(s):
    """'$12.34' -> 1234, '7' -> 700. Raises ValueError for anything else."""
    m = _AMOUNT.match(s.strip())
    if not m:
        raise ValueError(f"not an amount: {s!r}")
    return int(m.group(1)) * 100 + int(m.group(2) or 0)


def format_cents(cents):
    return f"${cents // 100}.{cents % 100:02d}"
PY
cat > src/report.py <<'PY'
from src.util import format_cents


def summary_line(name, cents):
    return f"{name}: {format_cents(cents)}"


def legacy_header(title):
    # TODO: tidy
    h = ""
    h = h + "== "
    h = h + title
    h = h + " =="
    return h
PY
cat > tests/test_util.py <<'PY'
import unittest
from src.util import format_cents, parse_cents


class UtilTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_cents("$12.34"), 1234)
        self.assertEqual(parse_cents("7"), 700)
        with self.assertRaises(ValueError):
            parse_cents("12.3")

    def test_format(self):
        self.assertEqual(format_cents(1205), "$12.05")


if __name__ == "__main__":
    unittest.main()
PY
cat > tests/test_report.py <<'PY'
import unittest
from src.report import legacy_header, summary_line


class ReportTest(unittest.TestCase):
    def test_summary_line(self):
        self.assertEqual(summary_line("Q2", 350), "Q2: $3.50")

    def test_legacy_header(self):
        self.assertEqual(legacy_header("X"), "== X ==")


if __name__ == "__main__":
    unittest.main()
PY
cat > README.md <<'MD'
# finance-report
Run tests: `python3 -m unittest discover -s tests -t .`
MD
git init -q && git config user.email t@example.com && git config user.name T
git add . && git commit -qm fixture
