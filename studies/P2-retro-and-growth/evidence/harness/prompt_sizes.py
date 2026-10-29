#!/usr/bin/env python3
"""G0 harness, helper M: the owner's prompt growth (design 20.4 A, "owner prompt growth"; E7 Section 17 check S17-6).

    python3 -B prompt_sizes.py <streamdir> --out <dir>
    python3 -B prompt_sizes.py --selfcheck <E7EV> --out <dir> [--expected PATH]

Per run of the agent that offers the service (`lead` in E7; detected from the root tasks' `to`, else from the contract path
`<owner>/services/<name>/SERVICE.md` in the run logs, else the only run-logs directory without a dash): the prompt bytes
(UTF-8 bytes between the line `# ---- prompt ----` and the line `# ---- output ----`, exactly as E7's extract_mechanical.py counted
them) and, for runs whose prompt has a `# Reflect before you start:` section, its words (E7's rule: the section from its heading line
to the next line that starts `# ` and is not a Reflect line, split on whitespace). Reported: first, max, last, last minus first
(runs ordered by the run stamp in the log's file name), and min/max Reflect words. E3's reference: 20.2 KB -> 29.9 KB, 452-679 words.

Standard library only. Never imports hirearchy product code. Reads the stream directory read-only.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_memos as sm  # noqa: E402

REFERENCE_E3 = {"first_kb": 20.2, "peak_kb": 29.9, "reflect_words_min": 452, "reflect_words_max": 679}
_REFLECT = re.compile(r"^# Reflect before you start:.*?(?=^# (?!Reflect)|\Z)", re.M | re.S)
_CONTRACT = re.compile(r"([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)/services/[^/\s;`]+/SERVICE\.md")
_SIZES_LINE = re.compile(r"^lead@(\d{8}T\d+)\s+bytes=(\d+)\s+reflect_section=(yes|no)\s+reflect_words=(\d+)")


def prompt_stats(text):
    """bytes of the prompt (None when the markers are missing), whether it has a Reflect section, and that section's words."""
    if "# ---- prompt ----\n" not in text:
        return {"bytes": None, "reflect": False, "reflect_words": 0}
    pr = text.split("# ---- prompt ----\n", 1)[1].split("# ---- output ----", 1)[0]
    m = _REFLECT.search(pr)
    return {"bytes": len(pr.encode("utf-8", errors="surrogateescape")), "reflect": m is not None, "reflect_words": len(m.group(0).split()) if m else 0}


def find_owner(stream):
    stream = Path(stream)
    logs = stream / "run-logs"
    tos = {}
    for p in sorted((stream / "msgs").glob("*/*.md")) if (stream / "msgs").is_dir() else []:
        h, _ = sm.parse_msg_text(p.read_text(encoding="utf-8", errors="replace"))
        if h.get("from") == "root" and h.get("type") == "task" and h.get("service") and h.get("to"):
            tos[h["to"]] = tos.get(h["to"], 0) + 1
    if tos:
        return max(tos, key=lambda k: (tos[k], k)), "root tasks"
    cp = {}
    for p in sorted(logs.glob("*/*.log")) if logs.is_dir() else []:
        for m in _CONTRACT.finditer(p.read_text(encoding="utf-8", errors="replace")):
            cp[m.group(1)] = cp.get(m.group(1), 0) + 1
    cp = {k: v for k, v in cp.items() if (logs / k.replace("/", "-")).is_dir()}
    if cp:
        return max(cp, key=lambda k: (cp[k], k)), "contract path"
    names = sorted(d.name for d in logs.iterdir() if d.is_dir() and "-" not in d.name) if logs.is_dir() else []
    return (names[0], "run-logs directory") if len(names) == 1 else (None, None)


