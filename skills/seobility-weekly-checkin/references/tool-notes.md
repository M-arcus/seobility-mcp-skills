# Seobility MCP — verified tool behaviour for the weekly check-in

Everything here was checked against live projects on 17.09.2026, not read off the tool
descriptions. Where a tool description and this file disagree, this file is right.

Parameters and limits below were re-checked against the live tool schemas on 29.09.2026.

Verified against three projects: a 335-keyword project with 522 crawled pages and weekly crawls,
a 4-keyword project with 2,708 pages crawled every three days, and an abandoned project with no
keywords, no backlinks and a single crawl from 2023.

## The cheapest call in the skill

**`list_projects`** already carries the week in it, for every project at once:

```json
{"project_id": 100003, "name": "…", "url": "…", "crawl_status": "finished",
 "pages_crawled": 2708, "finished_date": "2026-09-17T12:10:50+02:00",
 "is_scheduled_crawl": true, "health_status": "up",
 "page_score": {"current": 80, "delta": 0},
 "backlinks": {"current": 6000, "delta": 10},
 "problems": {"current": 11700, "delta": -43}}
```

(Id replaced, totals rounded.)

It returns every project of the account (46 in the test account, ~35-40k characters): `limit`
is ignored, and `compact: true` drops the deltas, `finished_date` and `pages_crawled`, so it
is no use here.

Three deltas and a health status before a single project-scoped call. Use it to decide which
project is worth a full run, and to say in one line which of several projects moved at all.

`is_scheduled_crawl` is the flag that decides whether the audit half of the check-in exists.
`false` means the "previous crawl" can be from any time at all — one project in the test account
had its newest crawl finished nine months earlier.

## Rankings

### `get_rankings_overview` — the delta is a percentage, not points

```json
{"desktop": {"rw": 4000, "visibility": 20000, "delta": "40.7"},
 "mobile":  {"rw": 4000, "visibility": 18600, "delta": "3.1"}}
```

`delta` arrives as a **string**, formatted with a thousands separator (`"10,366.7"`,
`"14,287.0"`), and it is a **percentage change**, not a change in visibility
points. Verified by arithmetic on both projects: 2,154 visibility at `delta: "51.8"` means the
previous value was 1,419, and the winners/losers rows for that week summed to +735 — the
matching absolute change. Writing "+51.8 visibility points" would be wrong by a factor of
fifteen. On a project whose keywords were added recently the base is close to zero
(`"14,287.0"` and `"832,757.1"` were real values): `weekly_deltas.py overview` parses the string
and suppresses the percentage when the base is under 1 point.

`rw` was identical (4125) for two projects with very different keyword sets and very different
visibility. It is not explained by the data and does not belong in a report.

### `get_rankings_winners_and_losers` — the whole ranking half, and it overflows

Returns `winners`, `losers` and `figures`. Fields per row:

| Field | What it is |
|---|---|
| `keyword_id`, `name` | the keyword |
| `search_engine_name` | `Google.de`, `Google.com`, … |
| `rank` | current position, or the string `"-/-"` when it left the tracked range |
| `rank_change` | int, or `"new"` (first ranking) or `"out"` (dropped out) |
| `visibility`, `visibility_delta` | search-volume-weighted, weighted towards the top positions (rows at ranks 77-90 still carry 0.4-1.9 points) — the impact measure |
| `best_ranking_url` | the own URL that ranks, `null` on `"out"` rows |
| `ai_overview`, `intents`, `competition`, `tags` | as in `list_keywords` |

**There is no `search_volume` field here**, unlike `list_keywords`. `visibility_delta` is the
only weighting available in this payload.

Size: 172 movers ≈ 74,000 characters. It overflows the tool result on any project with a real
tracked set. Filter it with `scripts/weekly_deltas.py`, never read it into context.

### `timescale` changes the answer, including its sign

The same keywords, same project, same minute:

| | winners | losers |
|---|---|---|
| `timescale: "days"` | 58 | 82 |
| `timescale: "weeks"` | 97 | 75 |

And per keyword: `google shopping` was `+1` over weeks and `-1` over days; `gzip` was `+3` over
weeks and `-1` over days. Both are correct for their window. Pick one window for the whole
report and name it.

Omitting `timescale` returns yet another window, with different positions again. Always pass it.

`date` shifts the end of the window (verified: `date: "2026-09-03"` returned a different set
from the same call without it), which is how you re-run last week's report.

### `device` splits the tracked set in two, with nothing in common

Desktop and mobile keywords are **separate rows with separate `keyword_id`s**. Verified: the
desktop and mobile winner/loser sets for the same project and window shared **zero** keyword
ids, and their project-level visibility deltas ran in different directions the same week
(+40.7% desktop, +3.1% mobile).

There is no merged view. Report both headline numbers, detail one device, and say which.

### `figures` does not reproduce from the rows

```json
{"winning_keywords": 97, "delta_rank_winning": 6285,
 "losing_keywords": 75, "delta_rank_losing": -963}
```

