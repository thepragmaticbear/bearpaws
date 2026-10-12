import sqlite3
import unittest

from src.backfill import backfill_display_name


class BackfillTest(unittest.TestCase):
    def test_empty_table(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, first TEXT, last TEXT, display_name TEXT)")
        backfill_display_name(conn)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
