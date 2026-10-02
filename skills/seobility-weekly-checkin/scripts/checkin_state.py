#!/usr/bin/env python3
"""The check-in's memory: one small file per project per run.

A weekly check-in with no memory cannot tell a fluctuation from a trend, and the job bar in
SKILL.md step 7 depends on exactly that distinction. So every run stores the few figures the
next run needs, and reads the previous one before it writes a word.

    python checkin_state.py previous <project_id>
    python checkin_state.py build    <project_id> --winners <winners-losers.json> [--overview <overview.json>] --out <state.json>
    python checkin_state.py compare  <project_id> --file <state.json>
    python checkin_state.py save     <project_id> --file <state.json> [--date YYYY-MM-DD]

State lives per user, outside the skill folder: ~/.seobility-checkin/<project_id>/<date>.json.
Override it with the SEOBILITY_CHECKIN_HOME environment variable or --home <dir> (any command).
An old <skill>/history/ folder is read once if present (and copied on save); it is never deleted.
A --file / --winners / --overview argument may be "-" to read the JSON from stdin.
compare only uses a stored run at least --min-gap days (default 5) older than this one, so a
same-day re-run never compares against itself. build stores every mover above the noise floor.

This stores figures, not prose. The report is written fresh every week; what carries over is
what moved, what was flagged, and what was still open.

State file shape (all keys optional except date, which is filled in on save):

    {
      "windows":  {"rankings": "...", "crawl": "...", "backlinks": "...", "uptime": "..."},
      "headline": {"visibility_desktop_pct": -4.6, "visibility_mobile_pct": 4.1,
                   "problems": 940, "problems_delta": -1,
                   "domains_gained": 46, "domains_lost": 48,
                   "uptime": "redirect"},
      "movers":   [{"keyword": "google trends", "device": "desktop", "rank": 7, "rank_change": -1,
                    "visibility_delta": -624.0, "url": "example.com/de/wiki/Google_Trends",
                    "suspect": false}],
      "dropped_out": {"count": 33, "visibility_total": -748.0,
                      "largest": ["dark web", "pogo sticking", "https", "google ads"]},
      "jobs":     ["Point Uptime Monitoring at the target URL"],
      "watch":    [{"item": "google trends", "condition": "still at 7 or lower next week"},
                   {"item": "dropped-out group of 33", "key": "dropped_out.count", "count": 33,
                    "condition": "same keywords still out next week"},
                   {"item": "crawl problems 1476", "key": "headline.problems", "count": 1476,
                    "condition": "under 1500 at the next crawl"}]
    }

A watch item that is not a keyword carries a "key" (a dotted path into the state, e.g.
"dropped_out.count" or "headline.problems") and its "count"; compare tracks it by that key.
A keyword watch item may carry "device". `build` writes the movers and the drop-out group;
add windows, headline, jobs and watch to its output file before you save it.
"""

import argparse
import json
import os
import shutil
import sys
from datetime import date as _date, timedelta

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
from weekly_deltas import load as _load_payload, parse_num, suspect_reasons

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# The old location, inside the skill folder. Read once if it exists; never written, never deleted.
LEGACY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "history")
HOME = os.environ.get("SEOBILITY_CHECKIN_HOME") or os.path.join(os.path.expanduser("~"), ".seobility-checkin")


def _dir(project_id, root=None):
    return os.path.join(root or HOME, str(project_id))


def _files(project_id, root):
    d = _dir(project_id, root)
    if not os.path.isdir(d):
        return {}
    return {n[:-5]: os.path.join(d, n) for n in os.listdir(d) if n.endswith(".json")}


def _runs(project_id):
    """Every stored run for this project, oldest first, as (date, path). The old skill-folder
    history counts too, for dates the per-user home does not have."""
    found = _files(project_id, LEGACY)
    found.update(_files(project_id, HOME))
    return sorted(found.items())


def _legacy_only(project_id):
    home = _files(project_id, HOME)
    return {d: p for d, p in _files(project_id, LEGACY).items() if d not in home}


