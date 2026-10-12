import unittest

from src.reset import verify_reset_token


def fresh_store():
    return {"abc": {"user_id": 7, "created_at": 1000.0}}


class Accept(unittest.TestCase):
    def test_within_hour(self):
        self.assertEqual(verify_reset_token(fresh_store(), "abc", 1000.0 + 1800), 7)

    def test_after_hour(self):
        self.assertIsNone(verify_reset_token(fresh_store(), "abc", 1000.0 + 7200))
