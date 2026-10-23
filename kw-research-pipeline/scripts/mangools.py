#!/usr/bin/env python3
"""
Mangools API v3 client for the KW Research Pipeline skill.

Bring-your-own-key: the customer's Mangools API key is read from the
MANGOOLS_API_KEY environment variable, or passed with --apikey.
Nothing is stored or transmitted anywhere except to api.mangools.com.

Uses only the Python standard library so it runs in Claude's code-execution
sandbox with no `pip install` required.

Commands
--------
  related    Related keywords + metrics (KWFinder)
             python mangools.py related --kw "uptime monitoring" --location 2840 --language 1000
  serp       Live SERP results for a keyword (SERPChecker)
             python mangools.py serp --kw "uptime monitoring" --location 2840
  gap        Gap analysis: your domain vs competitors (KWFinder)
             python mangools.py gap --domain you.com --competitors a.com,b.com --location 2840 --page 1
  serp-dual  Country SERP + SERP for one city in that country, with overlap stats.
             --country takes a built-in code (us gb au ca de fr), any country's
             location ID (e.g. 2724) or its name (e.g. Spain). Pass --city-id.
             python mangools.py serp-dual --kw "uptime monitoring" --country us --city-id 1018127
             python mangools.py serp-dual --kw "herramientas seo" --country Spain --city-id 1005493
  suggest-cities  Offer N random major cities in a country, each resolved to its
             location ID (free lookup, no SERP quota used)
             python mangools.py suggest-cities --country us --n 3 --kw "<seed>"
             Returns the cities plus `client_message`, the explanation to show
             the client before asking them to choose. Built-in city lists exist
             for us gb au ca de fr; for any other country `cities` is empty and
             `client_message` asks the client to name a city.
  locations  Look up Mangools/Google location IDs by name (free lookup)
             python mangools.py locations --query "Boston" --country us
  import-keywords  Volume, KD and CPC for a list of keywords (KWFinder keyword
             import; 2 keyword lookups per call of up to 100 keywords, 1 on the
             welcome bonus). Used in Step 5 to check every People-Also-Ask
             question at once.
             python mangools.py import-keywords --file data/<run>/questions.txt --location 2840 --language 1000
  domain-keywords  Keywords a domain ranks for (KWFinder suggested keywords,
             mostly positions 40-100; 2 keyword lookups, 1 on the welcome
             bonus). `show` prints the recurring terms, a hint at the site's
             field for the client profile.
             python mangools.py domain-keywords --url mangools.com --location 2840
  show       Print a compact summary of any saved output file (for SERP files
             also the People-Also-Ask questions as "PAA (country):" /
             "PAA (city):" lines), or
             "call failed: ..." (exit 1) if the file holds an error, is empty,
             is not JSON, or was cut off. Detects the file type itself.
             python mangools.py show data/<run>/related-<slug>.json [--rows 40]
  slug       Print the file-name slug of a keyword (no API call): lowercase,
             accent marks removed, letters of every script kept.
             python mangools.py slug --kw "Gartenmöbel Lounge"

All commands except show and slug print JSON to stdout. On error they print
{"error": "..."} to stdout and exit with a non-zero code.

Location IDs:  us=2840  gb=2826  au=2036  ca=2124  de=2276  fr=2250
               any other country: `locations --query "<country>"`, Country row
Language IDs:  en=1000  de=1001  fr=1002  es=1003  cs=1021  pl=1030  sk=1033
"""

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

BASE = "https://api.mangools.com/v3"


class _ApiError(Exception):
    """A Mangools call that failed for good; main() prints it as {"error": ...}."""


def _key(args):
    key = args.apikey or os.environ.get("MANGOOLS_API_KEY", "")
    if not key:
        _die("No Mangools API key. Set MANGOOLS_API_KEY or pass --apikey.")
    return key


def _die(msg, code=1):
    print(json.dumps({"error": msg}))
    sys.exit(code)


def _note(msg):
    """Progress note for the operator; stderr only, stdout stays pure JSON."""
    print("mangools.py: " + msg, file=sys.stderr, flush=True)


def _error_type(text):
    """Mangools error type from a JSON error body, e.g. RateLimit or CreditLimit."""
    try:
        j = json.loads(text)
        e = j.get("error")
        return (e.get("type") if isinstance(e, dict) else j.get("type")) or None
    except Exception:
        return None