def _note_migration(project_id):
    old = _legacy_only(project_id)
    if old:
        print(f"Migration: {len(old)} run(s) come from the old skill-folder history ({LEGACY}). "
              f"save copies them to {HOME}; the old folder is left as it is.\n")


def _load(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _age(then, today=None):
    today = today or _date.today()
    try:
        y, m, d = (int(x) for x in then.split("-"))
    except ValueError:
        return None
    return (today - _date(y, m, d)).days


def _parse(text):
    try:
        y, m, d = (int(x) for x in str(text).split("-"))
        return _date(y, m, d)
    except (ValueError, TypeError):
        return None


def _latest(project_id, before=None, ref=None, min_gap=0):
    """Newest stored run; with ref, only runs at least min_gap days older than ref."""
    runs = [r for r in _runs(project_id) if not before or r[0] < before]
    if ref is not None:
        runs = [r for r in runs if _age(r[0], ref) is not None and _age(r[0], ref) >= min_gap]
    return runs[-1] if runs else None


# --- previous -----------------------------------------------------------------------------

def previous(args):
    _note_migration(args.project_id)
    found = _latest(args.project_id, args.before)
    if not found:
        print(f"No stored run for project {args.project_id}.")
        print("This is the first check-in. Nothing can be called persistent yet: every ranking")
        print("finding is a watch item this week, however large it looks.")
        return
    when, path = found
    days = _age(when)
    state = _load(path)
    print(f"Previous run: {when}" + (f" ({days} days ago)" if days is not None else ""))
    if days is not None and days < args.min_gap:
        print(f"  That is only {days} days back: a same-day or early re-run. compare skips runs")
        print(f"  younger than {args.min_gap} days, so nothing can be persistent against it.")
    if days is not None and days > 21:
        print(f"  Careful: that is {days} days back, not a week. Anything you call 'persistent'")
        print("  against it spans that gap, so say the gap instead of saying 'last week'.")
    print(json.dumps(state, ensure_ascii=False, indent=2))


# --- save ---------------------------------------------------------------------------------

def save(args):
    state = _load(args.file)
    if not isinstance(state, dict):
        sys.exit("The state file must be a JSON object.")
    state["date"] = args.date or _date.today().isoformat()
    state["project_id"] = args.project_id
    d = _dir(args.project_id)
    os.makedirs(d, exist_ok=True)
    old = _legacy_only(args.project_id)
    for when, src in old.items():
        shutil.copyfile(src, os.path.join(d, when + ".json"))
    if old:
        print(f"Migrated {len(old)} run(s) from {LEGACY} to {d}; the old folder is untouched.")
    path = os.path.join(d, state["date"] + ".json")
    existing = " (overwriting the run already stored for that date)" if os.path.exists(path) else ""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Saved {path}{existing}")


# --- build --------------------------------------------------------------------------------

def _pct(overview, device, min_base=1.0):
    """Visibility change in percent, or None when unreadable or the base is under min_base points."""
    row = overview.get(device) if isinstance(overview, dict) else None
    if not isinstance(row, dict):
        return None
    vis, pct = parse_num(row.get("visibility")), parse_num(row.get("delta"))
    if vis is None or pct is None or pct <= -100 or vis / (1 + pct / 100) < min_base:
        return None
    return round(pct, 1)


def build(args):
    """State file from the winners/losers payload: every mover above the floor, and the drop-outs."""
    data = _load_payload(args.winners)["data"]
    rows = (data.get("winners") or []) + (data.get("losers") or [])
    sus = suspect_reasons(rows)
    device = args.device or "desktop"
    movers = []
    for r in rows:
        v = r.get("visibility_delta") or 0
        if abs(v) < args.floor or r.get("rank_change") == "out":
            continue
        m = {"keyword": r["name"], "keyword_id": r.get("keyword_id"), "device": device,
             "rank": r.get("rank"), "rank_change": r.get("rank_change"), "visibility_delta": v,
             "url": (r.get("best_ranking_url") or "").replace("https://", "").replace("www.", "")}
        if id(r) in sus:
            m["suspect"] = True
        movers.append(m)
    outs = sorted((r for r in rows if r.get("rank_change") == "out"),
                  key=lambda r: r.get("visibility_delta") or 0)
    state = {"movers": movers,
             "dropped_out": {"count": len(outs),
                             "visibility_total": round(sum(r.get("visibility_delta") or 0 for r in outs), 1),
                             "largest": [r["name"] for r in outs[:4]],
                             "keywords": [r["name"] for r in outs]}}
    if args.overview:
        ov = _load_payload(args.overview)
        state["headline"] = {f"visibility_{d}_pct": _pct(ov, d) for d in ("desktop", "mobile")}
    text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"Wrote {args.out}: {len(movers)} movers ({len(sus)} not confirmed), "
              f"{len(outs)} drop-outs, device {device}. Add windows, headline, jobs and watch, then save.")
    else:
        sys.stdout.write(text)


