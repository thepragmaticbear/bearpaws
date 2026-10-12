import sqlite3
import unittest

from src.users import search_users


class Accept(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        self.conn.executemany(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            [("Ann", "ann@example.com"), ("Bo", "bo@example.com"), ("O'Brien", "ob@example.com")],
        )

    def test_apostrophe_name(self):
        self.assertEqual(search_users(self.conn, "O'Brien"), [(3, "O'Brien")])

    def test_plain_name(self):
        self.assertEqual(search_users(self.conn, "Ann"), [(1, "Ann")])

    def test_sort_by_id(self):
        self.assertEqual(search_users(self.conn, "Bo", sort="id"), [(2, "Bo")])