def _retry_after(text, header=None):
    """Seconds to wait, from a Mangools error body or a Retry-After header."""
    try:
        j = json.loads(text)
        ra = (j.get("error") or {}).get("retry_after") if isinstance(j.get("error"), dict) else None
        ra = ra or j.get("retry_after")
        if ra:
            return int(ra)
    except Exception:
        pass
    try:
        return int(header) if header else None
    except Exception:
        return None


def _request(method, path, key, query=None, body=None):
    import time
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode() if body is not None else None
    headers = {"x-access-token": key, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (compatible; kw-research-pipeline/7.2)"}

    last_msg = "unknown error"
    # Mangools intermittently serves an anti-bot "Unathorized access" HTML page
    # even for valid keys. Retry a handful of times before giving up.
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        retry_hdr = None
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8", "replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            status = e.code
            retry_hdr = e.headers.get("Retry-After") if e.headers else None
        except Exception as e:  # network/DNS/timeout
            last_msg = f"Request failed: {e}"
            wait = 1.5 * (attempt + 1)
            _note(f"network error ({e}), retrying in {wait:g} s (attempt {attempt + 1}/6)")
            time.sleep(wait)
            continue

        text = raw.strip()
        # Retry the transient anti-bot HTML page.
        if text.startswith("<") and "nathorized" in text:
            last_msg = "Mangools intermittent unauthorized HTML page"
            wait = 1.5 * (attempt + 1)
            _note(f"anti-bot page, retrying in {wait:g} s (attempt {attempt + 1}/6)")
            time.sleep(wait)
            continue

        # Retry rate limits (429 RateLimit: "Too many requests in short period").
        # A 429 CreditLimit means the daily quota or the welcome bonus is used up: fail fast instead.
        if status == 429 and attempt < 5 and _error_type(text) != "CreditLimit":
            last_msg = f"Mangools 429: {text[:200]}"
            wait = min(_retry_after(text, retry_hdr) or 10, 60)
            _note(f"Mangools 429 rate limit, retrying in {wait} s (attempt {attempt + 1}/5)")
            time.sleep(wait)
            continue

        # Retry transient server-side failures (e.g. "No available SERP provider").
        if status >= 500 and attempt < 5:
            last_msg = f"Mangools {status}: {text[:200]}"
            wait = min(_retry_after(text, retry_hdr) or 5 * (attempt + 1), 30)
            _note(f"Mangools {status}, retrying in {wait} s (attempt {attempt + 1}/5)")
            time.sleep(wait)
            continue

        if status >= 400 or text.startswith("<"):
            msg = f"Mangools {status}"
            try:
                j = json.loads(text)
                e = j.get("error") if isinstance(j.get("error"), dict) else j
                parts = [e.get("type"), e.get("message") or j.get("message") or j.get("detail")]
                if isinstance(e.get("errors"), list):
                    parts.append(", ".join(str(x) for x in e["errors"]))
                if e.get("permanent_credits_used_up") or j.get("permanent_credits_used_up"):
                    unit = "SERP units" if path.startswith("/serpchecker/") else "keyword lookups"
                    parts.append(f"welcome bonus used up for {unit}; daily limits now apply at the paid rate"
                                 " (2 per request, 4 per serp-dual, 10 per gap page)")
                if e.get("reset"):
                    parts.append(f"quota resets in {e['reset']} s")
                detail = ": ".join(str(p) for p in parts if p)
                msg += ": " + (detail or (j.get("error") if isinstance(j.get("error"), str) else "") or json.dumps(j)[:300])
            except Exception:
                msg += ": " + (text[:300] or "non-JSON response")
            raise _ApiError(msg)

        try:
            return json.loads(text)
        except Exception:
            raise _ApiError(f"Could not parse Mangools response: {text[:300]}")

    raise _ApiError(f"Gave up after retries: {last_msg}")


def cmd_related(args):
    key = _key(args)
    q = {"kw": args.kw, "location_id": args.location, "language_id": args.language}
    print(json.dumps(_request("GET", "/kwfinder/related-keywords", key, query=q)))


def cmd_serp(args):
    key = _key(args)
    q = {"kw": args.kw, "location_id": args.location}
    print(json.dumps(_request("GET", "/serpchecker/serps", key, query=q)))


def cmd_import_keywords(args):
    key = _key(args)
    try:
        with open(args.file, encoding="utf-8") as f:
            kws = [line.strip() for line in f if line.strip()]
    except OSError as e:
        _die(f"Cannot read {args.file}: {e.strerror}")
    if not kws:
        _die(f"{args.file} holds no keywords (one per line).")
    rows, before = [], None
    for i in range(0, len(kws), args.chunk):
        body = {"keywords": kws[i:i + args.chunk], "location_id": int(args.location),
                "language_id": int(args.language)}
        res = _request("POST", "/kwfinder/keyword-imports", key, body=body)
        rows.extend(res.get("keywords") or [])
        before = res.get("countKeywordsBeforeLimit", before)
        lang, loc = res.get("language"), res.get("location")
    print(json.dumps({"keywords": rows, "countKeywordsBeforeLimit": before,
                      "language": lang, "location": loc, "imported": len(kws)}))


def cmd_domain_keywords(args):
    key = _key(args)
    q = {"url": args.url, "location_id": args.location}
    print(json.dumps(_request("GET", "/kwfinder/suggested-keywords", key, query=q)))


def cmd_gap(args):
    key = _key(args)
    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()][:5]
    body = {
        "domain": args.domain,
        "competitors": competitors,
        "location_id": int(args.location),
        "page": int(args.page),
    }
    print(json.dumps(_request("POST", "/kwfinder/gap-analysis", key, body=body)))


