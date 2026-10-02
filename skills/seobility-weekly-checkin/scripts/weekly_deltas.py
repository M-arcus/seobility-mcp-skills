#!/usr/bin/env python3
"""Filter the two Seobility payloads that overflow a tool result, for a weekly check-in.

Both of these come back too large to read into context on any real project:

    get_rankings_winners_and_losers(project_id, timescale="weeks")   -> rankings mode
    get_backlinks_new / get_backlinks_lost(project_id)               -> backlinks mode

Run this against the saved file instead of reading it.

    python weekly_deltas.py rankings <winners-losers.json> [--limit 8] [--floor 1.0]
    python weekly_deltas.py backlinks <new.json> [--lost lost.json] [--days 7]
    python weekly_deltas.py overview <rankings-overview.json>

Any file argument may be "-" to read the JSON from stdin (one "-" per run).

Nothing here is a judgement. The script filters, groups and orders; the report is written
from what it prints.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# --- field quirks, all verified against live payloads -------------------------------------
# rank        : int, or the string "-/-" when the keyword left the tracked range
# rank_change : int, or "new" (first ranking) / "out" (dropped out)
# search_volume is NOT in this payload. visibility_delta is the only impact measure here.

def rank_of(row):
    r = row.get("rank")
    return r if isinstance(r, int) and not isinstance(r, bool) else None


def change_of(row):
    c = row.get("rank_change")
    return c if isinstance(c, int) and not isinstance(c, bool) else None


def change_label(row):
    c = row.get("rank_change")
    if isinstance(c, str):
        return c.upper()
    return f"{c:+d}" if isinstance(c, int) else "?"


def load(path):
    """Read a saved tool result.

    A large MCP result lands in one of two envelopes, and which one you get is not
    something the run controls: a plain JSON object, or a list of content blocks
    [{"type": "text", "text": "<the JSON, as a string>"}]. Unwrap the second.
    """
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    while isinstance(payload, list) and payload and isinstance(payload[0], dict) \
            and "text" in payload[0] and "data" not in payload[0]:
        payload = json.loads(payload[0]["text"])
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload


def parse_num(value):
    """A number that may arrive as a locale-formatted string ("10,366.7", "1.581,0"). None if not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    t = re.sub(r"[\s%+]", "", value)
    if not re.fullmatch(r"-?[\d.,]+", t):
        return None
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
    elif "," in t:
        dec = "," if not re.fullmatch(r"-?\d{1,3}(,\d{3})+", t) else "."
    else:
        dec = "."
    t = t.replace(".", "").replace(",", ".") if dec == "," else t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def suspect_reasons(rows):
    """Row id -> reasons a ranking row is 'not confirmed' (SKILL.md: check the ranking data).

    Only what the winners/losers payload itself can show: a move of 30+ places, and rows that
    belong to a mass "new"/"out" block (SERP flips) -- 20+ such rows making up 40%+ of all movers.
    The rest of the gate (own URL twice in a SERP, list_keywords vs. the keyword's SERP snapshot, date_added) needs a call.
    """
    out = {}
    flips = [r for r in rows if r.get("rank_change") in ("new", "out")]
    mass = len(flips) >= 20 and len(flips) >= 0.4 * len(rows)
    for r in rows:
        why = []
        c = r.get("rank_change")
        if isinstance(c, int) and not isinstance(c, bool) and abs(c) >= 30:
            why.append("moved 30+ places in one check")
        if mass and c in ("new", "out"):
            why.append("part of a mass new/out block")
        if why:
            out[id(r)] = why
    return out


def short(url, width=52):
    if not url:
        return "-"
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return url if len(url) <= width else url[: width - 1] + "..."


# --- rankings -----------------------------------------------------------------------------

