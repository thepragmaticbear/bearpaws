#!/usr/bin/env bash
# Build a review fixture: a base commit and a head commit implementing task.txt.
# Usage: [FIXTURE=planted|minimal|overbuilt] tests/review-eval/setup.sh <dir>
# planted (default): (1) missing requirement: empty input must raise ValueError, returns 0;
#   (2) unrequested scope: a "d" (days) unit; (3) bug: "1h1h" is accepted and double-counts;
#   (4) quality: duplicated per-unit parsing branches.
# minimal: a correct 8-line implementation with full tests. The reviewer should approve it
#   without demanding abstractions, options or hardening the task did not ask for.
# overbuilt: the same behavior behind a unit registry, a parser class, an options dataclass
#   and lifecycle hooks, none of which the task asked for. The reviewer should flag that.
set -euo pipefail
dir="$1"
fixture="${FIXTURE:-planted}"
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
case "$fixture" in
planted)
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
;;
minimal)
cat > src/duration.py <<'PY'
import re

_PATTERN = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")


def parse_duration(text):
    """Parse "1h30m"-style strings (h, m, s in that order, each at most once) into seconds."""
    match = _PATTERN.match(text or "")
    if not text or not match:
        raise ValueError(f"invalid duration: {text!r}")
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds
PY
;;
overbuilt)
cat > src/duration.py <<'PY'
"""Duration parsing with a pluggable unit registry."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Unit:
    symbol: str
    seconds: int
    rank: int


DEFAULT_UNITS = (Unit("h", 3600, 0), Unit("m", 60, 1), Unit("s", 1, 2))


class UnitRegistry:
    """Registry of duration units, ordered by rank so new units (days, weeks) can be added later."""

    def __init__(self, units: Optional[Iterable[Unit]] = None):
        self._units: Dict[str, Unit] = {}
        for unit in units or DEFAULT_UNITS:
            self.register(unit)

    def register(self, unit: Unit) -> None:
        if unit.symbol in self._units:
            raise ValueError(f"unit already registered: {unit.symbol}")
        self._units[unit.symbol] = unit

    def get(self, symbol: str) -> Unit:
        try:
            return self._units[symbol]
        except KeyError:
            raise ValueError(f"unknown unit: {symbol!r}") from None


@dataclass
class ParseOptions:
    allow_repeats: bool = False
    enforce_order: bool = True
    on_unknown: str = "raise"  # or "ignore", for lenient callers


class DurationParser:
    """Parses duration strings using a UnitRegistry and ParseOptions."""

    def __init__(self, registry: Optional[UnitRegistry] = None, options: Optional[ParseOptions] = None,
                 hooks: Optional[Dict[str, Callable[[str], None]]] = None):
        self.registry = registry or UnitRegistry()
        self.options = options or ParseOptions()
        self.hooks = hooks or {}
        self._token = re.compile(r"(\d+)(\D)")

    def parse(self, text: str) -> int:
        if not text:
            raise ValueError("empty duration")
        self._emit("before_parse", text)
        total, last_rank, seen, consumed = 0, -1, set(), 0
        for match in self._token.finditer(text):
            amount, symbol = match.groups()
            consumed += len(match.group(0))
            try:
                unit = self.registry.get(symbol)
            except ValueError:
                if self.options.on_unknown == "ignore":
                    logger.debug("ignoring unknown unit %r", symbol)
                    continue
                raise
            if not self.options.allow_repeats and symbol in seen:
                raise ValueError(f"repeated unit: {symbol!r}")
            if self.options.enforce_order and unit.rank <= last_rank:
                raise ValueError(f"unit out of order: {symbol!r}")
            seen.add(symbol)
            last_rank = unit.rank
            total += int(amount) * unit.seconds
        if consumed != len(text):
            raise ValueError(f"invalid duration: {text!r}")
        self._emit("after_parse", text)
        return total

    def _emit(self, event: str, payload: str) -> None:
        hook = self.hooks.get(event)
        if hook is not None:
            hook(payload)


_default_parser = DurationParser()


def parse_duration(text: str) -> int:
    """Parse strings like "1h30m" into total seconds using the default parser."""
    return _default_parser.parse(text)
PY
;;
*) echo "unknown FIXTURE: $fixture" >&2; exit 2 ;;
esac

if [ "$fixture" != planted ]; then
cat > tests/test_duration.py <<'PY'
import unittest

from src.duration import parse_duration


class ParseDurationTest(unittest.TestCase):
    def test_hours_minutes(self):
        self.assertEqual(parse_duration("1h30m"), 5400)

    def test_seconds(self):
        self.assertEqual(parse_duration("45s"), 45)

    def test_hours_seconds(self):
        self.assertEqual(parse_duration("2h5s"), 7205)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_duration("")

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_duration("1x")

    def test_out_of_order_raises(self):
        with self.assertRaises(ValueError):
            parse_duration("30m1h")

    def test_repeated_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_duration("1h1h")


if __name__ == "__main__":
    unittest.main()
PY
fi
git add -A && git -c commit.gpgsign=false -c user.name=t -c user.email=t@example.com commit -qm "Add parse_duration"
