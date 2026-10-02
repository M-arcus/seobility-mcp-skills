# Seobility MCP - verified tool behaviour for audit triage

Everything here was checked against live projects on 22.09.2026, not read off the tool
descriptions. Where a tool description and this file disagree, this file is right.

Revised 29.09.2026 against the live tool schemas: `get_report` takes `limit` and `offset`,
`list_crawls` takes `limit` and carries `completion_reason`, `is_stopped`, `data_removed`,
`pages_crawled` and `pages_indexable`, `list_projects` returns all projects (~40,000 characters for 46)
and ignores `limit`. A stopped crawl still reads `status: "done"` and 100%.

Verified against three projects of one account: a 522-page reference site with 940 problems and a
weekly crawl, a 2,703-page multilingual site with 11,854 problems and a three-day crawl, and a
deliberately broken demo site - plus the project list of an account holding seven projects with
the same domain. Example URLs and titles below are anonymised.

## The two calls that carry the skill

### `get_site_audit_overview` - the whole catalogue for ~4,000 characters

One call returns the four scores with deltas, and every one of the ~60 issue reports with
`status`, `count` and `delta`, grouped as the app groups them:

```json
{"scores": {"overall": {"current": 92, "delta": 1}, "technique_and_meta": {...}, ...},
 "analyses": {"technique_and_meta": {"overview": {"problems": {"count": 652, "delta": -5}},
   "groups": {"meta_tags_and_page_attributes": {
     "title-problems": {"status": "warning", "count": 5, "delta": 0}, ...}}}},
 "start_url_tests": {"is_crawling_total_failure": false, ...},
 "special_checks": {"was_crawling_budget_reached": false,
                    "javascript_crawling_recommended": false},
 "ai_search_bots": {"total_blocked_pages": 0, "all_bots": [{"agent": "OAI-SearchBot", ...}]}}
```

Three blocks outside the counts are worth reading every run:

- `start_url_tests.is_crawling_total_failure` - the crawl never got in. Stop; the rest is noise.
- `special_checks.was_crawling_budget_reached` - the crawl hit the plan limit, so the counts
  describe an arbitrary slice.
- `ai_search_bots` - per-agent blocked page counts for OAI-SearchBot, Claude-SearchBot,
  PerplexityBot, BraveBot and the rest. Nothing else in the API surfaces this. Both test projects
  returned 0 across the board; a non-zero value is a finding in its own right.

### `get_site_audit_problems` - the ranking input

One flat row per report, with the two fields that matter:

| Field | What it is |
|---|---|
| `analysis` | the report slug, and the argument for `get_report` |
| `count` | affected pages - **except** for the coverage and block rows below |
| `total_impact` | Seobility's own severity for the whole report |
| `type` | `analysis`, `minicheck` or `hint` - only `analysis` rows are findings |
| `category` | `technique_and_meta`, `structure`, `content` |
| `importance`, `priority` | labels - **not stable, do not order by them** |

`categories: ["content"]` works and cuts the payload by about two thirds while still returning the
full `overview` block. `sort_by` takes `delta_desc`, `number_of_problems_desc` and the like, but
rejected `total_impact` (`invalid_sort_option`, 22.09.2026); sort in the script instead. About 40 of
the ~59 rows have `count: 0` and no filter removes them.

## `total_impact / count` is a stable per-issue weight

This is the finding that makes the ranking possible. The quotient is Seobility's own severity for
one occurrence of an issue, and it is **identical across unrelated projects**:

| Report | Project A | Project B | Weight |
|---|---|---|---|
| `pages-with-keyword-cannibalization` | 90 / 3 | 630 / 21 | 30 |
| `pages-missing-the-title-content-in-the-body` | 2300 / 92 | 8250 / 330 | 25 |
| `pages-with-duplicate-paragraphs` | 45 / 3 | 2445 / 163 | 15 |
| `pages-with-typos` | 10 / 1 | 140 / 14 | 10 |
| `heading-h1-problems` | 2870 / 287 | 9390 / 939 | 10 |

The range runs from 50 (`link-anchor-text-duplicates-for-different-pages`,
`pages-with-identical-page-duplicates`, `pages-with-many-internal-links`) down to 5
(`heading-problems`) - and 1 for `pages-with-duplicate-text-content`, which is the tell that its
rows are not pages.

### `importance` and `priority` are not stable and must not order anything

Same report, two projects, same minute:

| | Project A (3 affected) | Project B (163 affected) |
|---|---|---|
| `pages-with-duplicate-paragraphs` importance | `important` | `somewhat_important` |
| `pages-with-duplicate-paragraphs` priority | `high` | `highest` |

Both fields move with the affected count, so they rank volume, not severity. A third value appears
in `get_report_meta`: for `heading-h1-problems` it returned `somewhat_important` where
`get_site_audit_problems` said `important`, for the same project and the same crawl. Three
endpoints, three answers. Use the weight.

## The three counts that are not page counts

### Coverage rows: `count == indexed_pages`

`schema-validation` returned 335 on a project whose `indexed_pages` is 335, and 1,444 on a project
whose `indexed_pages` is 1,444, and was read as the number of pages checked. **That is not a rule**
(29.09.2026): on three other projects it counted 22 of 76 pages, 109 and 256. It is a real report with
per-row `critical` / `tip` severities and a `filters` histogram (`schema_recommended_missing`,
`schema_property_wrong_type`, ...). `total_impact` is 0 and `priority` is "highest", so it cannot be
scored. It is a coverage row only when every non-zero `filters` key is `schema_recommended_missing`.
A `critical` on a `{"@id": …}` reference can be a valid reference the validator does not resolve (18
rows on one site).

`indexed_pages` is `pages_indexable` in `list_crawls`, free; `get_report_meta.overview` carries it too.

### Block counts: `count > indexed_pages`

`pages-with-duplicate-text-content` returned **4,976** on a project with 1,444 indexable pages.
`get_report_meta.columns` for it reads `[{"name": "text"}, {"name": "pages"}]` - a row is a text
block with the pages it appears on. `affected_pages` mirrors `problems_found` here, so that field
does **not** disambiguate; `columns` does.

Its weight is 1 per finding, the lowest in the audit. That makes the count meaningless for
planning, **not the finding**: the rows carry the repeated text itself.

On a two-language blog (23.09.2026) the report said `count: 590`, yet `pagination.total` was
**120** rows - so the count is neither pages nor blocks, probably block-page pairs. Each row is
one text truncated to about 100 characters, with a `pages` list of two to four URLs (never more
than four seen; it may be capped). Sorted by hand, the 100 visible rows were:

- author bios and translation credit lines on each author's articles - by design
- the same teasers on the blog overview and its pages 2 to 4
- English quotes (Google announcements, tweets) in both language versions of one article - normal
- **more than 20 identical paragraphs per language across a seven-article CMS series**, on
  articles that rank - a real content job, and the most valuable finding in that audit

The text is what `pages-with-duplicate-paragraphs` does not give you (see below), so read this
report's rows before sending anyone to open a sample page for that one.

### Minicheck rows: measurements wearing an issue's clothes

```json
{"type": "minicheck", "translation_variable": "minicheck_avglinks", "count": 51, "delta": 51}
{"type": "minicheck", "translation_variable": "minicheck_avgloadtimecheck", "count": 0.1}
```

51 is the average links per page; 0.1 is a load time in seconds. Read as issue counts they invent
51 new problems in a week where nothing moved. A third type, `hint`, carries qualitative flags with
`count: 0`. Filtering to `type: "analysis"` handles all three.

## `get_report` - the rows, and how to page them

```json
{"rows": [{"page": "https://example.com/glossary/image-map",
           "items": [{"type": "formatted_text", "key": "formatted_text",
                      "formatted_text": {"raw": "Image Map - Example", "formatted": "…"},
                      "properties": {"pixel_length_calculated": 199,
                                     "pixel_length_min": 200, "pixel_length_max": 580}}],
           "problems": [{"name": "title_short"}], "strikehash": 3270148503, "checked": false}],
 "filters": {"title_short": 2, "title_long": 2, "title_wordrepeats": 1, …},
 "pagination": {"total": 5, "offset": 0, "limit": 100}}
```

### 100 rows by default; `limit` and `offset` change that

Verified on `pages-with-high-page-depth`: `pagination.total: 216`, 100 rows returned by default. On
22.09.2026 `get_report` accepted neither `limit` nor `offset`. Both work now, and `offset` must be a
multiple of `limit` (`limit: 10, offset: 100` works). The error for a wrong offset always quotes
"limit 50", whatever was sent.

Rows come back sorted worst-first (page level 6, then 5, then 4), and the `problems` parameter
subsets by sub-type. A small `limit` is the cheapest way to cut a payload: `limit: 1` reads `filters`,
`limit: 25` is enough to cluster.

