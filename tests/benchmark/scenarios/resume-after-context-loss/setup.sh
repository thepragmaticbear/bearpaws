#!/usr/bin/env bash
# Seed the state an interrupted session leaves behind (run inside the work repo after
# the initial commit):
#   Task 1 committed and checked       -> done
#   Task 2 committed, box unchecked    -> done; must not be rewritten
#   Task 3 written but uncommitted, with an off-by-one bug, box checked -> not done
#   Task 4 not started
set -euo pipefail
g() { git -c commit.gpgsign=false -c user.name=bench -c user.email=bench@example.com "$@"; }
printf 'def count_words(text):\n    return len(text.split())\n' > src/words.py
printf 'import unittest\n\nfrom src.words import count_words\n\n\nclass T(unittest.TestCase):\n    def test_count(self):\n        self.assertEqual(count_words("a b"), 2)\n        self.assertEqual(count_words("  "), 0)\n' > tests/test_words.py
sed -i.bak 's/- \[ \] Task 1/- [x] Task 1/' docs/plan.md && rm docs/plan.md.bak
g add -A && g commit -qm "Task 1: words"
cat > src/title.py <<'PY'
SMALL = {"a", "an", "the", "of", "and"}


def title_case(text):
    words = text.split()
    return " ".join(w if i and w in SMALL else w.capitalize() for i, w in enumerate(words))
PY
printf 'import unittest\n\nfrom src.title import title_case\n\n\nclass T(unittest.TestCase):\n    def test_title(self):\n        self.assertEqual(title_case("war and peace"), "War and Peace")\n' > tests/test_title.py
g add -A && g commit -qm "Task 2: title"
printf 'def truncate(text, width):\n    if len(text) <= width:\n        return text\n    return text[:width] + "\\u2026"\n' > src/truncate.py
sed -i.bak 's/- \[ \] Task 3/- [x] Task 3/' docs/plan.md && rm docs/plan.md.bak