# --- compare ------------------------------------------------------------------------------

def _key(m):
    return m.get("keyword"), m.get("device") or "desktop"


def _mover_index(state):
    out = {}
    for m in state.get("movers") or []:
        if m.get("keyword"):
            out[_key(m)] = m
    return out


def _path(state, dotted):
    cur = state
    for part in dotted.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def compare(args):
    """What the job bar in step 7 needs: which findings are in their second week."""
    current = _load(args.file)
    ref = _parse(args.date) or _parse(current.get("date")) or _date.today()
    _note_migration(args.project_id)
    found = _latest(args.project_id, args.before, ref, args.min_gap)
    if not found:
        newest = _latest(args.project_id, args.before)
        if newest:
            print(f"No stored run at least {args.min_gap} days older than {ref}. The newest is "
                  f"{newest[0]} ({_age(newest[0], ref)} days): a same-day or early re-run. Nothing is "
                  f"compared and nothing qualifies as persistent -- watch items only. "
                  f"(--min-gap 0 overrides.)")
        else:
            print("No previous run stored. Nothing qualifies as persistent -- watch items only.")
        return
    when, path = found
    prev = _load(path)
    days = _age(when, ref)
    print(f"Comparing against the run of {when}, {days} days earlier\n")
    if days > 10:
        print(f"Careful: a {days}-day gap, not a week. Say the gap; do not write 'last week'.\n")

    now, before = _mover_index(current), _mover_index(prev)

    def direction(m):
        """Visibility decides, as everywhere else. Fall back to the position only when a
        stored run carries no visibility figure -- older files sometimes do not."""
        v = m.get("visibility_delta")
        if isinstance(v, (int, float)):
            return (1 if v > 0 else -1 if v < 0 else 0), f"{v:+.0f}"
        r = m.get("rank_change")
        if isinstance(r, (int, float)):
            return (1 if r > 0 else -1 if r < 0 else 0), f"{r:+g} pos"
        return 0, "?"

    repeat, doubtful, reversed_ = [], [], []
    for k, m in now.items():
        p = before.get(k)
        if not p:
            continue
        (dn, sn), (db, sb) = direction(m), direction(p)
        row = (k[0], sb, sn, dn)
        if dn and dn == db:
            (doubtful if m.get("suspect") or p.get("suspect") else repeat).append(row)
        elif dn and db:
            reversed_.append(row)
    if repeat:
        print("SAME DIRECTION TWO WEEKS RUNNING -- these clear the persistence bar:")
        for name, sb, sn, _ in sorted(repeat, key=lambda r: r[3]):
            print(f"  {name[:40]:<40} {sb} then {sn} visibility")
    else:
        print("No keyword moved the same way in both weeks. Nothing clears the persistence bar")
        print("on movement alone -- a job needs the crawl or backlink data to account for it.")
    if doubtful:
        print("SAME DIRECTION, BUT NOT CONFIRMED (suspect ranking data in one week) -- never a job:")
        for name, sb, sn, _ in doubtful:
            print(f"  {name[:40]:<40} {sb} then {sn} visibility")
    if reversed_:
        print("MOVED THE OTHER WAY THIS WEEK (a reversal, not persistence):")
        for name, sb, sn, _ in reversed_:
            print(f"  {name[:40]:<40} {sb} then {sn} visibility")
    print()

    watch = [w for w in (prev.get("watch") or []) if w.get("item")]
    if watch:
        print("WATCH ITEMS FROM LAST WEEK -- judge each against its own condition:")
        for w in watch:
            item, cond = w["item"], w.get("condition") or "no condition stored"
            k = (item, w.get("device") or "desktop")
            if w.get("key"):
                then = w["count"] if w.get("count") is not None else _path(prev, w["key"])
                nowv = _path(current, w["key"])
                if nowv is None or then is None:
                    verdict = f"then {then}, now {nowv}: not comparable, judge by hand"
                else:
                    verdict = f"{then} then, {nowv} now ({'unchanged' if nowv == then else f'{nowv - then:+g}'})"
                if w["key"].startswith("dropped_out"):
                    a = set((prev.get("dropped_out") or {}).get("keywords") or [])
                    b = set((current.get("dropped_out") or {}).get("keywords") or [])
                    if a and b:
                        verdict += f", {len(a & b)} of {len(a)} still out"
            elif k in now:
                (dn, sn), (db, sb) = direction(now[k]), direction(before[k]) if k in before else (0, "?")
                rel = "same direction" if dn and dn == db else "reversed" if dn and db else "changed"
                verdict = f"moved again: {sb} then {sn} ({rel}), rank now {now[k].get('rank')}"
            elif k in before:
                verdict = "no longer a mover (held still, or moved under the noise floor); read its position before closing it"
            else:
                verdict = "no key stored, the script cannot judge it; judge by hand"
            print(f"  {item}: {verdict}\n      condition: {cond}")
        print()

    prev_jobs = prev.get("jobs") or []
    if prev_jobs:
        print("JOBS FROM LAST WEEK -- check each against this week's data before repeating it:")
        for j in prev_jobs:
            print(f"  {j}")
        print()

    pd, cd = prev.get("dropped_out") or {}, current.get("dropped_out") or {}
    if pd.get("count") is not None and cd.get("count") is not None:
        print(f"Drop-outs: {pd['count']} last time, {cd['count']} now "
              f"({pd.get('visibility_total', 0):+.0f} then, {cd.get('visibility_total', 0):+.0f} now)")


