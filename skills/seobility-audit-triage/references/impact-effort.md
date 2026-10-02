# The impact x effort reference

What a fix costs, and therefore what gets planned first. The one file in the skill that does not
come out of the API.

**Maintained by Seobility. Revised 23.09.2026, fifth pass: every fix shape aligned to its Seobility
Help Center article (37 rows changed or added, two URL reports moved from `none` to a low-priority
`page`, one report read the wrong way round corrected).**

The first version was authored from experience. The second checked each uncertain row against live
report payloads — and overfitted: a class derived from one blog was written down as if it held
everywhere. The third pass separates what is true about a **fix mechanism** from what is true about
**one site**, and turns the site-dependent half into rules the skill evaluates per run. The fourth
pass made the default of every rule the expensive branch, as the third pass had claimed but not
done for three of the six.

## The two axes

**Impact is not authored here.** Seobility carries a per-issue severity weight and it is stable
across projects: `total_impact / count` from `get_site_audit_problems`. Verified identical on three
projects for every report appearing on more than one.

`importance` and `priority` are **not** stable and must never order anything: both move with the
affected count, and `get_report_meta` returns a third value again for the same report and crawl.

**Effort is authored here**, because nothing in the crawl knows whether 939 missing H1s are one
template or 939 hand edits.

## How a class is derived

Three questions, in this order.

**1. Where does the defect live?** A setting, a template, a repeated structured field, a link
target, or prose. This sets the floor on how cheap the fix can be.

**2. Is the new value derivable, or is it a decision?** A link to a redirect has a knowable correct
target — follow the redirect. A title that is too long does not: someone decides what to cut.
Derivable is `bulk`; a decision per instance is `page` or `editorial`, however mechanical the edit
looks. This is what moved `image-alt-attribute-problems` out of `bulk` — an alt text is written,
not derived, on every site there has ever been.

**3. Is the answer the same on every site?** For about two thirds of the reports, yes: gzip is a
server setting everywhere, a broken hreflang block is one template everywhere, a typo is one edit
everywhere. For the rest it is not, and pretending otherwise is the mistake this pass corrects.
Those rows carry a **rule** instead of a class, and the skill resolves it from the clustering.

## Every class in this file is a default, not a verdict

Even the stable two thirds describe a typical site. What a fix costs on *this* site depends on
things the crawl cannot see: which parts come out of a template, what the CMS lets someone edit in
bulk.

**Resolving that is the skill's job, not the user's.** Most people cannot say whether their H1s are
generated — they did not build the theme. The skill works it out from reach, path clustering, the
flagged values and, where those are ambiguous, the pages themselves. `triage.py cluster --indexed`
returns the verdict. Only what stays unresolved is stated as an assumption, next to the group it
affects, so the user can overturn it if they do happen to know. Then
`triage.py rank --assume <report>=<class>` applies the correction.

**Reach only promotes what a template can hold.** High reach turns a heading, a title frame or an
oversized layout into one change. It does not do that for a value a person writes per instance:
every `editorial` report, plus `image-alt-attribute-problems` and the two anchor-text reports.
Missing alt texts on 80% of pages are 80% of the pages to write, unless the flagged element repeats
on every page (a logo, an icon), and `cluster` says so instead of calling it systematic.

What this file must not become is a questionnaire. Handing a user forty-five classes to confirm
gives them the work the skill exists to do.

## The classes

| Class | What it means | Cost model |
|---|---|---|
| `config` | One setting — server, robots.txt, sitemap generator, or the SEO plugin | flat 1 |
| `template` | One change in a layout, theme or component covers every affected page | flat 1 |
| `bulk` | Mechanical per instance, and the correct new value is derivable | 1 + n/50 |
| `page` | One short edit per page, but someone decides what it says | n x 0.1 |
| `editorial` | Writing or a judgement call per page | n x 0.5 |
| `inspect` | **Not scored.** Cost unknowable from the API; one sample page decides it |
| `none` | **Not scored.** A true finding with no sensible fix. Reported with its reason, never planned |

Plan order is `total_impact / cost`. Nothing else enters the ordering.

## The count is often not the cost driver

Before applying a cost model, check what the report is actually counting. On several reports the
quantity that drives effort is a different number, and it is usually much smaller.