def rankings(args):
    data = load(args.file)["data"]
    winners, losers = data.get("winners", []), data.get("losers", [])
    rows = winners + losers
    if not rows:
        print("Empty payload: no winners and no losers.")
        print("This does NOT yet mean a quiet week. An empty result and a project with no")
        print("monitored keywords look identical here. Check get_keyword_count(project_id)")
        print("before writing either sentence.")
        return

    engines = Counter(r.get("search_engine_name") for r in rows)
    kept = [r for r in rows if abs(r.get("visibility_delta") or 0) >= args.floor]
    dropped_out = [r for r in losers if r.get("rank_change") == "out"]
    entered = [r for r in winners if r.get("rank_change") == "new"]

    print(f"Movers: {len(winners)} up, {len(losers)} down, {len(rows)} total")
    print(f"Search engines in payload: {dict(engines)}")
    print(f"Visibility: {sum(r['visibility_delta'] for r in winners):+.0f} from gains, "
          f"{sum(r['visibility_delta'] for r in losers):+.0f} from drops, "
          f"net {sum(r['visibility_delta'] for r in rows):+.0f}")
    print(f"Below the noise floor (|visibility delta| < {args.floor}): "
          f"{len(rows) - len(kept)} of {len(rows)} rows. Not shown.")
    sus = suspect_reasons(rows)
    if sus:
        print(f"DATA GATE: {len(sus)} of {len(rows)} rows are NOT CONFIRMED (marked ? below): "
              f"{'; '.join(sorted({w for ws in sus.values() for w in ws}))}. "
              f"Never a job, never persistent.")
    top = max(rows, key=lambda r: abs(r.get("visibility_delta") or 0))
    print(f"Cross-check the top mover before quoting it: get_keyword_overview keyword_id "
          f"{top.get('keyword_id')} ({top['name'][:40]}, {top['visibility_delta']:+.1f})")
    print()

    def table(title, subset, reverse):
        if not subset:
            print(f"{title}: none above the floor.\n")
            return
        subset = sorted(subset, key=lambda r: r["visibility_delta"], reverse=reverse)[: args.limit]
        print(title)
        print(f"{'keyword':<32} {'pos':>5} {'chg':>5} {'vis':>8} {'vis d':>8}  url")
        for r in subset:
            pos = rank_of(r)
            print(f"{r['name'][:31] + ('?' if id(r) in sus else ''):<32} {(pos if pos else '-/-'):>5} {change_label(r):>5} "
                  f"{r.get('visibility', 0):>8.0f} {r['visibility_delta']:>+8.1f}  "
                  f"{short(r.get('best_ranking_url'))}")
        print()

    table("GAINED (ordered by visibility, not by positions)", [r for r in kept if r["visibility_delta"] > 0], True)
    table("LOST (ordered by visibility, not by positions)", [r for r in kept if r["visibility_delta"] < 0], False)

    # The totals go out whatever --limit is, because they decide whether the group is a
    # finding at all. Reading only the first rows of 33 drop-outs hides most of the loss.
    def group(label, rows, reverse, line):
        if not rows:
            return
        total = sum(r["visibility_delta"] for r in rows)
        shown = sorted(rows, key=lambda r: r["visibility_delta"], reverse=reverse)[: args.limit]
        print(f"{label} ({len(rows)}): {total:+.0f} visibility in total")
        for r in shown:
            print("  " + line(r))
        if len(rows) > len(shown):
            rest = total - sum(r["visibility_delta"] for r in shown)
            print(f"  ... and {len(rows) - len(shown)} more, {rest:+.0f} between them")
        print()

    group("DROPPED OUT of the tracked range", dropped_out, False,
          lambda r: f"{r['name'][:40]:<40} visibility {r['visibility_delta']:+.1f}")
    group("ENTERED the tracked range", entered, True,
          lambda r: f"{r['name'][:40]:<40} now {rank_of(r)}, "
                    f"visibility {r['visibility_delta']:+.1f}")

    # Several keywords dropping on one URL is a page-level signal; one keyword is not.
    by_url = defaultdict(list)
    for r in losers:
        if r.get("best_ranking_url"):
            by_url[r["best_ranking_url"]].append(r)
    clustered = {u: rs for u, rs in by_url.items() if len(rs) >= args.cluster}
    if clustered:
        print(f"DROPS SHARING ONE PAGE (>= {args.cluster} keywords):")
        for url, rs in sorted(clustered.items(), key=lambda kv: sum(r["visibility_delta"] for r in kv[1])):
            names = ", ".join(r["name"] for r in rs[:4])
            print(f"  {short(url, 60)}  {len(rs)} keywords, "
                  f"visibility {sum(r['visibility_delta'] for r in rs):+.1f}  ({names})")
        print()

    big = [r for r in rows if (r.get("visibility") or 0) > 0 and abs(r["visibility_delta"]) / max(r["visibility"], 1) > 5]
    if big:
        print(f"Note: {len(big)} row(s) moved by more than 5x their current visibility -- "
              f"usually a keyword entering or leaving the tracked range, not a gradual shift.")


# --- backlinks ----------------------------------------------------------------------------

def overview(args):
    """Headline visibility per device. `delta` is a locale string and a percentage of the base."""
    data = load(args.file)
    if isinstance(data, dict) and "data" in data and "desktop" not in data:
        data = data["data"]
    if not isinstance(data, dict) or not data:
        print("Empty overview: no monitored keywords. Not a quiet week -- say it is not monitored.")
        return
    for dev in ("desktop", "mobile"):
        row = data.get(dev)
        if not isinstance(row, dict):
            continue
        vis, pct = parse_num(row.get("visibility")), parse_num(row.get("delta"))
        if vis is None or pct is None or pct <= -100:
            print(f"{dev}: visibility {row.get('visibility')}, delta {row.get('delta')!r} -- unreadable, do not quote")
            continue
        base = vis / (1 + pct / 100)
        if base < args.min_base:
            print(f"{dev}: visibility {vis:.1f}, was {base:.2f} -- percentage SUPPRESSED (base under "
                  f"{args.min_base:g} point; delta string {row.get('delta')!r}). Quote points, or nothing.")
        else:
            print(f"{dev}: visibility {vis:.1f} ({pct:+.1f}% on a base of {base:.1f}; {vis - base:+.1f} points)")
    print("If the project's keywords were added inside the window, quote neither percentage.")


