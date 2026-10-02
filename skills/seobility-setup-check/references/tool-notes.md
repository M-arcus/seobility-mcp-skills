# Seobility MCP — verified tool behaviour for the setup check

Everything here was checked against live projects on 22.09.2026, not read off the tool
descriptions. **Where a tool description and this file disagree, this file is right** — and for
this skill they disagree more often than anywhere else in the library. Four of the calls it relies on do
something materially different from what their description says.

Verified against seven projects in one account, referred to below as projects A to E: a
335-keyword wiki project crawled weekly (A), a 10,013-page project whose crawl hit its own page
limit (B), a 4-keyword project tracking two markets (C), a project with its uptime monitor
switched off (D), and an abandoned test project with one crawl from 2023 (E). B and C share an
identical name *and* an identical URL. Ids, account figures and competitor names in the examples
are replaced with placeholders; the shapes and the behaviour are real.

---

## The four descriptions that are wrong

| Tool | What the description says | What it returns |
|---|---|---|
| `get_limitations` | "The user's plan limits and quotas" | the matrix of **every** plan tier, keyed by an opaque plan id |
| `get_keyword_settings` | "search engine, location targeting, devices" | **email reporting** settings, nothing else |
| `get_rankings_keyword_limit` | "used vs. allowed keywords" | account pool and per-project room — **never** the project's usage |
| `get_health_status` | availability summary | the last reading of a monitor that was switched off months ago (newer responses add a `monitoring: {active: false}` block) |

Each is expanded below.

---

## Account level

### `user_info` is the only source of the account's real limits

It carries the effective numbers directly, already including whatever add-ons were bought:

```json
{"level": 1, "projects_count": 7, "projects_max": 100,
 "keywords_count": 900, "keywords_max": 10000,
 "max_pages": 25000, "max_competitors": 20,
 "can_use_mcp": true, "email_verified": true, "is_sub_account": false}
```

(Values illustrative.)

**Use these for every "are you near your limit" statement.** They are the truth for this account.

### `get_limitations` is a price list, not this account's limits

It returns the full tier matrix. Every value is an object keyed by plan id:

```json
"keywords_included": {"0": 10, "3": 100, "1": 300, "2": 2000, "11": 100, "10": 100, "4": 700}
```

The ids are not ordered and are not documented. In the test account, the row for its own plan id
(`user_info.level`) said `keywords_included: 300` — while `user_info.keywords_max` was **more
than 30 times** that, because add-ons are not in the matrix. Reading `get_limitations` as "your
plan allows 300 keywords" would have been wrong by that factor.

So: `get_limitations` answers *"what would a different plan give me?"*. It never answers *"what do
I have?"*. For the setup check it is worth exactly one thing — the capability flags that gate a
feature the user is asking about (`scheduled_crawls`, `javascript_crawling`, `localisation_city`,
`website_health_email_alert`, `csv_upload`) — and only after resolving the plan id from
`user_info.level`.

The one genuinely useful pair hiding in it:

```json
"website_health_smallest_interval":          {"1": 15}
"website_health_smallest_interval_verified": {"1": 1}
```

On the test account's plan, domain verification takes the uptime check interval from 15 minutes
to 1. That is the concrete answer to "why should I verify?", and it is not stated anywhere else.
The pair is per plan like everything in this matrix: read both keys for the user's own plan id and
quote those, not 15 and 1.

### `get_credits` — the budget every skill in the library spends

```json
{"credits": 30000, "monthly_limit": 40000, "reset_at": "2026-10-01 10:00:00",
 "usage": [{"month": "2026-09", "credits": 1400, "calls": 200}]}
```

(Values illustrative.) Stored-data calls (everything this skill makes) are
the cheap end; the live tools (`seo_check`, `ranking_check`, `keyword_check`) are the expensive
end and are not used here.

`usage` is a per-month history, so it also answers "am I about to run out before the reset".
That is the only time a setup check needs it: call it for an account-wide sweep or a budget
question, and skip it on a single-project run.