COUNTRY_IDS = {"us": "2840", "gb": "2826", "au": "2036", "ca": "2124", "de": "2276", "fr": "2250"}

# Major cities per country as "City, Region" (the region disambiguates
# duplicates like Nashville, Arkansas vs Tennessee). Names only: the real location ID is resolved live
# via the Mangools locations endpoint, so no ID here can go stale or be wrong.
CITY_POOL = {
    "us": ["New York, New York", "Los Angeles, California", "Chicago, Illinois",
           "Houston, Texas", "Phoenix, Arizona", "Philadelphia, Pennsylvania",
           "San Antonio, Texas", "San Diego, California", "Dallas, Texas",
           "Austin, Texas", "San Francisco, California", "Seattle, Washington",
           "Denver, Colorado", "Boston, Massachusetts", "Miami, Florida",
           "Atlanta, Georgia", "Nashville, Tennessee", "Portland, Oregon"],
    "gb": ["London, England", "Manchester, England", "Birmingham, England",
           "Leeds, England", "Glasgow, Scotland", "Liverpool, England",
           "Bristol, England", "Edinburgh, Scotland"],
    "au": ["Sydney, New South Wales", "Melbourne, Victoria", "Brisbane, Queensland",
           "Perth, Western Australia", "Adelaide, South Australia"],
    "ca": ["Toronto, Ontario", "Montreal, Quebec", "Vancouver, British Columbia",
           "Calgary, Alberta", "Ottawa, Ontario", "Edmonton, Alberta"],
    "de": ["Berlin, Berlin", "Hamburg, Hamburg", "Munich, Bavaria",
           "Cologne, North Rhine-Westphalia", "Frankfurt, Hessen",
           "Stuttgart, Baden-Wurttemberg"],
    "fr": ["Paris, Ile-de-France", "Lyon, Auvergne-Rhone-Alpes",
           "Marseille, Provence-Alpes-Cote d'Azur", "Toulouse, Occitanie",
           "Nice, Provence-Alpes-Cote d'Azur", "Bordeaux, Nouvelle-Aquitaine"],
}


def _find_locations(key, query, country=None):
    res = _request("GET", "/kwfinder/locations", key, query={"query": query})
    out = []
    for loc in res if isinstance(res, list) else []:
        if country and (loc.get("country_code") or "").lower() != country.lower():
            continue
        out.append({
            "id": loc.get("_id"),
            "label": loc.get("canonical_name") or loc.get("label"),
            "type": loc.get("target_type"),
            "country": (loc.get("country_code") or "").lower(),
            "active": loc.get("active"),
        })
    return out


