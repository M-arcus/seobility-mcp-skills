#!/usr/bin/env python3
"""Filters for the Seobility setup check.

Three of the calls this skill makes overflow the tool result on real projects and
get written to a file instead:

    list_keywords                      168,000 chars at 335 keywords
    get_rankings_keyword_suggestions   116,000 chars at   4 keywords (up to 500 rows)
    list_crawls                        up to 100 crawl rows

Never read those files into the conversation. Run the matching subcommand and read
the summary.

    python scripts/setup_check.py keywords    <file> [--room N] [--created YYYY-MM-DD]
    python scripts/setup_check.py suggestions <file> [--top N] [--min-rating N]
    python scripts/setup_check.py crawls      <file> [--page-limit N] [--budget-reached true|false]

<file> may be - to read the JSON from stdin.

Every subcommand prints a compact block meant to be read by the assistant, not
pasted into the report.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone


def load(path):
    """Read a saved tool result (or - for stdin). Accepts the {"data": ...} envelope or a bare payload."""
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def pct(part, whole):
    return 0.0 if not whole else round(100.0 * part / whole, 1)


def parse_time(value):
    """Parse a date or an ISO timestamp such as 2026-09-23T02:52:18+0200. None if unreadable."""
    value = (value or "").strip()
    if len(value) > 5 and value[-5] in "+-" and value[-4:].isdigit() and "T" in value:
        value = value[:-2] + ":" + value[-2:]  # +0200 -> +02:00 for Python before 3.11
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def days_since(value):
    parsed = parse_time(value)
    return None if parsed is None else (datetime.now(timezone.utc) - parsed).days


# --------------------------------------------------------------------------
# keywords - what the monitored set actually covers
# --------------------------------------------------------------------------

def cmd_keywords(args):
    rows = load(args.file)
    if not rows:
        print("MONITORED KEYWORDS: none. Ranking Monitoring is not set up for this project.")
        return

    total = len(rows)
    names = {r.get("name") for r in rows}
    engines = Counter(r.get("search_engine_name") for r in rows)
    localised = [r for r in rows if r.get("location")]

    # `rank` is an int when the keyword ranks and the boolean False when it does not.
    # bool is a subclass of int in Python, so `isinstance(rank, int)` is True for False
    # and silently counts every non-ranking keyword as ranking. Test for bool FIRST.
    def ranks(row):
        rank = row.get("rank")
        return isinstance(rank, int) and not isinstance(rank, bool)

    # `rank: false` on a row with ranking_fetched false means "never measured", not
    # "not in the top 100". Only fetched rows can rank nowhere.
    unfetched = [r for r in rows if r.get("ranking_fetched") is False]
    measured = total - len(unfetched)
    unranked = [r for r in rows if r.get("ranking_fetched") is not False and not ranks(r)]
    deep = [r for r in rows if ranks(r) and r["rank"] > 20]

    no_volume = [r for r in rows if not r.get("search_volume")]
    tagged = [r for r in rows if r.get("tags")]
    ai = [r for r in rows if r.get("ai_overview")]

    urls = Counter(r["best_ranking_url"] for r in rows if r.get("best_ranking_url"))

    print("MONITORED KEYWORDS")
    print("  rows                 %d" % total)
    print("  distinct keywords    %d" % len(names))
    if len(names) != total:
        print("  -> this is %d keywords tracked across %d search engines, NOT %d keywords."
              % (len(names), len(engines), total))
        print("     Report the distinct count. The quota is charged per row.")
    print("  search engines       %s" % dict(engines))
    print("  with a location      %d (%s%%)%s"
          % (len(localised), pct(len(localised), total),
             "  [the rest are national]" if len(localised) < total else ""))

    if args.room is not None:
        # The project's own ceiling is rows used + room left. It was 2000 on the test
        # account's plan; compute it rather than assume it holds on every plan.
        print("  room in this project %d more keywords (project ceiling: %d = %d used + %d free)"
              % (args.room, total + args.room, total, args.room))

    print("")
    print("COVERAGE")
    if args.created:
        age = days_since(args.created)
        if age is None:
            print("  project age          created date unreadable")
        else:
            print("  project age          %d days%s" % (age,
                  " - under 60: unranked keywords are context, not a gap" if age < 60 else ""))
    print("  ranking nowhere      %d (%s%% of %d measured) - rank is false: not in the top 100, so"
          % (len(unranked), pct(len(unranked), measured), measured))
    print("                       they produce no visibility and no movement to report")
    print("  positions 21-100     %d (%s%% of %d measured) - ranking, but beyond page two they"
          % (len(deep), pct(len(deep), measured), measured))
    print("                       produce almost no visibility")
    if unfetched:
        print("  never measured       %d - ranking_fetched is false, no data yet" % len(unfetched))
    if no_volume:
        print("  no search volume     %d - the provider has no measured volume (0 is a floor, not"
              % len(no_volume))
        print("                       proof nobody searches; deliberate long-tail looks like this)")
    print("  tagged               %d (%s%%)%s"
          % (len(tagged), pct(len(tagged), total),
             " - a low share means the set cannot be filtered by segment"
             if pct(len(tagged), total) < 50 else ""))
    print("  AI Overview present  %d (%s%%) of the tracked SERPs"
          % (len(ai), pct(len(ai), total)))

    print("")
    print("RANKING URLS")
    ranking_rows = len([r for r in rows if ranks(r)])
    print("  distinct URLs        %d carrying %d ranking keywords" % (len(urls), ranking_rows))
    if urls:
        spread = round(ranking_rows / float(len(urls)), 2)
        print("  keywords per URL     %s" % spread)
        if spread < 1.3:
            print("  -> almost no page carries more than one keyword. The set is broad and thin:")
            print("     fine for site-wide coverage, useless for judging a single page.")
        for url, count in urls.most_common(args.top):
            print("    %3d  %s" % (count, url))


# --------------------------------------------------------------------------
# suggestions - untracked demand, shortlisted
# --------------------------------------------------------------------------

def cmd_suggestions(args):
    rows = load(args.file)
    if not rows:
        print("KEYWORD SUGGESTIONS: none returned.")
        return

    reasons = Counter(r.get("reason") for r in rows)
    engines = Counter(r.get("search_engine") for r in rows)

    print("KEYWORD SUGGESTIONS (candidates that are NOT currently monitored)")
    print("  rows                 %d (no paging, no filter)" % len(rows))
    print("  reasons              %s" % dict(reasons))
    print("  search engines       %s" % dict(engines))
    print("  note: the suggestion engine can differ from the engines the project monitors.")
    print("        A Google.de suggestion for a project tracking Google.com is a market")
    print("        question, not a keyword question.")

    ranking = [r for r in rows if r.get("reason") == "alreadyranking"]
    print("")
    print("ALREADY RANKING BUT UNMONITORED: %d" % len(ranking))
    print("  'alreadyranking' means the domain appeared somewhere in that SERP. It does not")
    print("  mean the keyword is relevant, or that the position is any good. Read the")
    print("  shortlist before naming any of it, and never add keywords automatically.")

    kept = [r for r in ranking if (r.get("rating") or 0) >= args.min_rating]
    print("  rating >= %-3d        %d" % (args.min_rating, len(kept)))

    print("")
    print("  TOP %d BY RELEVANCE RATING" % args.top)
    for r in sorted(kept, key=lambda r: -(r.get("rating") or 0))[: args.top]:
        vol = r.get("search_volume")
        vol = "{:,}".format(vol) if isinstance(vol, int) else str(vol)
        print("    rating %3s  vol %9s  %s" % (r.get("rating"), vol, r.get("keyword")))

    print("")
    print("  TOP %d BY SEARCH VOLUME - sanity-check every one of these. Volume tracks badly"
          % args.top)
    print("  against relevance, and the head terms are usually somebody else's brand.")
    for r in sorted(ranking, key=lambda r: -(r.get("search_volume") or 0))[: args.top]:
        vol = r.get("search_volume")
        vol = "{:,}".format(vol) if isinstance(vol, int) else str(vol)
        print("    rating %3s  vol %9s  %s" % (r.get("rating"), vol, r.get("keyword")))


# --------------------------------------------------------------------------
# crawls - recency, and whether the crawl reached the whole site
# --------------------------------------------------------------------------

def cmd_crawls(args):
    rows = load(args.file)
    if isinstance(rows, dict):
        rows = rows.get("crawls", [])
    done = [c for c in rows if c.get("status") == "done"]

    if not done:
        print("CRAWLS: no completed crawl. The audit half of every skill has nothing to read.")
        return

    done.sort(key=lambda c: c.get("end_time") or "", reverse=True)
    newest = done[0]

    def score(crawl):
        return (crawl.get("score_percent") or {}).get("overall")

    def regular(crawl):
        return (crawl.get("completion_reason") in (None, "regular")
                and not crawl.get("is_stopped") and (crawl.get("pages_crawled") or 0) > 0)

    # Baseline = the last regular, completed crawl. Stopped and 0-page crawls never count.
    # A crawl with data_removed keeps its row figures (fine for the scope test) but has no
    # audit data left, so audit deltas need one whose data is intact.
    older = done[1:]
    baseline = next((c for c in older if regular(c)), None)
    delta_base = next((c for c in older if regular(c) and not c.get("data_removed")), None)
    age = days_since(newest.get("end_time"))

    print("CRAWLS")
    print("  completed crawls     %d (first page of list_crawls)" % len(done))
    print("  newest               %s   %s pages, score %s"
          % (newest.get("end_time"), newest.get("pages_crawled"), score(newest)))
    if age is not None:
        print("  newest crawl age     %d days%s" % (age, " - over 30: stale" if age > 30 else ""))
    if not regular(newest):
        print("  -> the newest crawl is stopped or empty: its data is partial. Say so and do not")
        print("     build a plan on it.")
    if baseline is None:
        print("  previous regular     none - no regular completed crawl to compare against, so every")
        print("                       audit delta on this project is meaningless")
    else:
        skipped = older.index(baseline)
        print("  previous regular     %s   %s pages, score %s%s"
              % (baseline.get("end_time"), baseline.get("pages_crawled"), score(baseline),
                 "   (%d newer stopped/empty crawl(s) skipped)" % skipped if skipped else ""))
        if delta_base is not baseline:
            print("  audit-delta baseline %s"
                  % ("%s   (data_removed crawls skipped)" % delta_base.get("end_time")
                     if delta_base else "none - every regular crawl before it has data_removed"))

    print("")
    print("REACH")
    if args.budget_reached == "true":
        print("  TRUNCATED: get_site_audit_overview says the crawl budget was reached. The newest")
        print("  audit describes part of the site. Every count and score on it is a fraction.")
    elif args.budget_reached == "false":
        print("  budget reached: no (get_site_audit_overview). Trust this over the numbers below.")
    else:
        print("  budget flag not supplied. Read get_site_audit_overview -> special_checks."
              "was_crawling_budget_reached")
        print("  and pass it as --budget-reached; the numbers below are only a hint.")
    for crawl in done[:3]:
        crawled = crawl.get("pages_crawled") or 0
        found = crawl.get("pages_found") or 0
        flags = []
        if args.page_limit and crawled >= args.page_limit * 0.98:
            flags.append("AT THE %d PAGE LIMIT" % args.page_limit)
        # A handful of uncrawled pages is normal (redirects, blocked URLs). Only a real
        # gap between what the crawler found and what it fetched is a setup finding.
        # pages_found is uncapped and shown nowhere in the account: a hint, never a quote.
        gap = found - crawled
        if found and gap > 100 and gap / float(found) > 0.02:
            flags.append("pages_found is well above pages_crawled (internal hint, do not quote)")
        if crawl.get("is_stopped"):
            flags.append("STOPPED EARLY")
        if crawl.get("completion_reason") not in (None, "regular"):
            flags.append("completion_reason=%s" % crawl.get("completion_reason"))
        if crawl.get("data_removed"):
            flags.append("data_removed")
        print("  %s  crawled %s%s"
              % (crawl.get("end_time"), crawled,
                 "   <- " + "; ".join(flags) if flags else ""))

    # A changed page set makes the score delta unreadable. Compare crawled, indexable and
    # found: an at-limit crawl keeps pages_crawled flat while the rest of the slice moves.
    if regular(newest) and baseline:
        changes = []
        for key in ("pages_crawled", "pages_indexable", "pages_found"):
            now, before = newest.get(key) or 0, baseline.get(key) or 0
            if before and now and abs(now - before) / float(before) > 0.25:
                changes.append("%s %s -> %s (%+d%%)"
                               % (key, before, now, round(100.0 * (now - before) / before)))
        if changes:
            print("")
            print("  WARNING: the page set changed since the last regular crawl: %s." % "; ".join(changes))
            print("  The score moved %s -> %s across that change. Either the crawl scope changed or"
                  % (score(baseline), score(newest)))
            print("  the site itself did (check get_crawler_settings before saying which). A score")
            print("  delta over two different sets of pages is not like-for-like. Do not report it")
            print("  as a regression, and do not let another skill inherit it as a finding.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("keywords", help="coverage summary from a saved list_keywords")
    p.add_argument("file")
    p.add_argument("--room", type=int, default=None,
                   help="available_for_venture from get_rankings_keyword_limit")
    p.add_argument("--top", type=int, default=5,
                   help="how many of the busiest ranking URLs to list")
    p.add_argument("--created", default=None,
                   help="created_date from list_projects; prints the project age")
    p.set_defaults(func=cmd_keywords)

    p = sub.add_parser("suggestions",
                       help="untracked demand from a saved get_rankings_keyword_suggestions")
    p.add_argument("file")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--min-rating", type=int, default=40)
    p.set_defaults(func=cmd_suggestions)

    p = sub.add_parser("crawls", help="recency and reach from a saved list_crawls")
    p.add_argument("file")
    p.add_argument("--page-limit", type=int, default=None,
                   help="max_pages.limit from get_crawling_limits")
    p.add_argument("--budget-reached", choices=["true", "false"], default=None,
                   help="special_checks.was_crawling_budget_reached from get_site_audit_overview")
    p.set_defaults(func=cmd_crawls)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
