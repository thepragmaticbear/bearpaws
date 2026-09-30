import unittest


class Smoke(unittest.TestCase):
    def test_imports(self):
        import src.version  # noqa: F401