def _resolve_city(key, name, country):
    """Return the active City in `country` matching `name`.

    `name` may be "City" or "City, Region"; with a region, the match must have
    that region in its label, so duplicate city names resolve correctly.
    """
    city, _, region = [x.strip() for x in name.partition(",")]
    for loc in _find_locations(key, city, country):
        label = loc["label"] or ""
        if loc["type"] != "City" or not loc["active"]:
            continue
        if label.split(",")[0].strip().lower() != city.lower():
            continue
        if region and region.lower() not in label.lower():
            continue
        return loc
    return None


def _resolve_country(key, arg):
    """Return (code, location_id, label) for a built-in code, any country's
    location ID, or a country name looked up via the locations endpoint."""
    arg = str(arg).strip()
    low = arg.lower()
    if low in COUNTRY_IDS:
        return low, COUNTRY_IDS[low], COUNTRY_NAMES[low]
    for code, lid in COUNTRY_IDS.items():
        if lid == low:
            return code, lid, COUNTRY_NAMES[code]
    if low.isdigit():
        row = _request("GET", f"/kwfinder/locations/{low}", key)
        if not isinstance(row, dict) or row.get("target_type") != "Country":
            _die(f"Location {arg} is not a country. Use a country's location ID "
                 f"(locations --query \"<country>\", the Country row).")
        return (row.get("country_code") or "").lower(), str(row["_id"]), row.get("canonical_name") or arg
    if len(low) == 2:
        _die(f"Unknown country code '{arg}'. Built-in codes: {', '.join(COUNTRY_IDS)}. "
             f"For any other country pass its name (e.g. Spain) or its location ID "
             f"(locations --query \"<country>\", the Country row).")
    rows = _request("GET", "/kwfinder/locations", key, query={"query": arg})
    for row in rows if isinstance(rows, list) else []:
        if row.get("target_type") == "Country" and row.get("active"):
            return (row.get("country_code") or "").lower(), str(row["_id"]), row.get("canonical_name") or arg
    _die(f"No country matched '{arg}'. Look it up with: locations --query \"{arg}\"")


def _organic_results(serp, n=10):
    """Top-n organic results as [{pos, domain, url, title}] (ads/features skipped)."""
    items = serp.get("items") or []
    out = []
    for it in items:
        if it.get("type") == "ORGANIC" and it.get("url"):
            url = it.get("destination_url") or it["url"]
            d = (it.get("domain") or urllib.parse.urlparse(url).netloc).lower()
            if d.startswith("www."):
                d = d[4:]
            out.append({"pos": len(out) + 1, "domain": d, "url": url,
                        "title": (it.get("title") or "").strip()})
        if len(out) >= n:
            break
    return out


def _organic_domains(serp, n=10):
    return [r["domain"] for r in _organic_results(serp, n)]


def cmd_locations(args):
    key = _key(args)
    print(json.dumps(_find_locations(key, args.query, args.country)))


def _show_fail(msg):
    print("call failed: " + " ".join(str(msg).split()))
    sys.exit(1)


def _paa_questions(serp):
    """Questions from PEOPLE_ALSO_ASK items of a SERP response."""
    out = []
    for it in serp.get("items") or []:
        if it.get("type") in ("PEOPLE_ALSO_ASK", "SIMILAR_QUESTIONS"):
            for sub in it.get("items") or []:
                q = (sub.get("question") or sub.get("title") or sub.get("kw") or "").strip()
                if q and q not in out:
                    out.append(q)
    return out


def _show_results(label, rows):
    for x in rows:
        print(f"{label} {x.get('pos')} | {x.get('domain')} | {x.get('url')} | {(x.get('title') or '')[:80]}")