---

## Resolving the project — the step that goes wrong first

### `list_projects` carries enough to choose without a second call

```json
{"project_id": 100001, "name": "Example.com", "url": "https://www.example.com/de/wiki/",
 "crawl_status": "finished", "pages_crawled": 522, "is_verified": true,
 "finished_date": "2026-09-18T08:57:32+0200", "total_crawls": 438,
 "is_scheduled_crawl": true, "health_status": "down",
 "page_score": {"current": 90, "delta": 1}, "backlinks": {"current": 6000, "delta": 170},
 "problems": {"current": 900, "delta": -1}}
```

(Project A; id and domain replaced, score/backlink/problem figures rounded.)

`is_verified`, `is_scheduled_crawl`, `health_status` and `total_crawls` are four of this skill's
findings, for every project at once, in one call. Read it before anything else. Full rows also
carry `created_date`, which the keyword maturity rule uses.

It returns **all** projects (46 in the test account, 35,000 to 40,000 characters), `limit` is
ignored, and `compact: true` shrinks it to `project_id`, `name` and `url`, dropping every field
above. Search the result for the name or URL.

### Names do not identify a project, and neither do URLs

In the test account, **three projects carry the same name**, and two of those three share the
identical `url`:

| project | url | pages | last crawl | scheduled | verified |
|---|---|---|---|---|---|
| A | …/de/wiki/ | 522 | 18.09.2026 | yes | yes |
| B | …/de/ | 10,013 | 24.04.2026 | no | no |
| C | …/de/ | 2,703 | 20.09.2026 | yes | no |

B and C are distinguishable only by `pages_crawled` and `finished_date`. Guessing between them
is how a "wrong project" bug report happens: every subsequent call succeeds and describes a
different site than the user is looking at.

**Always confirm the project with the user by id + URL + last crawl date** when more than one
candidate matches, and never resolve by name.

### `is_verified` is per project, the verification token is per domain

`get_verification_status` returned the **identical** `dns_txt_record`, `html_meta_tag` and
`file_upload` values for project A (`is_verified: true`) and project B
(`is_verified: false`) — same domain, same token, different verification state. The options block
is returned whether or not the project is verified.

**The token is a credential.** Do not print it in a report. Name the method and offer to fetch
the value when the user is actually about to verify.

---

## Crawl setup

### `get_crawling_limits` — the project's own ceiling, not the account's

```json
{"max_pages": {"current": 522, "limit": 10000},
 "max_external_links": {"current": 78, "limit": 1000},
 "max_file_sources": {"current": 88, "limit": 1000},
 "crawling_mode": 1}
```

The project limit (10,000) is **not** `user_info.max_pages` (25,000). Per-project crawl budget is
configured per project. Compare `current` against `limit` here, never against the account figure.

**For `max_pages`, `current` can exceed `limit`, and that confirms truncation.** The direct answer
is `get_site_audit_overview` -> `special_checks.was_crawling_budget_reached`; read that first.
Project B returned:

```json
{"max_pages":          {"current": 10013, "limit": 10000},
 "max_external_links": {"current": 23590, "limit": 10000},
 "max_file_sources":   {"current": 493,   "limit": 1000},
 "crawling_mode": 2}
```

`max_pages` is over its limit: that is the truncation. **`max_external_links` is not a budget in
the same sense.** Its `current` counts discovered external targets, is uncapped, and may exceed
its own limit without anything being wrong; the tool description says so. `limit: 0` means
external checks are switched off (one project: `{"current": 2535, "limit": 0}`). Do not report
it as a blown budget. `max_file_sources` can overshoot too (5,036 against 5,000) without any
page being cut.

`crawling_mode: 2` is JavaScript rendering (mode 1 is the standard crawler). It is far slower —
the crawl above took 7.5 hours — which is worth knowing before recommending a bigger page limit
on the same project.

### The crawl that silently stops short

Project B, newest crawl:

```json
{"pages_crawled": 10013, "pages_found": 16480, "completion_reason": "regular",
 "is_stopped": false, "score_percent": {"overall": 29}}
```

`completion_reason: "regular"` and `is_stopped: false` — the payload claims a normal crawl. It
crawled 10,013 pages against a limit of 10,000, with more pages found than fetched. **Part of the
site was never looked at**, and nothing in the crawl row says so.

The tell is `was_crawling_budget_reached: true` in `get_site_audit_overview`. `pages_crawled`
sitting at the limit while `pages_found` runs well past it is only a hint: `list_crawls` says
`pages_found` is uncapped and shown nowhere in the account, so do not quote it.
`scripts/setup_check.py crawls --page-limit --budget-reached` reports both.

This matters beyond tidiness: every audit finding, every score and every "issues found" count on
that project describes part of the site, and audit triage and findings-to-tickets will inherit it
as fact.

### `list_crawls` and the baseline

`list_crawls` takes `limit` (default 100). Rows carry `completion_reason`, `is_stopped`,
`data_removed`, `pages_crawled`, `pages_found` and `pages_indexable`. A stopped crawl still reads
`status: "done"` and 100%; only `completion_reason: "stopped"` / `is_stopped: true` give it away.
The baseline for a comparison is the last regular completed crawl: skip stopped crawls, crawls
with 0 pages, and (for audit deltas) crawls with `data_removed: true`, whose rows are gone.

### A changed crawl scope makes the score delta meaningless

The same project, three crawls:

| crawl | pages crawled | score |
|---|---|---|
| 05.03.2026 | 6,897 | 79 |
| 16.03.2026 | 4,892 | 58 |
| 24.04.2026 | 10,013 | 29 |

The score did not fall 50 points because the site got worse. It fell because the crawler reached
twice as many pages, most of them worse than the ones it reached before. A score compared across
two different sets of pages is not a measurement of anything. The script compares
`pages_crawled`, `pages_indexable` and `pages_found` against the last regular crawl and warns at
>25% on any of them (a crawl at its limit keeps `pages_crawled` flat: the same page count
twice, with indexable pages down by two thirds). The page set also changes when the site grows, so the cause is for `get_crawler_settings` and the site's history to say.

### `get_crawler_settings` explains a crawl that looks too small

```json
{"crawl_url": "https://www.example.com/de/wiki/", "include_subdomains": false,
 "include_sitemaps": true, "sitemap_url": null, "crawling_mode": 1,
 "max_crawls": 10000, "wait_time": 200, "accept_language": "de,en",
 "robots_txt": "Disallow: /\r\nAllow: /de/wiki"}
```

That `robots_txt` override is why project A crawls 522 pages of a site with thousands: it is
deliberately scoped to one directory. **A small crawl is not automatically a problem** — check
this field before calling one a gap, or the skill reports a correctly configured project as
broken.

`crawling_mode: 1` is the standard crawler. JavaScript rendering is a different mode and a
plan-gated feature (`javascript_crawling` in `get_limitations`).

### `get_project_settings` — the scheduling and notification half

```json
{"project_title": "Example.com", "email_recipients": ["…@example.com"],
 "scheduled_crawls": true, "scheduled_crawls_waiting_period": 7,
 "email_notifications": false}
```

`scheduled_crawls_waiting_period: 7` is the crawl cadence in days while `scheduled_crawls` is
true — the number that tells you whether "the previous crawl" in a weekly skill is a week old or
three days old. The value stays populated when `scheduled_crawls` is false, so read it only
together with that flag. `total_crawls` is not a freshness signal; use the newest crawl's age.

Note the combination in the verified project: recipients are configured, `scheduled_crawls` is on,
and `email_notifications` is **false**. Crawls run every week and nobody is told. That is a real
finding and it is invisible from anywhere else.

---

## Keyword coverage

### `get_keyword_count` counts rows, not keywords

Project C returns `{"count": 4}`. Its four rows are:

| id | name | search engine |
|---|---|---|
| 1001 | seo tool | Google.com |
| 1002 | seo tool | Google.co.uk |
| 1003 | seo software | Google.com |
| 1004 | seo software | Google.co.uk |

**Two keywords, two markets, four rows.** Each market costs a row against the quota and gets its
own `keyword_id`.

So "you monitor 4 keywords" is wrong twice over: it overstates the topical coverage and hides the
fact that the project is multi-market. On the 335-keyword project all 335 rows were distinct names
on a single engine, so the two numbers agree there — which is exactly why the difference has to be
computed rather than assumed. The script reports both.

Because `list_keywords` has to be read for the coverage check anyway, and its row count is exactly
this number, the setup check does not call `get_keyword_count` at all.

### `get_rankings_keyword_limit` does not report the project's usage

```
project with 335 keywords:  {"available_for_venture": 1665, "unused": 9100, "total": 10000}
project with   0 keywords:  {"available_for_venture": 2000, "unused": 9100, "total": 10000}
```

(Account figures illustrative; the per-project figures are real.)

- `total` is the **account** allowance, matching `user_info.keywords_max`.
- `unused` is **account-wide** free capacity: `total` minus the keywords used across all
  projects. It is identical for both projects.
- `available_for_venture` is room left **in this project** — and 335 + 1,665 = 2,000 = the empty
  project's figure. So there is a **per-project ceiling**, independent of the account allowance.

Nothing in this payload says how many keywords the project uses. That is the row count of
`list_keywords`, which the coverage check reads anyway.

The per-project ceiling is the real answer for an agency asking why it cannot put all its keywords
in one project. It was 2,000 on every project of the test account, which is **one plan**. Whether
other plans have a different ceiling is not verified, so compute it as rows used +
`available_for_venture` rather than quoting 2,000. `setup_check.py keywords --room` does this.

### `list_keywords` overflows, and its `rank` field is a trap

168,000 characters for 335 keywords. It gets written to a file on any real project; run
`scripts/setup_check.py keywords`.

Row shape:

```json
{"id": 1001, "name": "seo tool", "search_engine_name": "Google.com", "search_engine_id": 16,
 "location": [], "ranking_fetched": true, "rank": 7, "rank_type": "organic", "rank_change": 1,
 "visibility": 2727, "visibility_change": 611, "cpc": "5.70", "competition": 0.02,
 "search_volume": 110000, "best_ranking_url": "…", "tags": [], "ai_overview": true,
 "intents": {"informational": 43, "commercial": 55, …}}
```

**`rank` is an integer when the keyword ranks and the boolean `false` when it does not.** On the
335-keyword project: 246 ints, 89 `false`. And because `bool` subclasses `int` in Python,
`isinstance(rank, int)` is `True` for `False` — the natural check silently reports 0 non-ranking
keywords instead of 89. Test for `bool` first. (This was caught by the script disagreeing with a
hand count, not by reading the payload.)

**`false` means "not in the top 100", not "outside the top 20".** Ranking Monitoring tracks 100
positions deep. Verified with `get_rankings_by_maximum_rank` on project A on 23.09.2026: 170
keywords in the top 20, 219 in the top 100. So an integer `rank` can be anything from 1 to 100,
and positions 21 to 100 are a separate bucket from the ones ranking nowhere — they rank, but
produce almost no visibility. The script counts both.

Other fields worth knowing:

- `location: []` means national. A populated array is city-level targeting.
- `search_engine_name` / `search_engine_id` is where the per-keyword market lives — **not** in
  `get_keyword_settings`.
- `search_volume`, `cpc` and `competition` are here but **absent** from
  `get_rankings_winners_and_losers`. This is the call to get volumes from.
- `competition` is Google Ads competition (0.02–0.22 in the sample), **not** ranking difficulty.
- `visibility_change` can arrive as `-0`.

Verified coverage picture of the 335-keyword project: 89 keywords (26.6%) rank nowhere in the
top 100, 4 have zero search volume, 31 (9.3%) carry a tag, and the 246 ranking keywords sit
on 242 distinct URLs — 1.02 keywords per page.

