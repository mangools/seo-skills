#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILL_NAME = "kw-research-pipeline"
VERSION_SOURCE = "SKILL.md"
VERSION_PATTERNS = {
    VERSION_SOURCE: r"^# KW Research Pipeline \(v([0-9.]+)\)$",
    "CUSTOMER-README.md": r"^# KW Research Pipeline — Setup \(v([0-9.]+)\)$",
    "scripts/mangools.py": r"kw-research-pipeline/([0-9.]+)\)",
}


def _version_in(text, pattern):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def version_problems(texts):
    found = {path: _version_in(texts[path], pattern) for path, pattern in VERSION_PATTERNS.items()}
    version = found[VERSION_SOURCE]
    if version is None:
        return None, [f"{VERSION_SOURCE}: no version in the H1"]
    problems = [f"{path}: {found_version or 'no version'}, expected {version} from {VERSION_SOURCE}"
                for path, found_version in found.items() if found_version != version]
    return version, problems


def _tracked_skill_files():
    listing = subprocess.run(["git", "ls-files", "-z", "--", SKILL_NAME], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout
    return [name for name in listing.split("\0") if name]


def build(out_dir):
    skill_dir = REPO / SKILL_NAME
    texts = {path: (skill_dir / path).read_text(encoding="utf-8") for path in VERSION_PATTERNS}
    version, problems = version_problems(texts)
    if problems:
        sys.exit("version mismatch, nothing built:\n  " + "\n  ".join(problems))
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"{SKILL_NAME}.skill"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in _tracked_skill_files():
            archive.write(REPO / name, name)
    print(f"built {archive_path} (v{version})")


def main():
    parser = argparse.ArgumentParser(description=f"Build dist/{SKILL_NAME}.skill from the tracked skill files")
    parser.add_argument("--out", type=Path, default=REPO / "dist", help="Output folder (default: dist)")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
