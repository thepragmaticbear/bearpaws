import os
import tempfile
import unittest

from src.uploads import save_upload


class SaveUploadTest(unittest.TestCase):
    def test_saves_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = save_upload(d, "a.txt", b"hi")
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"hi")


if __name__ == "__main__":
    unittest.main()