| Report | Counts | Cost actually driven by |
|---|---|---|
| `url-dynamic-parameters` | URLs, which on a faceted shop can be six figures | **Distinct parameters** — typically three to fifteen |
| `title-duplicates`, `description-duplicates` | Affected pages | **Duplicate groups** — `pagination.total` in the report |
| `internal-link-targets-on-redirects` | Already distinct targets | The count, which is also the number of search-and-replace pairs |
| `image-alt-attribute-problems` | Pages | **Images**, which is more than pages |
| `pages-with-duplicate-text-content` | Text blocks | The articles that share real paragraphs, which only the rows show |

Where the two differ, say both in the plan. "480,000 URLs" and "nine parameters to decide about"
are the same finding and produce opposite reactions.

## The rules for site-dependent reports

These seven rows do not have a fixed class. The skill resolves each from evidence it already has —
the clustering, the affected ratio — and says which branch it took.

**Unresolved, every rule defaults to `page`** (or to `config` where both branches are `config`).
The default has to be the branch that neither dismisses a real problem nor scores a big job as a
one-line fix. `none` dismisses; `config` and `template` cost a flat 1 and would put an unchecked
report at the top of the plan. `page` keeps the report visible at an honest price until the
evidence moves it.

### What are the affected pages? (`pages-with-high-page-depth`)

| If the deep pages are | Class | Why |
|---|---|---|
| Author archives, tag pages, paginated listings | `none` | They are deep because that is what they are. Restructuring for them buys nothing |
| Products, articles, or any page meant to rank | `template` | A real problem and a real project. Pagination tunnels can push products past depth 100; replacing them with category links and internal linking is a known, large, worthwhile job |
| Not yet resolved | `page` | The default. Keeps the report in the plan without dismissing it or promising a one-change fix |

The class depends on what the pages are — which the clustering already tells you. On a blog, the
deep pages are usually archives; on an ecommerce catalogue, depth beyond about five needs deliberate
internal linking to stay indexed at all, and under-crawling is common.

### How much of the site is affected? (`pages-with-large-file-size`)

| If | Class | Why |
|---|---|---|
| A small subset of pages | `page` | Individual pages with embedded media or a runaway component |
| Most of the crawled set | `config` or `template` | The cause is the page builder, inline base64 assets, or missing compression and minification — one build-level fix, not N edits |

The general causes are the same everywhere: inline CSS and JavaScript, base64 images and fonts,
and page-builder markup. What differs is whether they sit in the template or in a few pages, and
the ratio answers that.

### Are the duplicates generated or written? (`title-duplicates`, `description-duplicates`)

| If the affected pages | Class | Why |
|---|---|---|
| Are paginated or filtered variants of one listing | `config` | One variable in the SEO plugin's title template adds the page number. Not a code change and not N edits |
| Are one page reachable under several URLs (parameters, variants) | `config` | The Help Center's most common cause: a canonical to the main URL, set once |
| Are distinct pages that happen to share a title | `page` | Each needs its own title written |
| Not yet resolved | `page` | The default |

The report hands you the evidence without a second call: each row is a title text with its `pages`
array, so the URLs are already grouped.

### Is the defect in the template or in the content? (`heading-h1-problems`)

| If the affected URLs | Class |
|---|---|
| Cluster on one path pattern above the promotion threshold | `template` |
| Spread across the site | `page` |

Default `page`, so an unresolved report is not under-costed.

### How many parameters, not how many URLs? (`url-dynamic-parameters`)

| If | Class | Why |
|---|---|---|
| A handful of parameters, no faceted navigation | `config` | Decide per parameter: canonicalise, block in robots.txt, or leave |
| Faceted navigation on a catalogue | `config`, but say it is a project | The mechanism is the same — robots.txt for worthless parameters, canonicals for low-value combinations, selective indexing for high-demand ones — but the decisions are strategic and belong with whoever owns the catalogue |

Never plan this against the URL count. Ten thousand products can generate half a million crawlable
URLs from a dozen parameters.

### Do the targets share one pattern? (`internal-link-targets-on-redirects`)

| If the redirect targets | Class | Why |
|---|---|---|
| Share one path pattern (a navigation link with a trailing slash, an old image or asset path, http instead of https) | `template` | The links are generated. One change where they are built fixes every one of them |
| Are mixed, one-off URLs | `bulk` | One search-and-replace pair per target, the default |

A row's `page` is the redirecting URL, not an affected page, so reach does not apply. Verified on
a wiki (24.09.2026): 375 targets were the home link with a trailing slash plus every article image
linking to an old image path - two changes. `triage.py cluster` says `ONE RULE` for this case.

### Undecidable from the API (`pages-with-duplicate-paragraphs`)

