#!/usr/bin/env python3
"""G0 harness, helper M: reviewer ambiguity recall (E7 protocol section 9, D21; design 20.4 A).

    python3 -B ambiguity_recall.py <streamdir> --out <dir>
    python3 -B ambiguity_recall.py --pool <streamdir>... --out <dir>          # pooled k of n over several streams
    python3 -B ambiguity_recall.py --selfcheck <E7EV> --out <dir> [--expected PATH]

D21, as E7's protocol states it:
  * the ambiguity items: AMB-1 (Marta's agenda row, memo 2026-10-19) and AMB-2 (Sam's CI-cache row, memo 2026-10-12);
  * a version CONTAINS an item when its action-items table has a row for it (an "Open items" bullet is no row);
  * a REVIEWED version is a committed version (memos/versions/, INDEX.txt) that a review task to the final-check agent reviewed (the task
    is mapped to the memo by an ISO date in its title, else the `memo-<date>` path in its body). G0's reading of "sent after the version's
    commit and before the next version's commit" (protocol 12 A3; manager-decision-selfcheck.md item 4): the version at the first org-git
    commit that holds the task's sent copy (score_memos.map_reviews, rule "commit"); without that commit in org-git-log.txt, the time window;
  * the reviewer LISTED the item as ambiguous on its first review of that version when its first result to that version's first
    review task has a line or list item that names the row's owner and substance and contains the token `ambiguous` (any case),
    or when the row is an item of a `Questions for the client:` block of that result;
  * recall = k (versions x items listed) of n (reviewed versions x items they contain); `n/a (0 of 0)` when n == 0.
Also recorded per item and version: the lead forwarded it (a `Questions for the client:` item naming the row, in a result of the
owner to root created in the version's window), `progress` flagged it (a progress reply of the assistant or of the injection
script, at or after that result, shows the flag on that result's task line, and the item names a criterion id), and the writer
left it out of the next version.
Reported beside it: `recall_literal_timing`, D21's literal timing (a review task sent at or after the version's commit; rule "time"), and per
version `review_sent_before_commit_s` and `literal_reviewed` (E7 s2's memo-3 v1: its task was sent 10 s before the commit that holds it).

Standard library only. Never imports hirearchy product code. Reads the stream directory read-only.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_memos as sm  # noqa: E402
from score_memos import rate, rate_text  # noqa: E402,F401

FLAG = re.compile(r"\b\d+ questions? for the client: ask the user before you copy or deliver")
CRITERION_ID = re.compile(r"\bC[0-9]+\b")

# Pre-registered, frozen. `rows`: groups for sm.groups_match on the action text of a row of `owner`; `mention`: groups for a reviewer/lead
# line to "name the row's owner and substance" (whole-word owner).
ITEMS = {
    "AMB-1": {"memo": "2026-10-19", "owner": "Marta", "rows": [["agenda"]], "mention": [["=marta"], ["agenda"]]},
    "AMB-2": {"memo": "2026-10-12", "owner": "Sam", "rows": [["=ci", "cache", "runner", "flaky"]], "mention": [["=sam"], ["=ci", "cache", "runner", "flaky"]]},
}

_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


def _title_date(text):
    for ln in text.splitlines():
        if ln.strip():
            m = sm.ISO_DATE.search(ln)
            return m.group(0) if m else None
    return None


def item_rows(text, item_id, memo=None):
    it = ITEMS[item_id]
    memo = memo or _title_date(text)
    if memo and memo != it["memo"]:
        return []
    return [" | ".join(r["cells"]) for r in sm.action_rows(text)
            if sm.strip_marks(r["owner"]).lower() == it["owner"].lower() and sm.groups_match(it["rows"], r["action"])]


def text_units(body):
    """Lines and list items (a bullet with its indented continuation lines is one unit)."""
    units, cur = [], None
    for ln in body.splitlines():
        if not ln.strip():
            cur = None
            continue
        if _BULLET.match(ln):
            units.append(ln.strip())
            cur = len(units) - 1
        elif cur is not None and ln[:1].isspace():
            units[cur] += " " + ln.strip()
        else:
            units.append(ln.strip())
            cur = None
    return units


def client_question_items(body):
    """The items of every `Questions for the client:` block (T-A1's four tail rules, simplified): list lines after the marker (blank
    lines first skipped) up to the first blank line, heading or non-list line."""
    lines = body.splitlines()
    out = []
    for i, ln in enumerate(lines):
        s = re.sub(r"^[\s>#*_\-+]+", "", ln)
        if not s.lower().startswith("questions for the client"):
            continue
        tail = s[len("questions for the client"):].strip(" \t*_:").strip()
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        items = []
        while j < len(lines):
            m = _BULLET.match(lines[j])
            if not m or lines[j].lstrip().startswith("#"):
                break
            it = m.group(1).strip()
            if it.lower().strip(" .") not in ("none", "no", "n/a", "-"):
                items.append(it)
            j += 1
        first = (tail.split() or [""])[0].lower().strip(".,:;")
        none_word = first in ("none", "no", "n/a", "-")
        if tail and re.search(r"\bC[0-9]+\b", tail) and not none_word:
            out.append(tail)
        elif tail and not items and not none_word and not (tail.startswith("(") and tail.rstrip(".").endswith(")")):
            out.append(tail)
        out.extend(items)
    return out


def reviewer_lists(body, item_id):
    it = ITEMS[item_id]
    for u in text_units(body):
        if "ambiguous" in u.lower() and sm.groups_match(it["mention"], u):
            return {"listed": True, "how": "ambiguous token", "line": u[:240]}
    for q in client_question_items(body):
        if sm.groups_match(it["mention"], q):
            return {"listed": True, "how": "question for the client", "line": q[:240]}
    return {"listed": False, "how": None, "line": None}


def progress_flags(stream, rd=None):
    """Every progress reply line that shows `<n> question(s) for the client: ask the user before you copy or deliver`, with the task
    it names, the time of the reply and (assistant-tool-calls.txt) the call number."""
    rd = rd or sm.Reader(stream)
    stream = Path(stream)
    flags = []
    p = stream / "assistant-tool-calls.txt"
    if p.exists():
        call, ts = None, None
        for ln in rd.read_text(p).splitlines():
            m = re.match(r"^\[(\S+)\] CALL #(\d+)\b", ln)
            if m:
                ts, call = m.group(1), int(m.group(2))
                continue
            m = re.match(r"^\s+RESULT \[(\S+)\]", ln)
            if m:
                ts = m.group(1)
            if FLAG.search(ln):
                t = re.search(r"\(task (\S+?)\)\s*$", ln.strip())
                flags.append({"source": "assistant-tool-calls.txt", "call": call, "time": ts, "task": t.group(1) if t else None})
    p = stream / "injection" / "injection-log.txt"
    if p.exists():
        ts = None
        for ln in rd.read_text(p).splitlines():
            m = re.match(r"^--- (?:progress|request|\S+) at \S+.*?-> reply at (\S+)", ln)
            if m:
                ts = m.group(1)
                continue
            if FLAG.search(ln):
                t = re.search(r"\(task (\S+?)\)\s*$", ln.strip())
                flags.append({"source": "injection/injection-log.txt", "call": None, "time": ts, "task": t.group(1) if t else None})
    return flags


def analyse_stream(stream):
    stream = Path(stream)
    rd = sm.Reader(stream)
    versions = sm.load_versions(stream, rd)
    roles = sm.find_roles(stream, rd)
    rv = sm.map_reviews(stream, versions, roles, rd)
    rv_literal = sm.map_reviews(stream, versions, roles, rd, rule="time")
    msgs = sm.read_msgs(stream)
    flags = progress_flags(stream, rd)
    owner = roles["owner"]
    lead_results = sorted((m for m in msgs.values() if m["h"].get("from") == owner and m["h"].get("to") == "root" and m["h"].get("type") == "result"),
                          key=lambda m: m["h"].get("id", ""))
    by_memo = {}
    for v in versions:
        by_memo.setdefault(v["memo"], []).append(v)
    result = {"label": stream.name, "script": sm.script_info(__file__), "roles": roles, "items": {}, "could_not_derive": []}
    tot = {"k": 0, "n": 0, "kl": 0, "nl": 0}
    for item_id, it in ITEMS.items():
        vs = by_memo.get(it["memo"], [])
        entries, k, n, kl, nl = [], 0, 0, 0, 0
        for i, v in enumerate(vs):
            text = (stream / v["file"]).read_bytes().decode("utf-8", errors="replace")
            rows = item_rows(text, item_id, v["memo"])
            if not rows:
                continue
            nxt = vs[i + 1] if i + 1 < len(vs) else None
            lo = sm.parse_time(v["commit_time"]) if v["commit_time"] else None
            hi = sm.parse_time(nxt["commit_time"]) if nxt and nxt["commit_time"] else None
            e = {"version": v["version"], "sha": v["sha"], "commit_time": v["commit_time"], "contains": True, "row": rows[0]}
            rev = rv["by_version"].get((v["memo"], v["version"]))
            e["reviewed"] = rev is not None
            e["review_task"] = rev["task"] if rev else None
            e["review_result"] = rev["result"] if rev else None
            e["review_sent_before_commit_s"] = rev["sent_before_commit_s"] if rev else None
            lit = rv_literal["by_version"].get((v["memo"], v["version"]))
            e["literal_reviewed"] = lit is not None
            e["literal_listed_ambiguous"] = (reviewer_lists(msgs[lit["result"]]["body"], item_id)["listed"]
                                             if lit and lit["result"] else None)
            if rev and rev["result"]:
                body = msgs[rev["result"]]["body"]
                lst = reviewer_lists(body, item_id)
                e.update({"listed_ambiguous": lst["listed"], "listed_by": lst["how"], "listed_line": lst["line"]})
            else:
                e.update({"listed_ambiguous": None, "listed_by": None, "listed_line": None})
                if rev:
                    result["could_not_derive"].append(f"{item_id} v{v['version']}: the review task has no result")
            # lead forwarded
            fwd = None
            for m in lead_results:
                c = sm.parse_time(m["h"]["created"])
                if lo is not None and c >= lo and (hi is None or c < hi):
                    for q in client_question_items(m["body"]):
                        if sm.groups_match(it["mention"], q):
                            fwd = (m, q)
                            break
                if fwd:
                    break
            e["lead_forwarded"] = fwd is not None
            e["lead_result"] = fwd[0]["h"]["id"] if fwd else None
            e["lead_item"] = fwd[1][:240] if fwd else None
            e["lead_item_names_criterion"] = bool(CRITERION_ID.search(fwd[1])) if fwd else None
            if fwd:
                rd.note(fwd[0]["path"])
            # progress flagged it
            pf = None
            if fwd and e["lead_item_names_criterion"]:
                after = [f for f in flags if f["task"] == fwd[0]["h"].get("reply_to") and f["time"] and sm.parse_time(f["time"]) >= sm.parse_time(fwd[0]["h"]["created"])]
                after.sort(key=lambda f: sm.parse_time(f["time"]))
                pf = after[0] if after else None
            e["progress_flagged"] = pf is not None
            e["progress_call"] = pf["call"] if pf else None
            e["progress_source"] = pf["source"] if pf else None
            e["progress_time"] = pf["time"] if pf else None
            # the writer left it out of the next version
            if nxt:
                ntext = (stream / nxt["file"]).read_bytes().decode("utf-8", errors="replace")
                e["writer_left_out"] = not item_rows(ntext, item_id, nxt["memo"])
                e["next_version"] = nxt["version"]
            else:
                e["writer_left_out"], e["next_version"] = None, None
            entries.append(e)
            if e["reviewed"] and e["listed_ambiguous"] is not None:
                n += 1
                k += 1 if e["listed_ambiguous"] else 0
            if e["literal_reviewed"] and e["literal_listed_ambiguous"] is not None:
                nl += 1
                kl += 1 if e["literal_listed_ambiguous"] else 0
            if not e["reviewed"]:
                result["could_not_derive"].append(f"{item_id} v{v['version']} {v['sha']} contains the row but no review task reviewed it")
        result["items"][item_id] = {"memo": it["memo"], "owner": it["owner"], "recall": rate(k, n),
                                    "recall_literal_timing": rate(kl, nl), "versions": entries,
                                    "versions_of_the_memo": len(vs), "versions_containing": len(entries)}
        tot["k"] += k
        tot["n"] += n
        tot["kl"] += kl
        tot["nl"] += nl
    result["recall"] = rate(tot["k"], tot["n"])
    result["recall_literal_timing"] = rate(tot["kl"], tot["nl"])
    result["source_files"] = rd.source_files()
    return result


def pool(results):
    out = {"streams": [r["label"] for r in results], "items": {}, "script": sm.script_info(__file__)}
    for item_id in ITEMS:
        out["items"][item_id] = {
            "recall": rate(sum(r["items"][item_id]["recall"]["k"] for r in results), sum(r["items"][item_id]["recall"]["n"] for r in results)),
            "recall_literal_timing": rate(sum(r["items"][item_id]["recall_literal_timing"]["k"] for r in results),
                                                       sum(r["items"][item_id]["recall_literal_timing"]["n"] for r in results))}
    out["recall"] = rate(sum(r["recall"]["k"] for r in results), sum(r["recall"]["n"] for r in results))
    out["recall_literal_timing"] = rate(sum(r["recall_literal_timing"]["k"] for r in results),
                                                     sum(r["recall_literal_timing"]["n"] for r in results))
    return out


def render_txt(d):
    L = [f"ambiguity_recall {d['label']}: reviewer {d['roles']['reviewer']}, owner {d['roles']['owner']}", ""]
    for item_id, it in d["items"].items():
        L.append(f"{item_id}: {rate_text(it['recall'])} (memo {it['memo']}, {it['owner']})"
                 f"   [D21's literal timing: {rate_text(it['recall_literal_timing'])}]"
                 f"   versions of the memo {it['versions_of_the_memo']}, containing the row {it['versions_containing']}")
        for e in it["versions"]:
            L.append(f"  v{e['version']} {e['sha']}: reviewed={e['reviewed']} listed ambiguous={e['listed_ambiguous']}"
                     + (f" ({e['listed_by']})" if e["listed_by"] else "")
                     + f"; lead forwarded={e['lead_forwarded']}"
                     + (f" ({e['lead_result']})" if e["lead_result"] else "")
                     + f"; progress flagged={e['progress_flagged']}"
                     + (f" (#{e['progress_call']})" if e["progress_call"] else "")
                     + f"; writer left it out of the next version={e['writer_left_out']}")
            if e["review_sent_before_commit_s"]:
                L.append(f"    review task {e['review_task']} sent {e['review_sent_before_commit_s']} s before the version's commit (the commit that "
                         f"holds it); D21's literal timing: reviewed={e['literal_reviewed']}")
    L.append("")
    L.append(f"all items: {rate_text(d['recall'])}   [D21's literal timing: {rate_text(d['recall_literal_timing'])}]")
    if d["could_not_derive"]:
        L += ["", "could not derive / not reviewed:"] + [f"  {x}" for x in d["could_not_derive"]]
    return "\n".join(L) + "\n"


def render_pool_txt(p):
    L = [f"ambiguity_recall pooled over {', '.join(p['streams'])}", ""]
    for item_id, it in p["items"].items():
        L.append(f"{item_id}: {rate_text(it['recall'])}   [D21's literal timing: {rate_text(it['recall_literal_timing'])}]")
    L.append(f"all items: {rate_text(p['recall'])}   [D21's literal timing: {rate_text(p['recall_literal_timing'])}]")
    return "\n".join(L) + "\n"


def _post(results):
    p = pool([results[s] for s in sorted(results)])
    return {"pooled": (p, "ambiguity_recall-pooled", render_pool_txt(p))}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Reviewer ambiguity recall, D21 (G0 harness, helper M)")
    ap.add_argument("streamdir", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pool", nargs="+", metavar="STREAMDIR")
    ap.add_argument("--selfcheck", metavar="E7EV")
    ap.add_argument("--expected", default=sm.DEFAULT_EXPECTED)
    a = ap.parse_args(argv)
    if a.selfcheck:
        return sm.run_selfcheck("ambiguity_recall", a.selfcheck, a.out, a.expected, analyse_stream, "ambiguity_recall", render_txt, post=_post)
    if a.pool:
        rs = [analyse_stream(d) for d in a.pool]
        p = pool(rs)
        p["source_files"] = {r["label"]: r["source_files"] for r in rs}
        sm.write_outputs(a.out, "ambiguity_recall-pooled", p, render_pool_txt(p))
        return 0
    if not a.streamdir:
        ap.error("streamdir, --pool or --selfcheck is required")
    d = analyse_stream(a.streamdir)
    sm.write_outputs(a.out, "ambiguity_recall", d, render_txt(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
