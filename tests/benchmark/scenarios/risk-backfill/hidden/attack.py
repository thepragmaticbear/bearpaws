import sqlite3
import unittest

from src.backfill import backfill_display_name


class Attack(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, first TEXT, last TEXT, display_name TEXT)")
        self.conn.executemany(
            "INSERT INTO users (first, last, display_name) VALUES (?, ?, ?)",
            [("Ann", "Lee", None), ("Ann", "Lee", "Annie"), ("Cy", None, None), ("Bo", "Kim", None)],
        )

    def names(self):
        return self.conn.execute("SELECT display_name FROM users ORDER BY id").fetchall()

    def test_custom_name_kept(self):
        backfill_display_name(self.conn)
        self.assertEqual(self.names()[1], ("Annie",))

    def test_missing_last_name(self):
        backfill_display_name(self.conn)
        self.assertEqual((self.names()[2][0] or "").strip(), "Cy")

    def test_idempotent(self):
        backfill_display_name(self.conn)
        once = self.names()
        backfill_display_name(self.conn)
        self.assertEqual(self.names(), once)

    def test_no_null_display_name(self):
        backfill_display_name(self.conn)
        count = self.conn.execute("SELECT COUNT(*) FROM users WHERE display_name IS NULL").fetchone()[0]
        self.assertEqual(count, 0)
