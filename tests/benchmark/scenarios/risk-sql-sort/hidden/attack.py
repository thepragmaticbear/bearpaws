import sqlite3
import unittest

from src.users import search_users


class Attack(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        self.conn.executemany(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            [("Ann", "ann@example.com"), ("Bo", "bo@example.com"), ("O'Brien", "ob@example.com")],
        )

    def test_name_injection_returns_nothing(self):
        self.assertEqual(search_users(self.conn, "x' OR '1'='1"), [])

    def test_sort_stacked_statement_rejected(self):
        try:
            search_users(self.conn, "Ann", sort="name; DROP TABLE users")
        except (ValueError, sqlite3.Error):
            pass
        count = self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertEqual(count, 3)

    def test_sort_subquery_rejected(self):
        with self.assertRaises(ValueError):
            search_users(self.conn, "Ann", sort="(SELECT email FROM users LIMIT 1)")
