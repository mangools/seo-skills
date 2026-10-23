---
name: "kw-research-pipeline"
description: Run a complete 9-step SEO keyword-research pipeline for a seed keyword and domain — seed metrics, real organic competitors, long-tail discovery, competitor gap analysis, People-Also-Ask questions, topic + page-type clustering, traffic estimates, and a prioritised list of pages to create. Pulls live data from the Mangools API (KWFinder + SERPChecker) using the user's own Mangools key. Use this whenever the user wants keyword research, an SEO content plan, competitor keyword gaps, a topic/content map, "what pages should I build to rank for X", or mentions Mangools/KWFinder — even if they don't say "pipeline". Requires the Code Execution tool and a Mangools API key. Version 7.2.
---

# KW Research Pipeline (v7.2)

Turn one **seed keyword** + one **domain** into a prioritised SEO content plan,
backed by live Mangools data. You (Claude) orchestrate nine steps: some pull
data via the bundled Mangools script, others are your own analysis.

**Read `references/methodology.md` before running the pipeline.** It holds
every threshold, formula, list, class definition and response field name.
This file is the map; that file is the detail.

## Before you start

1. **Mangools API key (required).** Ask the user to upload `mangools.env` (one
   line: `MANGOOLS_API_KEY=...`). The bundled `scripts/loadkey.py` prints the
   key from that file, or a short error. Only ever call it inside `$(...)` as
   shown here, never on its own. A shell variable lives only inside the bash
   call that sets it, so load the key in the same call as every command that
   needs it, with this prefix:
   ```bash
   export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; <command>
   ```
   If the loader prints `no MANGOOLS_API_KEY=... line found`, do not open or
   print the file; ask the user to re-save it as a plain text file with exactly
   one line, `MANGOOLS_API_KEY=<key>`, and upload it again. If it prints
   `cannot open`, fix the path. If the user pasted the key as text instead,
   save it once with `printf 'MANGOOLS_API_KEY=%s\n' '<key>' > mangools.env`
   (in Claude Code, `mkdir -p /tmp/kw-research` and write it to
   `/tmp/kw-research/mangools.env`, never inside a repository; this is the
   only command that may ever contain the key), use that full path from then
   on, and tell them the key is now in this chat's history and should be reset
   at mangools.com/api-token after the session. Never print, echo or quote the
   key in a reply, in any other command or file, and never use the script's
   `--apikey` flag. Every lookup bills the user's own Mangools account; say so.
2. **Seed keyword + domain (required).** The domain is the user's own site: it
   is excluded from competitor results, is the baseline for the gap analysis
   (Step 4), and its profile (Step 0b) is the yardstick for relevance.
3. **Region (optional).** Default US/English. Built-in countries, with city
   suggestions: `us=2840 gb=2826 au=2036 ca=2124 de=2276 fr=2250`. Any other
   country works too: look up its ID (free) with `locations --query
   "<country>"` and take the `Country` row (Spain 2724, Czechia 2203). Pass the
   country ID as `--location` on `related`, `serp`, `gap`, `import-keywords` and
   `domain-keywords`; on `serp-dual`
   and `suggest-cities` pass `--country <country>` as the built-in code, the
   country ID or the country name (a two-letter code outside the six is
   rejected); `locations --country <code>` takes the two-letter code, which
   `suggest-cities` returns in its `country` field. Pass
   the seed language as `--language` on `related` and `import-keywords`, using Google Ads IDs:
   verified `en=1000 de=1001 fr=1002 es=1003 cs=1021 pl=1030 sk=1033`; other
   languages follow the same Google Ads list. A keyword in one language with
   another language's ID fails with a 500 "No available SERP provider".

## Commands, files and how to read them