def _date(row):
    return (row.get("found_date") or row.get("lost_date") or "")[:10]


def _window(rows, days):
    """Backlink data lags a few days, so the window ends at the newest date in the payload.

    The window is `days` calendar days back from there. Counting distinct dates instead
    stretched `--days 7` to 01.07.-27.09. on a domain that gains links once a fortnight.
    """
    from datetime import date, timedelta
    dates = sorted({_date(r) for r in rows if _date(r)})
    if not dates:
        return rows, None, None
    end = dates[-1]
    try:
        start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
    except ValueError:
        start = dates[max(0, len(dates) - days)] if len(dates) > days else dates[0]
    return [r for r in rows if _date(r) >= start], start, end


def _side(rows, label, days, limit):
    payload = rows["data"]
    total = rows.get("pagination", {}).get("total")
    inwin, start, end = _window(payload, days)
    if not payload:
        print(f"{label}: no rows at all (pagination total {total}). Either nothing was found in "
              f"this window, or the domain has no backlink data. get_backlinks_overview says "
              f"which: count 0 there means no backlink profile, not a quiet week.")
        return
    print(f"{label}: {len(payload)} rows in this page of {total} reported, "
          f"{len(inwin)} of them between {start} and {end}")
    if total and total > len(payload):
        oldest = min((_date(r) for r in payload if _date(r)), default="")
        more = ("The window may reach past this page: fetch the next one (offset = a multiple of limit)."
                if start and oldest >= start else "The window is covered by this page.")
        print(f"  This file holds one page: {len(payload)} newest rows of {total}. {more}")
    if not inwin:
        return
    domains = defaultdict(list)
    for r in inwin:
        domains[r["origin_domain"]].append(r)
    follow = sum(1 for r in inwin if r.get("rel") == "follow")
    print(f"  {len(domains)} distinct domains, {follow} follow / {len(inwin) - follow} nofollow")
    bulk = {d: rs for d, rs in domains.items() if len(rs) >= 5}
    if bulk:
        n = sum(len(rs) for rs in bulk.values())
        print(f"  {len(bulk)} domain(s) account for {n} of the links -- template, footer, widget or "
              f"badge placements. That is {len(bulk)} "
              f"{'decision' if len(bulk) == 1 else 'decisions'}, not {n}:")
        for d, rs in sorted(bulk.items(), key=lambda kv: -len(kv[1])):
            print(f"    {d:<38} {len(rs):>3} links -> {short(rs[0]['target_url'], 44)}")
    print(f"  strongest domains by Seobility rating:")
    best = sorted(domains.items(), key=lambda kv: -max(r["rating"] for r in kv[1]))[:limit]
    for d, rs in best:
        print(f"    {d:<38} rating {max(r['rating'] for r in rs):>3}  "
              f"{len(rs)} link(s) -> {short(rs[0]['target_url'], 40)}")
    print()


def backlinks(args):
    _side(load(args.file), "NEW", args.days, args.limit)
    if args.lost:
        _side(load(args.lost), "LOST", args.days, args.limit)
    print("Backlink data is domain-level: it is identical for every project on the same domain.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)

    r = sub.add_parser("rankings")
    r.add_argument("file")
    r.add_argument("--limit", type=int, default=8)
    r.add_argument("--floor", type=float, default=1.0, help="minimum absolute visibility delta")
    r.add_argument("--cluster", type=int, default=3, help="drops on one URL before it is called a cluster")
    r.set_defaults(func=rankings)

    o = sub.add_parser("overview")
    o.add_argument("file", help="get_rankings_overview payload")
    o.add_argument("--min-base", type=float, default=1.0, help="visibility points below which a percentage is suppressed")
    o.set_defaults(func=overview)

    b = sub.add_parser("backlinks")
    b.add_argument("file", help="get_backlinks_new payload")
    b.add_argument("--lost", help="get_backlinks_lost payload")
    b.add_argument("--days", type=int, default=7)
    b.add_argument("--limit", type=int, default=8)
    b.set_defaults(func=backlinks)

    args = p.parse_args()
    try:
        args.func(args)
    except FileNotFoundError as exc:
        sys.exit(f"File not found: {exc.filename}")


if __name__ == "__main__":
    main()
