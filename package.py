#!/usr/bin/env python3
"""Build dist/kw-research-pipeline.skill from the skill files of one commit.

The archive holds the files as committed, never the working tree, so an
uncommitted edit or the CRLF line endings of a Windows checkout (core.autocrlf)
cannot ship. Its layout is the one of the v7.3 release asset: each folder's
entry before its files, MS-DOS attributes and the commit's time on every entry,
so one commit always gives the same archive.
"""
import argparse
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILL_NAME = "kw-research-pipeline"
VERSION_SOURCE = ("SKILL.md", "H1")
VERSION_PATTERNS = {
    VERSION_SOURCE: r"^# KW Research Pipeline \(v([0-9.]+)\)$",
    ("SKILL.md", "description"): r"^description:.*\bVersion (\d+(?:\.\d+)*)",
    ("CUSTOMER-README.md", "H1"): r"^# KW Research Pipeline — Setup \(v([0-9.]+)\)$",
    ("scripts/mangools.py", "User-Agent"): r"kw-research-pipeline/([0-9.]+)\)",
}
MSDOS_DIRECTORY = 0x10
MSDOS_ARCHIVE = 0x20  # a plain file; zipfile would store Unix mode 0600 for 0


def _version_in(text, pattern):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def version_problems(texts):
    """`texts` maps a skill file's path to its text. Returns the version of the
    SKILL.md H1 and one problem for each place that states another version."""
    found = {place: _version_in(texts.get(place[0], ""), pattern) for place, pattern in VERSION_PATTERNS.items()}
    version = found[VERSION_SOURCE]
    if version is None:
        return None, ["SKILL.md: no version in the H1"]
    problems = [f"{path} ({where}): {found_version or 'no version'}, expected {version} from the SKILL.md H1"
                for (path, where), found_version in found.items() if found_version != version]
    return version, problems


def _git(*args):
    result = subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=False)
    if result.returncode:
        sys.exit(f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def committed_skill_files(ref):
    """{path: content} of every skill file as committed in `ref`."""
    files = {}
    for entry in _git("ls-tree", "-r", "-z", ref, "--", SKILL_NAME).split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, _kind, blob = meta.decode().split()
        if mode not in ("100644", "100755"):
            sys.exit(f"{path.decode()} is not a regular file in {ref}, nothing built")
        files[path.decode()] = _git("cat-file", "blob", blob)
    return files


def key_files(paths):
    """Paths named like an API key file (mangools.env, .env)."""
    return [path for path in paths if path.lower().endswith(".env")]


def _entries(paths):
    """Every file and every folder above it, sorted, so a folder precedes its files."""
    names = set(paths)
    for path in paths:
        folders = path.split("/")[:-1]
        names.update("/".join(folders[:depth]) + "/" for depth in range(1, len(folders) + 1))
    return sorted(names)


def build(out_dir, ref="HEAD"):
    files = committed_skill_files(ref)
    leaked = key_files(files)
    if leaked:
        sys.exit("API key file in the skill folder, nothing built. Untrack it with git rm --cached "
                 "and, if it was ever pushed, replace that key:\n  " + "\n  ".join(leaked))
    texts = {path: files[f"{SKILL_NAME}/{path}"].decode("utf-8")
             for path, _where in VERSION_PATTERNS if f"{SKILL_NAME}/{path}" in files}
    version, problems = version_problems(texts)
    if problems:
        sys.exit("version mismatch, nothing built:\n  " + "\n  ".join(problems))
    stamp = time.gmtime(int(_git("log", "-1", "--format=%ct", ref).decode()))[:6]
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"{SKILL_NAME}.skill"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name in _entries(files):
            entry = zipfile.ZipInfo(name, stamp)
            entry.create_system = 0  # MS-DOS attributes on every OS, as in the v7.3 asset
            if name.endswith("/"):
                entry.external_attr = MSDOS_DIRECTORY
                archive.writestr(entry, b"")
            else:
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = MSDOS_ARCHIVE
                archive.writestr(entry, files[name])
    print(f"built {archive_path} from {ref} (v{version})")
    if ref == "HEAD":
        changes = _git("status", "--porcelain", "--untracked-files=all", "--", SKILL_NAME)
        if changes.strip():
            print("note: uncommitted changes are not in the archive:\n" + changes.decode(errors="replace").rstrip(),
                  file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=f"Build dist/{SKILL_NAME}.skill from the skill files of a commit")
    parser.add_argument("--out", type=Path, default=REPO / "dist", help="Output folder (default: dist)")
    parser.add_argument("--ref", default="HEAD",
                        help="Commit or tag to build (default: HEAD); uncommitted changes never ship")
    args = parser.parse_args()
    build(args.out, args.ref)


if __name__ == "__main__":
    main()
