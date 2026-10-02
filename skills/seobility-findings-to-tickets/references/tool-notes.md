# Seobility MCP — verified tool behaviour for this skill

Everything here was checked against live projects, not read off the tool descriptions. Where a
tool description and this file disagree, this file is right.

Verified against three projects: a 522-page wiki project with a current crawl (940 open
findings), a 2,703-page site with a large backlog (11,854 findings), and a deliberately broken
1,406-page example site (6,011 findings, 3 crawls). First pass 22.09.2026, second pass on the
large-backlog project 23.09.2026. URLs and project ids in the examples are anonymised.

## The three calls the skill is built on

```
get_site_audit_overview(project_id)   → which of the ~69 reports have findings, per category
get_site_audit_problems(project_id)   → importance / priority / category / total_impact / slug
get_report(project_id, analysis=slug) → the rows, the defect keys, the thresholds
```

`get_site_audit_problems` is the bridge: every row carries an `analysis` field, and that value is
exactly the `analysis` argument `get_report` and `get_report_meta` take.

```json
{"type": "analysis", "translation_variable": "analysis_heading_h1_problems",
 "priority": "highest", "category": "technique_and_meta", "importance": "important",
 "total_impact": 2870, "analysis": "heading-h1-problems", "count": 287, "delta": 0}
```

`total_impact / count` is the severity of a single finding, and it is a stable, small set of
values across projects — verified on two:

| Report | total_impact | count | per finding |
|---|---|---|---|
| `pages-broken` | 1200 | 6 | 200 |
| `canonical-link-target-problems` | 300 | 3 | 100 |
| `redirect-target-problems` | 100 | 1 | 100 |
| `link-anchor-text-duplicates-for-different-pages` | 5850 | 117 | 50 |
| `title-problems` | 100 | 5 | 20 |
| `heading-h1-problems` | 2870 | 287 | 10 |
| `internal-link-targets-on-redirects` | 1770 | 177 | 10 |
| `schema-validation` | 0 | 335 | 0 |

Use the quotient when two reports of different sizes compete for a slot in the set. `total_impact`
alone rewards whichever report has the most rows, and `importance` / `priority` are labels that
move with the count — the same report comes back `important` on one project and
`somewhat_important` on another. `seobility-audit-triage` established this; do not order by them.

**There is no human-readable issue name anywhere in the payload.** `translation_variable` is a
translation key and `analysis` is a slug. Every ticket title is written by the model, which is why
the title rules in `SKILL.md` matter more here than in a normal report skill.

`priority` is a string on `type: "analysis"` rows (`highest`, `high`, `medium`, `low`) and the
integer `0` on `type: "minicheck"` rows. Anything that sorts on it has to survive both — which is
a second reason not to sort on it. The payload also carries `type: "hint"` rows, qualitative flags
that arrive with `count: 0`. Filter to `type: "analysis"`.

## The report payload

```json
{"rows": [{"page": "https://…/wiki/Image_Map",
           "items": [{"type": "formatted_text", "key": "formatted_text",
                      "formatted_text": {"raw": "Image Map – Example", "formatted": "…"},
                      "properties": {"pixel_length_calculated": 199,
                                     "pixel_length_min": 200, "pixel_length_max": 580}}],
           "problems": [{"name": "title_short"}],
           "strikehash": 3270148503, "checked": false}],
 "filters": {"title_short": 2, "title_long": 2, "title_wordrepeats": 1, …},
 "pagination": {"total": 5, "offset": 0, "limit": 100}}
```

- `problems[].name` is the **defect key** — the unit a ticket is written for. It is not always
  readable: `pages-broken` labels all six of its rows `dashboard_technicalissues_26`. Never put a
  defect key in a ticket title.
- `problems[].value` appears on some keys and carries the detail: the HTTP status on a broken
  link (`403`), the new host on a moved one (`ixdf.org`).
- `items[].properties` carries the **threshold the tool judged against**. That is the acceptance
  criterion, and it is the only one that is re-checkable.
- `strikehash` and `checked` belong to the "mark as checked" feature in the app. Not ticket data.

Four `items[].type` values are verified, and each hides its value somewhere else:

| `type` | Where the value is | Example |
|---|---|---|
| `formatted_text` | `formatted_text.raw`, thresholds in `properties` | the current title |
| `number` | under a key **named by the item's own `key` field** | `{"type": "number", "key": "statuscode", "statuscode": 404}` |
| `page` | `page` — this is a URL role, not evidence | the own page carrying a link |
| `text` | `text` | the anchor text, or the duplicated title or description |

**The limits in `properties` are not always the rule for the row's defect.** Every
`title-problems` row carries `pixel_length_min/max`, whatever its defect. Verified: 15 of 17
`title_wordrepeats` rows sat inside 200-580 px. For those the pixel range is not the acceptance
criterion; the script prints a threshold only when the rows break it.

`get_site_audit_problems` takes a `categories` array (`technique_and_meta`, `structure`,
`content`) and `sort_by` (for example `delta_desc`, new findings first). Verified: `categories`
drops the other categories from `problems` while the `overview` block still reports all three.
About 60 of its rows carry `count: 0`, roughly 8,000 tokens per project.

### `get_report` pages with `limit` and `offset`

`pagination` reports `{"total": 137, "offset": 0, "limit": 100}`. `get_report` takes `limit`
(default 100) and `offset`, and `offset` must be a multiple of `limit`. Verified 29.09.2026:
`limit` 1, 2, 5 and 6 are honoured, and `offset: 12` with `limit: 2` returns rows 13-14. Page
until a short page comes back. A wrong offset returns `invalid_offset_to_limit` (its message
quotes "limit 50" whatever limit you sent). `limit: 1` is also the cheapest way to read `filters`.

On grouped reports (duplicate text, anchors) `total` is not a row count; stop on a short page.
Rows of grouped reports list at most 4 pages each; the full set comes from
`get_sublist(analysis: duplicate-text-paragraphs, item: <hash>)` (its `limit` is ignored). Never
present a truncated URL list as complete.

Verified again on a saved live payload (23.09.2026): `title-problems` with `total: 113` returned
100 rows; `filters` said `title_long: 91`, the rows held 78 of them. The rows came back grouped by
defect key, and inside `title_long` not sorted by how far over the limit a title is, so do not
describe the missing 13 as "the mildest ones". The script reports
"91 findings, 78 in this payload" and prints no page count for the missing part.

### `problems` filters the rows and still returns the whole `filters` map

```
get_report(project_id, analysis="heading-h1-problems", problems=["h1_missing"])
→ {"rows": [], "filters": {"h1_missing": 0, "h1_empty": 0, "h1_toshort": 284,
                           "h1_onlyoneword": 137, "h1_tolong": 0, "h1_genericword": 1,
                           "h1_toomany": 0}}
```

An empty result still costs nothing and returns the full split. That is the cheapest discovery
call in the skill — but only with a **known** key. An unknown one is a hard error:

```
get_report(…, problems=["__probe__"]) → error: Unknown problem __probe__
```

### The defect counts overlap and must not be summed

On the wiki project, `heading-h1-problems` reported `count: 287` while the filters added up to
422: `h1_toshort: 284`, `h1_onlyoneword: 137`, `h1_genericword: 1`. Rows carry several keys at
once — most short H1s are also one-word H1s:

```json
"problems": [{"name": "h1_onlyoneword"}, {"name": "h1_toshort"}]
```

The same page therefore appears in more than one ticket. That is correct, and it has to be said in
the tickets, or two people fix the same line.

### The defect counts are findings, not pages

Verified on `external-link-target-problems`: `linkissue_status: 3` was three broken outbound links
on **two** pages, `linkissue_hostchange: 3` was three links on **one** page. On on-page reports
the two happen to coincide, which is what makes the difference easy to miss and easy to state
wrongly in a ticket. The script prints both.

### A report's count can exceed the number of pages it describes

Two shapes do this, and both make a ticket wrong in its first sentence:

- **Coverage rows** — `schema-validation` reported exactly 335 on a project with 335 indexed
  pages, and 1,444 on one with 1,444, both with `total_impact: 0`. A count of pages checked.
