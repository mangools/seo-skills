# KW Research Pipeline — Setup (v7.3)

A Claude skill that runs a full 9-step SEO keyword-research pipeline and hands
you a prioritised content plan, backed by live Mangools data.

## What you need

1. **A Claude plan that supports custom skills + Code Execution.** The skill
   runs code to call the Mangools API, so Code Execution must be available in
   your Claude settings.
2. **Your own Mangools API key.** Every lookup runs against *your* Mangools
   account and counts toward your plan's limits. Get your key at
   https://mangools.com/api-token
   (On Entry and Basic plans the gap analysis, Step 4, returns a small sample
   per competitor. Premium and Agency, and Free and Free+ accounts while the
   welcome bonus lasts, get a much longer list.)
3. **Allow the Mangools API once, wherever Claude runs the script in a
   sandbox.** This is needed in Claude chat (claude.ai in the browser, or the
   Chat tab of the desktop and mobile apps), in Cowork, and in Claude Code
   cloud sessions. It is not needed in a local Claude Code session (the
   terminal, or the desktop app's Code tab with Local selected), which runs on
   your own computer.
   - On a **Pro or Max** plan: open **Settings → Capabilities**, turn on code
     execution and network egress, and add `api.mangools.com` to the
     additional allowed domains.
   - On the **Free** plan you can't add allowed domains, so the script can't
     reach Mangools. Use a paid Claude plan, or connect the Mangools connector
     (see https://mangools.com/mcp) and Claude gets the data through it.
   - On a **Team or Enterprise** plan: an Owner opens **Organization settings
     → Capabilities**, allows network egress to package managers and specific
     domains, and adds `api.mangools.com`.
   - In a **Claude Code cloud session**: open the session's cloud environment
     from the environment selector, set **Network access** to **Custom**, add
     `api.mangools.com` under **Allowed domains** and tick **Also include
     default list of common package managers** so your other sessions can
     still install packages. On Team and Enterprise, a shared environment can
     only be changed by an Owner.

   After adding the domain, **start a new chat** (or a new cloud session): the
   allowlist is applied when the chat's sandbox is created, so an open chat
   stays blocked.

## Install the skill

1. In Claude, open **Customize → Skills**.
2. Click **+**, then **Create skill → Upload a skill**, and select the
   `kw-research-pipeline.skill` file you downloaded.
3. Make sure the skill's toggle is **on**.

## Save your key as a file

Create a plain text file named `mangools.env` with exactly one line:

```
MANGOOLS_API_KEY=your-key-here
```

Attach this file to the chat instead of pasting the key, so the key never
appears in the conversation.

## Use it

Start a chat, attach `mangools.env`, and say what you want, for example:

> Run keyword research for the seed "uptime monitoring" — my domain is
> mysite.com. My Mangools key is in the attached mangools.env.

Claude first checks how much Mangools quota you have left, then summarises in
two or three lines what your site offers (from its homepage) and asks you to
confirm, so that competitors and keywords are judged against your business.
Then it walks the pipeline: seed metrics → competitors → long-tails → gap analysis → People Also
Ask → topic clustering → traffic summary → page recommendations, and gives you
downloadable CSV/JSON at the end.

You can also run just part of it — e.g. "just find the keyword gaps against my
competitors" — and Claude will check your quota, confirm what your site
offers, then run only the steps it needs.

## Notes

- **Your key stays in your session.** It's used only to call the Mangools API
  and is never sent anywhere else. If you paste the key into the chat instead
  of attaching the file, Claude saves it to a file for you, but the key is
  then in the chat history: reset it at mangools.com/api-token afterwards.
- **Region:** defaults to US / English. Name any country and language and
  Claude looks up the Mangools location ID. City suggestions are built in for
  the US, UK, Australia, Canada, Germany and France; for other countries
  Claude asks you to name a city.
- **Country + city SERPs:** Google shows different results depending on
  where someone searches from, so the national rankings alone can give a
  misleading picture of your competition. To guard against that, every
  ranking check runs twice, once for the whole country and once for a city
  in it. After the seed metrics (Step 1),
  Claude explains this and offers you 3 cities to choose from (or you can name your own), and that
  city is used for the rest of the run. Rankings often differ a lot between
  the two, so you see both.
- **Costs:** Mangools counts two things, keyword lookups and SERP units. On
  paid plans (Entry, Basic, Premium, Agency) a fresh keyword search (a
  `related` call) costs 2 keyword lookups, a ranking check 4 SERP units (it
  runs twice, for the country and for a city) and a gap-analysis page 10
  lookups. Free and Free+ accounts spend their one-time API & MCP welcome
  bonus (100 keyword lookups and 100 SERP units) first, at 1 per request: a
  keyword search 1, a ranking check 2, a gap page 1. Once the bonus is used
  up, Free (5 lookups and 5 SERP units a day) and Free+ (10 and 10) pay the
  paid-plan rates, which covers the first steps of a run (seed metrics and
  competitors) but not a full one; Claude tells you and offers to stop there.
  Repeating the same call within a day is free (the People Also Ask import
  excepted). Per run: one keyword search for the seed (plus one if
  Claude needs the optional domain check to profile your site), one ranking
  check for the seed plus one per long-tail keyword checked (Claude checks at
  most 25, and never more than half of the SERP units you have left),
  one gap call per page (up to 3), one import to check all People Also Ask
  questions at once and one or two keyword searches to discover related
  questions. On a fresh Basic day (110 lookups, 105 SERP units) a full run
  uses about 16–20 lookups and 56 SERP units. Claude shows your remaining
  quota first and asks before each step that spends it.
