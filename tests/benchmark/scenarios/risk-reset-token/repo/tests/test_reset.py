import unittest

from src.reset import verify_reset_token


class ResetTest(unittest.TestCase):
    def test_fresh_token(self):
        store = {"abc": {"user_id": 7, "created_at": 1000.0}}
        self.assertEqual(verify_reset_token(store, "abc", 1010.0), 7)


if __name__ == "__main__":
    unittest.main()