`inspect`, on every site. The report means the same paragraph repeated **on one page** (Help
Center), not overlap between pages. A box the layout outputs twice is one template change; text
repeated inside an article is an edit per page. The MCP does not return the paragraph text — three
routes tried, all empty — but Details in the app shows it: one affected page decides.

## The table

Rows marked `~` are resolved by the rules above; their class is the unresolved default, so an
unresolved plan over-costs rather than under-costs. Rows marked `*` split into sub-types with
different fixes.

### Blocking — always first, whatever the score says

| Report | What a row is | Class | Fix shape |
|---|---|---|---|
| `pages-broken` | A URL the crawler could not fetch | `bulk` | Fix where it comes from: for a 404, correct or remove the internal links and add a 301 if the URL moved. Failures and timeouts (the crawler waits 10 s) usually mean a slow server or a blocked Seobility bot, a server setting, not N fixes. No status code on a report that was empty last time: re-crawl first, and if the pages come back, check response times and whether the bot is blocked |
| `redirect-target-problems` | A redirect whose target cannot be reached | `bulk` | Change the links on the linking pages to point straight at a working page. Only where that is impossible, fix the redirect or its target |
| `internal-link-targets-on-redirect-loops` | An internal link into a loop | `bulk` | Follow the chain, break the loop and link straight to the final page. Loops can also come from canonicals that point back, not only from redirect rules |
| `error-output-problems` | A PHP or framework error printed into the HTML | `bulk` | Fix the error itself first, then switch off error display on the live site and log errors on the server. Visible errors cost trust and reveal the software in use, a security risk |
| `canonical-link-target-problems` | A canonical pointing at a non-200, redirected or foreign URL | `page` | Several different jobs — split by sub-type before planning, see below. Every page needs exactly one canonical, to itself or the original, pointing at a URL that loads without error or redirect |

**`canonical-link-target-problems` is several jobs.** Four sub-types verified on 32 live findings;
the Help Center names six, adding an empty canonical tag (usually the theme or plugin: `template`)
and a target that is not a page, such as an image (`bulk`). The sub-type is in each row's
`problems[]` and `filters` is empty for this report, so the rows have to be read.

| Sub-type | Class | Fix shape |
|---|---|---|
| `canonical_multiple` | `template` | Two canonical tags on one page — almost always the theme and the SEO plugin both emitting one. Turn one off |
| `canonical_badtarget_httpstatus` | `bulk` | The canonical points at a 404 or a redirect. Repoint it at the live URL |
| `canonical_badtarget_targetisredirects` | `bulk` | The canonical points at a URL that redirects. Point it at the final URL - the target is derivable |
| `canonical_differentdomain` | `page` | The canonical hands the page to a foreign domain. Each is its own decision |

### Technique and meta