The counts are right. `delta_rank_winning` is not the sum of `rank_change` (285) and not the sum
of `visibility_delta` (7218), with or without the `"new"` rows: `new` rows count as 1000; `out` rows add a varying negative amount (not a constant).
Never report `figures` (40421 = 40 x 1000 + 421 on one project). On a 4-keyword project it did
equal the sum of `rank_change` — so whatever it is, it is not stable enough to report. Compute
your own totals.

### `get_keyword_lost_rankings` returns other people's lost rankings

The name says "lost rankings for ONE keyword — dates/positions where the site dropped out". It
returns neither dates nor your own site. It returns **the other domains that dropped out of that
keyword's SERP**:

```json
[{"old_rank": 5, "domain": "getbootstrap.com", "url": "…/components/pagination/",
  "localpack": 0, "featured_snippet": 0}, …]
```

Useful as SERP context for one keyword you are already investigating — who else left the page
this week. It is not the source for "which keywords did I lose". That is the `losers` array of
`get_rankings_winners_and_losers`.

## Crawl issues

### `get_site_audit_problems` is the whole audit half in one call

Returns `overview` (net count and delta per category) plus one row per issue report, each with
`count`, `delta`, `importance`, `priority`, `category`, `total_impact` and a stable `analysis`
slug. No second call needed for a check-in.

The net delta hides the composition: a verified week showed `problems_found.delta: -43` made of
content `-29`, technique `-23`, structure `+9`.

Rows are sorted by importance and impact — a backlog order, in which everything that did not
change sits at the top. Re-sort by `delta`, or pass `sort_by: "delta_desc"`; `categories`
(`technique_and_meta`, `structure`, `content`) narrows it. About 40 of ~59 rows have `count: 0`.

`count` is a number of findings, not of pages: duplicate text reported 384 on a 124-page site
(page-block pairs). The unit depends on the report.