Say "the first N of M" in any output built on a partial pull.

### `filters` is a free sub-type histogram

Requesting a sub-type with no hits returns no rows and the **complete** histogram anyway:

```
get_report(project_id, analysis="title-problems", problems=["title_missing"])
-> {"rows": [], "filters": {"title_short": 7, "title_long": 91, "title_wordrepeats": 17, …},
    "pagination": {"total": 0, …}}
```

About 200 characters for the answer to "which edit is this report actually asking for". Verified on
two projects and two reports.

Two shapes to handle:

- The sub-type counts **sum to more than the report's `count`**, because a page can carry two at
  once: 284 `h1_toshort` plus 137 `h1_onlyoneword` across 287 affected pages.
- `filters` is an empty **array** `[]`, not an object, on reports with no sub-types
  (`pages-with-duplicate-paragraphs`, `pages-with-high-page-depth`). Test the shape.

### `filters` is empty on some reports that do have sub-types

`canonical-link-target-problems` returns `filters: []` while every row carries its sub-type in
`problems[]`:

```json
{"page": "https://example.com/stuff/canon2404.php",
 "items": [{"type": "page", "page": "https://example.com/stuff/404.php"}],
 "problems": [{"name": "canonical_badtarget_httpstatus"}]}
```

The four sub-types seen live: `canonical_multiple`, `canonical_badtarget_httpstatus`,
`canonical_badtarget_targetisredirects`, `canonical_differentdomain`. The probe does not work on
this report - read the rows and count the `problems[].name` values yourself.

So `filters: []` means one of two different things: no sub-types, or sub-types that live per row.
Check a row's `problems[]` before concluding the report is uniform.

### Some reports return groups, and then `count` and `pagination.total` are different things

`title-duplicates` reported `count: 39` in the overview and `pagination.total: 4` in the report.
Both are right: 39 affected **pages**, in 4 duplicate **groups**. A row is a title text plus the
pages carrying it, and there is no `page` field on the row at all:

```json
{"items": [{"type": "text", "key": "text", "text": "Example Blog - …"}],
 "pages": ["https://example.com/de/blog/", "https://example.com/de/blog/page/2/", …19 URLs]}
```

The `pages` array is free clustering evidence: 34 of the 39 pages were `/blog/page/N/`, which is
what made the fix one setting rather than 39 edits. `description-duplicates` has the same shape.

### `internal-link-targets-on-redirects` counts targets, not links

`get_report_meta.columns` reads `pages` and `page_with_page_item` - a row is a redirect target with
the pages linking to it. So `count: 605` is **605 distinct redirect targets**, which is also the
number of search-and-replace pairs the fix needs, not 605 individual clicks. That is what makes
`1 + n/50` a fair cost model for it.

### `items` differs per report, and sometimes there is no page at all

`{"type": "formatted_text", …}` for titles, `{"type": "number", "key": "page_level"}` for depth,
`{"type": "number", "key": "count"}` for duplicate paragraphs. Read `get_report_meta.columns`
rather than assuming. When the first column is `text` or `item` rather than `page`, the rows are
not pages and no per-URL plan can be built from them.

### `pages-broken` with no status code is a crawl that got no answer

Verified on a fourth project (a two-language blog, 23.09.2026): 51 rows, every one of them

```json
{"page": "https://example.com/de/blog/c/content/",
 "items": [{"type": "number", "key": "statuscode", "statuscode": null}],
 "problems": [{"name": "dashboard_technicalissues_4"}]}
```

The same URLs appear in `pages-non-indexable` with `statuscode: 0` and
`problems: [{"name": "failure", "value": 4}]`. No HTTP status at all - not a 404, not a 5xx. The
report's `get_report_meta` history read 0 for 309 crawls and 51 in the last one, and the same crawl
had 18 slow server responses. That is a server that timed out during one crawl. A null status on a
report that was empty last time means re-crawl before planning anything.

### `pages-non-indexable` explains the gap between crawled and indexable

`pagination.total` is `pages_crawled - indexed_pages` less the `pages-with-unsupported-file-type`
count (3,259 = 3,459 - 200 on the blog above, which has no such files; 29,487 against 29,543 on a
34,028-page site with 56 of them), and each row names its reason in `problems[].name`: `failure`, `noindex`, `redirect` seen
live. Two limits:

- `filters` is `[]`, and `problems` does not subset by reason: `["noindex"]` returns
  `Unknown problem noindex`. There is no count per reason.
