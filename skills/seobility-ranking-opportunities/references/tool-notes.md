# Seobility MCP — verified tool behaviour for this skill

Everything here was checked against a live project, not read off the tool descriptions. Where a
tool description and this file disagree, this file is right.

Verified against a project with roughly 150 monitored keywords.

## The one call that does the work

**`list_keywords(project_id)`** returns the whole monitored set with every field this skill needs:

| Field | What it is |
|---|---|
| `id` | keyword id, needed for any per-keyword call |
| `name` | the keyword |
| `search_engine_name` | `Google.de`, `Google.com`, … — **the grouping key, see below** |
| `rank` | current position, `false` or `null` when not ranking (see below) |
| `rank_type` | `organic`, or `null` when not ranking |
| `rank_change` | change since the previous check |
| `search_volume` | monthly volume for that market |
| `best_ranking_url` | the own URL that ranks |
| `visibility` / `visibility_change` | search-volume-weighted; rows ranked well below 20 still carry points |
| `ai_overview` / `ai_overview_rank` | presence in the AI Overview |
| `intents` | informational / navigational / commercial / transactional, in percent |
| `tags` | the user's own keyword tags, if they use them |

Cost: a stored-data call, at the cheap end.

It has no ranking date, no `date_added` and no `limit`/`offset`. The date and `date_added` of a
keyword come from `get_keyword_overview` (below).

**It overflows the tool-result limit.** ~150 keywords came to ~83,000 characters and were written
to a file. A 1,900-keyword agency project would be roughly ten times that. Never read the file
into context — filter it with `scripts/ranking_opportunities.py`.

## Traps

### `get_rankings_keyword_overview` does not return a keyword overview

The name and the description both promise "every monitored keyword with position, change, volume".
It returns four counters:

```json
{"keywords": {"ranking": <n>, "count_all_keywords": <n>, "delta": <n>},
 "winning_keywords": {"count": 25, "delta": 5},
 "losing_keywords": {"count": 17, "delta": -4}}
```

Useful as a one-line summary of the project. Useless as the data source for this skill. Use
`list_keywords`.

### `get_keyword_rankings` returns the stored SERP, not a ranking history

Its description says "ranking history for ONE monitored keyword — daily Google positions", which
reads like a time series. It is not. It returns **the search results page**: every domain in
order, roughly 90 rows, one per position.

```json
{"snapshot_position": 95, "next_snapshot_date": "<date>",
 "rankings": [{"rank": 1, "rank_change": 0, "domain": "...", "is_self": false,
               "is_competition": false, "url": "...", "featured_snippet": 0,
               "localpack": 0, "visibility": 594}]}
```

This is the only tool that answers "who actually outranks me here", and it needs no live credits
because the snapshot is already stored. `is_self` marks the user's own rows; `is_competition`
marks domains from the project's tracked competitor list.

It fits in a tool result without overflowing, but it is big (~20k characters), so it usually
arrives inline. One keyword at a time. Apply the SERP checks by reading the rows; run
`ranking_opportunities.py --serp` only when the host saved the result as a file, never on a hand-copied part.
**What the SERP checks look at.** The own URL more than once; a block of "new" rows at the top
(`rank_change: 1000` marks a row as new); three or more other sites listed twice. One other site
twice in the top 10 is common and says nothing about the own position. A list of 25-30 rows is
normal for some searches. A keyword that does not pass is left out of the assessment for this run,
and the report names it as not confirmed.

`date` works; the response does not echo the resolved date. URLs are stored HTML-escaped
(`&amp;`), so unescape them before fetching a page.

`ranking_check` returns the same stored snapshot, so it is not a second source for this check.

**`is_competition` is the proof that a tracked competitor list is the wrong basis for a
comparison.** On a glossary keyword, the top 10 held an encyclopedia, a browser vendor's
documentation, a dictionary and a same-named company — not one of them flagged
`is_competition`. The tracked rivals first appeared in the twenties and thirties. A comparison
built on the tracked list would have reported no competition at all.

### `get_keyword_overview` is the cheap cross-check

One keyword, ~500 characters: `rank`, `rank_change` (`"new"`, or `-99` for "out"), `date_added`
and `last_update` — the only ranking date anywhere. Use it once per pick for the ranking-data
gate and for the date line of the report.

### `get_keyword_count` is the cheapest project-sizing call there is

`get_keyword_count(project_id)` returns `{"count": n}` and nothing else. Verified against two
projects: the count matched the number of rows `list_keywords` returned, exactly.

Use it to size a project before pulling anything. It is the one number that decides whether a
ranking analysis can produce anything, and it is not in `list_projects`.

### `overview.rank` in `get_page_analysis` is always null

