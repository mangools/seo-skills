import json
import unittest

from support import BOSTON, LIMITS_PAID, mangools, run_cli, serp_response

SERPS = "/serpchecker/serps"
RELATED = "/kwfinder/related-keywords"
RELATED_OK = {"keywords": [{"kw": "seo tools", "sv": 1000, "seo": 40, "cpc": 2.5}], "countKeywordsBeforeLimit": 1}
CREDIT_LIMIT = {"error": {"type": "CreditLimit", "message": "Daily limit reached", "reset": 3600}}
RATE_LIMIT = {"error": {"type": "RateLimit", "message": "Too many requests in short period", "retry_after": 2}}
ANTI_BOT_PAGE = "<html><body>Unathorized access</body></html>"
NASHVILLE_ARKANSAS = {"_id": 9001, "canonical_name": "Nashville,Arkansas,United States",
                      "target_type": "City", "country_code": "US", "active": True}
NASHVILLE_TENNESSEE = {"_id": 9002, "canonical_name": "Nashville,Tennessee,United States",
                       "target_type": "City", "country_code": "US", "active": True}
BROOKLYN = {"_id": 1022762, "canonical_name": "Brooklyn,New York,United States",
            "target_type": "Borough", "country_code": "US", "active": True}
UNKNOWN_LOCATION_ID = 999999
EMPTY_NOT_FOUND = (404, "")


def dual_serps(country_domains, city_domains):
    return [(200, serp_response("seo tools", country_domains)), (200, serp_response("seo tools", city_domains))]


def serp_dual_for_boston(country_domains=("alpha.test",), city_domains=("alpha.test",)):
    return run_cli("serp-dual", "--kw", "seo tools", "--country", "us", "--city-id", str(BOSTON["_id"]),
                   routes={f"/kwfinder/locations/{BOSTON['_id']}": [(200, BOSTON)],
                           SERPS: dual_serps(country_domains, city_domains)})


class SerpDualTest(unittest.TestCase):
    def test_overlap_counts_a_domain_holding_two_positions_once(self):
        run = serp_dual_for_boston(["alpha.test", "alpha.test", "beta.test"], ["alpha.test", "gamma.test"])
        self.assertEqual(run.exit_code, 0, run.stdout)
        comparison = json.loads(run.stdout)["comparison"]
        self.assertEqual(comparison["shared_domains"], ["alpha.test"])
        self.assertEqual(comparison["overlap_pct"], 33.3)
        self.assertEqual(run.api.location_ids(SERPS), ["2840", str(BOSTON["_id"])])

    def test_rejects_city_id_outside_the_run_country_before_any_serp(self):
        rows = {
            "city abroad": {"_id": 2643743, "canonical_name": "London,England,United Kingdom",
                            "target_type": "City", "country_code": "GB", "active": True},
            "the country itself": {"_id": 2840, "canonical_name": "United States",
                                   "target_type": "Country", "country_code": "US", "active": True},
        }
        for name, row in rows.items():
            with self.subTest(name):
                run = run_cli("serp-dual", "--kw", "seo tools", "--country", "us", "--city-id", str(row["_id"]),
                              routes={f"/kwfinder/locations/{row['_id']}": [(200, row)],
                                      SERPS: dual_serps(["alpha.test"], ["alpha.test"])})
                self.assertEqual(run.exit_code, 1, run.stdout)
                self.assertIn(row["canonical_name"], json.loads(run.stdout)["error"])
                self.assertNotIn(SERPS, run.api.paths())

    def test_accepts_a_place_inside_the_run_country_that_is_not_a_city(self):
        run = run_cli("serp-dual", "--kw", "seo tools", "--country", "us", "--city-id", str(BROOKLYN["_id"]),
                      routes={f"/kwfinder/locations/{BROOKLYN['_id']}": [(200, BROOKLYN)],
                              SERPS: dual_serps(["alpha.test"], ["alpha.test"])})
        self.assertEqual(run.exit_code, 0, run.stdout)
        self.assertEqual(run.api.location_ids(SERPS), ["2840", str(BROOKLYN["_id"])])

    def test_unknown_city_id_is_named_unknown_before_any_serp(self):
        run = run_cli("serp-dual", "--kw", "seo tools", "--country", "us", "--city-id", str(UNKNOWN_LOCATION_ID),
                      routes={f"/kwfinder/locations/{UNKNOWN_LOCATION_ID}": [EMPTY_NOT_FOUND],
                              SERPS: dual_serps(["alpha.test"], ["alpha.test"])})
        self.assertEqual(run.exit_code, 1, run.stdout)
        self.assertIn(f"--city-id {UNKNOWN_LOCATION_ID} is not a known Mangools location",
                      json.loads(run.stdout)["error"])
        self.assertNotIn(SERPS, run.api.paths())

    def test_unknown_country_id_is_refused_as_not_a_country(self):
        run = run_cli("serp-dual", "--kw", "seo tools", "--country", str(UNKNOWN_LOCATION_ID),
                      "--city-id", str(BOSTON["_id"]),
                      routes={f"/kwfinder/locations/{UNKNOWN_LOCATION_ID}": [EMPTY_NOT_FOUND]})
        self.assertEqual(run.exit_code, 1, run.stdout)
        self.assertIn(f"Location {UNKNOWN_LOCATION_ID} is not a country", json.loads(run.stdout)["error"])

    def test_city_name_resolves_within_its_region(self):
        run = run_cli("serp-dual", "--kw", "seo tools", "--country", "us", "--city", "Nashville, Tennessee",
                      routes={"/kwfinder/locations": [(200, [NASHVILLE_ARKANSAS, NASHVILLE_TENNESSEE])],
                              SERPS: dual_serps(["alpha.test"], ["alpha.test"])})
        self.assertEqual(run.exit_code, 0, run.stdout)
        self.assertEqual(run.api.location_ids(SERPS), ["2840", str(NASHVILLE_TENNESSEE["_id"])])


class CityMessageTest(unittest.TestCase):
    def test_states_the_city_check_cost_at_both_rates(self):
        message = mangools._city_explainer("us", [], "seo tools")
        self.assertIn("2 extra SERP units on paid Mangools plans", message)
        self.assertIn("1 while your welcome bonus lasts", message)


class LimitsTest(unittest.TestCase):
    def test_prints_the_quota_response(self):
        run = run_cli("limits", routes={"/kwfinder/limits": [(200, LIMITS_PAID)]})
        self.assertEqual(run.exit_code, 0, run.stdout)
        self.assertEqual(json.loads(run.stdout), LIMITS_PAID)


class RequestPolicyTest(unittest.TestCase):
    def test_waits_eleven_seconds_between_requests_of_one_pool(self):
        run = serp_dual_for_boston()
        self.assertEqual(run.exit_code, 0, run.stdout)
        self.assertEqual(run.sleeps, [11])

    def test_retries_transient_failures_but_stops_at_once_on_used_up_quota(self):
        cases = [
            ("credit limit", [(429, CREDIT_LIMIT)], 3, 1, "CreditLimit"),
            ("rate limit", [(429, RATE_LIMIT), (200, RELATED_OK)], 0, 2, '"keywords"'),
            ("anti-bot page", [(401, ANTI_BOT_PAGE), (200, RELATED_OK)], 0, 2, '"keywords"'),
        ]
        for name, replies, exit_code, request_count, output in cases:
            with self.subTest(name):
                run = run_cli("related", "--kw", "seo tools", routes={RELATED: replies})
                self.assertEqual((run.exit_code, len(run.api.requests)), (exit_code, request_count))
                self.assertIn(output, run.stdout)


if __name__ == "__main__":
    unittest.main()