- Rows come back grouped by reason (failures first, then noindex, then redirects), so the visible
  100 can over-represent the first group. Cluster the page URLs rather than counting reasons.

On that blog the pattern was `/{lang}/blog/{post}/page/{n}/`: up to 25 noindex copies of single
articles. No audit report flags this.

### `link-anchor-text-duplicates-for-different-pages` can return fewer groups than its count

`count: 19` in the overview and `pagination.total: 19`, but only **2 rows** came back: "show more"
on six listing pages, and a credit line linking to three original articles. Whether the other
findings are hidden or the count counts something else is not clear. Say what was visible.

### `external-link-target-problems` can overflow the context on a small count

78 rows came to about 77,000 characters and could not be returned inline. `items[]` lists every own
page carrying the link, including 513 `/page/{n}/` copies out of 681 references. Save it to a file
and count distinct source pages after folding `/page/{n}/` - 60 articles, not 681. The sub-types
are in `filters` and per row: `linkissue_hostchange` (a redirect to another host),
`linkissue_status` (an error status), `linkissue_down` (no answer).

### `internal-link-targets-on-redirects` rows: `page` is the redirecting URL

Verified on a wiki project (24.09.2026): each row is
`{"page": <redirecting URL>, "items": [{"type": "page", "page": <final URL>}], "pages": [<linking pages>]}`.
So `page` is a link target, not an affected page, and the count set against `indexed_pages` is a
different unit. The 100 visible of 375 rows were one home link (`/en/glossary/` -> `/en/glossary`,
linked from every article) and 98 article images (`/en/glossary/images/…` -> `/media/glossary/…`).
`get_http_status_distribution` showed 376 redirects in the crawl, matching the count.

### Keyword-match reports mark the missing words in bold

`pages-missing-the-title-content-in-the-body` returns the title per row with the words that are
missing from the text wrapped in `**` in `formatted_text.formatted`
(`"Crawl budget \- Definition \+ All factors **explained** \- Example Glossary"`). `filters` is
`[]`. On the wiki, most bold words were title frame words ("Definition", "explained",
"Practices"), and the same rows showed 11 of 100 titles containing a double-encoded `&amp;` -
visible as code in the search result and flagged by no report.

### `pages-with-keyword-cannibalization` rows are page groups with the shared terms

`{"items": [{"type": "text", "text": "SEO"}, {"type": "text", "text": "off page seo"}, …],
"pages": [<2-3 URLs>]}`, no `page` field. On the wiki two of five groups paired the English and
German version of one article, and the rest paired related but distinct terms (On-Page and
Off-Page SEO, ChatGPT and GPT). Read the groups before planning a merge.

## Links into the Seobility app

Verified 24.09.2026 in a logged-in session. The report slugs are the same as the MCP's `analysis`
values:

| Target | URL |
|---|---|
| Site Audit overview | `https://app.seobility.net/project/{project_id}/site-audit` |
| One report | `https://app.seobility.net/project/{project_id}/site-audit/reports/{analysis}` |
| One page's detail panel, over any report | report URL + `?browser=site&url={URL-encoded page}` |
| That page's repeated paragraphs | the same + `&tab=elements&element=text-blocks` |

The detail panel opens on the Analysis tab by default. Other `tab`/`element` values exist but were
not checked; use only the ones above.

## The duplicate paragraph text is not reachable

`pages-with-duplicate-paragraphs` gives a per-page count and nothing else. Three ways in were
tried and none returned the paragraph:

- `get_sublist(analysis="duplicate-text-paragraphs", item=<page url>)` - `{"data": []}`, with and
  without the `url` argument. The `item` format is undocumented and was not guessable.
- `get_page_duplicate_content(url)` - `{"data": []}` for a page the report flags. It answers
  page-level duplication, not paragraph-level.

This is why the report's effort class is `inspect` rather than a guess: shared boilerplate and
genuine prose overlap differ in cost by two orders of magnitude, and nothing in the API separates
them. Someone has to open one page - and the app link with `element=text-blocks` (above) takes
them straight to the repeated paragraph.

## `get_report_meta` is not the cheap pre-check it claims to be

Its description calls it a cheap pre-check before pulling a large report. It returns the report's
**entire crawl history, one row per crawl** - 438 rows for a project crawling weekly since 2018,
about 30,000 characters, to deliver four numbers.

Call it when you need `columns` or the report's history, once, preferably on a project with a short
crawl history. `indexed_pages` is free as `pages_indexable` in `list_crawls`. The counts it returns are already in `get_site_audit_overview`.

