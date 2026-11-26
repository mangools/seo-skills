import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

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
    def test_finds_key_files_anywhere_in_the_skill_folder(self):
        paths = ["kw-research-pipeline/SKILL.md", "kw-research-pipeline/mangools.env",
                 "kw-research-pipeline/scripts/.env", "kw-research-pipeline/MANGOOLS.ENV",
                 "kw-research-pipeline/references/environment.md"]
        self.assertEqual(package.key_files(dict.fromkeys(paths, b"text")), paths[1:4])

    def test_finds_a_key_by_its_content_under_any_file_name(self):
        files = {
            # Notepad saves a file typed as mangools.env with a hidden .txt.
            "kw-research-pipeline/mangools.env.txt": f"MANGOOLS_API_KEY={DUMMY_KEY}\r\n".encode(),
            "kw-research-pipeline/scripts/.env.local": f"export MANGOOLS_API_KEY = '{DUMMY_KEY}'\n".encode(),
            "kw-research-pipeline/key.txt": f'mangools_api_key="{DUMMY_KEY}"\n'.encode("utf-16"),
            "kw-research-pipeline/SKILL.md": b"Save MANGOOLS_API_KEY=<your key> as mangools.env\n",
            "kw-research-pipeline/hash.md": f"sha256 {DUMMY_KEY}\n".encode(),
        }
        self.assertEqual(package.key_files(files), list(files)[:3])

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

    def repository(self):
        """A throwaway repository holding a consistent skill as its one commit, isolated from the
        developer's git config (hooks, signing, autocrlf). Returns it and the env for git and package.py."""
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        tmp = Path(tmp_dir.name)
        (tmp / "gitconfig").write_text("")
        env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
               "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
               # An even second, because zip stores time in two-second steps.
               "GIT_COMMITTER_DATE": "2026-01-02T03:04:06Z"}
        repo, skill = tmp / "repo", tmp / "repo" / "kw-research-pipeline"
        (skill / "scripts").mkdir(parents=True)
        shutil.copy(REPO / "package.py", repo)
        for path, text in CONSISTENT.items():
            (skill / path).write_bytes(text.encode())
        self.git(repo, env, "init", "-q")
        self.git(repo, env, "add", "-A")
        self.git(repo, env, "commit", "-q", "-m", "skill")
        return repo, env

    @staticmethod
    def git(repo, env, *args):
        subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, check=True)

    def test_ships_the_commit_not_the_working_tree_and_rebuilds_it_byte_for_byte(self):
        repo, env = self.repository()
        skill = repo / "kw-research-pipeline"
        committed = (skill / "SKILL.md").read_bytes()
        # What a Windows checkout with core.autocrlf looks like, plus an edit nobody committed.
        self.git(repo, env, "config", "core.autocrlf", "true")
        (skill / "SKILL.md").write_bytes(committed.replace(b"\n", b"\r\n") + b"uncommitted edit\r\n")

        archives = []
        for out in ("first", "second"):
            result = build(repo, repo.parent / out, env)
            self.assertEqual(result.returncode, 0, result.stderr)
            archives.append((repo.parent / out / "kw-research-pipeline.skill").read_bytes())
        self.assertIn("uncommitted changes are not in the archive", result.stderr)
        with zipfile.ZipFile(io.BytesIO(archives[0])) as archive:
            self.assertEqual(archive.read("kw-research-pipeline/SKILL.md"), committed)
            # The commit's time, not the time of the build, so a later build gives the same bytes.
            self.assertEqual({entry.date_time for entry in archive.infolist()}, {(2026, 1, 2, 3, 4, 6)})
        self.assertEqual(archives[0], archives[1])

    def test_refuses_to_build_when_a_key_file_is_committed(self):
        repo, env = self.repository()
        (repo / "kw-research-pipeline" / "mangools.env").write_text("MANGOOLS_API_KEY=test-key\n")
        self.git(repo, env, "add", "-f", "kw-research-pipeline/mangools.env")
        self.git(repo, env, "commit", "-q", "-m", "key file")
        result = build(repo, repo.parent / "out", env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("kw-research-pipeline/mangools.env", result.stderr)
        self.assertFalse((repo.parent / "out" / "kw-research-pipeline.skill").exists())

    def test_ref_builds_that_commit_and_not_head(self):
        repo, env = self.repository()
        skill_md = repo / "kw-research-pipeline" / "SKILL.md"
        tagged = skill_md.read_bytes()
        self.git(repo, env, "tag", "v7.4")
        skill_md.write_bytes(tagged + b"\nAn edit committed after the tag.\n")
        self.git(repo, {**env, "GIT_COMMITTER_DATE": "2026-03-04T05:06:08Z"}, "commit", "-q", "-am", "after the tag")
        result = subprocess.run([sys.executable, "-B", str(repo / "package.py"), "--out", str(repo.parent / "out"),
                                 "--ref", "v7.4"], capture_output=True, text=True, check=False, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(repo.parent / "out" / "kw-research-pipeline.skill") as archive:
            self.assertEqual(archive.read("kw-research-pipeline/SKILL.md"), tagged)
            # The tagged commit's time, not the time of HEAD.
            self.assertEqual({entry.date_time for entry in archive.infolist()}, {(2026, 1, 2, 3, 4, 6)})

    def test_refuses_a_key_in_the_commit_that_the_working_tree_no_longer_has(self):
        repo, env = self.repository()
        notes = repo / "kw-research-pipeline" / "notes.txt"
        notes.write_text(f"MANGOOLS_API_KEY={DUMMY_KEY}\n")
        self.git(repo, env, "add", "-A")
        self.git(repo, env, "commit", "-q", "-m", "notes")
        notes.write_text("no key here\n")
        result = build(repo, repo.parent / "out", env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("kw-research-pipeline/notes.txt", result.stderr)
        self.assertFalse((repo.parent / "out" / "kw-research-pipeline.skill").exists())

if __name__ == "__main__":
    unittest.main()