To name the URLs behind a delta, `get_report` takes `analysis` (the row's slug), `limit` and
`offset` (a multiple of `limit`); it lists every affected URL, not only the new ones.

### `type: "minicheck"` rows are measurements, not issue counts

```json
{"type": "minicheck", "translation_variable": "minicheck_avglinks", "count": 56, "delta": 56}
{"type": "minicheck", "translation_variable": "minicheck_avgloadtimecheck", "count": 0.17}
```

56 is the average number of links per page; 0.17 is a load time in seconds. Counted as issues
they invent 56 new problems in a week where nothing happened. Filter to `type: "analysis"`
before touching the deltas.

Two `analysis` rows also count pages checked rather than pages broken, and both carry
`total_impact: 0` as the tell: `schema-validation` (1444) and `pages-with-unsupported-file-type`
(563).

### `previous_crawl: true` does not move the audit numbers

Called on `get_site_audit_problems` with and without it, same project, same minute: identical
`overview` and identical per-row `count` and `delta`. It is in the schema; it does not give you
the crawl before last here. There is no way to build a 7-day audit window out of 3-day crawls.

### `get_site_audit_messages` is not a message log

Despite "system messages/notifications for the Site Audit", it returns a per-URL map of hint
names — 938 URLs, ~150,000 characters, for a 2,708-page project:

```json
{"https://www.example.com/de/preise/": [{"name": "hint_urldynamic_lessdynamic",
                                           "importance": "critical"}, …]}
```

Nothing in it is dated, so nothing in it is a "this week" event. Not for this skill.

### `list_crawls` takes `limit` and sort parameters

Returns up to 100 crawl rows by default, with scores and page counts. All you need from it is
the two newest `end_time` values: pass `limit: 10`, `sort_column: "end_time"`,
`sort_direction: "desc"`. Call it once. Read `completion_reason` and `is_stopped`: a stopped
crawl reports `status: "done"` and 100%. `data_removed: true` marks a crawl whose rows are gone.

## Backlinks

### They are domain-level, not project-level

Five projects covering different scopes of one domain all returned `backlinks: 6006, delta: 10`
in `list_projects`, and `get_backlinks_new` returns the same rows whichever of them you pass.
Word every backlink finding as "the domain", not "this project".

### One page of a larger total, with no way to reach the rest

| Tool | Rows returned | `pagination.total` | Payload |
|---|---|---|---|
| `get_backlinks_new` | 100 | 499 | ~58,000 chars |
| `get_backlinks_lost` | 100 | 500 | ~58,000 chars |

Both take `limit` and `offset` (a multiple of `limit`). Page one holds the newest rows: in the verified run
both covered exactly the seven days from 07.09. to 13.09. On a domain with less link movement
the same 100 rows will span months instead, which is why the window has to be read from the data
rather than assumed.

### The date field differs between the two

`get_backlinks_new` rows carry `found_date`; `get_backlinks_lost` rows carry `lost_date` and no
`found_date` at all. Both carry `discovered_on`, `last_checked`, `rating`, `rel`, `type`,
`anchor_text`, `origin_domain`, `origin_url`, `target_url` and `link_removed`.

`last_checked` is not the event date — it ran back to 30.05. on the lost list.

### The data lags the calendar

On 17.09. the newest `found_date` and `lost_date` in both payloads was 13.09. A window counted
back from today returns four fewer days than the user thinks they asked for. Set the window from
the newest date in the payload.

### Links are not decisions

100 new links came from 47 domains, and four of those domains contributed 39 of the links: a
badge widget, a directory and two affiliate footers. On the lost side, one blog dropping a
footer widget removed 18 links at once. Report referring domains; flag any domain contributing
five or more links as one placement.

Median `rating` of the new links that week was 21 of 100, and a third were `rel: "nofollow"`.

## Uptime

### `get_health_status` is the compact call

`time_scale: "weeks"` is 60 buckets of 36 hours, about 90 days, so `uptime_percentage` covers a
quarter and `interval: "36 hours"` is the chart bucket, not the check interval.

```json
{"status": "ok",
 "current": {"time": "2026-09-17 16:29:01", "status": "down", "info": "redirect"},
 "alert":   {"time": "2026-06-23 21:39:01", "status": "down", "info": "redirect"},
 "uptime_percentage": 0, "timescale": "weeks", "interval": "36 hours"}
```

- Top-level `status: "ok"` is the API call. The site is `current.status`.
- **`info` decides what "down" means.** Every check in this verified project said `redirect`:
  the monitored URL redirects elsewhere, so the monitor has reported a three-month outage for a
  site that was never down. `info: "available"` is genuinely up.
- `uptime_percentage: 0` next to a healthy site is the same artefact. Read `info` first.
- `health_status: "inactive"` in `list_projects` means no monitoring at all — not 100% uptime.
- `alert.time` can equal the start of a down check while `status` is `up`: it is not a reliable
  "last incident". `info` also takes `timeout`, `ssl`, `unknown` and `threshold`; name the value.

### `get_health_downtimes` by day is cheap; the default and `get_health_dashboard` are payload traps

With `time_scale: "days"` it is ~8k characters and is the way to count a week's failed checks.
With the default it returned every 30-minute interval of the last 30 hours with each
individual check inside it, for one ongoing event — thousands of lines to say "still
redirecting".

`get_health_dashboard` returns that same 30-hour pill series **for every project in the
account**, including dozens that `list_projects` does not show. Never in a weekly check-in.

## Empty projects: what every tool returns when there is nothing to report

Verified against a project with 0 monitored keywords, 0 backlinks and exactly one crawl, from
2023. This is the shape the skill has to survive, because it is what a new or abandoned project
looks like.

### An empty result is shaped like a quiet week

| Call | With nothing set up | With a quiet week |
|---|---|---|
| `get_rankings_winners_and_losers` | `{"winners": [], "losers": [], "figures": {…: 0}}` | the same |
| `get_backlinks_new` | `{"data": [], "pagination": {"total": 0}}` | the same |

Nothing in either payload distinguishes them. `get_keyword_count` (`{"count": 0}`) and
`get_backlinks_overview` (`domain.count: 0`) do, at one call each.

### A populated object becomes an empty **array** when it is empty

`get_rankings_overview` returns `{"desktop": {…}, "mobile": {…}}` normally and **`[]`** on a
project with no keywords. The same switch happens inside `get_backlinks_overview`, where
`tld_stats` and `languages` are objects with data and `[]` without.

Any code doing `data["desktop"]` raises on the empty case. Test for the shape, not for
truthiness.

### `delta: 0` on every row, with no previous crawl to compare against

On the single-crawl project, `get_site_audit_problems` returned `delta: 0` for all 16 structure
rows — and `overview.problems_found.delta: null`, along with `null` for every category.

The rows look like a week in which nothing changed. The overview is the only place the payload
admits there is nothing to compare. Read `overview…delta` before reading any row delta, and
treat `null` as "no comparison exists", never as zero.

### `problems` rows come in three `type`s, not two

`analysis` (countable findings), `minicheck` (measurements — see above) and `hint`
(`hint_link_average_low`, a qualitative flag with `count: 0`). Filtering to `type: "analysis"`
handles all three correctly; filtering out only `minicheck` does not.

### `alert` in `get_health_status` is the last status change, not the last outage

On a healthy project it came back as `{"time": "2026-08-04 06:34:01", "status": "up", "info":
"available"}` — a recovery, not an incident. Read `alert.status` before calling it an alert.

## What Seobility does not have

State these when they come up rather than working around them silently:

- **No Google Search Console connection.** No impressions, no clicks, no CTR anywhere.
- **Response time is not page speed.** The health monitor times the server's response.
- **No automatic fixes.** Every output of this skill is a recommendation for a human.

## Cost

A full run is about ten to fifteen calls: `list_projects`, `get_keyword_count`,
`get_backlinks_overview`, `list_crawls`, `get_rankings_overview`,
`get_rankings_winners_and_losers`, `get_site_audit_problems`, `get_backlinks_new`,
`get_backlinks_lost`, `get_health_status`, and one `get_report` per audit job. Every MCP call is billed against
the account's credit balance, which `get_credits` reports along with the monthly allowance and
the reset date.
