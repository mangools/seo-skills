# Methodology reference

Authoritative detail for every threshold, list, and formula the pipeline uses.
When SKILL.md says "per the reference," this is the reference.

## Table of contents
1. Mangools response fields
2. Generic domains to exclude (Step 2 & 4)
3. Non-organic SERP types (Step 2)
4. Long-tail filters (Step 3)
5. Gap analysis: pagination + progressive filter (Step 4)
6. Clustering rules (Step 6)
7. Page-type taxonomy
8. CTR, traffic, and scoring formulas (Steps 8 & 9)
9. Export formats (Step 7)

---

## 1. Mangools response fields

Keyword objects (from `related` / gap results) use short field names:
- `kw`: the keyword text
- `sv`: search volume (monthly), may be null
- `seo`: keyword difficulty (KD), 0–100, may be null
- `cpc`: cost per click

The script writes the API body as-is; there is no `data` wrapper.

`related` output: top-level `keywords` (list of keyword objects) and `countKeywordsBeforeLimit` (rows available before the plan cap).

`serp` output: top-level `kw`, `items` (each with `type`, e.g. `ORGANIC`, `url`, `domain`, `title`, `serpRank`, and sometimes `m.moz.v.pda` / `m.moz.v.upa` for domain/page authority) and top-level `rank`, the keyword's KD. Items of type `PEOPLE_ALSO_ASK` (older responses: `SIMILAR_QUESTIONS`) carry the real People-Also-Ask questions as nested `items[]` with `question`, `title`, `url` and `type` (`show` prints the questions as `PAA (country):` / `PAA (city):` lines). KD: `seo` in keyword objects is the KD KWFinder stores; `rank` in a SERP response is the KD recomputed for the SERP just fetched and is the freshest value (it updates the stored one). Use the national `rank` as the Keyword Difficulty for keywords whose SERP was checked (the seed from Step 1 on) and `seo` for the others; one KD per keyword, never two. Mention the city `rank` only when it differs from the national one by more than ~15 points.

`serp-dual` output: `kw`; `country` and `city`, each with `location_id`, `code` (country only), `label` (city only) and `serp` (a full `serp` output as above); and `comparison`, with `country_results` / `city_results` (top 10 organic, each `pos`, `domain`, `url`, `title`), `country_top10`, `city_top10`, `shared_domains`, `country_only`, `city_only` and `overlap_pct`. `pos` is the rank among organic results only (ads and SERP features are skipped), not the absolute Google position. `shared_domains`, `country_only` and `city_only` list each domain once; `overlap_pct` = distinct domains present in both top 10s ÷ distinct domains present in either, × 100, over all organic domains including generic platforms.

`suggest-cities` output: `country` (code), `country_id`, `country_label`, `cities[]` (each `name`, `location_id`, `label`; empty for countries without a built-in city list) and `client_message` (asks the client to name a city when `cities` is empty).

`locations` output: a list of `id`, `label`, `type` (`City`, `Country`, ...), `country` and `active`.

Quota file (`<run>/limits.json`, the Step 0 curl response): `highestPlan` and `resources`, where `resources.related-keywords` and `resources.serps` each carry `remaining` and `limit` (the daily figures); `kw-gap-max-competitors` (competitors one `gap` call takes), `related-keywords-rows` and `competitor-keywords-rows` (rows per lookup); and, for Free and Free+ accounts, `permanent_credits`, the one-time API & MCP welcome bonus, whose `related-keywords` and `serps` each carry `limit` and `remaining`. Mangools spends the bonus before the daily limits, at 1 per request (a gap page included). `show` prints all of these in plain words.

`import-keywords` output: `keywords[]` (keyword objects for the imported phrases, `sv` null when Mangools has no figure), `countKeywordsBeforeLimit`, `language`, `location` and `imported` (how many phrases were sent). `show` prints the rows and how many have volume. One call covers up to 100 phrases for 2 keyword lookups (1 on the welcome bonus).