def analyse_stream(stream):
    stream = Path(stream)
    rd = sm.Reader(stream)
    owner, by = find_owner(stream)
    out = {"label": stream.name, "script": sm.script_info(__file__), "owner": owner, "owner_detected_by": by, "lead_runs": [], "could_not_parse": [],
           "reference_E3": dict(REFERENCE_E3)}
    d = stream / "run-logs" / owner.replace("/", "-") if owner else None
    for p in sorted(d.glob("*.log")) if d and d.is_dir() else []:
        st = prompt_stats(rd.read_bytes(p).decode("utf-8", errors="surrogateescape"))
        if st["bytes"] is None:
            out["could_not_parse"].append(rd.rel(p))
            continue
        out["lead_runs"].append({"file": rd.rel(p), "stamp": p.stem, **st})
    sizes = [r["bytes"] for r in out["lead_runs"]]
    out["bytes"] = ({"first": sizes[0], "max": max(sizes), "last": sizes[-1], "last_minus_first": sizes[-1] - sizes[0], "runs": len(sizes)} if sizes else
                    {"first": None, "max": None, "last": None, "last_minus_first": None, "runs": 0})
    words = [r["reflect_words"] for r in out["lead_runs"] if r["reflect"]]
    out["reflect_words"] = {"min": min(words) if words else None, "max": max(words) if words else None, "sections": len(words)}
    # cross-check against extract_mechanical.py's own lead-prompt-sizes.txt (when the stream has one)
    cc = {"present": False, "compared": 0, "differences": []}
    sp = stream / "lead-prompt-sizes.txt"
    if sp.exists():
        cc["present"] = True
        mine = {r["stamp"]: r for r in out["lead_runs"]}
        for ln in rd.read_text(sp).splitlines():
            m = _SIZES_LINE.match(ln)
            if not m:
                continue
            cc["compared"] += 1
            r = mine.get(m.group(1))
            theirs = {"bytes": int(m.group(2)), "reflect": m.group(3) == "yes", "reflect_words": int(m.group(4))}
            if r is None or any(r[k] != theirs[k] for k in theirs):
                cc["differences"].append({"stamp": m.group(1), "mine": {k: r[k] for k in theirs} if r else None, "lead-prompt-sizes.txt": theirs})
    out["lead_prompt_sizes_txt"] = cc
    out["source_files"] = rd.source_files()
    return out


def render_txt(d):
    b, w, r = d["bytes"], d["reflect_words"], d["reference_E3"]
    L = [f"prompt_sizes {d['label']}: owner {d['owner']} (detected from {d['owner_detected_by']}), {b['runs']} runs", "",
         f"prompt bytes: first {b['first']}, max {b['max']}, last {b['last']}, last minus first {b['last_minus_first']}",
         f"Reflect section words: min {w['min']}, max {w['max']} ({w['sections']} sections)",
         f"reference E3: {r['first_kb']} KB -> {r['peak_kb']} KB, {r['reflect_words_min']}-{r['reflect_words_max']} words", ""]
    for x in d["lead_runs"]:
        L.append(f"  {x['stamp']}  bytes={x['bytes']}  reflect={'yes' if x['reflect'] else 'no'}  reflect_words={x['reflect_words']}")
    c = d["lead_prompt_sizes_txt"]
    L.append("")
    L.append(f"lead-prompt-sizes.txt: {'compared ' + str(c['compared']) + ' runs, ' + str(len(c['differences'])) + ' differences' if c['present'] else 'not present'}")
    for x in d["could_not_parse"]:
        L.append(f"could not parse (no prompt markers): {x}")
    return "\n".join(L) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Owner prompt bytes and Reflect words per run (G0 harness, helper M)")
    ap.add_argument("streamdir", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--selfcheck", metavar="E7EV")
    ap.add_argument("--expected", default=sm.DEFAULT_EXPECTED)
    a = ap.parse_args(argv)
    if a.selfcheck:
        return sm.run_selfcheck("prompt_sizes", a.selfcheck, a.out, a.expected, analyse_stream, "prompt_sizes", render_txt)
    if not a.streamdir:
        ap.error("streamdir is required (or --selfcheck E7EV)")
    d = analyse_stream(a.streamdir)
    sm.write_outputs(a.out, "prompt_sizes", d, render_txt(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
