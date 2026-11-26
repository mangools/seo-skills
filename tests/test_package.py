import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from support import REPO, load_module

package = load_module(REPO / "package.py", "package")

# The layout of the v7.3 release asset: each folder's entry before its files.
SHIPPED_ENTRIES = [
    "kw-research-pipeline/",
    "kw-research-pipeline/CUSTOMER-README.md",
    "kw-research-pipeline/SKILL.md",
    "kw-research-pipeline/references/",
    "kw-research-pipeline/references/methodology.md",
    "kw-research-pipeline/scripts/",
    "kw-research-pipeline/scripts/loadkey.py",
    "kw-research-pipeline/scripts/mangools.py",
]

CONSISTENT = {
    "SKILL.md": "---\nname: x\ndescription: Research keywords. Version 7.4.\n---\n\n# KW Research Pipeline (v7.4)\n",
    "CUSTOMER-README.md": "# KW Research Pipeline — Setup (v7.4)\n",
    "scripts/mangools.py": 'headers = {"User-Agent": "Mozilla/5.0 (compatible; kw-research-pipeline/7.4)"}\n',
}


def build(repo, out, env=None):
    return subprocess.run([sys.executable, "-B", str(repo / "package.py"), "--out", str(out)],
                          capture_output=True, text=True, check=False, env=env)


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

    def test_names_a_stale_version_in_the_skill_description(self):
        skill = CONSISTENT["SKILL.md"].replace("Version 7.4.", "Version 7.3.")
        version, problems = package.version_problems({**CONSISTENT, "SKILL.md": skill})
        self.assertEqual(version, "7.4")
        self.assertEqual(problems, ["SKILL.md (description): 7.3, expected 7.4 from the SKILL.md H1"])


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
    def test_archive_holds_the_committed_skill_files_in_the_v7_3_layout(self):
        with tempfile.TemporaryDirectory() as out:
            result = build(REPO, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(Path(out) / "kw-research-pipeline.skill") as archive:
                self.assertEqual(archive.namelist(), SHIPPED_ENTRIES)
                for entry in archive.infolist():
                    with self.subTest(entry.filename):
                        self.assertEqual(entry.create_system, 0)
                        # No Unix mode, so unzip gives the default permissions, as for v7.3.
                        self.assertEqual(entry.external_attr >> 16, 0)
                        if entry.is_dir():
                            self.assertEqual(entry.external_attr, 0x10)
                            continue
                        committed = subprocess.run(["git", "cat-file", "blob", f"HEAD:{entry.filename}"],
                                                   cwd=REPO, capture_output=True, check=True).stdout
                        self.assertEqual(archive.read(entry), committed)

    def test_ships_the_commit_not_the_working_tree_and_rebuilds_it_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "gitconfig").write_text("")
            # A throwaway repository, isolated from the developer's git config (hooks, signing, autocrlf).
            env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                   "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
            repo, skill = tmp / "repo", tmp / "repo" / "kw-research-pipeline"
            (skill / "scripts").mkdir(parents=True)
            shutil.copy(REPO / "package.py", repo)
            for path, text in CONSISTENT.items():
                (skill / path).write_bytes(text.encode())

            def git(*args):
                subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, check=True)

            git("init", "-q")
            git("add", "-A")
            git("commit", "-q", "-m", "skill")
            committed = (skill / "SKILL.md").read_bytes()
            # What a Windows checkout with core.autocrlf looks like, plus an edit nobody committed.
            git("config", "core.autocrlf", "true")
            (skill / "SKILL.md").write_bytes(committed.replace(b"\n", b"\r\n") + b"uncommitted edit\r\n")

            archives = []
            for out in ("first", "second"):
                result = build(repo, tmp / out, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                archives.append((tmp / out / "kw-research-pipeline.skill").read_bytes())
            self.assertIn("uncommitted changes are not in the archive", result.stderr)
            with zipfile.ZipFile(io.BytesIO(archives[0])) as archive:
                self.assertEqual(archive.read("kw-research-pipeline/SKILL.md"), committed)
            self.assertEqual(archives[0], archives[1])

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
