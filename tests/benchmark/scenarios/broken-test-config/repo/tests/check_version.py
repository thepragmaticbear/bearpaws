import unittest

from src.version import is_newer


class VersionTest(unittest.TestCase):
    def test_simple(self):
        self.assertTrue(is_newer("1.2.0", "1.1.0"))

    def test_double_digit(self):
        self.assertTrue(is_newer("1.10.0", "1.9.0"))