What it is genuinely good for: `overview.indexed_pages` (the denominator for the coverage check)
and `columns` (what a row is).

## The distribution endpoints

### `get_http_status_distribution` - small, exact, worth calling

```json
{"chart": {"200": {"count": 2092}, "301": {"count": 604}, "302": {"count": 1}, "404": {"count": 6}},
 "figures": {"successful": 2092, "redirects": 605, "errors": 6, "crawledPages": 2703}}
```

605 redirects inside a 2,703-page crawl is a structural fact about the site, and it explains the
605 rows of `internal-link-targets-on-redirects` sitting in the problem list. The two belong in the
same plan entry.

### `get_click_depth_distribution` - use `avg` and `highest`, never `median`

```json
{"figures": {"avg": 2.878, "median": 10.5, "highest": 6}, "chart": {"1": 32, "2": 389, "3": 829, …}}
```

`avg` is correct - it reproduces exactly from the chart on both test projects. `highest` is the
deepest level reached.

**`median` is not a median.** It is the sum of the bucket labels divided by two: buckets 1-6 gave
10.5, buckets 1-2 gave 1.5. On the first project the true median depth is 3 and the field says
10.5, a number deeper than the deepest page on the site. Never print it.

The chart also covers fewer pages than the crawl - 1,478 of 2,703 on one project - so do not
compute shares against `pages_crawled`.

### `get_page_score_distribution` - a 10-number histogram wrapped around 1,387 ids

Every bucket carries a `crawl_urls_ids` array listing every page in it. The useful part is four
numbers:

```json
{"figures": {"good": 1367, "medium": 20, "bad": 0, "average": 93}}
```

The ids are not usable: no tool in the MCP takes a `crawl_url_id`. On a 2,703-page project the call
came to roughly 20,000 characters to deliver those four numbers. Skip it unless the user asks for
the score spread specifically.

`good + medium + bad` (1,387) matches neither `pages_crawled` (2,703) nor the 200s (2,092). Report
the figures, not a percentage of anything.

## `get_rankings_landingpages` - the "does anyone see this page" join

```json
{"landingpages": [{"url": "https://example.com/glossary/ascii-code", "visibility": 460,
                   "visibility_delta": 0, "keywords_count": 2}],
 "figures": {"landingpages": 258, "winners": 73, "losers": 75, …}}
```

258 ranking URLs came to about 30,000 characters - large but not overflowing, and it scales with
the monitored keyword set, so an agency project with 1,900 keywords needs to go to a file.

It is the only thing in this skill that knows whether a page matters to anyone. Use it to weight
groups, never to estimate traffic.

`timescale` behaves as in the weekly check-in: pass it explicitly, because omitting it returns a
different window again.

## The two endpoints disagree about the totals

For one project: `get_site_audit_overview` sums to 11,291 across its three categories, while
`get_site_audit_problems.overview.problems_found.count` says 11,854 - which is the figure
`list_projects` also reports. The problems endpoint includes reports the overview's groups leave
out.

Pick one source for the headline number and name it. The problems endpoint agrees with what the
user sees in the app.

## What Seobility does not have

State these when they come up rather than working around them silently:

- **No Google Search Console connection.** No impressions, no clicks, no CTR. Whether anyone
  actually visits an affected page is not knowable from this data.
- **Response time is not page speed.** `pages-with-slow-server-response-times` measures the
  server's HTML response, not Core Web Vitals.
- **The crawl is not the site.** Blocked, logged-in and out-of-scope pages produce no findings,
  and their absence looks identical to health.
- **Seobility fixes nothing.** Every output of this skill is a change a human makes.

## Cost

A full run is 12 to 15 report pulls per site plus the Help Center articles: about 50 calls (39 of
them `get_report`) and 270 KB of payload were measured on three small sites. The fixed part is
`list_projects` (or `compact`), `list_crawls`, `get_site_audit_overview`, `get_site_audit_problems`
and `get_rankings_landingpages`. Each report in the plan adds a `filters` probe and a rows pull for
the clustering (`limit: 25` keeps them small); skip both for a count of 1 or 2.
`pages-non-indexable` adds one call when the crawled/indexable gap is large. Make the one
`get_report_meta` call on `pages-broken`: it costs the same history dump as any other report and
also answers whether the broken pages are new. `get_credits` reports the balance, the monthly
allowance and the reset date.
