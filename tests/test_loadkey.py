import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SCRIPTS_DIR

LOADKEY = SCRIPTS_DIR / "loadkey.py"
KEY = "k3y-For-Tests_01"


def run_loadkey(path):
    return subprocess.run([sys.executable, "-B", str(LOADKEY), str(path)],
                          capture_output=True, text=True, check=False)


class LoadKeyTest(unittest.TestCase):
    def setUp(self):
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.env_file = Path(workdir.name) / "mangools.env"

    def test_prints_key_from_every_accepted_format(self):
        formats = {
            "plain": f"MANGOOLS_API_KEY={KEY}\n".encode(),
            "export, spaced, double-quoted, CRLF": f'export MANGOOLS_API_KEY = "{KEY}"\r\n'.encode(),
            "single-quoted on a later line": f"OTHER=1\nMANGOOLS_API_KEY='{KEY}'\n".encode(),
            "UTF-8 BOM": b"\xef\xbb\xbf" + f"MANGOOLS_API_KEY={KEY}\n".encode(),
            "UTF-16 with BOM": f"MANGOOLS_API_KEY={KEY}\r\n".encode("utf-16"),
        }
        for name, content in formats.items():
            with self.subTest(name):
                self.env_file.write_bytes(content)
                result = run_loadkey(self.env_file)
                self.assertEqual((result.returncode, result.stdout), (0, KEY + "\n"))

    def test_missing_file_names_the_path_problem(self):
        result = run_loadkey(self.env_file)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("mangools.env: cannot open "))

    def test_file_without_key_line_fails_without_echoing_its_content(self):
        self.env_file.write_text("MANGOOLS_KEY=s3cret-value\n")
        result = run_loadkey(self.env_file)
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertEqual(result.stderr, "mangools.env: no MANGOOLS_API_KEY=... line found\n")


if __name__ == "__main__":
    unittest.main()