| Report | What a row is | Class | Fix shape |
|---|---|---|---|
| `title-problems` | One page, sub-type in `problems` | `page` | Rewrite the title for the named sub-type: at most the pixel limit the row carries (`pixel_length_max`; a 60-character title can exceed it, so quote pixels, not characters; an overshoot of a few pixels is one word), 2 to 3 keywords in a natural phrase, the most important first, unique across the site, not changed too often. The free SERP Snippet Generator shows the result. Pull the sub-type split first |
| `meta-description-problems` | One page | `page` | Write an accurate summary with a call to action, relevant keywords (Google shows them in bold), at most the pixel limit the row carries (`pixel_length_max`, about 1,000 px; even 1 px over risks truncation, usually one word), unique per page. Several descriptions on one page is a theme or plugin conflict, one change. Affects the click, not the position - say so |
| `title-duplicates` | A title text, with its pages | `page` | Resolved by rule: paginated listings are one setting in the SEO plugin; one page reachable under several URLs (parameters) needs a canonical, one setting; distinct pages need their own title |
| `description-duplicates` | A description text, with its pages | `page` | Same rule as titles. On large sites a description template for less important pages is an accepted cheap fix |
| `heading-h1-problems` | One page, sub-type in `problems` | `page` | Exactly one H1 per page, at most 120 characters, specific rather than generic, with the main keyword, and different from the title. Several H1s on many pages is almost always the theme: template. Resolved by clustering |
| `heading-problems` | One page, sub-type in `problems` | `page` | Five sub-types: empty, wrong order or skipped levels, duplicate, none, too many. Headings in sidebars, footers, widgets and forms are one template change - headings belong to the content only. Split by sub-type and cluster |
| `strong-bold-problems` | One page, sub-type in `problems` | `page` | Sub-types: too many tags, empty tags, bold passages over 70 characters, the same words bolded repeatedly. Little SEO benefit; the aim is only to avoid over-optimisation. Empty tags clustered across pages come from the editor or theme: template. Backlog unless free |
| `image-alt-attribute-problems` | One page with images missing alt | `page` | One alt text per image is written, not derived. Bulk *work*, not a bulk *fix* — never promise a script. Cost scales with images, not pages. Exception: an image on nearly every page (the header logo) is one template edit - give it a descriptive alt; `aria-hidden` may stay. An empty alt counts as missing for SEO |
| `pages-with-large-file-size` | One oversized HTML document | `page` | Flags HTML over 0.5 MB; over 5 MB is not analysed at all. Move inline CSS and JavaScript into files, stop inlining SVGs and base64 assets, switch off CMS or theme features that bloat the code, enable compression. Resolved by ratio - a few pages are page edits, most of the site is a build fix |
| `missing-gzip` | Compression off | `config` | Switch compression on at the server |
| `pages-with-charset-encoding-problems` | One page with a broken or conflicting charset | `config` | Declare the charset in the server's HTTP header (UTF-8) and keep the meta tag in the page head identical. Fixing only the head can leave the mismatch in place |
| `pages-with-language-mismatch` | Declared language differs from the text | `template` | Correct the `lang` attribute, usually one template expression |
| `pages-with-slow-server-response-times` | One slow response | `config` | Caching and preloading first, then hosting or a slow query. Slow is measured against the site's own average, from Germany, HTML only - not page speed. A cold cache can make a first crawl look slow: warm it and re-crawl before planning. When at least half the count of this or the medium report is new in this crawl, re-measure both before planning anything |
| `pages-with-medium-server-response-times` | One response between 0.5 and 1 s | `config` | Same work as slow responses, lower urgency. HTML response only, not page speed. Re-measured together with slow responses (same server, same crawl) |
| `pages-with-framesets` | A frameset document | `page` | Replace the frameset |
| `url-dynamic-parameters` | A URL with parameters | `config` | Resolved by rule — decide per parameter, never per URL |
| `url-session-id` | A session id in the URL | `config` | Move the session out of the URL. Unlike the other URL rows this is worth doing: session ids create infinite crawlable variants |
| `url-too-many-subdirectories` | A URL more than 5 folders deep | `page` | Low priority. For new pages: 1 to 2 levels, from general to specific, important pages near the root - a URL scheme decision. Existing URLs change only with a 301, best during a relaunch. Making every folder level load as its own overview page needs no URL change |
| `url-too-long` | A URL over 140 characters | `page` | Low priority: the reason is a cut-off in the Google snippet and readability, not rankings. For new pages, short slugs with the keyword first (slug and permalink settings). Existing URLs change only with a 301 |
| `schema-validation` | A page whose structured data has property errors, severity per row (`critical` or `tip`) | `page` | No Seobility weight, so it cannot be scored, but the rows are real. Read `filters` (`get_report` with `limit: 1`): only `schema_recommended_missing` keys means optional tips, so not worth changing (`--assume schema-validation=none`). Otherwise fix the named property per sub-type. A `critical` on a `{"@id": …}` reference the validator cannot resolve is a warning, never critical: read the page's JSON-LD first |
| `file-sources-broken` | A CSS/JS/image the page requests and does not get | `bulk` | For 404s and invalid URLs, correct or remove the reference. Failures, timeouts and 403s usually mean a slow server or a blocked Seobility bot - a server setting, not a fix per file |
| `file-sources-mixed-content-on-https` | An http asset on an https page | `bulk` | Switch the asset to https — one character per URL |
| `file-sources-problems` | An asset with a problem, sub-type in `problems` | `bulk` | Split by sub-type: a redirect means repointing the asset (bulk); missing or wrong content type and missing compression for text files from 1 KB are server settings (config); load time over 1 s or large files (images over 2 MB, CSS/JS over 0.5 MB) mean optimising the files |
| `pages-with-too-many-file-sources` | One page loading many assets | `template` | Bundle at the template level |
| `pages-blocked-from-ai-search` | A page AI search crawlers may not fetch | `config` | Check robots.txt and firewall rules for the AI crawlers. Unblock them unless keeping the site out of AI answers is a deliberate decision - say which pages are affected either way |
| `pages-with-unsupported-file-type` | A URL serving a file the crawler cannot analyse (PDF, download) | `none` | Zero weight and not a defect: PDFs and downloads are expected. Say so under not worth changing, with the count. It is also the difference between `pages-non-indexable` and crawled minus indexable |
| `url-possible-errors` | A URL that may be a mistake | `page` | Seobility does not score it. Check whether each URL is intended; where it is a mistake, correct the internal links that point to it |