Even for a page that demonstrably ranks. Do not read it as a position — positions come from
`list_keywords`.

### `get_page_meta_tags` contains no title and no meta description

It returns the raw meta tag list — `og:title`, `og:description`, `robots`, `twitter:*`,
`article:*`, `viewport`. The page's actual `<title>` and `<meta name="description">` are **not**
in it.

Use `get_page_analysis(project_id, url)` instead. One call, and it returns:

- `analyses.meta_information` — `title`, `description`, `h1_headline`, `canonical_link`,
  `language_detected_in_text`
- `overview` — `statuscode`, `is_noindex`, `is_nofollow`, `canonical_target`, `word_count`,
  `response_time`, `score`
- `links` — `incoming`, `outgoing.internal`, `click_depth`, each with the site's max for context
- `todos` — the page's audit findings with an `importance` of `important` or `tip`

It is a large payload. Cap the skill at three row pages per run.

### `get_keyword_ranked_pages` is a history, not a current SERP

It lists every own URL that has ranked for the keyword, each with its own `rank`,
`snippet_title`, `snippet_description`, `featured_snippet` flag and `last_ranking_date`.

Those dates differ per row. One keyword returned four own URLs at positions 7, 8, 8 and 9 with
dates spread across three months, while `list_keywords` reported the keyword at a different
position entirely. The rows are not comparable with each other and not comparable with the current
position.

Each URL comes back with its **best-ever** position up to `date`, not its current one, so it
disagrees with `list_keywords` whenever a keyword now ranks worse than its best. Never use it to
check a position. URLs absent from the current snapshot are listed too: three tools once gave 3,
4 and 23 ranking URLs for the same keyword.

- Take the **current position from `list_keywords`**, always.
- Use this tool for **which own URLs have ranked** (several = a cannibalisation signal worth
  reporting) and for the **actual SERP snippet text**, which is not available anywhere else.

### `number_ranking_urls` is not the count of your own ranking URLs

It was `0` on the large majority of rows, including rows with a populated `best_ranking_url`. Do not read it
as "how many of my pages rank for this". Use `get_keyword_ranked_pages` when the answer matters.

### One keyword, several markets, several rows

A project can monitor the same keyword on several search engines. Each is its own row with its own
`id`, `rank` and `search_volume`. In the test project, roughly one keyword name in six appeared more than
once — `meta description` was position 5 with 2,400 volume on Google.com and position 11 with 720
volume on Google.de.

`ranking_opportunities.py` picks across all markets but takes each keyword name once, so the same keyword
never shows up twice as two separate opportunities. The same keyword on another market also does
not count as "the URL ranks better for another keyword".

### `competition` is Google Ads competition

Not ranking difficulty. A keyword at competition 0.03 can have a top 10 that the user's page has
no realistic route into. This skill does not use the field; do not introduce it.

### A ranking URL can sit outside the project's crawl

`get_page_analysis` and `get_page_meta_tags` only know pages the project has crawled. A URL
outside the crawl's scope comes back empty or as `CrawlUndiscovered` — this happens routinely when
a blog-scoped project ranks with a wiki URL, or vice versa.

Report the keyword and its position, say the page is outside this project's crawl, and stop. Do
not fall back to general advice about a page you cannot see.

**Except when the outside URL is the same page in another language.** On a DE-scoped wiki project
(335 keywords, 30.09.2026), 12 of 74 keywords in positions 4-20 ranked on Google.de with the `/en/`
page, while a `/de/` page on the same topic sat inside the crawl. Treating them as "outside the
crawl" hid the one pattern in the band. The EN pages declared their DE version correctly in hreflang
(`<link rel="alternate" hreflang="de">`), and slugs differ between languages (ES:
`Dominios_caducados` for `Expired_Domains`), so the market's version is found through the hreflang
links of the ranking page, never by swapping the language folder. `ranking_opportunities.py --screen` does that
live and free.

## What Seobility does not have

State these when they come up, rather than working around them silently:

- **No Google Search Console connection.** There are no impressions, no clicks and no CTR in this
  data. Anything about clicks has to come from the user's own GSC export.
- **Response time is not page speed.** `response_time` in `get_page_analysis` is the server's HTML
  response, not Core Web Vitals.
- **Seobility does not fix anything.** Every output of this skill is a recommendation for a human.

## Field types that break naive parsing

Found by running this skill against three projects of different sizes.

### `rank` is `false`, not `null`, when a keyword does not rank

```json
{"name": "seo software", "rank": false, "rank_type": null, "best_ranking_url": null}
```

In the same payload, other non-ranking rows carry `rank_type: null`. Test for a real integer, not
for truthiness alone — in Python, `isinstance(rank, int) and not isinstance(rank, bool)`, because
`False` is an `int` there.

