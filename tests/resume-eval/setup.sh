#!/usr/bin/env bash
# Fixture: an interrupted plan whose checkboxes disagree with git history.
#   Task 1: checked, committed          -> done
#   Task 2: checked, NOT implemented    -> must be done now
#   Task 3: unchecked, committed        -> already done; must not be redone
#   Task 4: unchecked, not implemented  -> must be done now
# Usage: tests/resume-eval/setup.sh <dir>
set -euo pipefail
dir="$1"
mkdir -p "$dir/src" "$dir/tests" "$dir/docs"
cd "$dir"
git init -q
touch src/__init__.py tests/__init__.py
g() { git -c user.name=t -c user.email=t@example.com "$@"; }
cat > docs/plan.md <<'MD'
# Numbers Plan

Each task adds one module and one unittest file. Run tests with `python3 -m unittest discover -s tests -t .`. Commit after each task.

- [x] Task 1: Create src/one.py with `def one(): return 1` and tests/test_one.py asserting it.
- [x] Task 2: Create src/two.py with `def two(): return 2` and tests/test_two.py asserting it.
- [ ] Task 3: Create src/three.py with `def three(): return 3` and tests/test_three.py asserting it.
- [ ] Task 4: Create src/four.py with `def four(): return 4` and tests/test_four.py asserting it.
MD
g add -A && g commit -qm "Add plan"
mk() {
  printf 'def %s():\n    return %s\n' "$1" "$2" > "src/$1.py"
  printf 'import unittest\n\nfrom src.%s import %s\n\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        self.assertEqual(%s(), %s)\n' "$1" "$1" "$1" "$2" > "tests/test_$1.py"
  g add -A && g commit -qm "Task $3: add $1"
}
mk one 1 1
mk three 3 3
