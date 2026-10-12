import unittest

from src.reset import verify_reset_token


class Attack(unittest.TestCase):
    def test_single_use(self):
        store = {"abc": {"user_id": 7, "created_at": 1000.0}}
        self.assertEqual(verify_reset_token(store, "abc", 1010.0), 7)
        self.assertIsNone(verify_reset_token(store, "abc", 1020.0))

    def test_expiry_counts_from_creation(self):
        t = 1000.0
        store = {"abc": {"user_id": 7, "created_at": t, "last_used": t + 3500}}
        self.assertIsNone(verify_reset_token(store, "abc", t + 3700))

    def test_unknown_token(self):
        self.assertIsNone(verify_reset_token({}, "nope", 1000.0))