- **Block and pair rows** — `pages-with-duplicate-text-content` reported 4,976 on a project whose
  whole indexable set is 1,444 pages, because a row is a text block with a list of pages attached.
  `get_report_meta.columns` gives it away: `text` and `pages` instead of `page`.

Anything above `indexed_pages` is one of the two. Check `columns` before writing a page count.

### `filters` is sometimes an empty **list**

`internal-link-targets-on-redirects` returned `"filters": []` and `"problems": []` on every row.
There the report itself is the unit. Any code doing `filters.items()` breaks on it — the script
handles both shapes.

**But an empty `filters` does not always mean there are no sub-types.** Verified on
`canonical-link-target-problems` (on the large-backlog project): `filters: []`, and every row carries its
sub-type in the row instead:

```json
{"page": "https://www.example.com/en/wiki/Rich_Snippets",
 "items": [{"type": "page", "page": "https://www.example.com/"}],
 "problems": [{"name": "canonical_badtarget_httpstatus"}]}
```

So the cheap filter probe cannot be used on those reports, and an empty `filters` is a reason to
pull the rows rather than a licence to skip them. The script groups by the row's `problems[]`, so
it splits this report correctly either way.

## The trap that ruins a ticket set: which URL is `rows[].page`

It is not always the page to fix. Verified on three report families:

**On-page reports** — `title-problems`, `heading-h1-problems` and the other content checks:
`rows[].page` is the affected page, `items[]` carries its current value as text.

**External link problems** — the row is the *link target*, and the own page is inside `items`:

```json
{"page": "https://www.microsoft.com/en-us/microsoft-365/copilot",
 "items": [{"type": "page", "page": "https://www.example.com/de/wiki/ChatGPT"}],
 "problems": [{"name": "linkissue_down"}]}
```

**Canonical link target problems** — both URLs are on the own domain, and the row is the page to
fix: `rows[].page` carries the canonical, `items[].page` is the target it points at. Verified on
the large-backlog project, where all three rows were `canonical_badtarget_httpstatus` — a canonical pointing
at a URL that does not return 200.

**Internal links on redirects** — three roles in one row, and the pages a developer edits are in
`pages[]`, a field the other families do not have at all:

```json
{"page": "https://demo-site.example/stuff/page-a.php",
 "items": [{"type": "page", "page": "https://demo-site.example/stuff/page-b.php"}],
 "pages": ["https://demo-site.example/sitemap.php"],
 "problems": []}
```

`page` redirects to `items[].page`, and `pages[]` lists the own pages that still link to the
redirecting URL. On that project all eleven rows pointed at one generated sitemap — one ticket,
not eleven.

`redirect-target-problems` has the same three-role shape. Verified (23.09.2026): one row, a
typo'd link inside a blog post (curly quotes around an example domain turned into part of the
URL); `pages[]` named the post. The same typo also showed up in `pages-broken`: one own edit, not
two findings.

**Same shape, opposite roles: the two text-group reports.** Verified 23.09.2026 on one project,
both reports returning rows with **no `page` field**, one `text` item and a `pages[]` list:

```json
// description-duplicates — pages[] are the pages sharing this description: edit these
{"items": [{"type": "text", "key": "text", "text": "Our blog articles will help you …"}],
 "pages": ["https://www.example.com/en/blog/", "https://www.example.com/en/blog/page/2/", …]}

// link-anchor-text-duplicates-for-different-pages — pages[] are the link TARGETS
{"items": [{"type": "text", "key": "text", "text": "dofollow"}],
 "pages": ["https://www.example.com/de/wiki/Dofollow", "https://www.example.com/de/wiki/Follow_Link"]}
```

In the second report, the pages that carry the anchor, the ones an editor opens, are not in the
payload at all. `get_page_incoming_links(url=<target>)` supplies them: for `/de/wiki/Dofollow` it
returned four linking pages, one of them with the anchor "dofollow". So the role cannot be read off
the row shape; the script keeps a per-report map (`ROLES`) and flags any unlisted report with
`pages[]` and no `page` as unverified.

