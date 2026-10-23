# Mangools SEO skill for Claude

**Keyword research, competitor gap analysis and a prioritized content plan, built on live Mangools data.**

The Mangools SEO skill is a Claude skill for keyword research and content planning. You can give Claude a seed keyword and your domain, and the SEO skill will run a 9-step research pipeline on live data from the [Mangools API](https://mangools.com/api) ([KWFinder](https://mangools.com/kwfinder/) and [SERPChecker](https://mangools.com/serpchecker/)).

The SEO skill will find during the process your real organic competitors in both a country and a city SERP, discovers long-tail keywords, runs a competitor keyword gap analysis, collects People Also Ask questions, groups everything into topic clusters tagged by page type and estimates the traffic each page could bring.

At the end you will get a ranked list of pages to create from the performed keyword research and downloadable CSV and JSON files.

It works in Claude chat (claude.ai and the desktop and mobile apps), in Cowork and in Claude Code (skill name: `kw-research-pipeline`).

## Quick start

1. **Install the skill.** Download [`kw-research-pipeline.skill`](https://github.com/mangools/seo-skills/releases/latest/download/kw-research-pipeline.skill). In Claude, open **Settings → Customize → Skills**, click **+**, then **Create skill → Upload a skill**, and select the file. Using Claude Code on your computer? [Unzip it into `~/.claude/skills/` instead](#how-to-install-mangools-seo-skill).
2. **Let Claude reach Mangools.** On a paid Claude plan, add `api.mangools.com` to the allowed domains ([how](#requirements-for-the-mangools-seo-skill)) and start a new chat. On the Free Claude plan, add the [Mangools connector](https://mangools.com/mcp) instead. When Claude says its script can't reach Mangools and asks whether to continue through the connector, say yes.
3. **Run it.** Copy your API key from [mangools.com/api-token](https://mangools.com/api-token) into a plain text file named `mangools.env` with one line, `MANGOOLS_API_KEY=your-key-here`. Attach the file to a new chat and write: *Run keyword research for "your keyword" for yoursite.com.*

A full run takes about 15–30 minutes. Stay in the chat: Claude asks you to confirm what your site offers, to pick a city and to approve each step that spends lookups.

On a free Mangools account, the first run uses about 6 keyword lookups and 50 SERP lookups of your one-time welcome bonus (100 of each). Later runs check fewer long-tail keywords, so the bonus covers about two full runs plus a smaller third one. On a Mangools Basic plan, a run uses about 16–20 keyword lookups and 56 SERP lookups.

## Table of contents

- [Quick start](#quick-start)
- [What is a Claude SEO skill?](#what-is-a-claude-seo-skill)
- [Why use the Mangools SEO skill for Claude](#why-use-the-mangools-seo-skill-for-claude)
- [Manual keyword research vs. standard AI prompts vs. Mangools SEO skill](#manual-keyword-research-vs-standard-ai-prompts-vs-mangools-seo-skill)
- [Who is the SEO skill for?](#who-is-the-seo-skill-for)
- [Requirements for the Mangools SEO skill](#requirements-for-the-mangools-seo-skill)
- [How to install Mangools SEO skill?](#how-to-install-mangools-seo-skill)
- [How to use Mangools SEO skill](#how-to-use-mangools-seo-skill)
- [Mangools SEO skill: Keyword research pipeline and output](#mangools-seo-skill-keyword-research-pipeline-and-output)
- [Mangools SEO API credit usage](#mangools-seo-api-credit-usage)
- [Limitations and troubleshooting](#limitations-and-troubleshooting)
- [Frequently asked questions](#frequently-asked-questions)
- [Help and feedback](#help-and-feedback)
- [About Mangools](#about-mangools)

## What is a Claude SEO skill?

A Claude SEO skill is an add-on that teaches Claude how to do a specific SEO task, such as keyword research, SERP analysis or content planning. It's a folder with a SKILL.md file of instructions at its root, often with reference files and scripts alongside it, and Claude loads it automatically when your request matches what the skill does. An SEO skill packages an SEO workflow this way, so Claude follows the same method, thresholds and data sources every time instead of improvising.

The Mangools SEO skill packages a complete keyword research method plus a small Python client for the Mangools API. Claude does the orchestration and the SEO analysis, and the Mangools API provides the SEO data to work with.

<p align="center"><a href="https://mangools.com/users/sign_up"><strong>Create a Mangools account & get API access for FREE →</strong></a></p>

## Why use the Mangools SEO skill for Claude

- **Real data, not guesses** - search volume, keyword difficulty (KD) and ranking positions come from the Mangools API. If a seed keyword has no volume figure, Claude says so and shows you the closest variants instead of guessing.
- **Country and city SERPs, side by side** - Google often shows someone searching from a city a different top 10 than the country as a whole. So every ranking check runs twice, once for the country and once for a city you choose, and you see both.
- **Competitors judged against your business** - before spending any quota, Claude writes a description of your site (to ensure that it understands your brand correctly) and asks you to confirm it. You can also add products you plan to launch or markets you want to enter. Every ranking result is then classified as a direct competitor, publisher, marketplace/directory, community, platform or off-topic, so a listicle or an app-store page doesn't end up as a baseline in your gap analysis.
- **You control your quota** - Claude checks your remaining Mangools quota first, tells you what each step costs and asks you to confirm whether or not you want to spend it. Long-tail SERP checks are capped at 25 keywords and never use more than half of your SERP lookups. Identical calls repeated within 24 hours are free on the Mangools side, except keyword imports.
- **Full pipeline or a single step** - run all 9 steps, or ask only for the gap analysis, the competitors or the questions.
- **You keep all the files** - the keyword list and page recommendations as CSV, plus a JSON file, ready to download.

## Manual keyword research vs. standard AI prompts vs. Mangools SEO skill

|  | Manual research in an SEO tool | Plain AI prompt | Mangools SEO skill |
| ----- | ----- | ----- | ----- |
| **Your time** | Hours of exporting, filtering and pivoting | Minutes | Minutes. Claude does the lookups and analysis, you approve each step that spends lookups |
| **Where the numbers come from** | Your SEO tool | The model's memory, so volumes and KD are often made up | Live data from the Mangools API (KWFinder + SERPChecker) |
| **Competitor discovery** | You check SERP results by hand | Guesswork | Live SERPs, every result compared against your confirmed business profile |
| **Location** | Usually one SERP location at a time | None | Country and city SERPs side by side |
| **Clustering** | Spreadsheets and pivot tables | Generic groupings | Specific topic clusters, every keyword tagged with a page type |
| **Prioritization** | Judgment call | Qualitative advice | Score: 70% estimated traffic + 30% ease of ranking |
| **Output** | Exports you assemble yourself | Text in the chat | Keyword CSV, recommendations CSV and JSON |

## Who is the SEO skill for?

### a) In-house SEO and content leads

Turn a seed keyword into a ranked roadmap of pages, each with target keywords, estimated traffic at #1, average KD and a competitor example URL, without the spreadsheet work.

### b) SEO agencies and consultants

Run the same documented method for every client and show them a clear competitor map, keyword gaps and a ready-to-go content plan.

The city check also helps clients who offer services or sell products in specific areas because you see who ranks in an exact location and not just nationally (which is excellent for local SEO).

### c) SaaS and e-commerce founders

See which keywords your direct competitors rank for and you don't, which long-tail search queries are realistic to target (KD 60 or lower) and rank for with your website and which pages to publish first.

### d) Beginners and site owners

All you need is a seed keyword and your domain. Claude explains each step in plain language, keeps the summaries short and asks before it spends any quota.

## Requirements for the Mangools SEO skill

**1. A Claude plan with skills and code execution** - the skill runs a script that calls the Mangools API. Use a paid Claude plan (on the Free Claude plan you can't add allowed domains, so the script can't reach Mangools), or connect the [Mangools connector](https://mangools.com/mcp) and Claude gets the data through it.

| Claude plan and type | What to do |
| ----- | ----- |
| Pro or Max plan | Open **Settings → Capabilities**, turn on code execution and network egress, then add `api.mangools.com` to the additional allowed domains. |
| Team or Enterprise plan | An Owner opens **Organization settings → Capabilities**, allows network egress to package managers and specific domains, and adds `api.mangools.com`. |
| Claude Code cloud session | Open the session's cloud environment from the environment selector, set **Network access** to **Custom**, add `api.mangools.com` under **Allowed domains** and tick **Also include default list of common package managers**, so your other sessions can still install packages. On Team and Enterprise, only an Owner can change a shared environment. |
| Claude Code, local | Nothing to do. |
| Free Claude plan | Allowed domains aren't available. Use the [Mangools connector](https://mangools.com/mcp) instead. |

**2. A Mangools account and API key** - copy your key at [mangools.com/api-token](https://mangools.com/api-token). Every lookup runs against your own Mangools account and counts toward your plan's limits. On Entry and Basic plans the gap analysis returns a small sample per competitor. Premium and Agency plans, and free accounts while the welcome bonus lasts, get a much longer list.

**3. Network access to `api.mangools.com`** - wherever Claude runs the script in a sandbox: Claude chat (claude.ai, or the Chat tab of the desktop and mobile apps), Cowork and Claude Code cloud sessions. A local Claude Code session runs on your own computer and doesn't need it.

## How to install Mangools SEO skill?

### 1. Claude chat and Cowork

- Download [`kw-research-pipeline.skill`](https://github.com/mangools/seo-skills/releases/latest/download/kw-research-pipeline.skill) from the latest release.
- In Claude, open **Settings → Customize → Skills**.
- Click **+**, then **Create skill → Upload a skill**, select the file and make sure the skill's toggle is on.

Skills you upload in Claude also load in Cowork and in Claude Code cloud sessions.

> [!WARNING]
> Don't use GitHub's green **Code → Download ZIP** button or the release's **Source code (zip)**. Those files wrap the skill in an extra folder, and Claude won't accept them. Download `kw-research-pipeline.skill` from the link above.

> [!NOTE]
> If you use Claude Code locally: Claude Code loads personal skills from `~/.claude/skills/`. The `.skill` file is a zip archive, so install it with:
>
> ```bash
> mkdir -p ~/.claude/skills
> unzip -o ~/Downloads/kw-research-pipeline.skill -d ~/.claude/skills/
> ```
>
> `-o` replaces an older version without asking. If your browser saved the file somewhere else, change the path. Check that `~/.claude/skills/kw-research-pipeline/SKILL.md` exists, then restart Claude Code. You'll also need Python 3 and curl on your machine. Save `mangools.env` in `/tmp/kw-research` (see below). Claude writes the research files there too, outside any git repository, so they are never committed. Your computer may empty `/tmp` when it restarts, so copy the CSV and JSON files you want to keep.

### 2. Save your API key as a file

Create a plain text file named `mangools.env` with exactly one line:

```
MANGOOLS_API_KEY=your-key-here
```

In Claude chat, attach this file to the conversation instead of pasting the key, so the key never appears in the chat.

In Claude Code on your computer, create the folder with `mkdir -p /tmp/kw-research`, save the file there as `mangools.env` and tell Claude where it is.

<p align="center"><a href="https://mangools.com/users/sign_up"><strong>Sign up to Mangools & get the FREE API access →</strong></a></p>

## How to use Mangools SEO skill

Start a chat, attach `mangools.env` and say what you want, for example: *Run keyword research for the seed "uptime monitoring". My domain is mysite.com. My Mangools key is in the attached mangools.env.*

Claude then:

1. Checks your remaining Mangools quota and tells you what the run will cost.
2. Sums up what your site offers in two or three lines and asks you to confirm or correct it.
3. Reports the seed keyword's volume, CPC and KD, explains the country + city check and asks you to pick a city (one of three suggestions, or your own).
4. Works through the remaining steps, with a short summary after each one and a question before anything that spends quota.
5. Hands you the CSV and JSON files.

### Example prompts for the SEO skill

| Goal | Prompt |
| ----- | ----- |
| Full keyword research and content plan | *Run keyword research for "project management software" for mysite.com. My Mangools key is in mangools.env.* |
| Keyword gap against competitors you name | *Find keyword gaps between mysite.com and competitor1.com, competitor2.com and competitor3.com. Key in mangools.env.* |
| Your real organic competitors | *Who are my real organic competitors for "email warmup"? My domain is mysite.com.* |
| Long-tail keywords | *Find low-difficulty long-tail keywords for "keyword tracker" for mysite.com.* |
| Questions people ask | *What questions do people ask about "rank tracking"? Check which ones have search volume. My domain is mysite.com.* |
| Another country and language | *Run keyword research for "gartenmöbel" in Germany, in German, for mein-shop.de.* |

When you name the competitors for a gap analysis (up to five), Claude skips competitor discovery and goes straight to the gap step.

Every partial run still starts with the free quota check and the site-profile confirmation, then runs only the steps that part depends on.

<p align="center"><a href="https://mangools.com/users/sign_up"><strong>Create a FREE Mangools account & get the API access →</strong></a></p>

## Mangools SEO skill: Keyword research pipeline and output

Two free checks come first (your quota and your site profile), then nine steps. Claude always confirms with you before each step that spends quota. Here is the full breakdown of the SEO skill process:

| Step | What happens | Mangools cost | What you get |
| ----- | ----- | ----- | ----- |
| **0a. Quota check** | Reads your remaining keyword lookups and SERP lookups (`/v3/kwfinder/limits`) and estimates what the run will cost. | Free | Remaining quota and cost per step |
| **0b. Site profile** | Claude drafts a short profile of your business from its own knowledge and your site's homepage and product pages. You confirm or correct it. If it's still vague, Claude can offer a domain-keyword check. | Free (optional check: 2 keyword lookups) | The yardstick for every relevance decision |
| **1. Seed metrics** | Volume and CPC from KWFinder, KD from a fresh national SERP. Flags ambiguous seeds. Then asks you to pick the city used for all ranking checks. | 2 keyword lookups + 2 SERP lookups | Seed baseline and your city |
| **2. Organic competitors** | Country and city SERPs for the seed. Removes your domain and generic platforms, classifies every result (direct, publisher, marketplace/directory, community, platform, off-topic) and records each full ranking URL and page type. | 2 SERP lookups (4 if more than 24 hours after Step 1) | Two SERP tables, overlap stats, a merged competitor set and your five strongest direct competitors |
| **3. Long-tail discovery** | From the seed's related keywords: those that contain the seed, with volume ≥ 10 and KD ≤ 60 (or no KD yet). Up to 25 are checked in both SERPs. | 4 SERP lookups per keyword checked | Long-tails labeled `validated`, `content_competition`, `checked` or `not_checked`, with competitor URLs |
| **4. Gap analysis** | Keywords your 5 direct competitors rank for and you don't, filtered for relevance to your business. | 10 keyword lookups per page (up to 3 pages) | Gap keywords prioritized high / medium / low, each with a one-sentence reason |
| **5. People Also Ask** | Real PAA questions collected from the SERPs already fetched. Claude adds its own only if fewer than about 10 remain. Volumes checked in one import; question keywords with real volume harvested from related searches. | 2 keyword lookups for the import + 2–4 for discovery | Question keywords with volume, plus questions for FAQ sections |
| **6. Topic clustering** | Pools long-tails, gaps and questions into specific subject clusters and tags each keyword with a page type: `blog_post`, `feature_page`, `glossary`, `comparison`, `landing_page` or `case_study`. | Free | A topic map by page type |
| **7. Export** | Writes the files to disk for download. | Free | Keyword CSV, page-recommendation CSV and JSON |
| **8. Traffic summary** | Applies a position-based click-through-rate model. | Free | Traffic if you ranked #1 everywhere, a conservative average across positions 1–5 and a breakdown by page type |
| **9. Page recommendations** | One page per high-opportunity cluster, scored 70% estimated traffic + 30% ease of ranking. | Free | Up to 12 ranked pages, plus about 12 adjacent seed keywords to research next |

The costs above are for paid Mangools plans, and for free accounts once the welcome bonus is used up. While a free account spends its welcome bonus, every request costs 1: each keyword call in Steps 0b, 1, 4 and 5 (including each gap-analysis page) costs 1 keyword lookup, and each SERP costs 1 SERP lookup per location, so 2 per long-tail keyword checked.

At the end of the process you will get:

**1. A ranked page roadmap** - Each recommendation includes the page type, an exact suggested title, 3–5 target keywords from the real data, their summed search volume, the monthly traffic the page could get at position #1 (28.7% of that volume), average KD, a competitor example URL and a one-sentence rationale. Pages are ranked by a normalized score of 70% estimated traffic and 30% ease of ranking, with no two pages targeting the same topic.

**2. A full keyword list** - Every keyword from the run, deduplicated, with its topic, page type, volume, KD, traffic estimates, SERP status and competitor URLs. Topics without volume data become FAQ sections of the closest page instead of standalone pages.

**3. Country vs. city SERP tables** - For the seed and every long-tail checked, you see which domains rank nationally, which rank in your city and how much the two overlap.

## Mangools SEO API credit usage

Mangools counts 2 things: keyword lookups and SERP lookups. Every call counts toward your own Mangools account's limits.

| Feature/operation | Endpoint | Paid plans (Entry, Basic, Premium, Agency), and free accounts after the bonus | Free account, welcome bonus |
| ----- | ----- | ----- | ----- |
| Related keywords | `GET /v3/kwfinder/related-keywords` | 2 keyword lookups | 1 keyword lookup |
| Keyword import (question volumes) | `POST /v3/kwfinder/keyword-imports` | 2 keyword lookups | 1 keyword lookup |
| Gap analysis (5 competitors) | `POST /v3/kwfinder/gap-analysis` | 10 keyword lookups per page | 1 keyword lookup per page |
| Domain keywords (optional, Step 0b) | `GET /v3/kwfinder/suggested-keywords` | 2 keyword lookups | 1 keyword lookup |
| SERP, one location | `GET /v3/serpchecker/serps` | 2 SERP lookups | 1 SERP lookup |
| SERP, country + city (every ranking check) | `GET /v3/serpchecker/serps` × 2 | 4 SERP lookups | 2 SERP lookups |
| Quota check, location and city lookups | `GET /v3/kwfinder/limits`, location search | Free | Free |

On a Mangools Basic plan (**110 keyword lookups**, **105 SERP lookups**), a full run uses approximately 16–20 keyword lookups and 56 SERP lookups: 4 lookups for the seed and 4 for each of 13 long-tails, because Claude never spends more than half of your SERP lookups on long-tails.

On a free Mangools account, the one-time welcome bonus gives you 100 keyword lookups and 100 SERP lookups. Our first test run on a fresh bonus used 6 keyword lookups and 50 SERP lookups and checked 24 long-tail keywords. Long-tail checks never use more than half of the SERP lookups left, so later runs check fewer keywords (about 26, then 12 SERP lookups), and the bonus covers about two full runs plus a smaller third one.

Repeating an identical call (same keyword, location and language) within 24 hours is free: Mangools doesn't count it again. Keyword imports are the exception and are counted every time.

On larger plans (more SERP lookups, full gap-analysis results), a run can use up to about **40 keyword lookups** and **104 SERP lookups** (25 long-tails).

For more information about individual plans, pricing and lookup credits, make sure to check out the [Mangools pricing page](https://mangools.com/plans-and-pricing).

<p align="center"><a href="https://mangools.com/users/sign_up"><strong>Create a FREE Mangools account →</strong></a></p>

## Limitations and troubleshooting

- Gap analysis depth depends on your Mangools plan: Entry and Basic plans return a sample per competitor. Premium and Agency plans, and free accounts while the welcome bonus lasts, get a much longer list.
- Long-tail SERP checks are capped at 25 keywords per run and never use more than half of your SERP lookups.
- The Free Claude plan can't reach the Mangools API from the sandbox. Use a paid Claude plan or the Mangools connector.

There are a few special circumstances that might prevent the SEO skill from finishing correctly:

### a) Claude's sandbox can't reach the Mangools API

Every call fails the same way, including the quota check: an empty file, a `Mangools 403`, `Request failed` / `Gave up after retries`, or a page that mentions a proxy or allowlist.

Add `api.mangools.com` to your allowed domains as described under [Requirements](#requirements-for-the-mangools-seo-skill), then start a new chat.

On the Free Claude plan, connect the [Mangools connector](https://mangools.com/mcp) instead. If the connector is already connected, Claude offers to continue through it and tells you which data it didn't return.

### b) Rate limits (`Mangools 429`)

The script retries rate limits and server errors on its own, up to five times. If a call still fails, Claude waits a minute and re-runs it once.

A 429 that says `CreditLimit` means your daily quota or your welcome bonus is used up: **Claude stops that step, tells you which steps still fit and when your daily quota resets (the welcome bonus doesn't), and doesn't retry**.

### c) The API key isn't recognized

If the quota check shows 0 for both limits, or Claude reports that no `MANGOOLS_API_KEY=` line was found, re-save `mangools.env` as a plain text file (not RTF or Word) with exactly one line, `MANGOOLS_API_KEY=<your key>`, and attach it again.

### d) `500 No available SERP provider`

The keyword and the language ID don't match, for example a German keyword sent with the English language ID. Tell Claude which language your seed keyword is in.

### e) The gap analysis looks small or empty

On Entry and Basic plans the gap analysis returns a sample per competitor. Premium and Agency plans, and free accounts while the welcome bonus lasts, get a much longer list.

An empty result can also mean that no competitor keyword passed the relevance and volume filters. Claude will inform you about it plainly rather than padding the list.

### f) The seed keyword has no search volume

Claude shows the closest related keywords that contain the seed, with their volumes, and asks which one to treat as the demand signal instead of guessing a volume.

## Frequently asked questions

### 1. What is the Mangools SEO Skill?

The Mangools SEO skill is a Claude skill that runs a 9-step keyword research pipeline with live Mangools data. It needs only a seed keyword and your domain as input and turns them into a prioritized content plan: real organic competitors, long-tail keywords, keyword gaps, People Also Ask questions, topic clusters, traffic estimates and up to 12 ranked page recommendations.

### 2. Does Mangools SEO skill work in Claude Code?

Yes, it does. In a local Claude Code session it works without any network setup; you only need Python 3 and curl on your machine. In Claude Code cloud sessions, Claude chat (web, desktop and mobile apps) and Cowork, the script runs in a sandbox, so `api.mangools.com` must first be added to the allowed domains. The Free Claude plan doesn't allow that, so there you can use the Mangools connector instead.

### 3. Do I need a paid Mangools account?

No, you can try it for free. Every Free and Free+ Mangools account with a confirmed e-mail address gets a one-time API & MCP welcome bonus of 100 keyword lookups and 100 SERP lookups.

While you spend it, each request costs 1 lookup, including each gap-analysis page, and returns Premium-level results, including gap analysis for up to 5 competitors. In our test, the first full run used 6 keyword lookups and 50 SERP lookups. Later runs check fewer long-tail keywords (about 26, then 12 SERP lookups), so the bonus covers about two full runs plus a smaller third one.

The bonus doesn't reset. Once it's used up, Free accounts are back to 5 keyword and 5 SERP lookups a day (Free+: 10 and 10), and each request costs as many lookups as on a paid plan (for example, 4 SERP lookups per ranking check). That covers the first steps of a run but not a full one, so for regular use you'll need a paid Mangools plan.

If you're on the Free Claude plan, Claude gets the data through the [Mangools connector](https://mangools.com/mcp) instead of the script (see the next question).

### 4. Do I need a paid Claude plan?

For the script, yes. The Free Claude plan can't add allowed domains, so the sandbox can't reach the Mangools API. On the Free Claude plan, connect the [Mangools connector](https://mangools.com/mcp) and Claude gets the data through it.

### 5. How much Mangools quota does one run use?

About 16–20 keyword lookups and 56 SERP lookups on a Mangools Basic plan with its full daily quota available. On a free account's welcome bonus, the first run uses about 6 keyword lookups and 50 SERP lookups, and later runs use fewer.

Larger plans can use more, up to about 40 keyword lookups and 104 SERP lookups. See [Mangools SEO API credit usage](#mangools-seo-api-credit-usage) for the breakdown. Claude shows your remaining quota first and asks before every step that spends it.

### 6. Why does it check a city as well as the country?

Google often shows people searching from a city a different top 10 than the country as a whole, so the national SERP alone can point you at the wrong competitors.

You just need to pick the city once and that city is used for the whole run; each ranking check costs 2 extra SERP lookups (1 while you spend the welcome bonus).

### 7. Which countries and languages are supported?

The default is the US in English. Any country Mangools supports works, and Claude looks up the location ID for free.

City suggestions are built in for the US, UK, Australia, Canada, Germany and France; for other countries you just need to name a city. For other languages, simply tell Claude which language your seed keyword is in.

### 8. How are page SEO recommendations scored?

Each page gets a normalized score: 70% estimated monthly traffic (at position #1) and 30% ease of ranking, based on keyword difficulty.

That favors pages with real traffic potential that you can realistically rank for. You will get at most one page per topic cluster and up to 12 pages in total.

### 9. Is my Mangools API key safe?

The skill reads the key from the `mangools.env` file you attach, only inside the command that calls Mangools. The skill tells Claude never to print the key or copy it to another file, and its script sends the key only to `api.mangools.com`.

If you paste the key into the chat instead, Claude saves it to a file for you, but the key is then in the chat history, so reset it at [mangools.com/api-token](https://mangools.com/api-token) afterwards.

In Claude Code, keep `mangools.env` outside any git repository.

### 10. Can I run only part of the SEO pipeline?

Yes. You can just ask for the part you need, for example "*just find the keyword gaps against competitor1.com and competitor2.com*". Claude will check your quota, confirm what your site offers, and then run only the steps that part depends on.

### 11. What's the difference between the Mangools SEO skill and the Mangools connector?

The Mangools connector (MCP) gives Claude access to Mangools data. The SEO skill adds the method on top: the steps, thresholds, competitor classes, clustering rules and scoring that turn that data into a content plan.

<p align="center"><a href="#how-to-install-mangools-seo-skill"><strong>Start using Mangools SEO skill today →</strong></a></p>

## Help and feedback

Stuck, or found a bug? Contact Mangools support through the live chat on [mangools.com](https://mangools.com) or at [mangools.com/contact](https://mangools.com/contact), or [open an issue](https://github.com/mangools/seo-skills/issues) in this repository. Never paste your API key into an issue.

## About Mangools

[Mangools](https://mangools.com) is an easy and affordable SEO suite with tools for keyword research (KWFinder), SERP analysis (SERPChecker), rank tracking (SERPWatcher), backlink analysis (LinkMiner) and domain analysis (SiteProfiler). It also offers several [free SEO tools](https://mangools.com/free-seo-tools) that can simplify your everyday SEO tasks.

Users who would like to use Mangools data in their own projects can also utilize the [Mangools SEO API](https://mangools.com/api), and anyone who'd rather ask Claude in plain language than learn an SEO tool can use the [Mangools MCP connector](https://mangools.com/mcp).

## License

MIT. See [LICENSE](LICENSE).
