# Tool notes: how the tools behave, verified against live responses

Verified on 30.09.2026 on three keyword/page pairs on google.de: a long guide at position 4 in an
agency-dominated SERP, a long guide at position 13 in a SERP split between guides and link shops,
and a glossary entry at position 5 in a SERP of guides. Values below are rounded or anonymised.

## `tfidf_check`

**Request.** `search_term`, `search_engine` (e.g. `google.de`, case-insensitive; the response writes
`Google.de`), `website` (our URL, optional). `serp_depth` is 3, 7, 10 (default) or 15/20 on premium
accounts. `calculation_result_limit` is a deprecated alias of `serp_depth`: it never limited the
number of terms, it limits the number of competitor pages, so it changes the verdicts.
`include_competitor_terms` and `include_analyzed_text` default to `false` on MCP; leave them.

**Cost.** The most expensive live call of the run. A depth of 7 cost the same as a depth of 10, so
a smaller depth saves nothing and only weakens the comparison.

**Size.** 35,000 to 45,000 characters with the MCP defaults (about 120 to 190 `stats` rows). It
arrived inline every time (30.09. and 01.10.2026), not as a saved file.

**Shape.**

```json
{"request": {"search_term": "…", "search_engine": "Google.de", "url": "<our url>", "serp_depth": 10},
 "stats": [{"keyword": "e-commerce", "avg_tf_idf_used": 6.33, "avg_tf_idf_total": 2.53,
            "occurrences": 4, "max_tf_idf": 11.9, "max_tf": 0.48, "url_tf": 0}],
 "results": [{"rank": 2, "title": "…", "description": "…", "domain": "…", "url": "…",
              "load_time": 0.55, "word_count": 2137, "crawl_error": null,
              "backlinks": 1, "referring_domains": 1}],
 "target_url_results": {"link": "<our url>", "tf_idf": {"content": 6.2, "seo": 7.9}},
 "term_suggestions": {"b2b": {"max_keyword_use": 49, "min_keyword_use": 9,
                              "current_keyword_use_count": 0, "usage": "not_often_enough"}},
 "analyzed_text": {"word_count": 5528, "percent": 100, "type": "success"},
 "credits": 37000}
```

- `results` is the live top 10, **our page included** when it ranks there (then it carries our own
  `word_count` and `referring_domains`). `title` and `description` are the SERP snippet, useful for
  classifying page types without fetching anything.
- `crawl_error: "wdfidf_error_statuscode"` with `word_count: 0` on forum threads (Reddit): the page
  was not analysed. Video pages come back with `word_count` around 12: also not analysed in any
  useful sense.
- `results[].referring_domains` is the page's own link count, not the domain's. On two SERPs almost
  every page had 0-1; on the third the top guide had 37 and a link marketplace 311. The numbers are
  plausible but thin; use them for "links do or do not explain this", never for a ranking.
- **`term_suggestions[].current_keyword_use_count` is our page's TF\*IDF weight, not a count.** It
  equals `target_url_results.tf_idf[term]` in every row checked, while `min_keyword_use` and
  `max_keyword_use` are counts. "backlinks": ours 6.8, band 76-149, verdict `not_often_enough`;
  "saas": ours 5.9, band 15-74, verdict `perfect`. The verdict is computed on something else; only
  the verdict is usable.
- **Hyphenated compounds are separate tokens.** A page that writes "SaaS SEO" shows `url_tf: 0` for
  `saas-seo` and gets `not_often_enough` for it, while `saas` and `seo` are both on the page. Same
  for the hyphenated German terms for "image SEO" and "SaaS SEO strategy". Before calling such a term missing, check its parts.
- **Inflections are separate tokens** (on a German seed, an inflected form of "high-quality" missing while the base
  form is used), and so are synonyms ("guest article" missing while "guest posts" is used). `competitor_gap.py tfidf` flags the
  inflections; synonyms need judgement.
- `stats` rows with `occurrences` of 2 are dominated by one competitor's own vocabulary: agency
  names, city names, product names, legal forms ("llc"), an author's first name.
- The `credits` field is the **remaining balance** after the call.
- **A URL listed twice in `results`** is counted twice in `stats.occurrences`.
  `competitor_gap.py tfidf` names such URLs; compare the page once.
- **Local searches.** Without a `location_id`, results for local-service keywords can show
  providers from one region. City names then show up as terms on 3-4 pages. They are never a gap
  for our page. Pass `location_id` (from `search_locations`) when the user names a city.

## `keyword_autocomplete`

About 100 related searches for a big seed ("frontend", 01.10.2026), 1 to 18 for small ones (2, 1 and
18 rows on three keywords the same day; a low-volume seed
returns one or two, and two seeds returned none), not the 30-100 first noted. Each row has
`search_volume`, `competition` (Google Ads, 0-1, not ranking difficulty), `cpc` and `intents`. The
cheap call of the run. A volume of 0 or none is shown as "<10" in reports.

- On a German market it mixes English and German variants ("saas seo agency" on google.de) and
  matches words, not meaning (a search for photos of an Italian buffet restaurant came back for the German seed "image SEO").
- The most useful signal was the **commercial twin**: "buy high-quality backlinks" at the same 90
  searches as "high-quality backlinks" (German seeds, translated here); "saas seo agency" at 110 against 70 for "saas seo".
- Long tails come in spelling variants of 10 each ("alt-tag image seo", "alt tag image seo",
  "alt-text image-seo" …, translated from German). Clustered, one image-SEO topic added up to about 250 searches.