### Structure

| Report | What a row is | Class | Fix shape |
|---|---|---|---|
| `internal-link-targets-on-redirects` | A redirect target, with the pages linking to it | `bulk` | Repoint the links at the final URL. Resolved by rule: targets sharing one pattern (a trailing slash on a navigation link, an old asset path) are one change where the links are built; mixed targets are one search-and-replace pair each |
| `external-link-target-problems` | An outbound link that is broken, redirected or parked | `inspect` | Re-request every flagged URL with a browser user agent first: 503, `down`, 202 and even a 404 can be alive, and results are cached for a few days. Only a live 404/410 or a DNS failure is dead; a 301 is a link update. Then plan the confirmed ones as `bulk` on their own count, repoint or remove. Owned by whoever maintains the page, not by dev |
| `link-anchor-text-problems` | A link with an empty, generic or overlong anchor | `page` | Sub-types: empty, generic ("here", "read more"), over 120 characters, image link without alt text. Give the link a text that names the target; keyword anchors are fine internally. Generic labels and logo links clustered across pages come from the template: one change |
| `link-anchor-text-duplicates-for-different-pages` | One anchor used for several targets | `page` | One anchor pointing at several pages tells search engines they share a topic, which can end in cannibalisation. Give every target its own anchor. Generic labels on listings ("show more", "read more") are a template fix: put the target's title into the link text. A descriptive keyword whose target depends on the section is by design, not a defect. Fixed credit lines can wait. Weight 50 |
| `pages-with-many-internal-links` | A page with more than 400 links, or far above the site average | `template` | Reduce the links in the component that generates them, or split very large pages. An HTML sitemap is the exception: set it to noindex instead of cutting links |
| `pages-with-few-internal-links` | A page with few outgoing internal links | `page` | The page itself links to little: usually missing navigation or related links, or an empty list with nothing to show. Add navigation or related links (template, if the pages share a type), fill or remove empty pages and the links to them. Weight 35 |
| `pages-with-high-page-depth` | A page far from the start URL | `page` | Resolved by rule — archives are noise, buried products are a project |
| `alternate-link-target-problems` | A broken hreflang target | `template` | Correct the hreflang block. One template, every language |
| `sitemaps-issues` | A problem in a sitemap file | `config` | Fix the sitemap generator. No Seobility weight, so it cannot be scored — judge it yourself |
| `sitemaps-pages-only-found-in-sitemaps` | A URL in the sitemap nothing links to | `page` | First check the crawl limit - a limit too low for the site makes this report wrong. Then link relevant pages internally and remove outdated URLs from the sitemap. A decision per URL |

### Content