def cmd_show(args):
    # Summarise a saved output file without ever printing the whole body.
    n = args.rows
    try:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    except OSError as e:
        _show_fail(f"cannot open {args.file} ({e.strerror})")
    stripped = text.strip()
    if not stripped:
        _show_fail("empty file (the call wrote nothing)")
    try:
        d = json.loads(stripped)
    except Exception:
        _show_fail(stripped[:300] + (" ... (not valid JSON; cut off or not a Mangools response)" if stripped[:1] in "{[" else " (not JSON)"))
    if isinstance(d, dict) and "error" in d:
        kept = (d.get("country") or {}).get("serp") if isinstance(d.get("country"), dict) else None
        if isinstance(kept, dict):  # serp-dual whose city half failed
            print("call failed: " + " ".join(json.dumps({"error": d["error"]})[:300].split()))
            print(f"country half kept in this file under country: kw {d.get('kw')} | KD {kept.get('rank')}")
            _show_results("country", _organic_results(kept, n))
            qs = _paa_questions(kept)
            if qs:
                print("PAA (country): " + " | ".join(qs))
            sys.exit(1)
        _show_fail(json.dumps(d)[:300])

    if isinstance(d, list):  # locations
        if not d:
            print("no location matched (the call succeeded; try the city name alone)")
            sys.exit(1)
        if not all(isinstance(r, dict) for r in d):
            _show_fail("unexpected response shape")
        d.sort(key=lambda r: r.get("type") != "City")
        print(len(d), "rows (cities first)")
        for r in d[:n]:
            print(f"{r.get('id')} | {r.get('label')} | {r.get('type')} | {'active' if r.get('active') else 'INACTIVE'}")
        return
    if not isinstance(d, dict):
        _show_fail("unexpected response shape")

    if "keywords" in d and "url_type" in d:  # domain-keywords
        r = d["keywords"] or []
        pos = [k.get("position") for k in r if k.get("position") is not None]
        print(f"{len(r)} keywords returned of {d.get('totalCount')} the domain ranks for"
              + (f" | positions {min(pos)}–{max(pos)}" if pos else ""))
        stop = set("a an the and or of for to in on with how what is are best free tool tools your my you vs top "
                   "google search engine website site page online web internet".split())
        freq = {}
        for k in r:
            for w in set(str(k.get("kw") or "").lower().split()):
                if w.isalpha() and w not in stop and len(w) > 2:
                    freq[w] = freq.get(w, 0) + 1
        terms = sorted(freq.items(), key=lambda kv: -kv[1])[:15]
        print("recurring terms (hint at the site's field): " + ", ".join(f"{w} {c}" for w, c in terms))
        print("highest-volume rows (keyword | volume | position):")
        for k in sorted(r, key=lambda k: -(k.get("sv") or 0))[:n]:
            print(f"{k.get('kw')} | {k.get('sv')} | {k.get('position')}")
    elif "keywords" in d:  # related, or import-keywords
        r = d["keywords"] or []
        if "imported" in d:
            print(f"{len(r)} rows for {d.get('imported')} imported keywords | {sum(1 for k in r if k.get('sv'))} with volume")
        else:
            print(len(r), "rows,", d.get("countKeywordsBeforeLimit"), "before plan cap")
        for k in r[:n]:
            print(f"{k.get('kw')} | {k.get('sv')} | {k.get('seo')} | {k.get('cpc')}")
    elif "comparison" in d:  # serp-dual
        c = d["comparison"]
        print(f"kw {d.get('kw')} | city {d.get('city', {}).get('label')} | overlap {c.get('overlap_pct')} %")
        print("shared", c.get("shared_domains"), "| country only", c.get("country_only"), "| city only", c.get("city_only"))
        print("KD country", d.get("country", {}).get("serp", {}).get("rank"), "| KD city", d.get("city", {}).get("serp", {}).get("rank"))
        _show_results("country", (c.get("country_results") or [])[:n])
        _show_results("city", (c.get("city_results") or [])[:n])
        for lab in ("country", "city"):
            qs = _paa_questions(d.get(lab, {}).get("serp") or {})
            if qs:
                print(f"PAA ({lab}): " + " | ".join(qs))
    elif "items" in d:  # single serp
        items = d.get("items") or []
        types = {}
        for it in items:
            types[it.get("type")] = types.get(it.get("type"), 0) + 1
        print(f"kw {d.get('kw')} | KD {d.get('rank')} | {len(items)} items {types}")
        _show_results("organic", _organic_results(d, n))
        qs = _paa_questions(d)
        if qs:
            print("PAA: " + " | ".join(qs))
    elif "cities" in d:  # suggest-cities
        if not d.get("cities"):
            print(f"no built-in city list for {d.get('country_label') or d.get('country')}: ask the client to name a city, then look it up with locations")
        for c in d.get("cities") or []:
            print(f"{c.get('location_id')} | {c.get('label')}")
        print(d.get("client_message", ""))
    elif "resources" in d:  # limits
        r = d["resources"]
        rk, sp = r.get("related-keywords", {}), r.get("serps", {})
        print(f"plan {d.get('highestPlan')} | keyword lookups left {rk.get('remaining')} / {rk.get('limit')} | SERP units left {sp.get('remaining')} / {sp.get('limit')}")
        pc = d.get("permanent_credits", r.get("permanent_credits"))
        unknown = False
        if isinstance(pc, dict):  # Free/Free+ one-time API & MCP welcome bonus
            units = [("keyword lookups", pc.get("related-keywords") or {}), ("SERP units", pc.get("serps") or {})]
            left = [(name, u) for name, u in units if (u.get("remaining") or 0) > 0]
            if left:
                print("welcome bonus left: " + ", ".join(f"{u.get('remaining')} / {u.get('limit')} {name}" for name, u in left)
                      + " (one-time; spent before the daily limits above, 1 per request, a gap page included)")
            spent = [name for name, u in units if u.get("remaining") == 0]
            if spent:
                print(f"welcome bonus used up for {' and '.join(spent)}: those requests now use the daily limits above"
                      " at the paid rate (2 per request, 4 per serp-dual, 10 per gap page)")
        else:
            other = {k: v for k, v in list(d.items()) + list(r.items()) if "credit" in k.lower() or "bonus" in k.lower()}
            if other:
                print("bonus credits:", json.dumps(other))
            unknown = not rk.get("limit") and not sp.get("limit")
            if unknown:
                print("key not recognised: all limits are 0 (an empty or unknown key gets this answer)")
        gm = d.get("kw-gap-max-competitors")
        caps = [(gm, "gap takes up to {} competitor" + ("" if gm == 1 else "s") + " per call"),
                (d.get("related-keywords-rows"), "up to {} related keywords per lookup"),
                (d.get("competitor-keywords-rows"), "up to {} gap keywords per competitor")]
        caps = [t.format(v) for v, t in caps if v is not None]
        if caps and not unknown:
            print(" | ".join(caps))
    elif "results" in d:  # gap
        res = d.get("results") or []
        print(f"{len(res)} competitors | isAllowedPagination {d.get('isAllowedPagination')} | resultsSize {d.get('resultsSize')}")
        for comp in res:
            kws = comp.get("keywords") or []
            print(f"-- {comp.get('domain')} | totalCount {comp.get('totalCount')} | {len(kws)} rows returned")
            for k in kws[:n]:
                print(f"   {k.get('kw')} | {k.get('sv')} | {k.get('seo')} | pos {k.get('position')}")
    else:
        print("unrecognised file; top-level keys:", sorted(d.keys())[:20])