Counts on the anchor report do not describe anything a ticket can use: `count: 117`, 41 anchor
rows, 97 target URLs across them. Report the anchor groups, never "117 pages".

**Subdomains.** The host test has to treat subdomains as the project's own site. Verified: a 404 on
the main site had four incoming links, all from a contest subdomain the project also crawls. Those
linking pages are the ones to fix, and on that site another team runs them: owner `external`.

The reliable test when a report is not in the table: compare the host of `rows[].page` with the
project's site, subdomains included. A foreign host means the row is a target.

## `pages-broken` names the 404, not who links to it

```json
{"page": "https://www.example.com/en/changelog/",
 "items": [{"type": "number", "key": "statuscode", "statuscode": 404}],
 "problems": [{"name": "dashboard_technicalissues_26"}]}
```

No `pages[]`, no linking page. `get_page_incoming_links(project_id, url)` supplies it:

```json
[{"url": "https://www.example.com/page-sitemap.xml",
  "labels": [{"type": "info", "label": "non_relevant_page"}],
  "click_depth": null,
  "anchor_texts": [{"anchor_text": "",
                    "labels": [{"type": "danger", "label": "no_anchor_text"}]}]}]
```

Verified: that 404 had exactly one incoming link, from the XML sitemap. Small payload, paginated
at 100, worth one call per broken or redirecting URL — and worth nothing for on-page defects,
where the affected page is already the page to edit.

Four more 404s on the same project, 23.09.2026, and four different tickets:

| 404 | Incoming links | What it becomes |
|---|---|---|
| a wiki URL that no longer exists | two blog posts, anchor "rich snippets" | own edit: repoint two links (`page (2)`, editor) |
| a landing-page URL that returns 404 | four pages on a subdomain the project crawls | ticket for the team running the subdomain (`external`) |
| `/cdn-cgi/l/email-protection` | four wiki pages, anchor `[email protected]` | **check**: Cloudflare's email obfuscation turns addresses into that link |
| the sitemap case above | the XML sitemap only | `config`, owner `ops` |

Same report, same severity, four owners. That split is only visible after the incoming-links call.

## `get_report_meta` is not the cheap pre-check its description promises

It returns two useful numbers and the **entire crawl history** of the report:

```json
{"overview": {"importance": "important",
              "problems_found": {"count": 5, "delta": 0},
              "affected_pages": {"count": 5, "delta": 0},
              "indexed_pages": 335},
 "columns": [...],
 "history": [{"crawl_number": 1, "datetime": "2018-04-25T09:19:14+0200", "count": 60,
              "crawling_status": 1}, … 438 rows …]}
```

438 history rows for a project with 438 crawls, roughly 30,000 characters for two numbers. Call it
only where the answer decides something — in this skill, where `affected_pages.count` against
`indexed_pages` decides whether a defect is a template fix or page-by-page work.

It has **no `filters` key**, although the `get_report` description points at
`get_report_meta.filters` for the problem keys. The keys come from `get_report`.

The `history` array is the one place per-report trend lives: the same report at 60 findings in
2018 and 5 today. Useful for saying whether a defect is new or standing debt — but it is a count
per crawl, not per URL, so it cannot tell you when a specific page broke.

## `previous_crawl: true` does not give you the previous crawl

Verified twice, on both endpoints:

- `get_report(project_id=12345, analysis="pages-broken", previous_crawl=true)` returned
  `rows: [], total: 0` — while the problems payload reported `count: 0, delta: -3`, meaning the
  previous crawl had three broken pages.
- `get_report_meta(project_id=67890, analysis="title-problems", previous_crawl=true)` returned
  `count: 473, delta: -8` — the current crawl's numbers. The history in the same response shows
  the previous crawl at 481.

So report rows cannot be diffed across crawls. "Is this new?" is answerable only from `delta` on
the problem row and from the `history` counts in the meta call, both at report level.

## `get_page_analysis` — and why `todos` is not the finding list

For a single URL it returns the page's own analysis. The findings are **not** in `todos`:

```json
"todos": [],
"analyses": {"analyses… sections": {
  "page_structure": {"h1_heading": {"factor_name": "factor_h1", "importance": "very_important",
    "messages": [{"message": "h1_toshort", "importance": "important",
                  "injections": {"size": 9}}]}}}}
```

