import os
import tempfile
import unittest

from src.uploads import save_upload


class Accept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.base = os.path.join(self.root, "uploads")
        os.makedirs(os.path.join(self.base, "sub"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_dotdot_rejected(self):
        with self.assertRaises(PermissionError):
            save_upload(self.base, "../x.txt", b"x")
        self.assertFalse(os.path.exists(os.path.join(self.root, "x.txt")))

    def test_subdir_saves(self):
        path = save_upload(self.base, "sub/b.txt", b"b")
        with open(os.path.join(self.base, "sub", "b.txt"), "rb") as f:
            self.assertEqual(f.read(), b"b")
        self.assertTrue(os.path.exists(path))
