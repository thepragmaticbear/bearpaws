import os
import tempfile
import unittest

from src.files import read_user_file


class ReadUserFileTest(unittest.TestCase):
    def test_reads_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.txt"), "w") as f:
                f.write("hi")
            self.assertEqual(read_user_file(d, "a.txt"), "hi")


if __name__ == "__main__":
    unittest.main()
