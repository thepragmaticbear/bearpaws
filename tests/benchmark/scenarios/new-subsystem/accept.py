import unittest

from src.app import lookup_price
from src.cache import Cache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Accept(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.c = Cache(2, 10, clock=self.clock)

    def test_basic(self):
        self.c.set("a", 1)
        self.assertEqual(self.c.get("a"), 1)
        self.assertEqual(self.c.get("x", "d"), "d")
        self.c.delete("a")
        self.assertIsNone(self.c.get("a"))

    def test_ttl(self):
        self.c.set("a", 1)
        self.clock.t = 9
        self.assertEqual(self.c.get("a"), 1)
        self.clock.t = 10.5
        self.assertIsNone(self.c.get("a"))
        self.assertEqual(len(self.c), 0)

    def test_ttl_refresh_on_set(self):
        self.c.set("a", 1)
        self.clock.t = 8
        self.c.set("a", 2)
        self.clock.t = 15
        self.assertEqual(self.c.get("a"), 2)

    def test_lru_eviction_counts_get(self):
        self.c.set("a", 1)
        self.c.set("b", 2)
        self.c.get("a")
        self.c.set("c", 3)
        self.assertIsNone(self.c.get("b"))
        self.assertEqual(self.c.get("a"), 1)
        self.assertEqual(self.c.stats()["evictions"], 1)

    def test_update_existing_no_eviction(self):
        self.c.set("a", 1)
        self.c.set("b", 2)
        self.c.set("a", 3)
        self.assertEqual(len(self.c), 2)
        self.assertEqual(self.c.stats()["evictions"], 0)

    def test_stats(self):
        self.c.set("a", 1)
        self.c.get("a")
        self.c.get("zz")
        s = self.c.stats()
        self.assertEqual((s["hits"], s["misses"]), (1, 1))

    def test_lookup_uses_cache(self):
        calls = []
        cache = Cache(10, 60, clock=self.clock)
        fetch = lambda s: calls.append(s) or 7
        self.assertEqual(lookup_price("a", fetch, cache=cache), 7)
        self.assertEqual(lookup_price("a", fetch, cache=cache), 7)
        self.assertEqual(calls, ["a"])
        self.assertEqual(lookup_price("b", lambda s: 1), 1)
