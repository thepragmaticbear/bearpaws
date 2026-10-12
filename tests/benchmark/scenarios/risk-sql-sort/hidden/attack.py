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

    def test_sort_is_never_executed_as_sql(self):
        calls = []
        self.conn.create_function("probe", 0, lambda: calls.append(1) or 1)
        for sort in ("probe()", "(SELECT probe())", "name, probe()"):
            try:
                search_users(self.conn, "Ann", sort=sort)
            except Exception:
                pass
        self.assertEqual(calls, [])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 3)
