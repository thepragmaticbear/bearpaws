import os
import tempfile
import unittest

from src.uploads import save_upload


class Attack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.base = os.path.join(self.root, "uploads")
        os.makedirs(self.base)
        os.makedirs(os.path.join(self.root, "uploads-evil"))
        os.makedirs(os.path.join(self.root, "outside"))
        os.symlink(os.path.join(self.root, "outside"), os.path.join(self.base, "link"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_absolute_path_outside_rejected(self):
        target = os.path.join(self.root, "outside", "abs.txt")
        with self.assertRaises(PermissionError):
            save_upload(self.base, target, b"x")
        self.assertFalse(os.path.exists(target))

    def test_sibling_prefix_dir_rejected(self):
        with self.assertRaises(PermissionError):
            save_upload(self.base, "../uploads-evil/e.txt", b"x")
        self.assertFalse(os.path.exists(os.path.join(self.root, "uploads-evil", "e.txt")))

    def test_symlinked_subdir_rejected(self):
        with self.assertRaises(PermissionError):
            save_upload(self.base, "link/x.txt", b"x")
        self.assertFalse(os.path.exists(os.path.join(self.root, "outside", "x.txt")))

    def test_dots_inside_name_allowed(self):
        save_upload(self.base, "x..y.txt", b"ok")
        with open(os.path.join(self.base, "x..y.txt"), "rb") as f:
            self.assertEqual(f.read(), b"ok")
