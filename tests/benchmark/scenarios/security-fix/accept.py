import os
import tempfile
import unittest

from src.files import read_user_file


class Accept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.base = os.path.join(root, "uploads")
        os.makedirs(os.path.join(self.base, "sub"))
        with open(os.path.join(root, "secret.txt"), "w") as f:
            f.write("secret")
        with open(os.path.join(self.base, "a.txt"), "w") as f:
            f.write("a")
        with open(os.path.join(self.base, "sub", "b.txt"), "w") as f:
            f.write("b")
        with open(os.path.join(self.base, "x..y.txt"), "w") as f:
            f.write("dots")
        os.symlink(os.path.join(root, "secret.txt"), os.path.join(self.base, "link.txt"))
        os.makedirs(os.path.join(root, "uploads-evil"))
        with open(os.path.join(root, "uploads-evil", "e.txt"), "w") as f:
            f.write("evil")

    def tearDown(self):
        self.tmp.cleanup()

    def test_normal(self):
        self.assertEqual(read_user_file(self.base, "a.txt"), "a")
        self.assertEqual(read_user_file(self.base, "sub/b.txt"), "b")
        self.assertEqual(read_user_file(self.base, "x..y.txt"), "dots")

    def test_dotdot(self):
        with self.assertRaises(PermissionError):
            read_user_file(self.base, "../secret.txt")

    def test_absolute(self):
        with self.assertRaises(PermissionError):
            read_user_file(self.base, os.path.join(self.tmp.name, "secret.txt"))

    def test_symlink_escape(self):
        with self.assertRaises(PermissionError):
            read_user_file(self.base, "link.txt")

    def test_sibling_prefix(self):
        with self.assertRaises(PermissionError):
            read_user_file(self.base, "../uploads-evil/e.txt")