`todos` came back empty on a page that carries two flagged findings. The findings live in
`analyses.sections.<section>.<factor>.messages[]`, each with its own `importance` and an
`injections` object holding the measured value.

Those `message` keys are the **same vocabulary as the report defect keys** — `h1_toshort`,
`title_wordrepeats`. That is the bridge for a per-URL ticket: the report says which pages, the
page analysis says with which value.

It is a large payload. Use it for the one or two URLs a ticket needs to quote, never as a loop.

## Defect keys verified so far

| Report | Keys |
|---|---|
| `title-problems` | `title_empty`, `title_missing`, `title_short`, `title_onlyoneword`, `title_long`, `title_genericword`, `title_domaintitle`, `title_wordrepeats` |
| `heading-h1-problems` | `h1_missing`, `h1_empty`, `h1_toshort`, `h1_onlyoneword`, `h1_tolong`, `h1_genericword`, `h1_toomany` |
| `external-link-target-problems` | `linkissue_status` (carries the code as `value`), `linkissue_down`, `linkissue_hostchange` (carries the new host), `linkissue_parking`, `linkissue_arecord` |
| `internal-link-targets-on-redirects` | none — `filters: []` |
| `pages-broken` | one opaque key on every row: `dashboard_technicalissues_26`; `filters: []` |
| `canonical-link-target-problems` | `filters: []`; sub-type per row, e.g. `canonical_badtarget_httpstatus` |
| `redirect-target-problems` | none — `filters: []`, empty `problems[]` |
| `title-duplicates`, `description-duplicates`, `link-anchor-text-duplicates-for-different-pages` | none — `filters: []`, one row per shared text |

For every other report: one `get_report` call returns its keys in `filters`. Add what you verify.

## Signals in the overview that change the whole set

- `special_checks.was_crawling_budget_reached` — a partial crawl. Counts are lower bounds.
- `special_checks.javascript_crawling_recommended` — the crawler saw less than a browser. Content
  findings from that crawl may be about the crawler.
- `ai_search_bots.total_blocked_pages` — on the example project, **501 of 501 pages** blocked for
  Googlebot and bingbot. Every on-page ticket on such a site is moot until the block is lifted.
- `start_url_tests.is_crawling_total_failure` — nothing was crawled. No tickets at all.

`get_site_audit_messages(project_id)` returned `[]` on both projects tested. Do not build the
"is this crawl healthy" check on it.

## What Seobility does not have

State these when they come up, rather than working around them silently:

- **No Search Console connection.** No impressions, clicks or CTR. A ticket cannot carry a traffic
  number unless the user supplies their own export.
- **Response time is not page speed.** `response_time` is the server's HTML response, not Core Web
  Vitals. A "slow pages" ticket says server response time, or it is wrong.
- **Seobility does not fix anything, and this skill does not file anything.** Every output is a
  recommendation a human schedules.

## `seo_check` is the live check for an old crawl

`seo_check(website=<url>, detail_level="full")` fetches one URL now, outside the project, and
returns its title (`title_text`), headings (`html_body.headings`) and every link on it
(`elements.html_body.links[]`, each with `url` and `anchor.text`). The MCP default is
`detail_level: "analysis"` (about 20,000 characters), which has no link list. Verified 24.09.2026
on a wiki page from a nine-month-old crawl:

- the H1 was still the bare term (`h1_toshort`, 12 characters): the ticket stood;
- the page still linked its image at the old `/wiki/images/...` path: the ticket stood;
- all 112 links pointed at the wiki home without the trailing slash the crawl had flagged: that
  ticket was already fixed and left the set;
- `title_text` contained a literal `&amp;` (JSON `\u0026amp;`), confirming a suspicion from the
  crawl rows: an own edit, not a check.

The `full` payload is about 56,000 characters and may overflow into a file. Read it with a short script
(`json.load`, then the three paths above), never into context.

A plain `curl` from the model's environment is no substitute: the same site, behind Cloudflare,
answered it with a 403 "Attention Required" page. Seobility's checker is let through.
