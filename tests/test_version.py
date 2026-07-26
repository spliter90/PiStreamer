import unittest

import pistreamer


class VersionTests(unittest.TestCase):
    def test_version_comes_from_version_file(self):
        self.assertEqual(pistreamer.__version__, "1.2.0")


if __name__ == "__main__":
    unittest.main()
