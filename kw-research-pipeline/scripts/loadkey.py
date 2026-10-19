#!/usr/bin/env python3
"""Print the Mangools API key found in an uploaded mangools.env file.

Usage (always inside $(...), never on its own, so the key is not shown):
  export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-mangools.env>)"; <command>

Accepts: plain or CRLF line endings, an optional `export ` prefix, spaces
around `=`, single or double quotes, a UTF-8 BOM, UTF-16 with BOM, and the
key on any line. Exits 1 with a short message (no file contents) if the file
is missing or holds no MANGOOLS_API_KEY=... line.
"""
import re
import sys

if len(sys.argv) != 2:
    sys.exit("usage: loadkey.py <path-to-mangools.env>")
path = sys.argv[1]
try:
    raw = open(path, "rb").read()
except OSError as e:
    sys.exit(f"mangools.env: cannot open {path} ({e.strerror}); check the upload path")
text = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig", "replace")
m = re.search(r'^[ \t]*(?:export[ \t]+)?MANGOOLS_API_KEY[ \t]*=[ \t]*["\']?([^\s"\']+)', text, re.I | re.M)
if not m:
    sys.exit("mangools.env: no MANGOOLS_API_KEY=... line found")
print(m.group(1))