`domain-keywords` output: `totalCount` (keywords the domain ranks for), `keywords[]` (each `kw`, `sv`, `position`, `lid`; up to 1000 rows, mostly positions 40–100), `countKeywordsBeforeLimit`, `url_type`, `__hasNextPage`. `show` prints the recurring terms and the highest-volume rows; use it as a hint about the site's field, not as a list of its best keywords.

`gap` output: `isAllowedPagination` (false on plans that cannot paginate; see §5), `resultsSize`, and `results[]`, one per competitor, with `domain`, `totalCount` and `keywords[]` (keyword objects that also carry `position`).

Any command that fails writes `{"error": "..."}` instead; a `serp-dual` whose city half failed also keeps `kw` and the paid `country` half (`show` prints it).

---

## 2. Generic domains to exclude

Drop these from competitors (Step 2) and skip them as gap competitors (Step 4).
They're UGC/news/aggregators, not competitors worth modelling:

```
reddit.com, youtube.com, wikipedia.org, quora.com, amazon.com,
facebook.com, twitter.com, x.com, linkedin.com, instagram.com,
tiktok.com, pinterest.com, medium.com, stackoverflow.com, github.com,
yelp.com, tripadvisor.com, trustpilot.com, g2.com, capterra.com,
producthunt.com, getapp.com, g2crowd.com, softwareadvice.com,
forbes.com, businessinsider.com, techcrunch.com, wired.com,
cnet.com, pcmag.com, zdnet.com, theverge.com, engadget.com,
huffpost.com, buzzfeed.com, mashable.com, gizmodo.com,
news.ycombinator.com, dev.to, hashnode.com, substack.com
```
Compare after stripping `www.`. Also always exclude the user's own domain.

**Classify every remaining organic result by its title and URL** (judge by the
title first; the description is often the placeholder "Read more"):
- **direct**: a business offering what the client offers, a product, service
  or content, competing for the seed's intent;
- **publisher**: a blog, magazine or listicle site writing about the subject;
- **marketplace / directory**, **community**: compare sites, forums, Q&A;
- **platform**: see below;
- **off-topic**: a different subject that happens to share the words (game
  stat trackers for "rank tracker", flight trackers for "tracker"). Judge
  relevance against the client profile confirmed in Step 0b: a result is
  relevant when it serves a need the client's business serves or, per the
  profile, wants to serve, in the seed's sense; the same test applies to gap keywords (§5)
  and PAA questions (Step 5).

Off-topic domains are never competitors: they never enter the merged set,
Step 3's presence check or the gap analysis. Name them in one sentence so the
client sees why they were dropped. If four or more of the national organic
results (usually 9 of them) are off-topic, the seed is ambiguous: say so, name
the off-topic domains, propose two or three narrower seeds, and ask whether to
continue with them excluded or to switch seed; spend no quota on Steps 3–4
until the client answers. The gap analysis takes the strongest **direct**
domains, as many as one `gap` call takes (five on most plans); publishers
make weak gap baselines.

**Platforms (show, label, never gap):** Google, Apple and Microsoft properties
(google.com including play.google.com, apple.com, microsoft.com) are not
dropped from the Step 2 tables. Show them, label them for what they are (e.g.
"app store listing"), and read them as an intent signal (Google rewards an app
for this query). Never pass them to `gap` and never count them among the five
direct domains used for the gap analysis; a gap against google.com is
meaningless.

**Step 2 fallback:** if filtering leaves zero competitors, re-include generic
domains but still exclude the user's domain and `reddit.com`, then take top 5.

---

## 3. Non-organic SERP types (Step 2)