### `get_keyword_settings` is about emails

```json
{"reporting_desktop_enabled": false, "reporting_mobile_enabled": false,
 "reporting_localpacks_enabled": true, "reporting_target_mails": ["…@example.com"]}
```

Despite the description, there is no search engine, no device and no location in it. It configures
which ranking reports get mailed. Useful for one finding — reports configured but both device
reports switched off — and useless for the setup question it appears to answer.

### `get_rankings_keyword_suggestions` is the 116k-character context bomb

**Up to 500 rows (0 to 500 observed) with no paging and no filter parameter** — 116,000 characters
on a project with *four* monitored keywords. This is the call behind reported 110–117k-character responses
eating a context window, and it reproduces on the smallest project in the account.

Never call it without sending the result through `scripts/setup_check.py suggestions`.

```json
{"keyword": "seo check", "reason": "alreadyranking", "search_engine": "Google.de",
 "rating": 100, "competition_count": 0, "search_volume": 5400, "cpc": 3.84,
 "intents": {"informational": 59, "navigational": 40, …}}
```

`reason` takes two values, and the split is lopsided — 498 `alreadyranking` to 2 `competition` in
the verified run. `alreadyranking` is the untracked-demand signal: the domain already appears for
this term and it is not in monitoring.

**`rating` is a relevance score that needs a human.** Sorted by rating, the verified project's top
five for a site selling SEO software were `seo check` (100), `backlinks checken` (91) — and then
`amazon seller central` (79), `amazon sell center` (75) and `seller amazon central` (75). Sorted
by volume it is worse: four of the top five are `google search console` and `keyword research`
variants at 368,000 searches with ratings of 2 to 7.

So `alreadyranking` means *the domain surfaced somewhere in that SERP*, at any depth. It does not
mean the keyword is relevant, winnable, or worth a quota row. Shortlist it, show it, let the user
choose.

**The suggestion engine need not match the monitored engines.** All 500 suggestions came back for
`Google.de` on a project that monitors only Google.com and Google.co.uk. Before treating that as a
keyword gap, note it is a market question.

---

## Competitors

### `list_competitors` returns an object with a `self` key, not a list

```json
{"keyword_count": 335, "max_competition": 20,
 "competitors": {
   "self":     {"id": 2001, "name": "example.com", "visibility": 21000,
                "ranking_keywords": 246, "referring_domains": 6000},
   "2002":     {"id": 2002, "name": "competitor-a.de", "visibility": 5000,
                "ranking_keywords": 82, "add_date": "2018-12-06…"}},
 "pagination": {"total": 15}}
```

`competitors` is keyed by competitor id **plus the literal key `self`**, which is the project's own
domain. `len(competitors)` therefore returns 16 for 15 competitors — and returns **1 for a project
with none**, verified on the empty project, where `competitors` contained `self` alone and
`pagination.total` was `0`. Exclude `self` and trust `pagination.total`.

`self` is genuinely useful: own visibility, own ranking keywords and own referring domains, with no
extra call.

### Dead competitor slots are a real finding

Of the 15 tracked competitors on the verified project, **three** (all software-review platforms)
carry `visibility: 0, ranking_keywords: 0` — added in February 2024 and never seen in a tracked
SERP since. `max_competition` is 20, so three of twenty
slots are spent on domains that produce nothing.

`visibility_change: 9999` is a sentinel, not a percentage — one competitor showed it against a
visibility of 0.14. Do not print it.

### `get_competitor_suggestions` must never be passed through raw

68 rows of "domains that rank for your keywords", ordered by count:

```
youtube.com 614 · de.wikipedia.org 445 · en.wikipedia.org 314 · <an SEO agency> 240 ·
ionos.de 207 · … instagram.com 139 · facebook.com 127 · amazon.de 66 · duden.de 60
```

For an informational site this is dominated by platforms, encyclopedias and dictionaries. They are
correct answers to "who else ranks here" and wrong answers to "who is my competitor". The real
candidates in that list — a handful of SEO agencies and SEO software vendors, scattered between
the platforms — have to be picked out by someone who knows the market.

