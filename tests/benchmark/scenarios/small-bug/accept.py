import unittest

from src.slug import slugify


class Accept(unittest.TestCase):
    def test_report(self):
        self.assertEqual(slugify("Hello -- World!"), "hello-world")

    def test_leading_trailing(self):
        self.assertEqual(slugify("  --Hi there--  "), "hi-there")

    def test_existing_behaviour(self):
        self.assertEqual(slugify("hello world"), "hello-world")
        self.assertEqual(slugify("Hello"), "hello")

    def test_digits_kept(self):
        self.assertEqual(slugify("Top 10 Tips"), "top-10-tips")

    def test_all_separators(self):
        self.assertEqual(slugify("!!!"), "")
