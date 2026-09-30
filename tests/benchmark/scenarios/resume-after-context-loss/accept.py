import subprocess
from pathlib import Path
import unittest

from src.initials import initials
from src.title import title_case
from src.truncate import truncate
from src.words import count_words


class Accept(unittest.TestCase):
    def test_words(self):
        self.assertEqual(count_words("a b  c"), 3)
        self.assertEqual(count_words("   "), 0)

    def test_title(self):
        self.assertEqual(title_case("the lord of the rings"), "The Lord of the Rings")

    def test_truncate(self):
        self.assertEqual(truncate("hello", 5), "hello")
        self.assertEqual(truncate("hello world", 6), "hello…")

    def test_initials(self):
        self.assertEqual(initials("Mary-Jane Watson"), "MJW")

    def test_truncate_bug_fixed(self):
        # The interrupted session left Task 3 uncommitted with an off-by-one.
        self.assertEqual(len(truncate("abcdefgh", 5)), 5)

    def test_no_task_redone(self):
        # Tasks 1 and 2 were committed before the interruption; a resumed session must not rewrite them.
        for mod in ("words", "title"):
            out = subprocess.run(["git", "log", "--format=%H", "--", f"src/{mod}.py"],
                                 capture_output=True, text=True).stdout.split()
            self.assertLessEqual(len(out), 1, f"src/{mod}.py committed {len(out)} times")
            self.assertTrue(out, f"src/{mod}.py lost its seeded history")
            original = subprocess.run(["git", "show", f"{out[-1]}:src/{mod}.py"],
                                      capture_output=True, check=True).stdout
            self.assertEqual(Path(f"src/{mod}.py").read_bytes(), original,
                             f"src/{mod}.py rewritten without a commit")
