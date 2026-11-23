import json
import tempfile
import unittest
from pathlib import Path

from support import LIMITS_PAID, run_cli, serp_response

BOSTON_LABEL = "Boston,Massachusetts,United States"
COUNTRY_SERP = serp_response("seo tools", ["alpha.test", "beta.test"], paa=["What is SEO?"])
CITY_SERP = serp_response("seo tools", ["alpha.test", "gamma.test"], paa=["Is SEO worth it?"])
FREE_DAILY = {"related-keywords": {"remaining": 5, "limit": 5}, "serps": {"remaining": 5, "limit": 5}}

MISSING = object()

CASES = [
    ("missing file", MISSING, 1, ["call failed: cannot open"]),
    ("empty file", "", 1, ["call failed: empty file"]),
    ("HTML page", "<html><body>Blocked by proxy allowlist</body></html>", 1,
     ["call failed: <html>", "(not JSON)"]),
    ("cut-off JSON", '{"keywords": [{"kw": "seo', 1, ["not valid JSON; cut off"]),
    ("error JSON", {"error": "Mangools 403: Forbidden"}, 1,
     ['call failed: {"error": "Mangools 403: Forbidden"}']),
    ("serp-dual with failed city half",
     {"error": "Mangools 503: No available SERP provider (city half)", "kw": "seo tools",
      "country": {"code": "us", "location_id": 2840, "serp": COUNTRY_SERP}}, 1,
     ["call failed:", "country half kept in this file under country",
      "country 1 | alpha.test", "PAA (country): What is SEO?"]),
    ("list of non-objects", [1, 2], 1, ["call failed: unexpected response shape"]),
    ("empty locations", [], 1, ["no location matched"]),
    ("locations",
     [{"id": 2840, "label": "United States", "type": "Country", "country": "us", "active": True},
      {"id": 1018127, "label": BOSTON_LABEL, "type": "City", "country": "us", "active": False}], 0,
     ["2 rows (cities first)", f"1018127 | {BOSTON_LABEL} | City | INACTIVE",
      "2840 | United States | Country | active"]),
    ("related",
     {"keywords": [{"kw": "seo tools", "sv": 1000, "seo": 40, "cpc": 2.5}], "countKeywordsBeforeLimit": 350}, 0,
     ["1 rows, 350 before plan cap", "seo tools | 1000 | 40 | 2.5"]),
    ("import-keywords",
     {"keywords": [{"kw": "what is seo", "sv": 500, "seo": 30, "cpc": 1.0},
                   {"kw": "why seo", "sv": None, "seo": None, "cpc": None}],
      "countKeywordsBeforeLimit": 2, "language": 1000, "location": 2840, "imported": 2}, 0,
     ["2 rows for 2 imported keywords | 1 with volume"]),
    ("domain-keywords",
     {"keywords": [{"kw": "backlink checker", "sv": 900, "position": 45},
                   {"kw": "free backlink tool", "sv": 300, "position": 60}],
      "url_type": "domain", "totalCount": 1200, "countKeywordsBeforeLimit": 1200}, 0,
     ["2 keywords returned of 1200 the domain ranks for | positions 45–60",
      "recurring terms (hint at the site's field): backlink 2", "backlink checker | 900 | 45"]),
    ("single serp",
     {"kw": "seo tools", "rank": 42, "items": [
         {"type": "ADV_TOP", "url": "https://ads.test/", "domain": "ads.test", "title": "Ad"},
         {"type": "ORGANIC", "url": "https://www.alpha.test/r?id=1", "domain": "www.alpha.test",
          "destination_url": "https://www.alpha.test/seo-tools", "title": "Alpha SEO tools"},
         {"type": "PEOPLE_ALSO_ASK", "items": [{"question": "What is an SEO tool?"}]}]}, 0,
     ["kw seo tools | KD 42", "organic 1 | alpha.test | https://www.alpha.test/seo-tools",
      "PAA: What is an SEO tool?"]),
    ("serp-dual",
     {"kw": "seo tools",
      "country": {"code": "us", "location_id": 2840, "serp": COUNTRY_SERP},
      "city": {"location_id": 1018127, "label": BOSTON_LABEL, "serp": CITY_SERP},
      "comparison": {
          "country_results": [{"pos": 1, "domain": "beta.test", "url": "https://beta.test/x", "title": "B"}],
          "city_results": [{"pos": 1, "domain": "gamma.test", "url": "https://gamma.test/x", "title": "G"}],
          "shared_domains": [], "country_only": ["beta.test"], "city_only": ["gamma.test"],
          "overlap_pct": 0.0}}, 0,
     [f"city {BOSTON_LABEL} | overlap 0.0 %", "country 1 | beta.test", "city 1 | gamma.test",
      "PAA (country): What is SEO?", "PAA (city): Is SEO worth it?"]),
    ("suggest-cities",
     {"country": "us", "country_id": 2840, "country_label": "the United States",
      "cities": [{"name": "Boston", "location_id": 1018127, "label": BOSTON_LABEL}],
      "client_message": "Which city should we use?"}, 0,
     [f"1018127 | {BOSTON_LABEL}", "Which city should we use?"]),
    ("suggest-cities without a city list",
     {"country": "es", "country_id": 2724, "country_label": "Spain", "cities": [],
      "client_message": "Please name a city."}, 0,
     ["no built-in city list for Spain", "Please name a city."]),
    ("limits, paid plan", LIMITS_PAID, 0,
     ["plan basic | keyword lookups left 100 / 110 | SERP units left 90 / 105",
      "gap takes up to 5 competitors per call"]),
    ("limits, welcome bonus left",
     {"highestPlan": "free", "resources": FREE_DAILY,
      "permanent_credits": {"related-keywords": {"remaining": 80, "limit": 100},
                            "serps": {"remaining": 60, "limit": 100}}}, 0,
     ["welcome bonus left: 80 / 100 keyword lookups, 60 / 100 SERP units"]),
    ("limits, welcome bonus spent for SERPs",
     {"highestPlan": "free", "resources": FREE_DAILY,
      "permanent_credits": {"related-keywords": {"remaining": 80, "limit": 100},
                            "serps": {"remaining": 0, "limit": 100}}}, 0,
     ["welcome bonus used up for SERP units"]),
    ("limits, unknown key",
     {"highestPlan": "free", "resources": {"related-keywords": {"remaining": 0, "limit": 0},
                                           "serps": {"remaining": 0, "limit": 0}}}, 0,
     ["key not recognised"]),
    ("gap",
     {"isAllowedPagination": False, "resultsSize": 25, "results": [
         {"domain": "rival.test", "totalCount": 900,
          "keywords": [{"kw": "rank tracker", "sv": 2400, "seo": 55, "position": 3}]}]}, 0,
     ["1 competitors | isAllowedPagination False | resultsSize 25",
      "-- rival.test | totalCount 900 | 1 rows returned", "rank tracker | 2400 | 55 | pos 3"]),
    ("unrecognised object", {"foo": 1}, 0, ["unrecognised file"]),
]


class ShowTest(unittest.TestCase):
    def assert_in_order(self, text, fragments):
        position = 0
        for fragment in fragments:
            found = text.find(fragment, position)
            self.assertNotEqual(found, -1, f"{fragment!r} missing after position {position} in:\n{text}")
            position = found + len(fragment)

    def test_summarises_every_file_type_with_the_documented_lines(self):
        with tempfile.TemporaryDirectory() as workdir:
            for name, content, exit_code, fragments in CASES:
                with self.subTest(name):
                    path = Path(workdir) / f"{name}.json"
                    if content is not MISSING:
                        path.write_text(content if isinstance(content, str) else json.dumps(content),
                                        encoding="utf-8")
                    run = run_cli("show", str(path))
                    self.assertEqual(run.exit_code, exit_code, run.stdout)
                    self.assert_in_order(run.stdout, fragments)


if __name__ == "__main__":
    unittest.main()