Treat a result as non-organic (drop it) if `type` is any of:
```
ADV_TOP, ADV_BOTTOM, FEATURED_SNIPPET, KNO_GRAPH, KNO_GRAPH_LINK,
LOCAL_PACK, TOP_CAROUSEL, TOP_STORIES, NEWS_CAROUSEL, NEWS_PACK,
IMG_PACK, VIDEO_PACK, SIMILAR_QUESTIONS, SIMILAR_QUERIES, SHOP_RESULTS,
SPELL_ERROR, SUGGESTION, FLIGHTS, JOB_POSTING, SPORTS, WEATHER,
TRANSLATOR, DICTIONARY, CURRENCY, TIME, QUANTITY_ANSWER, VIDEO_PANEL,
INSTALL_APP, INSTALL_APP_GRID, PROGRAM_OVERVIEW, POPULAR_LIST,
SIMILAR_ENTITIES, SIMILAR_ENTITIES2, SIMILAR_PLACES, SPECIFY_QUERY,
INDEPTH_ARTICLE, TRAVEL_BOX, TOP_SIGHTS, PEOPLE_ALSO_ASK, AI_OVERVIEW
```
Keep only results with `type == ORGANIC` and a `url`; this is exactly what the
script's `comparison` block does.

---

## 4. Long-tail filters (Step 3)

From `related` results, keep a keyword when ALL hold:
- its text contains the seed (case-insensitive)
- it is not exactly the seed
- `sv` ≥ min volume (default 10)
- `seo` is null/undefined, OR `seo` ≤ max KD (default 60)

Take up to 50. Run `serp-dual` on the top N, where S is the SERP units the
run can spend and Step 3 may spend at most half of S:
- paid plans, and Free/Free+ once the SERP bonus is used up: S is the
  `SERP units left` figure of the latest quota check (Step 0, or for a
  Free/Free+ account its re-check before Step 3); a `serp-dual` costs 4
  units, so N = min(25, floor(S / 8));
- while that check shows SERP units left in the welcome bonus: S is that
  bonus figure (not the daily one); a `serp-dual` costs 2 units, so
  N = min(25, floor(S / 4)).

A keyword is `validated` when a **direct**
domain from the Step 2 merged set appears in the top 10 of either SERP,
`content_competition` when only publishers, marketplaces or communities from
the merged set appear, and `checked` when a SERP was fetched and none of them
appear. Mark the remainder `not_checked` to conserve quota.

---

## 5. Gap analysis (Step 4)

### Plans without pagination
When `isAllowedPagination` is false (seen on Basic: 25 rows per competitor;
lower plans return fewer), each competitor returns a small sample of roughly
its highest-volume keywords, not its full keyword set, and the sample often
holds keywords far from the seed's subject (for an SEO tool site: "how old
is google", "wayback machine", "ai detector"). Run the progressive filter,
then keep every keyword about the client's topic as the Step 0b profile
defines it, however few, and list the rest separately with the note that competitors rank for these keywords, which
are not directly about the client's topic but could still bring traffic. Add
that Premium and Agency plans return each competitor's full keyword set and
therefore more gap keywords.

### Pagination stop rule
Fetch page 1..3 of `gap`. Stop early when:
- a page returns no results, OR
- page > 1 and the first keyword of the first block equals the previous page's
  first keyword (this repetition means the Mangools plan won't paginate
  further — common on lower tiers), OR
- a batch's block did NOT contain 1000 keywords (no full page = last page), OR
- you hit the 3-page safety cap.

### Progressive filter
A gap keyword needs competitors ranking where the user doesn't. Start strict
and relax **only until you have at least 5 keywords**, then stop:

| Order | Min competitors | Max position |
|------:|:---------------:|:------------:|
| 1 | 2 | ≤ 10 |
| 2 | 2 | ≤ 20 |
| 3 | 1 | ≤ 10 |
| 4 | 1 | ≤ 20 |
| 5 | 1 | ≤ 50 |

If you relaxed past the first row, tell the user which filter matched. Sort
results by volume. Then prioritise each high/medium/low with a one-sentence
reason (proven demand + reachable KD + intent = higher priority). Cap the set
you reason over at ~60 keywords.

---

## 6. Clustering rules (Step 6)

**Topic names must describe the actual subject matter** — what a website
section would be called.

- BAD (never use): "Educational Content", "Informational Queries", "Commercial
  Intent", "General Topics", "Miscellaneous".
- GOOD (for "uptime monitoring"): "Free & Open-Source Tools", "Cloud Provider
  Integrations", "Status Pages & Incident Management", "Response-Time &
  Performance", "Alerting & Notifications".

