import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from support import REPO, load_module

package = load_module(REPO / "package.py", "package")

SHIPPED_FILES = [
    "kw-research-pipeline/CUSTOMER-README.md",
    "kw-research-pipeline/SKILL.md",
    "kw-research-pipeline/references/methodology.md",
    "kw-research-pipeline/scripts/loadkey.py",
    "kw-research-pipeline/scripts/mangools.py",
]

CONSISTENT = {
    "SKILL.md": "---\nname: x\n---\n\n# KW Research Pipeline (v7.4)\n",
    "CUSTOMER-README.md": "# KW Research Pipeline — Setup (v7.4)\n",
    "scripts/mangools.py": 'headers = {"User-Agent": "Mozilla/5.0 (compatible; kw-research-pipeline/7.4)"}\n',
}


class VersionCheckTest(unittest.TestCase):
    def test_names_each_file_whose_version_differs_from_skill_md(self):
        stale = {
            "CUSTOMER-README.md": "# KW Research Pipeline — Setup (v7.3)\n",
            "scripts/mangools.py": 'headers = {"User-Agent": "Mozilla/5.0 (compatible; kw-research-pipeline/7.3)"}\n',
        }
        for path, text in stale.items():
            with self.subTest(path):
                version, problems = package.version_problems({**CONSISTENT, path: text})
                self.assertEqual(version, "7.4")
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(path, problems[0])


class BuildTest(unittest.TestCase):
    def test_archive_holds_exactly_the_tracked_skill_files(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run([sys.executable, "-B", str(REPO / "package.py"), "--out", out],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(Path(out) / "kw-research-pipeline.skill") as archive:
                self.assertEqual(sorted(archive.namelist()), SHIPPED_FILES)


if __name__ == "__main__":
    unittest.main()
