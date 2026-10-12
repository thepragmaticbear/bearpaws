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