## `keyword_similar`, `keyword_questions_and_similar_searches`

Both tested on "saas seo" (google.de). `keyword_similar` returned the keyword itself and one
unrelated term ("jimdo seo"). `keyword_questions_and_similar_searches` returned four generic questions
("what exactly does seo mean"), all with volume 0, and an empty `similar_searches`. Neither is worth
calling by default; the questions tool is the fallback when an FAQ needs real questions and
autocomplete has none.

## `backlink_check`

- **URL mode** (pass a full URL): `mode: "url"`, `meta_info.referring_domains_count` and
  `total_link_count` (strings), `follow_percent`, and `domain_score` of the host. `results` lists
  the links when there are some; it came back empty on a URL with a count of 1. Small and cheap.
- **Domain mode** (pass a bare domain): the domain's whole link list with titles, anchors and
  dates. Large, and not needed for this skill.
- `domain_score` is the host's score in URL mode too, so it compares sites, not pages.
- **Verified 01.10.2026** on "social bookmarks" (google.de): Wikipedia article at #1 = 107
  referring domains, domain score 76; a glossary at #2 = 0 and 52; our wiki entry at #4 = 0 and 60.
  The #2 page is ahead on a weaker domain with no links: domain strength and links do not separate
  it. One call per page, cheap.
- **On a well-linked page the URL mode is large too**: the Wikipedia URL with 107 linking sites
  returned 113k characters (saved to a file), one with 41 linking sites about 30k (arrived inline,
  01.10.2026), because `results` holds the page's link list.
- `meta_info.referring_domains_count` matched `tfidf_check` `results[].referring_domains` on all
  three pages checked (41 / 3 / 3, "frontend" on google.de, 01.10.2026). For a top-10 comparison the
  free tfidf value is the link count; `backlink_check` is only needed for `domain_score`. `results` is a dict keyed by
  linking domain; a value is one link object or a list of them, each with `origin_url`,
  `origin_title`, `anchor_text`, `rating` (link strength, 12-45 on that page), `rel`,
  `link_removed`, `status`, `discovered_on`. `competitor_gap.py links` reduces it. On pages with few
  links `results` is an empty list.
- `total_link_count` can be huge (281,293 for 107 referring domains on Wikipedia): sitewide links.
  Compare referring domains, never total links.
- **"1 / 1 / 1" with an empty `meta_title` and empty `results`** is the answer for a page with no
  link data yet. Report it as "no link data", not as one linking site; `tfidf_check`
  `results[].referring_domains` shows the same value. Pages with link data return real counts, "0"
  included, and a title.
- **Small sites sit at the bottom of the domain scale.** Values of 0, 10 and 20 are all small, so
  the domain rule in SKILL.md needs the competitors at 30 or more before it calls ours behind.
- The thresholds in SKILL.md step 6 (ten times the linking sites on all three, domain score 10+
  points above on two of three) are **working rules from one SERP**. Re-check them on the next runs.

## `seo_score`

Returns `{"score": n}` and nothing else: the overall 0-100 score of the free SEO Check for any URL.
A live call per page, so score the pages actually compared, and the rest of a first page only when
ours scores below most of them. It said "no disadvantage" in 5 of 5 test runs. Verified 01.10.2026: our wiki entry 87, Wikipedia 81, the glossary at #2 58. A page above
ours with a lower score shows that on-page optimisation does not explain its position, which is the
comparison the Seobility guide "Why are my competitors ranking higher on Google?" builds on. For the findings
behind the score use the Website Audit (project pages) or `seo_check` (expensive, ours only).

## `seo_compare`

Head-to-head of two URLs for a keyword. Not used: it runs the full check on both pages, and the
skill needs a score for four pages, which `seo_score` gives cheaper.

## `tfidf_check` `results[].load_time`

Server response in seconds per page. It is the time until the server answers, not page speed or
Core Web Vitals. `competitor_gap.py tfidf` prints it next to word count and referring domains.

## `get_page_incoming_links`

`limit: 1` is enough: `pagination.total` is the number of internal pages linking to the URL. On a
blog, most of them come from a "more from our blog" widget with the post title as anchor, so a
high total says little about deliberate linking.

## What the free page read (`competitor_gap.py pages`) sees

- It reads the HTML a script gets. On all tested pages (blogs, a wiki, agency sites, a SaaS blog) it
  returned title, description, H1, the outline and JSON-LD. Forum threads and video pages were not
  among the pages read; they are the ones to expect `FAILED` or an empty shell from.
- The outline includes page furniture: author boxes, "related posts", comment headings, trial
  boxes, a table-of-contents heading. Headings inside `nav`, `header`, `footer` and `aside` are
  excluded; the rest has to be filtered by reading.
- Structured data lists every `@type` in the JSON-LD, nested ones included (`ReadAction`,
  `EntryPoint` from a WordPress SEO plugin). The ones that matter for the comparison are
  `FAQPage`/`Question`, `HowTo`, `Article`/`NewsArticle`, `Product`, `Review`.
- Word counts are body text without navigation, header, footer and sidebars, so they come out a
  little lower than `results[].word_count` from `tfidf_check`.
- Dates come from `article:published_time` / `article:modified_time` meta tags, `itemprop` dates,
  JSON-LD `datePublished` / `dateModified` (the usual WordPress SEO plugin route) and the first
  `<time datetime>`. Before 01.10.2026 only the meta tags were read, and the freshness row stayed
  empty for all three of our test pages.