COUNTRY_NAMES = {"us": "the United States", "gb": "the United Kingdom", "au": "Australia",
                 "ca": "Canada", "de": "Germany", "fr": "France"}


def _city_explainer(country_code, cities, kw=None, country_label=None):
    """Client-facing explanation for the city check. Shown before asking."""
    country = COUNTRY_NAMES.get(country_code) or country_label or country_code.upper()
    target = f'who ranks for "{kw}"' if kw else "who ranks for your keywords"
    options = "\n".join(f"{i}. {c['label']}" for i, c in enumerate(cities, 1))
    if not cities:
        options = (f"I don't have a built-in list of cities for {country}, so please name "
                   f"one or two major cities there (for example where most of your customers "
                   f"are) and I'll use the first one Mangools knows.")
    return (
        f"**One extra check before the next step: which city should we use?**\n\n"
        f"Next I'll look at {target}. Google doesn't show everyone the same results: "
        f"rankings shift depending on where the person is searching from, and they change "
        f"all the time. Your customers search from real cities, not from {country} as a "
        f"whole, so looking only at the national results can give a misleading picture of "
        f"who you're really competing with. In testing, the national and city results for "
        f"the same keyword sometimes had just 1 site in common out of 9.\n\n"
        f"So as a precaution, I'll run every ranking check twice: once for all of "
        f"{country}, and once for one city. You'll see both side by side, so we can tell "
        f"whether your competition is the same everywhere or changes by location. That makes "
        f"the competitor list, and everything built on it, more reliable.\n\n"
        f"The cost: each ranking check runs once more for the city, so it uses twice the SERP units. We'll "
        f"keep the same city for the whole research, so I'll only ask this once.\n\n"
        f"Which city should we use?\n\n{options}\n\n"
        + ("" if not cities else
           "If another city matters more to your business, for example where most of your "
           "customers are, just tell me and I'll use that one instead.")
    )


