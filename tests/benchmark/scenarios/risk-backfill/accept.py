import sqlite3
import unittest

from src.backfill import backfill_display_name


class Accept(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, first TEXT, last TEXT, display_name TEXT)")
        self.conn.executemany(
            "INSERT INTO users (first, last, display_name) VALUES (?, ?, NULL)",
            [("Ann", "Lee"), ("Bo", "Kim")],
        )

    def test_names_filled(self):
        backfill_display_name(self.conn)
        rows = self.conn.execute("SELECT display_name FROM users ORDER BY id").fetchall()
        self.assertEqual(rows, [("Ann Lee",), ("Bo Kim",)])
