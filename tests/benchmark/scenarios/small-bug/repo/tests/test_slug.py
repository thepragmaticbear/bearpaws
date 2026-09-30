import unittest

from src.slug import slugify


class SlugifyTest(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(slugify("Hello"), "hello")

    def test_replaces_space(self):
        self.assertEqual(slugify("hello world"), "hello-world")


if __name__ == "__main__":
    unittest.main()
