import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

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


# A made-up key in the shape of a real one (64 lowercase hex characters).
DUMMY_KEY = "0123456789abcdef" * 4


class KeyFileTest(unittest.TestCase):
    def key_files_in(self, files):
        """key_files over `files` ({path: bytes}) written to a throwaway checkout."""
        with tempfile.TemporaryDirectory() as root:
            for name, content in files.items():
                (Path(root) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(root) / name).write_bytes(content)
            with mock.patch.object(package, "REPO", Path(root)):
                return package.key_files(list(files))

    def test_finds_key_files_anywhere_in_the_skill_folder(self):
        paths = ["kw-research-pipeline/SKILL.md", "kw-research-pipeline/mangools.env",
                 "kw-research-pipeline/scripts/.env", "kw-research-pipeline/MANGOOLS.ENV",
                 "kw-research-pipeline/references/environment.md"]
        self.assertEqual(self.key_files_in(dict.fromkeys(paths, b"text")), paths[1:4])

    def test_finds_a_key_by_its_content_under_any_file_name(self):
        files = {
            # Notepad saves a file typed as mangools.env with a hidden .txt.
            "kw-research-pipeline/mangools.env.txt": f"MANGOOLS_API_KEY={DUMMY_KEY}\r\n".encode(),
            "kw-research-pipeline/scripts/.env.local": f"export MANGOOLS_API_KEY = '{DUMMY_KEY}'\n".encode(),
            "kw-research-pipeline/key.txt": f'mangools_api_key="{DUMMY_KEY}"\n'.encode("utf-16"),
            "kw-research-pipeline/SKILL.md": b"Save MANGOOLS_API_KEY=<your key> as mangools.env\n",
            "kw-research-pipeline/hash.md": f"sha256 {DUMMY_KEY}\n".encode(),
        }
        self.assertEqual(self.key_files_in(files), list(files)[:3])

    def test_git_ignores_a_key_file_saved_in_the_skill_folder(self):
        for name in ("mangools.env", "mangools.env.txt", ".env", ".env.local"):
            with self.subTest(name):
                result = subprocess.run(["git", "check-ignore", "-q", "--no-index", f"kw-research-pipeline/{name}"],
                                        cwd=REPO, check=False)
                self.assertEqual(result.returncode, 0)


class BuildTest(unittest.TestCase):
    def test_archive_holds_exactly_the_tracked_skill_files(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run([sys.executable, "-B", str(REPO / "package.py"), "--out", out],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(Path(out) / "kw-research-pipeline.skill") as archive:
                self.assertEqual(sorted(archive.namelist()), SHIPPED_FILES)

    def test_refuses_to_build_when_a_key_file_is_tracked(self):
        tracked = [*SHIPPED_FILES, "kw-research-pipeline/mangools.env"]
        with tempfile.TemporaryDirectory() as out, \
                mock.patch.object(package, "_tracked_skill_files", return_value=tracked):
            with self.assertRaises(SystemExit) as exit_:
                package.build(Path(out))
            self.assertIn("kw-research-pipeline/mangools.env", str(exit_.exception.code))
            self.assertFalse((Path(out) / "kw-research-pipeline.skill").exists())


if __name__ == "__main__":
    unittest.main()