The script `<skill-folder>/scripts/mangools.py` uses only the standard
library. Commands: `related`, `serp` (one location), `serp-dual` (country +
city; use it for every SERP check except the seed's national SERP in Step 1),
`gap`, `import-keywords`, `domain-keywords`, `suggest-cities`, `locations`,
`show` and `slug`. `--help` lists the flags.

Run every command from the sandbox's default working folder, never from
inside the skill folder, and call the script by its full path. In Claude
Code, local or cloud, write nothing inside a repository: use absolute paths
under `/tmp/kw-research/` for the key file and the run folders (the shell can
be back in the project folder between commands, and a relative `data/` would
then land in the repository).

**Each run has its own folder, `<run>` = `data/<seed-slug>-<country-code>`**
(in Claude Code `/tmp/kw-research/data/<seed-slug>-<country-code>`;
`<seed-slug>` is the seed's `<slug>`, below, or the user's domain for a
request without a seed; `<country-code>` is the two-letter code). If that
folder already exists from an earlier run, add `-2`, `-3` and keep that name
for the whole run. Create it in Step 0 and write every file of the run there;
nothing is read from another run's folder. A new seed or region in the same
chat is a new run: start it at Step 0, keep the confirmed profile unless the
domain changed, and ask the city question again, offering the previous city
first. A seed switch in Step 1 also starts a new folder. **Always redirect
script output to a file under `<run>/` and never print a full response.**

```bash
mkdir -p <run>
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py related --kw "<seed>" --location <country-id> --language <language-id> > <run>/related-<slug>.json
python3 <skill-folder>/scripts/mangools.py show <run>/related-<slug>.json --rows 40
```

`<slug>` is what `python3 <skill-folder>/scripts/mangools.py slug --kw
"<keyword>"` prints (no key, no API call): the keyword in lowercase, letters
of every language kept as typed ("gartenmöbel lounge" → "gartenmöbel-lounge",
"купити диван" → "купити-диван"), every run of spaces and other characters
replaced by one hyphen. When punctuation was dropped or the keyword is very
long, a 6-character code is added, so two keywords never share a file ("c++
tutorial" and "c tutorial" get different names). The loops below and the
export file names use it.

Read every saved file with `show` (no key, no API call). It detects the file
type and prints a compact summary: rows with `countKeywordsBeforeLimit` for
`related`; overlap stats, KD, both result lists and `PAA` lines for
`serp-dual`. A broken file (error, empty, not JSON, cut off) gives one
`call failed: ...` message and exit 1, the error to handle under Output
principles; `unrecognised file` (or `call failed: unexpected response shape`)
means the call succeeded with an unexpected shape (inspect the file with a
short script); `no location matched` is an empty `locations` result. `show` prints files in API order: whenever a step
says to filter or sort, do it in a short Python script over the saved file and
print only the matching rows; never pick keywords from the first rows of
`show`. Field names are in the reference, §1.

## Every SERP check is dual: country + one city

Google often serves a city-located searcher a very different SERP; in testing
the national and city top 10 for the same keyword shared as few as 1 of 9
domains, sometimes none. So every SERP check runs `serp-dual` for the country
and one city (the seed's national half is fetched in Step 1 and completed in
Step 2):

```bash
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py serp-dual --kw "<keyword>" --country <country> --city-id <id> --city-label "<label>" > <run>/serp-<slug>.json
```

- **The client picks the city at the end of Step 1**, after the full
  explanation (see Step 1). If they name a different city, look it up (free)
  and show the first 10 matches, cities first; take the `City` row with the
  right region (Nashville, Tennessee, not Nashville, Arkansas), skip
  `INACTIVE` rows, and if nothing matches retry with the city name alone. A
  city must be inside the run's country; if the client names one abroad, say
  so and keep the run's country.
  ```bash
  export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py locations --query "<city>" --country <code> > <run>/locations.json; python3 <skill-folder>/scripts/mangools.py show <run>/locations.json --rows 10
  ```
- **Reuse that city for the whole run**: every `serp-dual` passes the same
  `--city-id`. Don't ask again.
- **Report the comparison** from the `comparison` block (`shared_domains`,
  `country_only`, `city_only`, `overlap_pct`; definition in §1). Below ~50%
  overlap, say that the two audiences see different results and what differs.
- **Cost: 4 SERP units per keyword** (2 per SERP) on paid plans, **2** (1 per
  SERP) while the welcome bonus lasts (Step 0); say so when quoting quota for
  Steps 2–3. The seed costs one SERP in Step 1 and one in Step 2 when Step 2
  runs within 24 hours (identical calls repeat free for 24 hours; otherwise
  two). Mangools allows 3 requests per 30 seconds per pool and asks for 11
  seconds between them, so the script waits 11 s between its two calls and
  the loops below wait 11 s between keywords (about 35 s per keyword); it
  retries rate limits and transient errors itself and reports each wait on
  stderr.
- **`related` stays national**: volume and KD are national figures; only
  ranking data is dual.

## Running the pipeline

Run the steps in order; after each, show a compact summary and confirm before
spending more quota. Two questions wait for the client's answer before Steps
2–5 spend anything: the client profile (Step 0b) and the city (Step 1). For a
partial request ("just the gap analysis") run Steps 0 and 0b, then only what
that part needs (gap: Step 2 with its city question unless the user names
competitors, then Step 4; gap itself is national), then stop.

### Step 0 — Quota check (free)
```bash
python3 <skill-folder>/scripts/mangools.py slug --kw "<seed>"   # <run> = data/<printed slug>-<country-code>
mkdir -p <run>
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; curl -s --retry 2 -H "x-access-token: $MANGOOLS_API_KEY" https://api.mangools.com/v3/kwfinder/limits > <run>/limits.json; python3 <skill-folder>/scripts/mangools.py show <run>/limits.json
```

Tell the user what is left and what the run costs, in the two units `show`
prints. Mangools spends a Free or Free+ account's one-time API & MCP welcome
bonus before the daily limits. While `show` prints a `welcome bonus left`
line, quote each unit that line lists from its bonus figure, not the daily
one above it, and at the bonus rate; a unit it does not list is on the daily
limits at the paid rate:

| Fresh call | Paid plans (Entry, Basic, Premium, Agency), and Free/Free+ once the bonus is used up | Welcome bonus |
|---|---|---|
| `related` | 2 keyword lookups | 1 |
| `serp` / `serp-dual` | 2 / 4 SERP units | 1 / 2 |
| `import-keywords` (up to 100 phrases) | 2 keyword lookups | 1 |
| `domain-keywords` | 2 keyword lookups | 1 |
| `gap`, one page | 10 keyword lookups | 1 |

An identical call within 24 hours is free (keyword imports excepted). Per
step: Step 0b = 0, or one `domain-keywords` if the optional check is used;
Step 1 = one `related` + one `serp`; Step 2 = one SERP (the city half; the
national half repeats free); Step 3 = one `serp-dual` per long-tail checked;
Step 4 = one `gap` per page; Step 5 = one `import-keywords` plus one `related`
per discovery lookup (one or two). `show` also prints how many competitors
one `gap` call takes; Step 4 never passes more.

If `show` prints `welcome bonus used up for <unit>`, that unit is back on the
account's daily limits at the paid rate (Free: 5 keyword lookups and 5 SERP
units a day; Free+: 10 and 10). Tell the user which steps still fit:
- SERP units used up: Steps 1–2 fit; Step 3 takes N from the daily figure
  (§4: none on Free, one on Free+), so the long-tails stay `not_checked`;
  Steps 4–5 still run on the keyword bonus.
- Keyword lookups used up: each keyword call costs 2 from the daily limit
  (Step 1's `related` fits) and Steps 2–3 run on the SERP bonus, but a `gap`
  page costs 10, more than Free has in a day and all of Free+'s, so offer to
  skip Step 4; Step 5 needs 4–6.
- Both used up: only Steps 0–2 fit, and on Free the gap analysis never will.

Say so plainly, offer to stop where the quota ends or a paid Mangools plan,
and never promise that the rest fits tomorrow. For an account with a bonus,
re-run this check (free) before Steps 3, 4 and 5 and use that check's figures
for the step (Step 3's N, Step 4's competitors per call); say so if a bonus
figure has dropped to 0.

If the loader printed its error, or `show` prints `key not recognised`, the
key did not load or was not recognised: stop and ask for a corrected
`mangools.env`. If Step 0 alone prints `call failed:`, re-run it once; if it
fails again, see "If Mangools is blocked".

### Step 0b — Client profile (free; optional domain check), first question
Build a two-to-three-line profile of the client's business: what it offers
(products, services or content), its main offerings or features, and who it
is for. Sources, cheapest first:
1. your own knowledge of the brand, as a draft to confirm;
2. the site itself, opened with your web tool (not the code sandbox, which in
   claude.ai can reach only api.mangools.com): the homepage title, H1, meta
   description, the products, services or features menu and the footer; if
   the menu shows a products, services or pricing page, open that too,
   because a homepage rarely names every offering. With no web tool and no knowledge of the
   brand, ask the user to describe the site in two lines or paste the
   homepage text;
3. only if the profile is still vague, offer in the same confirmation message
   an optional Mangools check (one `domain-keywords`): up to 1,000 keywords the
   domain ranks for, mostly in positions 40–100, so not its best keywords;
   `show` prints the recurring terms, which hint at the site's field (for an
   SEO suite: seo, backlink, keyword, serp, rank). Run it only if the user
   says yes, then show the sharpened profile once more.
   ```bash
   export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py domain-keywords --url <user-domain> --location <country-id> > <run>/domain-keywords.json; python3 <skill-folder>/scripts/mangools.py show <run>/domain-keywords.json --rows 10
   ```

Show the profile and ask the user to confirm or correct it, in your own
words, then wait. If the user corrects or rewrites it, their wording becomes
the profile and overrides anything you found; if they only say it is wrong,
ask them to describe the site in two lines. Invite them to add offerings they
plan to launch or markets they want to enter, since keyword research is often
about where the business is going. The confirmed profile is the yardstick
wherever relevance is judged, Steps 2–5 (§2): "about the client's topic" means
serving a need the client's business serves or wants to serve, in the seed's
sense.

### Step 1 — Seed metrics, then the city question (second question)
Run `related` for the seed (volume, CPC; command above) and fetch its national
SERP for the freshest KD, which also updates the value KWFinder stores:

```bash
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py serp --kw "<seed>" --location <country-id> > <run>/seed-serp-<slug>.json; python3 <skill-folder>/scripts/mangools.py show <run>/seed-serp-<slug>.json --rows 10
```

Report volume and CPC (from `related`), KD (from the SERP file; `seo` in
`related` is not used for the seed), one line on what it means (demand,
competition), and `countKeywordsBeforeLimit` next to the row count so users
on capped plans see what their plan hides. If the volume is null, say so,
report the CPC as returned, show the three to five closest related keywords
that contain the seed with their volumes (non-branded first, e.g. "free
backlink checker, 2,900"), and ask the user which one to treat as the demand
signal, or none; leave the seed's volume empty in the export and never invent
a number. Apply the ambiguous-seed rule of §2 to this national SERP now, here
only: if it fires, put the seed choice in the same message as the city
question below, and if the client switches seed, repeat Step 1 for the new
seed (one `related` + one `serp`, in a new run folder) before Step 2.

**Then, in the same message, ask the client to pick the city:**

```bash
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py suggest-cities --country <country> --n 3 --kw "<seed>" > <run>/cities.json; python3 <skill-folder>/scripts/mangools.py show <run>/cities.json
```

It is free and returns 3 random major cities with verified IDs plus
`client_message`, a complete explanation. For a country outside the built-in
six it returns no cities and a `client_message` that asks the client to name
one or two major cities; look the answer up with `locations --query "<city>"
--country <code>` (the two-letter code is in the `country` field). **Show `client_message` in full as
the text of your reply, right after the seed metrics.** You may adapt the
wording to the niche, but keep all its parts: what happens (results differ by location
and change often), why it matters (customers search from real cities, the
national results alone can point to the wrong competitors), what they get
(both result sets side by side, a more reliable competitor list), what it
costs (each ranking check runs once more for the city; add the figure at
the Step 0 rate, 2 extra SERP units per check on paid plans or 1 on the
welcome bonus; same city for the whole run, asked once), the numbered cities or the request
to name one, and that they can name their own. Never ask it without the explanation, never through
a tappable-options tool (the explanation gets lost), and wait for the answer
before Step 2; keep the three IDs to map the answer ("2", "Houston").

### Step 2 — Real organic competitors
Run `serp-dual` for the seed with the chosen city, and remind the client in
one sentence what the two checks are for. Then:

1. **Filter** both `comparison` lists: drop the user's own domain and the
   generic platforms of §2, and say which you removed.
2. **Classify** every remaining result by title and URL as direct, publisher,
   marketplace/directory, community, platform or off-topic (§2), judged
   against the confirmed client profile (Step 0b). Platform
   results stay in the tables, labelled (e.g. "app store listing") with a
   one-line intent insight; off-topic domains are named in one sentence and
   never used again. State the seed's dominant intent in one line (the
   ambiguous-seed check itself was done in Step 1).
3. **Show two tables, one per location.** Columns: `#` (the organic rank
   `pos`; ads and features are skipped), domain, the full ranking URL exactly
   as returned (never shortened: a listicle and a free tool page on the same
   domain compete differently), and your short page-type read (free tool,
   homepage, guide, listicle, comparison, help doc). Mark domains that appear
   in both tables, then give the overlap stats in one line; they count generic
   platforms too, so name those when quoting them.

   **United States (national)**

   | # | Domain | Ranking page | Page type |
   |---|---|---|---|
   | 1 | mailflowauthority.com | https://mailflowauthority.com/monitoring-analytics/deliverability-monitoring-tools | Tool comparison |
   | 2 | warmy.io | https://www.warmy.io/blog/email-deliverability-testing-methods-placement-diagnostics/ | Guide |

   **Boston, MA (city)**

   | # | Domain | Ranking page | Page type |
   |---|---|---|---|
   | 1 | mxtoolbox.com | https://mxtoolbox.com/deliverability | Free tool |

4. **Merge** into one competitor set: every direct, publisher, marketplace or
   community domain from either SERP, deduped, tagged with its class, with
   country / city / both, its best position and its full URL(s) (both URLs
   when a domain ranks with different pages, a finding in itself); order by
   "both" first, then best position. Step 3 checks presence against this set.
   If everything got filtered, use §2's fallback.
5. **Pick the strongest direct competitors, as many as one `gap` call takes
   (Step 0; five on most plans)** (businesses offering what the client
   offers) for the gap analysis and say which; publishers of listicles make
   weak gap baselines.

Close with one or two sentences on what the city check showed: low overlap,
what differs and how it shaped the set; high overlap, the list holds across
locations. KD: one value per keyword, the national SERP KD where a SERP was
checked and `seo` otherwise (§1); mention the city KD only when it differs
from the national one by more than ~15 points.

### Step 3 — Long-tail discovery
From the Step 1 `related` file (no new call) keep the keywords that contain
the seed, excluding the exact seed, with volume ≥ 10 and KD ≤ 60 or null (§4),
in a short Python script, sorted by volume; take up to 50. If fewer than ~10
remain (common with 3+ word seeds), say so and offer to widen to related
keywords that pass the profile test (§2) with the same thresholds. Quote the cost (4 SERP
units per keyword, 2 on the welcome bonus), confirm, then run `serp-dual` on
the top N (§4: at most 25, and never more than half of the SERP units the
latest quota check showed: the bonus figure while the SERP bonus lasts, the
daily one after), reusing the
run's `--city-id`, in batches of about 5 keywords per command (a longer batch
can outlast a single command's time limit):

```bash
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; for kw in "<keyword 1>" "<keyword 2>" "<keyword 3>"; do slug=$(python3 <skill-folder>/scripts/mangools.py slug --kw "$kw"); python3 <skill-folder>/scripts/mangools.py serp-dual --kw "$kw" --country <country> --city-id <id> --city-label "<label>" > "<run>/serp-$slug.json"; grep -q CreditLimit "<run>/serp-$slug.json" && break; sleep 11; done
```

`show` each file and record, per keyword, which merged-set domains appear in
the top 10 of the country SERP, the city SERP or both. A keyword is
`validated` when a direct domain from the merged set appears in either SERP, `content_competition` when
only publishers, marketplaces or communities appear, `checked` when none
appear; keywords you did not check are `not_checked` (§4, §9). Keep every
competitor's full URL for the export; in the chat table show `domain #pos`
and say the URLs are in the export.

### Step 4 — Gap analysis
`gap --domain <user> --competitors <c1,...> --location <country-id> --page <n>`
with the direct domains picked in Step 2 (never generic, platform or
off-topic domains, and never more than the competitors per call of the
latest quota check), one file per page (`<run>/gap-p<n>.json`), one `gap` call each,
up to 3 pages by §5's stop rule. Collect the keywords where
competitors rank and the user doesn't, apply §5's progressive filter in a
short Python script over the saved files, drop the keywords that fail the
profile test (§2) on every plan, then prioritise each gap high/medium/low
with a one-sentence reason; sort by priority, then volume. On plans without
pagination (`isAllowedPagination` false in `show`) follow §5's sample rule
for the dropped ones. If the pool is empty, say so plainly.

### Step 5 — People Also Ask
Collect the real questions first, for free: `show` prints the
`PEOPLE_ALSO_ASK` questions of every SERP saved in this run's folder as `PAA` lines (4 per SERP
when present; about half the SERPs had none in testing). Pool and dedupe
them, drop off-topic questions (the same test as §2) and name them. If fewer
than ~10 remain, add your own realistic questions for the seed and top
keywords (how/what/why/when/which/is/can/does, specific) up to ~15–20. Then
check the volume of the whole pool in one `import-keywords` call:

```bash
printf '%s\n' "<question 1>" "<question 2>" "<question 3>" > <run>/questions.txt
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; python3 <skill-folder>/scripts/mangools.py import-keywords --file <run>/questions.txt --location <country-id> --language <language-id> > <run>/questions-import.json; python3 <skill-folder>/scripts/mangools.py show <run>/questions-import.json --rows 5
```

The header line (`N rows for M imported keywords | k with volume`) is what
matters; the rows stay in the file. Exact question phrasings rarely have a
volume figure (2 of 32 in testing); say so plainly. Then run `related` on the
most general question of the pool, and on a second one only if
the first brought fewer than ~5 question-form rows with volume: each response
holds up to the plan's row cap (200 on Basic) of neighbouring phrases, and the
question-form ones with volume are real question keywords nobody generated
(in testing: "how to check keyword position on google", 1,000; "how to track
keyword ranking", 720). Take them into the pool in a short Python script over
the saved `<run>/paa-*.json` files.

```bash
export MANGOOLS_API_KEY="$(python3 <skill-folder>/scripts/loadkey.py <path-to-uploaded-mangools.env>)"; for kw in "<general question 1>" "<general question 2>"; do slug=$(python3 <skill-folder>/scripts/mangools.py slug --kw "$kw"); python3 <skill-folder>/scripts/mangools.py related --kw "$kw" --location <country-id> --language <language-id> > "<run>/paa-$slug.json"; grep -q CreditLimit "<run>/paa-$slug.json" && break; sleep 11; done
```

Sort by volume, then by how many SERPs showed the question. Questions with
volume are keywords like any other and may form a `blog_post` page; questions
without volume become FAQ entries of the closest page in Step 9 (§8).

### Step 6 — Topic + page-type clustering
Pool the long-tails, gap keywords, PAA questions and the question keywords
harvested in Step 5; dedupe. Group them into
**specific, subject-matter topic clusters** (never generic labels like
"Informational" — see the reference's naming rules), and tag every keyword with
one page type: `blog_post`, `feature_page`, `glossary`, `comparison`,
`landing_page`, or `case_study`. For large pools, cluster in batches of ~40 and
merge clusters that share a topic name. Every keyword must land in a cluster.

### Step 7 — Export
Offer two CSVs and a JSON in §9's formats: the full deduped keyword list
(keyword, topic, page type, volume, KD, traffic estimates, SERP status,
competitor URLs) and, after Step 9, the page recommendations. Write real
files to disk and hand them over so the user can download them.

### Step 8 — Traffic summary
Using the position-based CTR table in the reference, report totals: keyword
count, total monthly search volume, estimated traffic if ranking #1
everywhere, and a conservative average across positions 1–5, plus a breakdown
by page type.

### Step 9 — Page recommendations
The payoff. Produce **up to 12 page recommendations**, one per distinct
high-opportunity cluster (no two pages for the same topic; clusters without
volume data become FAQ sections per §8). For each: page type, exact suggested
title, 3–5 target keywords from the real data, summed volume, estimated
monthly traffic (28.7% × volume), average KD, a competitor example URL, and a
one-sentence strategic rationale. Score and rank each page **70% estimated
traffic + 30% ease of ranking** (see the reference for the exact normalised
formula), sort by score, and present as a ranked roadmap. Finish with ~12
adjacent seed keywords to research next.

## Output principles

- Ground every number in real Mangools data — never invent volumes or KD.
- Keep intermediate output skimmable (tables/short summaries); save the heavy
  detail for the CSV/JSON exports.
- A `call failed:` message: show it plainly and continue with what you have
  rather than aborting the run. The script already retries rate limits (429)
  and server errors up to five times; if a file still holds a `Mangools 429`
  or `Mangools 5xx` error, wait a minute and re-run that one call once (the
  half of a `serp-dual` that already succeeded repeats free; the failed half
  is billed when it succeeds). If only the city half failed, `show` says so
  and prints the country half, which stays in the file under `country`; use
  it if the step stops there. A 429
  that says `CreditLimit` means the quota is used up: the script stops
  at once; stop that step, tell the user when the quota resets (`quota resets
  in N s` in the message), and do not retry. If the message also says
  `welcome bonus used up for <unit>`, that unit's one-time bonus is spent:
  re-run the Step 0 check (free), tell the user which remaining steps still
  fit (Step 0's used-up rules), and don't promise to finish tomorrow.
- The reference file is authoritative for any threshold, formula, class or
  list — consult it rather than guessing.

### If Mangools is blocked
If every call fails the same way, including Step 0 (`call failed: empty file`,
a `Mangools 403`, a `Request failed` / `Gave up after retries` error, or a
non-JSON page mentioning a proxy or allowlist), the sandbox is not allowed to
reach `api.mangools.com`. This happens wherever the script runs in a sandbox:
Claude chat, Cowork and Claude Code cloud sessions; never in a local Claude
Code session. Stop and tell the user:

> Claude's sandbox can't reach the Mangools API yet. In Claude chat, open
> Settings → Capabilities, make sure code execution and network egress are on,
> and add api.mangools.com to the allowed domains. On a Team or Enterprise
> plan, an Owner adds it under Organization settings → Capabilities. In a
> Claude Code cloud session, set the environment's Network access to Custom,
> add api.mangools.com under Allowed domains and tick "Also include default
> list of common package managers" so your other sessions can still install
> packages. Then start a new chat.
> On the Free Claude plan you can't add allowed domains, so the script can't
> run there: use a paid Claude plan, or connect the Mangools connector
> (mangools.com/mcp) and I'll get the data through it.

If Mangools connector (MCP) tools are already available in this chat, say
that the script is blocked and ask whether to continue through the connector
instead. If the user agrees, run the same steps with the matching connector
tools and say which data the connector did not return.
