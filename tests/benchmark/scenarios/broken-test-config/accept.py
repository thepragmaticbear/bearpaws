import unittest

from src.version import is_newer


class Accept(unittest.TestCase):
    def test_versions(self):
        self.assertTrue(is_newer("1.10.0", "1.9.0"))
        self.assertTrue(is_newer("2.0.0", "1.99.99"))
        self.assertFalse(is_newer("1.9.0", "1.10.0"))
        self.assertFalse(is_newer("1.0.0", "1.0.0"))
        self.assertTrue(is_newer("1.0.10", "1.0.9"))

    def test_suite_runs_version_tests(self):
        # The documented command must now discover the version tests.
        suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
        names = []

        def walk(s):
            for t in s:
                walk(t) if isinstance(t, unittest.TestSuite) else names.append(t.id())

        walk(suite)
        self.assertTrue(any("double_digit" in n for n in names), names)
