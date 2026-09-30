import unittest

from src.app import lookup_price


class AppTest(unittest.TestCase):
    def test_lookup(self):
        self.assertEqual(lookup_price("a", lambda s: 3), 3)