### `rank_change` is `"new"` for a first-time ranking — and a number elsewhere

```json
{"name": "seo software", "rank": 6, "rank_change": "new"}
```

Every other row has an integer. Any formatting that assumes a number crashes on the first
first-time ranking in the set — which is exactly the row a quick-win report wants to show.

Other tools encode the same states as numbers: `get_keyword_rankings` rows use `1000` for "new",
`get_keyword_overview` uses `-99` for "out". Read them as states, never as moves.

"New" means "no position in the previous check", not "recently added". On one project 55 of 169
ranking keywords carried it, including one tracked since 2018 (`date_added` in
`get_keyword_overview`): a re-entry from outside the tracked range. It is not a data-quality
signal on its own; a contiguous block of `1000` at the top of a SERP is.

### `list_projects` returns several projects with the same name

A single account held three projects with the same name, covering different scopes of the
same site (522, 2,708 and 10,013 pages crawled). Never ask the user to pick by name. Offer `url`,
`pages_crawled` and `finished_date`, which do differ.

The full shape is ~40k characters for 46 projects and `limit` is ignored. `compact: true` returns
only `project_id`, `name` and `url`; take `pages_crawled` and the finish date of the candidates
from `list_crawls(project_id, limit: 1)`.

### `get_pages_using_anchor_text` matches lowercase, exactly

Anchors are stored lowercase. "Download the Template (PDF)" returned nothing; the lowercase form
returned 125 rows. Substrings return nothing. Rows are link occurrences, not
pages. Lowercase the anchor before the call.

### `seo_check` defaults to `detail_level: "analysis"` on MCP

`analysis` (~20 kB) has score, meta, title, description, word count and the headings in page
order (`page.elements.html_body.headings`), but no link list, media sources or text blocks.
`full` (~56 kB) adds them. In practice `analysis` returned 22-50 kB per page (it carries the
site's robots.txt, all HTTP headers and schema error lists) and is a **live
call at the expensive end of the credit scale** (the response's `credits` field shows the cost). For the
intent step (title, description, H1 of the top 3) it is therefore only the second route, for
pages that block `ranking_opportunities.py --promise`. It reads the `<head>`, which a host web fetch usually
misses (title for 5 of 9 pages, description for 1 of 9 in one test), and it read a page that
answered the web fetch with 403. Its H1 is the first `<h1>` in the markup, which can be a
navigation label ("Tutorials" on a page with six H1s).

### A page inside the crawl can still be unreadable

`get_page_analysis` returns `display_type: "robots_excluded"` (the `error` field names a robots block; its exact string varied between two runs) for a page
the crawler found but was not allowed to read: title, description and H1 null, `word_count` 0,
`statuscode` null (not a failed status), `get_page_headlines` a list of `missing_level` entries.
The link block is still filled. Treat it like `CrawlUndiscovered`: nothing on the page can be
judged.

### `get_page_alternate_links` lists the declared language versions

`get_page_analysis` gives only a verdict and a count for hreflang. This tool returns the list:
`[{"url": ..., "href_lang": "en"}, {"url": ..., "href_lang": "de"}, ..., {"href_lang": "x-default"}]`
(verified 30.09.2026). Only for a page inside the crawl.

### `get_page_headlines` is not in page order

Headings come back sorted alphabetically within each level (an FAQ heading listed second on a
page where the FAQ is last). `sort_by` accepts no documented value. Use it for which headings
exist; read the live page for their order.

### Ranking data and crawl data age separately

In the test account, one project had rankings from the current week and a crawl that finished nine
months earlier. Nothing in the ranking payload signals this. Read `finished_date` from
`list_projects` before deriving any on-page action, and say the date when the crawl is old.

### Payload size scales with the keyword set

| Keywords | Characters |
|---|---|
| 4 | inline, no file |
| 150 | ~83,000 |
| 300 | ~170,000 |

A verified agency account runs up to ~1,900 keywords, which extrapolates to roughly a million
characters. There is no keyword count at which reading this payload into context is acceptable.

## The control check, verified

The control rule in `SKILL.md` was tested against a real project rather than reasoned about.

A page sitting at position 4 carried 7 incoming internal links, against a project maximum in the
hundreds. Read on its own, that is a starved page and the obvious action is "add internal links".

The control page — same page type, same project, already holding **position 3** — carried **4**.
Fewer than the page that was supposedly starved. Both pages also shared a one-word H1 that the
audit flags as too short, and near-identical word counts.

So the trait was not a cause. It was what a page on that site looks like, winners included. The
correct output for that row was "no on-page cause visible", and the real explanation was visible
only in the SERP: the keyword had several word senses, and the positions above were held by an
encyclopedia, a dictionary and a company of the same name.

Two calls decided it. Make them.