def cmd_suggest_cities(args):
    import random
    key = _key(args)
    code, country_id, label = _resolve_country(key, args.country)
    pool = CITY_POOL.get(code, [])
    picks = []
    for name in random.sample(pool, len(pool)):
        loc = _resolve_city(key, name, code)
        if loc:
            picks.append({"name": name.split(",")[0].strip(), "location_id": loc["id"],
                          "label": loc["label"]})
        if len(picks) >= args.n:
            break
    if pool and not picks:
        _die(f"Could not resolve any cities for '{code}'.")
    print(json.dumps({"country": code, "country_id": int(country_id), "country_label": label,
                      "cities": picks,
                      "client_message": _city_explainer(code, picks, args.kw, label)}))


def cmd_serp_dual(args):
    import random
    import time
    key = _key(args)
    code, country_id, _label = _resolve_country(key, args.country)

    # Resolve the city: explicit ID > explicit name > random from the pool.
    city = None
    if args.city_id:
        city = {"id": int(args.city_id), "label": args.city_label or f"location {args.city_id}"}
    else:
        names = [args.city] if args.city else random.sample(CITY_POOL.get(code, []), len(CITY_POOL.get(code, [])))
        for name in names:
            city = _resolve_city(key, name, code)
            if city:
                break
        if not city:
            _die(f"Could not resolve a city in '{code}'. Pass --city-id explicitly "
                 f"(find one with: locations --query \"<city>\" --country {code}).")

    country_serp = _request("GET", "/serpchecker/serps", key,
                            query={"kw": args.kw, "location_id": country_id})
    # The API allows 3 requests per 30 s per pool and asks for 11 s between requests.
    time.sleep(11)
    try:
        city_serp = _request("GET", "/serpchecker/serps", key,
                             query={"kw": args.kw, "location_id": city["id"]})
    except _ApiError as e:
        # Keep the country SERP that was already paid for.
        print(json.dumps({"error": f"{e} (city half; the country half succeeded and is kept in this file)",
                          "kw": args.kw,
                          "country": {"code": code, "location_id": int(country_id), "serp": country_serp}}))
        sys.exit(3)

    c_res, y_res = _organic_results(country_serp), _organic_results(city_serp)
    c_doms, y_doms = [r["domain"] for r in c_res], [r["domain"] for r in y_res]
    # A domain can hold two positions in one top 10; count each domain once.
    c_uniq, y_uniq = list(dict.fromkeys(c_doms)), list(dict.fromkeys(y_doms))
    shared = [d for d in c_uniq if d in y_uniq]
    union = set(c_uniq) | set(y_uniq)
    print(json.dumps({
        "kw": args.kw,
        "country": {"code": code, "location_id": int(country_id), "serp": country_serp},
        "city": {"location_id": city["id"], "label": city["label"], "serp": city_serp},
        "comparison": {
            "country_results": c_res,
            "city_results": y_res,
            "country_top10": c_doms,
            "city_top10": y_doms,
            "shared_domains": shared,
            "country_only": [d for d in c_uniq if d not in y_uniq],
            "city_only": [d for d in y_uniq if d not in c_uniq],
            "overlap_pct": round(100 * len(shared) / len(union), 1) if union else None,
        },
    }))


def _slug(text):
    """File-name slug: lowercase, letters, digits and marks of every language kept
    as typed (NFC), any other run of characters one hyphen. A 6-character code is
    added when punctuation was dropped or the keyword is long, so two different
    keywords never share a file ("c++ tutorial" vs "c tutorial")."""
    t = unicodedata.normalize("NFKC", text).strip().lower()
    s = "".join(c if unicodedata.category(c)[0] in "LNM" else "-" for c in t)
    s = re.sub(r"-+", "-", unicodedata.normalize("NFC", s)).strip("-")
    if not s or s != re.sub(r"\s+", "-", t) or len(s) > 60:
        s = (s[:60].rstrip("-") + "-" if s else "kw-") + hashlib.sha1(t.encode("utf-8")).hexdigest()[:6]
    return s


def cmd_slug(args):
    print(_slug(args.kw))


