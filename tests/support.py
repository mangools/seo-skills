import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / "kw-research-pipeline"
SCRIPTS_DIR = SKILL_DIR / "scripts"
FROZEN_NOW = 1_000_000.0
TEST_KEY = "test-key"
UNEXPECTED_REQUEST = (404, {"error": {"type": "NotFound", "message": "unexpected request in test"}})


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mangools = load_module(SCRIPTS_DIR / "mangools.py", "mangools")

BOSTON = {"_id": 1018127, "canonical_name": "Boston,Massachusetts,United States",
          "target_type": "City", "country_code": "US", "active": True}

LIMITS_PAID = {
    "highestPlan": "basic",
    "resources": {"related-keywords": {"remaining": 100, "limit": 110},
                  "serps": {"remaining": 90, "limit": 105}},
    "kw-gap-max-competitors": 5,
    "related-keywords-rows": 200,
    "competitor-keywords-rows": 25,
}


def serp_response(kw, domains, paa=()):
    slug = kw.replace(" ", "-")
    items = [{"type": "ADV_TOP", "url": "https://ads.test/", "domain": "ads.test", "title": "Ad"}]
    items += [{"type": "ORGANIC", "url": f"https://{domain}/{slug}", "domain": domain,
               "title": f"{domain} on {kw}"} for domain in domains]
    if paa:
        items.append({"type": "PEOPLE_ALSO_ASK", "items": [{"question": q} for q in paa]})
    return {"kw": kw, "rank": 42, "items": items}


class _Response:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeMangools:
    def __init__(self, routes):
        self._replies = {path: list(replies) for path, replies in routes.items()}
        self.requests = []

    def __call__(self, request, timeout=None):
        url = urllib.parse.urlsplit(request.full_url)
        path = url.path.removeprefix("/v3")
        self.requests.append((path, dict(urllib.parse.parse_qsl(url.query))))
        replies = self._replies.get(path)
        status, body = replies.pop(0) if replies else UNEXPECTED_REQUEST
        raw = (body if isinstance(body, str) else json.dumps(body)).encode()
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(raw))
        return _Response(status, raw)

    def paths(self):
        return [path for path, _ in self.requests]

    def location_ids(self, path):
        return [query.get("location_id") for requested, query in self.requests if requested == path]


@dataclass
class CliRun:
    exit_code: int
    stdout: str
    api: FakeMangools
    sleeps: list


def run_cli(*argv, routes=None):
    api = FakeMangools(routes or {})
    sleeps = []
    stdout = io.StringIO()
    with tempfile.TemporaryDirectory() as pace_dir, contextlib.ExitStack() as stack:
        for patch in (
            mock.patch.object(sys, "argv", ["mangools.py", *argv]),
            mock.patch.dict(os.environ, {"MANGOOLS_API_KEY": TEST_KEY}),
            mock.patch("urllib.request.urlopen", api),
            mock.patch("time.sleep", sleeps.append),
            mock.patch("time.time", lambda: FROZEN_NOW),
            mock.patch.object(tempfile, "tempdir", pace_dir),
            mock.patch.dict(mangools._LAST, clear=True),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            stack.enter_context(patch)
        try:
            mangools.main()
            exit_code = 0
        except SystemExit as stop:
            exit_code = stop.code
    return CliRun(exit_code, stdout.getvalue(), api, sleeps)