Test: if a user landed on this cluster's page, what specific thing are they
reading about? Cluster in batches of ~40 keywords for large pools, then merge
clusters that share a topic name. Preserve real volume/KD from the data pool
when merging. Every keyword must end up in exactly one cluster; if a few are
left over, place them in the nearest fitting cluster rather than a generic
catch-all.

---

## 7. Page-type taxonomy

Assign exactly one per keyword:

| page_type | Use for |
|-----------|---------|
| `blog_post` | how-to articles, tutorials, explainers, technique comparisons |
| `feature_page` | product capability / integration pages ("Datadog integration") |
| `glossary` | standalone definitions ("what is X", terminology) |
| `comparison` | "X vs Y", "best X for Y", alternatives lists |
| `landing_page` | high commercial intent — pricing, signup, free trial, buy |
| `case_study` | industry use cases, success stories |

---

## 8. CTR, traffic, and scoring

### Position CTR (positions 1–5)
```
#1 = 28.7%   #2 = 15.4%   #3 = 9.6%   #4 = 6.3%   #5 = 4.7%
```
- **Best traffic** (rank #1)   = round(volume × 0.287)
- **Average traffic** (P1–5)  = round(volume × mean(CTR)) = round(volume × 0.1294)

### Priority score (Step 9)
Score each page **70% traffic + 30% ease of ranking**, both normalised 0–100:
```
trafficScore = (page_est_traffic / max_est_traffic_across_pages) * 100
kdScore      = (avg_kd != null) ? (100 - avg_kd) : 50   # null KD -> neutral 50
score        = round(0.7 * trafficScore + 0.3 * kdScore)
```
Compute `est_traffic` for a page as 28.7% × (sum of its target-keyword volumes),
using the real per-keyword volumes — not model estimates. Sort pages by score
descending; keep the top 12, deduped by topic. A keyword without volume data
(typically a PAA question) never drives a page: inside a cluster that has
volume it becomes an FAQ entry of that cluster's page; a cluster with no volume
at all is not a page, fold its questions into the FAQ section of the closest
page and do not count it among the 12. List those questions in the page's
`FAQ Questions` column (§9).

---

## 9. Export formats (Step 7)

Write real files to disk and hand them to the user. Write both CSVs as UTF-8
with a byte-order mark (Python: `open(path, "w", newline="",
encoding="utf-8-sig")`), so Excel shows accented and non-Latin keywords
correctly when the file is opened with a double-click.

### Keywords CSV (deduped by keyword)
Columns:
```
Keyword, Topic Cluster, Page Type, Search Volume, Keyword Difficulty,
Est. Avg Traffic, Est. Best Traffic (#1), SERP Status, Competitor 1..N (URLs)
```
`Keyword Difficulty` is the national SERP KD (`rank`) for keywords whose SERP
was checked (the seed in Steps 1–2, long-tails in Step 3) and KWFinder's `seo`
for the others. `SERP Status` is one of `validated`, `content_competition`,
`checked` (§4) or `not_checked`; the seed row follows the same rule from its
Step 2 SERPs. Competitor columns are empty for `not_checked` rows.

### Page recommendations CSV
Columns:
```
Rank, Page Title, Page Type, Topic Cluster, Est. Monthly Traffic,
Keyword Volume, Avg KD, Priority Score, Target Keywords, Competitor Example,
Strategic Rationale, FAQ Questions
```
`FAQ Questions` holds the no-volume questions folded into the page (§8),
separated by `;`; the JSON bundle carries them as `faq[]` per page.

### JSON bundle
```json
{
  "seed": "...",
  "competitors": [...],
  "clusters": [...],
  "keywords": [...],
  "pageRecommendations": [...]
}
```
Quote fields containing commas and escape embedded quotes by doubling them.
Name files `keywords-<slug>-<YYYY-MM-DD>.csv`,
`page-recommendations-<slug>-<YYYY-MM-DD>.csv` and
`research-<slug>-<YYYY-MM-DD>.json`, where `<slug>` is the seed's slug from
the script's `slug` command (lowercase, letters of every language kept as
typed, other characters as one hyphen, plus a 6-character code when
punctuation was dropped).