| Report | What a row is | Class | Fix shape |
|---|---|---|---|
| `pages-with-keyword-cannibalization` | Two of the site's pages competing | `editorial` | Three options: merge, redirect one to the other, or give both clearly different content. Check first whether the pair is a near-duplicate (duplicate content fixes) or two thin pages with the same headings (thin content, not cannibalisation). Two language versions of one page do not compete, and two articles on related but distinct terms are not merge candidates: both go under not worth changing. Weight 30 |
| `pages-missing-the-title-content-in-the-body` | The title's words do not appear in the text | `editorial` | Compare title and text: where the text is right and the title is weak, fix the title instead. The check ignores synonyms and inflected forms, so many flagged pages need nothing - look before planning all of them. The missing words are bold in each row's `formatted`: when they are frame words the title adds to every page ("Definition", "explained"), plan it as later. Weight 25 |
| `pages-missing-the-h1-content-in-the-text` | Same for the H1 | `editorial` | As above, and the H1 should differ from the title |
| `pages-with-very-little-text-content` | A page under 500 words | `editorial` | Often fine: galleries, landing pages, quick answers. Before expanding, compare with the length of the top 10 results for the page's keyword (TF*IDF tool). Expand or merge only where the competition is clearly more thorough |
| `pages-with-little-text-structure` | A page with fewer than 3 text blocks (100+ characters each) | `page` | Split by the word count: long text in few blocks needs paragraphs and headings; short pages need expanding, or nothing; galleries and result lists can be ignored |
| `pages-with-duplicate-paragraphs` | One page repeating the same paragraph | `inspect` | The same paragraph appears several times on one page. Open Details in the app for one affected page: it shows the paragraph and how often it appears. A box the layout outputs twice is one template change; text repeated inside the article is an edit per page. Cookie banners are ignored; `data-nosnippet` excludes a block |
| `pages-with-duplicate-text-content` | A text block, with the pages it appears on | `editorial` | Read the rows and sort them. Long teasers on the homepage, category or overview pages compete with the article itself: shorten the excerpt length, one setting. The same paragraphs across several articles are a rewrite per article. Author bios and credit lines can wait. Site-wide disclaimers and cookie banners are already excluded by Seobility. Never plan against the count, never drop the report |
| `pages-with-identical-page-duplicates` | Two URLs serving the same page | `config` | Canonicalise or redirect one of them. Weight 50 |
| `duplicate-content-pages` | A page duplicating or containing another | `editorial` | Find the technical cause first - it rarely is text written twice: www and non-www (one site-wide 301), parameter variants (canonical), overlapping tags and categories, full articles on category pages (show a short excerpt). Merge or differentiate only pages that really were written twice |
| `pages-without-text-content` | A page with no text at all | `page` | Check it should be indexable at all before writing anything for it |
| `pages-with-typos` | One page with flagged spellings | `page` | Correct them. Frequently product names and jargon — check before mass-correcting |
| `pages-with-placeholder-text` | Lorem ipsum in production | `page` | Replace it. Rare, embarrassing, cheap |
| `pages-with-very-much-text-content` | A page over 4,000 words | `editorial` | Not a problem in itself. Compare with the length of the top 10 results (TF*IDF tool) first. If the page lacks focus, split it into articles and link them; otherwise structure it with headings and a table of contents with jump links. Start with the longest and those that already rank |
| `pages-without-keyword-optimization` | No keyword focus detected | `editorial` | Judgement call per page. Backlog unless the page is commercially important |

## What is still uncertain, and what would settle it

| Row | The doubt | What would settle it |
|---|---|---|
| `pages-with-large-file-size` | The ratio threshold between "a few pages" and "the template". Set at a third, from reasoning | Crawls of two or three page-builder sites |
| `pages-without-keyword-optimization` | Whether this fires often enough to be worth a row at all — zero findings on all test projects | Any crawl where it is non-zero |
| `url-session-id` | Ranked above the other URL rows because session ids create infinite variants, a crawl problem rather than a cosmetic one | A site that actually has them |
| The four cost constants | `n/50`, `n x 0.1`, `n x 0.5`, and the 60% clustering threshold are conventions, not measurements | Timing two or three real fix rounds |

Nothing on this list is likely to top a plan, and none of it blocks the skill.

## What this table deliberately does not do

It does not rank the reports. The ranking is the score, and the score depends on counts that change
with every crawl.

It does not carry hours. The cost model is relative and exists only to order the plan. "605 link
repoints take thirteen hours" is a number we cannot stand behind.

## Sources for the site-independent claims

**The Seobility Help Center is the primary source** for what each report means and how it is
fixed: one article per report, mapped in `help-center.md`. Every fix shape above was checked
against the English article on 23.09.2026. Where a row and its article disagree, the article is
right and the row is a bug. The sources below only back claims the articles do not make.

- Faceted navigation and parameter handling — [Search Engine Journal](https://www.searchenginejournal.com/technical-seo/faceted-navigation/), [Oncrawl](https://www.oncrawl.com/technical-seo/managing-faceted-navigation-scale/)
- Click depth on large catalogues — [Portent's pagination experiment](https://portent.com/blog/seo/pagination-tunnels-experiment-click-depth.htm), [GoFish Digital](https://gofishdigital.com/blog/crawl-depth-audit-optimization-guide/)
- The risk of changing established URLs — [Search Engine Land](https://searchengineland.com/change-url-seo-389209), [Sitebulb](https://sitebulb.com/resources/guides/beware-considerations-and-consequences-of-changing-established-urls/)
- HTML size causes and fixes — [Search Engine Journal](https://www.searchenginejournal.com/page-size-seo/420828/)
- Duplicate titles on paginated archives — [Yoast](https://yoast.com/help/how-do-i-fix-duplicate-meta-tags/)
- Site-wide internal link updates — [WPBeginner](https://www.wpbeginner.com/plugins/how-to-update-urls-when-moving-your-wordpress-site/)