def main():
    global HOME
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", help="state directory (default: $SEOBILITY_CHECKIN_HOME or ~/.seobility-checkin)")
    gap = argparse.ArgumentParser(add_help=False)
    gap.add_argument("--min-gap", type=int, default=5, help="days a stored run must be older than this one (default 5)")

    p = sub.add_parser("previous", parents=[common, gap], help="print the most recent stored run for a project")
    p.add_argument("project_id")
    p.add_argument("--before", help="only runs strictly before this YYYY-MM-DD")
    p.set_defaults(func=previous)

    p = sub.add_parser("save", parents=[common], help="store this run's figures")
    p.add_argument("project_id")
    p.add_argument("--file", required=True, help="JSON file holding this run's state")
    p.add_argument("--date", help="defaults to today")
    p.set_defaults(func=save)

    p = sub.add_parser("build", parents=[common], help="start a state file from the winners/losers payload")
    p.add_argument("project_id")
    p.add_argument("--winners", required=True, help="get_rankings_winners_and_losers payload")
    p.add_argument("--overview", help="get_rankings_overview payload, for the headline percentages")
    p.add_argument("--out", help="state file to write (default: stdout)")
    p.add_argument("--floor", type=float, default=1.0, help="minimum absolute visibility delta")
    p.add_argument("--device", help="device the payload covers (default desktop)")
    p.set_defaults(func=build)

    p = sub.add_parser("compare", parents=[common, gap], help="this run against the previous one")
    p.add_argument("project_id")
    p.add_argument("--file", required=True, help="JSON file holding this run's state")
    p.add_argument("--before", help="only runs strictly before this YYYY-MM-DD")
    p.add_argument("--date", help="date of this run (default: the file's date, else today)")
    p.set_defaults(func=compare)

    args = ap.parse_args()
    if args.home:
        HOME = args.home
    args.func(args)


if __name__ == "__main__":
    main()
