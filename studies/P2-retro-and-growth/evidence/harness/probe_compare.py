#!/usr/bin/env python3
"""P2 probe comparison (protocol 8.3). Usage: probe_compare.py <probe dir> | --selfcheck <dir>

Over probe-C1, probe-R1, probe-R2, probe-C2 (each with session-messages.jsonl, turn-*.stderr.txt, skill-proof.json, turn-02.txt) and
catalog-R.json / catalog-C.json:
  1. session_start equal in all four (masked: the sandbox path, the probe label, the product path, ISO times, UUIDs, digits runs inside
     paths; the <memories> block cut out and reported);
  2. the non-`[tool]` stderr lines equal (digits masked);
  3. within an arm, every tool loaded in both repetitions has the same hash; across arms, every loaded tool's hash equals its arm's catalog
     entry (the only explained cross-arm difference is the products' catalogs);
  4. failed empty-argument calls (P1's empty_calls.py rule) 0 in every session;
  5. the skill proof PROVED in every session;
  6. the positive control: catalog-R holds `retro`, catalog-C does not; every turn-2 reply names `probe-memo`.
Prints each finding and last `PROBE: PASS` or `PROBE: STOP: <differences>`.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

SESS = ["probe-C1", "probe-R1", "probe-R2", "probe-C2"]
REPOS = ["/Volumes/workspace/hirearchy/.worktrees/p2-arm-c", "/Volumes/workspace/hirearchy"]


def payload(d):
    p = d.get("payload")
    return json.loads(p) if isinstance(p, str) else (p or {})


def mask(s: str, label: str) -> str:
    for r in REPOS:
        s = s.replace(r, "<PRODUCT>")
    s = re.sub(r"/(?:private/)?tmp/hirearchy-p2/[^\s\"')]+", "<S>", s).replace(label, "<LABEL>")
    s = re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?", "<T>", s)
    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<UUID>", s)


def session(d: Path, label: str):
    start, loads, empty = None, {}, 0
    calls = {}
    for ln in (d / "session-messages.jsonl").read_text(errors="replace").splitlines() if (d / "session-messages.jsonl").is_file() else []:
        if not ln.strip():
            continue
        p = payload(json.loads(ln))
        t = p.get("type")
        if t == "session_start" and start is None:
            start = mask(json.dumps(p, sort_keys=True), label)
        if t == "tool_call":
            calls[p.get("toolCallId")] = p
            if p.get("toolName") in ("tool_call", "tool_load") and (p.get("args") or {}) == {} and str(p.get("status")).lower() == "failed":
                empty += 1
        if t == "tool_result" and calls.get(p.get("toolCallId"), {}).get("toolName") == "tool_load":
            # the result is {"loaded": [{tool_id, description, input_schema}, ...]} (P1's kept sessions): one hash per tool, of its
            # description and input schema (masked), the form mcp_catalog.py hashes the product's catalog in
            c = p.get("content")
            c = c if isinstance(c, str) else json.dumps(c)
            try:
                entries = json.loads(c).get("loaded") or []
            except Exception:
                entries = [{"tool_id": f"hirearchy::{m.group(1)}", "description": c, "input_schema": None} for m in re.finditer(r"hirearchy::(\w+)", c)]
            for e in entries:
                tid = str(e.get("tool_id", ""))
                if tid.startswith("hirearchy::"):
                    h = json.dumps({"description": e.get("description"), "input_schema": e.get("input_schema")}, sort_keys=True)
                    loads.setdefault(tid.split("::", 1)[1], hashlib.md5(mask(h, label).encode()).hexdigest())
    mem = None
    if start:
        m = re.search(r"<memories>.*?</memories>", start, re.S)
        mem = len(m.group(0)) if m else 0
        start = re.sub(r"<memories>.*?</memories>", "<MEMORIES>", start, flags=re.S)
    err = []
    for f in sorted(d.glob("turn-*.stderr.txt")):
        err += [re.sub(r"\d+", "#", mask(x, label)) for x in f.read_text(errors="replace").splitlines() if x.strip() and not x.startswith("[tool]")]
    return start, loads, empty, mem, err


def compare(pr: Path) -> tuple[list[str], list[str]]:
    notes, stops = [], []
    cat = {a: json.loads((pr / f"catalog-{a}.json").read_text())["tools"] for a in "RC" if (pr / f"catalog-{a}.json").is_file()}
    if set(cat) != {"R", "C"}:
        return notes, ["a product catalog is missing"]
    S = {s: session(pr / s, s) for s in SESS}
    starts = {s: v[0] for s, v in S.items()}
    if None in starts.values() or len(set(starts.values())) != 1:
        stops.append("session_start differs (masked): " + ", ".join(f"{s}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}" for s, v in starts.items()))
    notes.append("memories block lengths: " + ", ".join(f"{s}={v[3]}" for s, v in S.items()))
    errs = {s: v[4] for s, v in S.items()}
    if len({json.dumps(e) for e in errs.values()}) != 1:
        stops.append("non-[tool] stderr differs")
    for arm in "RC":
        a, b = S[f"probe-{arm}1"][1], S[f"probe-{arm}2"][1]
        for tool in set(a) & set(b):
            if a[tool] != b[tool]:
                stops.append(f"arm {arm}: tool {tool} loaded with different hashes in its two repetitions")
    # across arms: a loaded tool's hash is the catalog's when the products' catalog entries agree; a tool the catalogs disagree on is explained
    for tool in set(S["probe-R1"][1]) & set(S["probe-C1"][1]):
        if S["probe-R1"][1][tool] != S["probe-C1"][1][tool] and cat["R"].get(tool) == cat["C"].get(tool):
            stops.append(f"tool {tool}: the arms' loads differ while the products' catalogs agree")
    for arm in "RC":
        same = sorted(t for t, h in S[f"probe-{arm}1"][1].items() if cat[arm].get(t) == h)
        notes.append(f"arm {arm}: loaded tools whose hash equals the catalog's: {len(same)} of {len(S[f'probe-{arm}1'][1])} (reported)")
    for s, v in S.items():
        if v[2]:
            stops.append(f"{s}: {v[2]} failed empty-argument call(s)")
        sp = pr / s / "skill-proof.json"
        if not sp.is_file() or json.loads(sp.read_text()).get("verdict") != "PROVED":
            stops.append(f"{s}: skill proof not PROVED")
        t2 = pr / s / "turn-02.txt"
        if not t2.is_file() or "probe-memo" not in t2.read_text(errors="replace"):
            stops.append(f"{s}: turn 2's reply does not name probe-memo")
    if "retro" not in cat["R"] or "retro" in cat["C"]:
        stops.append("positive control: catalog-R lacks retro or catalog-C has it")
    notes.append(f"catalogs: R {len(cat['R'])} tools, C {len(cat['C'])}; differing entries: {sorted(t for t in set(cat['R']) | set(cat['C']) if cat['R'].get(t) != cat['C'].get(t))}")
    return notes, stops


def selfcheck(out: Path) -> int:
    """Constructed probe folders (F12 of the review): the four sessions alike -> PASS; each difference the arm setup does not explain ->
    STOP; a tool whose hash differs between the arms where the products' catalogs differ -> explained (PASS)."""
    import shutil

    def build(name, mut=None):
        pr = out / name
        shutil.rmtree(pr, ignore_errors=True)
        cat = {"R": {"retro": "r1", "whoami": "w1", "services": "s1"}, "C": {"whoami": "w1", "services": "s1"}}
        for s in SESS:
            arm = s[6]
            d = pr / s
            d.mkdir(parents=True)
            start = {"type": "session_start", "text": f"workspace /tmp/hirearchy-p2/{s}-1/x <memories>m</memories> {REPOS[0] if arm == 'C' else REPOS[1]}"}
            ld = [{"tool_id": "hirearchy::whoami", "description": "w", "input_schema": {}}, {"tool_id": "hirearchy::services", "description": "s", "input_schema": {}}]
            ld += [{"tool_id": "hirearchy::retro", "description": "r", "input_schema": {}}] if arm == "R" else []
            load = {"type": "tool_result", "toolCallId": "l1", "content": json.dumps({"loaded": ld})}
            rows = [{"payload": start}, {"payload": {"type": "tool_call", "toolCallId": "l1", "toolName": "tool_load", "args": {"tool_ids": ["hirearchy::*"]}}}, {"payload": load}]
            if mut:
                rows = mut(s, rows, d) or rows
            (d / "session-messages.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            (d / "turn-01.stderr.txt").write_text("[tool] x\nengine ready in 12 ms\n")
            if not (d / "skill-proof.json").exists():
                (d / "skill-proof.json").write_text(json.dumps({"verdict": "PROVED"}))
            (d / "turn-02.txt").write_text("services: probe-memo (lead)\n")
        for a in "RC":
            (pr / f"catalog-{a}.json").write_text(json.dumps({"tools": cat[a]}))
        return pr
    cases = []
    cases.append(("four alike sessions: PASS", not compare(build("alike"))[1]))
    (out / "pc").mkdir(parents=True, exist_ok=True)
    for a, tools in (("R", {"retro": "1", "whoami": "2"}), ("C", {"whoami": "3"})):
        (out / "pc" / f"catalog-{a}.json").write_text(json.dumps({"tools": tools}))
    cases.append(("no sessions: STOP (fail closed)", any("session_start" in s for s in compare(out / "pc")[1])))

    def start_diff(s, rows, d):
        if s == "probe-R2":
            rows[0]["payload"]["text"] += " an extra steering block"
    cases.append(("a session_start difference: STOP", any("session_start" in x for x in compare(build("start", start_diff))[1])))

    def empty(s, rows, d):
        if s == "probe-C2":
            rows.append({"payload": {"type": "tool_call", "toolCallId": "e1", "toolName": "tool_call", "args": {}, "status": "failed"}})
    cases.append(("a failed empty-argument call: STOP", any("empty-argument" in x for x in compare(build("empty", empty))[1])))

    def unproved(s, rows, d):
        if s == "probe-C1":
            (d / "skill-proof.json").write_text(json.dumps({"verdict": "NOT PROVED"}))
    cases.append(("a skill proof not PROVED: STOP", any("skill proof" in x for x in compare(build("proof", unproved))[1])))

    def within(s, rows, d):
        if s == "probe-R2":
            rows[2]["payload"]["content"] = rows[2]["payload"]["content"].replace('"description": "w"', '"description": "W2"')
    cases.append(("a tool loaded with two hashes within one arm: STOP", any("two repetitions" in x for x in compare(build("within", within))[1])))
    pr = build("control")
    (pr / "catalog-C.json").write_text(json.dumps({"tools": {"retro": "r1", "whoami": "w1", "services": "s1"}}))
    cases.append(("the positive control fails (retro in arm C's catalog): STOP", any("positive control" in x for x in compare(pr)[1])))

    def across(s, rows, d):
        if s.startswith("probe-C"):
            rows[2]["payload"]["content"] = rows[2]["payload"]["content"].replace('"description": "s"', '"description": "S other"')
    cases.append(("a tool the catalogs agree on, loaded differently in the two arms: STOP", any("catalogs agree" in x for x in compare(build("across", across))[1])))
    print("\n".join(f"{'ok' if v else 'MISMATCH'}  {n}" for n, v in cases))
    print(f"probe_compare selfcheck: {sum(v for _, v in cases)} of {len(cases)} ok")
    return 0 if all(v for _, v in cases) else 1


def main():
    if sys.argv[1:2] == ["--selfcheck"]:
        return selfcheck(Path(sys.argv[2]))
    pr = Path(sys.argv[1])
    notes, stops = compare(pr)
    for n in notes:
        print("note:", n)
    for s in stops:
        print("difference:", s)
    print("PROBE: PASS" if not stops else "PROBE: STOP: " + "; ".join(stops))
    return 0 if not stops else 1


if __name__ == "__main__":
    sys.exit(main())