Filter to domains that plausibly sell what the user sells, cap the proposal at a handful, and say
what was filtered out.

---

## Uptime

### `get_health_status` looks the same whether or not the monitor is running

Project D has `health_status: "inactive"` in `list_projects` — monitoring is off. The health
call still answers:

```json
{"status": "ok",
 "current": {"time": "2026-02-20 08:46:03", "status": "down", "info": "client"},
 "alert":   {"time": "2026-02-04 12:16:02", "status": "down", "info": "redirect"},
 "uptime_percentage": null, "timescale": "hours", "interval": "30 minutes"}
```

Read alone, that says the site has been down since February. It says nothing of the kind: the
monitor was switched off in February and this is the last reading it ever took.

Tells: `health_status: "inactive"` in `list_projects`, a `monitoring: {active: false}` block in
newer responses, and `uptime_percentage: null` in the older shape. Check `list_projects`
**before** reading any health payload, and note that `timescale` came back `"hours"` regardless
of what was requested.

`interval` in this payload is the chart bucket (`"30 minutes"`), not the check interval; that is
in `get_health_job` / `get_health_config`. A monitor pointed at a URL that permanently redirects
returns `uptime_percentage: 0` (not null) with `info: "redirect"`. No tool returns the monitored
URL: read the project URL's status with a web fetch, or run `redirect_check` (needs `target_state`;
checks www/https consistency, unverified for path redirects). One case: a start URL that
answers 301 to another language folder, with the monitor "down" ever since.

Carried over from the weekly check-in and still true: top-level `status: "ok"` is the API call, not
the site; the site is `current.status`; and `info` decides what "down" means — `"redirect"` is a
monitor pointed at a URL that redirects, not an outage. `"client"` appeared here as a third value.

**"Not monitored" and "no downtime" are different sentences.** So are "down" and "misconfigured".

---

## Empty and broken projects

The shapes a new or abandoned project returns, verified on project E (0 keywords, 0
backlinks, one crawl from 2023):

| Call | Returns |
|---|---|
| `get_keyword_count` | `{"count": 0}` |
| `get_rankings_overview` | `[]` — an **empty array** where a populated project returns an object |
| `list_competitors` | `competitors` containing only `self`, `pagination.total: 0` |
| `get_rankings_keyword_limit` | `available_for_venture` equal to the full per-project ceiling (2000 on the test plan) |

`get_rankings_overview` switching from object to array on an empty project is the same trap
documented for `get_backlinks_overview`. Test for the shape, never for truthiness.

---

## What Seobility does not have

State these plainly when they come up rather than working around them silently:

- **No Google Search Console connection.** No impressions, clicks or CTR anywhere in this data.
- **Response time is not page speed.** The health monitor times the server's response.
- **No automatic fixes.** Every output of this skill is a recommendation for a human.
- **This skill changes nothing.** There is a write tool for most of what it finds
  (`update_crawler_settings`, `add_keywords`, `add_competitor`, `start_crawl`). It calls none of
  them.

---

## Cost

A full single-project run is **10 to 11 calls**: `user_info`, `list_projects`, `list_crawls`,
`get_site_audit_overview`, `get_crawling_limits`, `get_crawler_settings`, `get_project_settings`,
`get_rankings_keyword_limit`, `list_keywords`, `list_competitors`, and `get_health_status` when
the monitor is active. `get_credits` is added only for an account-wide sweep or a budget question.
`get_keyword_count` is not called: the `list_keywords` row count is the same number.

`get_rankings_keyword_suggestions` and `get_competitor_suggestions` are the two optional extras,
added only when the coverage or competitor section found a gap worth filling.

`get_limitations` is one call and answers a question the user rarely asked. Skip it unless a
plan-gated feature is actually in question.

None of these are live tools, so none of them carry the per-check cost of `seo_check`,
`ranking_check` or `keyword_check`.