def _positive_int(v):
    try:
        i = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a whole number, got {v!r}")
    if i < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return i


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--apikey", help="Mangools API key (else uses MANGOOLS_API_KEY env var)"
    )

    p = argparse.ArgumentParser(description="Mangools v3 client (BYOK)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("related", parents=[common], help="Related keywords + metrics")
    r.add_argument("--kw", required=True)
    r.add_argument("--location", type=int, default=2840, help="Google location ID (country), e.g. 2840 = US")
    r.add_argument("--language", type=int, default=1000, help="Google Ads language ID, e.g. 1000 = English")
    r.set_defaults(func=cmd_related)

    s = sub.add_parser("serp", parents=[common], help="Live SERP results")
    s.add_argument("--kw", required=True)
    s.add_argument("--location", type=int, default=2840, help="Google location ID (country or city)")
    s.set_defaults(func=cmd_serp)

    ik = sub.add_parser("import-keywords", parents=[common], help="Volume/KD/CPC for a list of keywords (2 lookups per 100, 1 on the welcome bonus)")
    ik.add_argument("--file", required=True, help="Text file, one keyword per line")
    ik.add_argument("--location", type=int, default=2840, help="Google location ID (country)")
    ik.add_argument("--language", type=int, default=1000, help="Google Ads language ID")
    ik.add_argument("--chunk", type=_positive_int, default=100, help="Keywords per call (plan caps apply; default 100)")
    ik.set_defaults(func=cmd_import_keywords)

    dk = sub.add_parser("domain-keywords", parents=[common], help="Keywords a domain already ranks for (2 lookups, 1 on the welcome bonus)")
    dk.add_argument("--url", required=True, help="The domain, e.g. mangools.com")
    dk.add_argument("--location", type=int, default=2840, help="Google location ID (country)")
    dk.set_defaults(func=cmd_domain_keywords)

    g = sub.add_parser("gap", parents=[common], help="Gap analysis vs competitors")
    g.add_argument("--domain", required=True)
    g.add_argument("--competitors", required=True, help="comma-separated domains")
    g.add_argument("--location", type=int, default=2840, help="Google location ID (country)")
    g.add_argument("--page", type=_positive_int, default=1, help="Result page (pagination needs Premium/Agency)")
    g.set_defaults(func=cmd_gap)

    d = sub.add_parser("serp-dual", parents=[common],
                       help="Country SERP + one city SERP, with overlap stats")
    d.add_argument("--kw", required=True)
    d.add_argument("--country", default="us", help="built-in code (us gb au ca de fr), any country's location ID, or its name")
    d.add_argument("--city", help="City name to use instead of a random one")
    d.add_argument("--city-id", type=int, help="Exact city location ID (reuse the run's city)")
    d.add_argument("--city-label", help="Label for --city-id (display only)")
    d.set_defaults(func=cmd_serp_dual)

    sc = sub.add_parser("suggest-cities", parents=[common],
                        help="Offer N random cities with location IDs")
    sc.add_argument("--country", default="us", help="built-in code (us gb au ca de fr), any country's location ID, or its name")
    sc.add_argument("--n", type=_positive_int, default=3, help="How many cities to offer (default 3)")
    sc.add_argument("--kw", help="Seed keyword, used in the client message")
    sc.set_defaults(func=cmd_suggest_cities)

    lo = sub.add_parser("locations", parents=[common], help="Look up location IDs by name")
    lo.add_argument("--query", required=True)
    lo.add_argument("--country", help="Filter by country code, e.g. us")
    lo.set_defaults(func=cmd_locations)

    sh = sub.add_parser("show", help="Summarise a saved output file (no API call)")
    sh.add_argument("file", help="Path of a saved output file, e.g. data/<run>/related-<slug>.json")
    sh.add_argument("--rows", type=_positive_int, default=40, help="Rows to print (default 40)")
    sh.set_defaults(func=cmd_show)

    sl = sub.add_parser("slug", help="Print a keyword's file-name slug (no API call)")
    sl.add_argument("--kw", required=True)
    sl.set_defaults(func=cmd_slug)

    # Keyword text is printed as UTF-8 everywhere (Windows pipes default to the ANSI code page).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    args = p.parse_args()
    try:
        args.func(args)
    except _ApiError as e:
        _die(str(e), 3)


if __name__ == "__main__":
    main()
