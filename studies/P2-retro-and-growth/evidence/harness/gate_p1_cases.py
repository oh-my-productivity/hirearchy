#!/usr/bin/env python3
"""P2 constructed cases for gate_p1.py (protocol 13.3; F4 and F12 of the review). Run by `gate_p1.py --selfcheck <dir>`.
Expectations written from P1's protocol 12.1-12.2 and P2's protocol 12.3 before the code ran. Each case is a small stream folder: root's
mail (msgs/sent, msgs/read) in the session-store-free format the evidence copy keeps, the study service's contract and playbook versions,
the watch re-derivation's files, turn-times.txt, lena-lines.txt, injection/request-args.json, measures/*.json."""
import json
import shutil
from pathlib import Path

import gate_p1 as G


def stamp(sec: int) -> str:
    return f"20261029T10{sec // 60:02d}{sec % 60:02d}000000"


def msg(d: Path, folder: str, mid: str, **meta):
    p = d / "msgs" / folder
    p.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(f"{k}: {json.dumps(v) if not isinstance(v, str) else repr(v)}" for k, v in {"id": mid, **meta}.items())
    (p / f"{mid}.md").write_text(f"---\n{fm}\n---\n{meta.get('_body', '')}\n")


def base(root: Path, name: str) -> Path:
    d = root / name
    shutil.rmtree(d, ignore_errors=True)
    svc = d / "services-all" / "lead--weekly-memo"
    (svc / "service").mkdir(parents=True)
    (svc / "playbook").mkdir(parents=True)
    (svc / "service" / "SERVICE.v1.md").write_text("---\nversion: 1\ncreated: '2026-10-29T10:00:00+00:00'\ndefined: '2026-10-29T10:00:00+00:00'\n"
                                                   "acceptance:\n- One memo.\n---\n")
    T = lambda s, **k: msg(d, "sent", f"{stamp(s)}-root-{s:04x}", **k)  # noqa: E731
    # case 1: request (10:00:10), delivered (10:00:20), rejected R1 (10:00:30), linked (10:00:40); case 2 likewise; then requests
    T(10, type="task", to="lead", service="weekly-memo", title="memo 1", _body="## Request\nnotes_file: 2026-10-05.md")
    msg(d, "read", f"{stamp(20)}-lead-0001", type="result", reply_to=f"{stamp(10)}-root-000a", status="done", **{"from": "lead"})
    T(30, type="note", reply_to=f"{stamp(10)}-root-000a", feedback="reject", source="human")
    T(40, type="note", reply_to=f"{stamp(30)}-root-001e", criterion="C1", source="human")
    T(50, type="task", to="lead", service="weekly-memo", title="memo 2", _body="## Request\nnotes_file: 2026-10-12.md")
    msg(d, "read", f"{stamp(60)}-lead-0002", type="result", reply_to=f"{stamp(50)}-root-0032", status="done", **{"from": "lead"})
    T(70, type="note", reply_to=f"{stamp(50)}-root-0032", feedback="reject", source="human")
    T(80, type="note", reply_to=f"{stamp(70)}-root-0046", criterion="C1", source="human")
    for f in ("sent", "read"):
        for p in (d / "msgs" / f).glob("*.md"):
            t = p.read_text().replace("id: ", "from: 'root'\nid: ", 1) if "from:" not in p.read_text() else p.read_text()
            p.write_text(t)
    (d / "lena-lines.txt").write_text("turn 1 | rules H6 | table rows none | facts: x\nturn 2 | rules VR-REJECT@2026-10-12 | table rows none | facts: x\n")
    (d / "turn-times.txt").write_text("turn 1: x  utc 2026-10-29T10:00:25+00:00 - 2026-10-29T10:00:45+00:00  exit 0\n"
                                      "turn 2: x  utc 2026-10-29T10:01:05+00:00 - 2026-10-29T10:01:25+00:00  exit 0\n")
    (d / "watch" / "lead--weekly-memo").mkdir(parents=True)
    (d / "watch" / "lead--weekly-memo" / "watch-mismatches.txt").write_text("no mismatches\n")
    (d / "watch" / "lead--weekly-memo" / "watch-rederived.json").write_text(json.dumps({"states": {"end": []}}))
    v = d / "watch-views" / "lead--weekly-memo"
    v.mkdir(parents=True)
    (v / "msgs").symlink_to(d / "msgs")
    (v / "service").symlink_to(svc / "service")
    (v / "playbook").symlink_to(svc / "playbook")
    (d / "quality").mkdir()
    (d / "quality" / "end.json").write_text(json.dumps({"services": [{"service": "weekly-memo", "watch": [], "escapes": [
        {"assertion": "R1", "rule": "link", "cause": "reviewer-miss"}]}]}))
    (d / "measures").mkdir()
    (d / "measures" / "assistant_facts.json").write_text(json.dumps({"x": {"hand_edits": {"k": 0, "n": 3}}}))
    (d / "measures" / "score_p2.json").write_text(json.dumps({"p2_delivered_versions": {"ok": True, "versions": 8}}))
    (d / "measures" / "judged.json").write_text(json.dumps({"g1_d_judged": {"value": True, "hits_decided": []}, "d8_presented_deliveries": {"value": []}}))
    (d / "empty-calls.txt").write_text("total: 0\n")
    (d / "end.txt").write_text("end retro-2-done at turn 2\n")
    return d


def pb(d: Path, v: int, **meta):
    fm = "\n".join(f"{k}: {json.dumps(x)}" for k, x in {"version": v, **meta}.items())
    (d / "services-all" / "lead--weekly-memo" / "playbook" / f"PLAYBOOK.v{v}.md").write_text(f"---\n{fm}\n---\n## Steps\n1. [P1] x\n")


def due(d: Path, item="P3", related=("R1", "R2")):
    (d / "watch" / "lead--weekly-memo" / "watch-rederived.json").write_text(json.dumps({"states": {"turn-02": [
        {"item": item, "state": "warning", "related": list(related), "retire_due": True}]}}))


def run(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    ok = []

    def case(name, got, want):
        ok.append((name, got, want))
    d = base(out, "plain")
    m = G.measures(d)
    case("a clean stream: every measure PASS or G1(b) VACUOUS", sorted({str(v).split(" ")[0] for v in G.flat(m).values()}), ["PASS", "VACUOUS"])
    # G1(b): retire due; the runtime retire in the call that recorded the second related answer (10:01:20, turn 2 ends 10:01:25)
    d = base(out, "g1b-pass")
    due(d)
    pb(d, 2, revised="2026-10-29T10:01:22+00:00", by="runtime (watch)", op="watch", item="P3")
    case("G1(b): the runtime retire in the call of the second related answer", G.g1(d)["b"].split(" ")[0], "PASS")
    d = base(out, "g1b-late")
    due(d)
    pb(d, 2, revised="2026-10-29T10:09:00+00:00", by="runtime (watch)", op="watch", item="P3")
    case("G1(b): a runtime retire minutes after that call", G.g1(d)["b"].split(" ")[0], "FAIL")
    d = base(out, "g1b-none")
    due(d)
    case("G1(b): retire due and no runtime retire", G.g1(d)["b"].split(" ")[0], "FAIL")
    d = base(out, "g1b-spurious")
    pb(d, 2, revised="2026-10-29T10:01:22+00:00", by="runtime (watch)", op="watch", item="P4")
    case("G1(b): a runtime retire of an item never due", G.g1(d)["b"].split(" ")[0], "FAIL")
    # G1(c) by tier
    d = base(out, "g1c-one")
    pb(d, 2, revised="2026-10-29T10:01:22+00:00", by="lead", op="add", admitted="b", why={"P3": ["R1"]})
    case("G1(c): rule (b) with one R id", G.g1(d)["c"].split(" ")[0], "FAIL")
    d = base(out, "g1c-two")
    pb(d, 2, revised="2026-10-29T10:01:22+00:00", by="lead", op="add", admitted="b", why={"P3": ["R1", "R2"]})
    case("G1(c): rule (b) with two human-tier R ids", G.g1(d)["c"].split(" ")[0], "PASS")
    d = base(out, "g1c-foreign")
    pb(d, 2, revised="2026-10-29T10:01:22+00:00", by="lead", op="add", admitted="b", why={"P3": ["R1", "R9"]})
    case("G1(c): an R id that is no human-tier rejection of the service", G.g1(d)["c"].split(" ")[0], "FAIL")
    d = base(out, "g1c-c")
    pb(d, 2, revised="2026-10-29T10:01:22+00:00", by="lead", op="add", admitted="c", why={"P3": ["R1", "C1"]})
    case("G1(c): rule (c) with a C id a human link names", G.g1(d)["c"].split(" ")[0], "PASS")
    # G1(f), G1(a), G1(d)
    d = base(out, "g1f")
    (d / "watch" / "lead--weekly-memo" / "watch-mismatches.txt").write_text("MISMATCH turn-02 P3 state pinned: re-derived 'warning', product 'kept'\n")
    case("G1(f): a pinned-key mismatch", G.g1(d)["f"].split(" ")[0], "FAIL")
    d = base(out, "g1f-since")
    (d / "watch" / "lead--weekly-memo" / "watch-mismatches.txt").write_text(
        "MISMATCH turn-02 P3 since pinned: re-derived '2026-10-29T10:01:20.699651+00:00', product '2026-10-29T10:01:20+00:00'\n")
    case("G1(f): `since` equal at whole seconds (P1's ruling 1)", G.g1(d)["f"].split(" ")[0], "PASS")
    d = base(out, "g1a")
    (d / "quality" / "turn-02.json").write_text(json.dumps({"services": [{"service": "weekly-memo", "watch": [{"item": "P3", "state": "kept", "related": ["R1"]}]}]}))
    case("G1(a): an item kept with a related rejection", G.g1(d)["a"].split(" ")[0], "FAIL")
    d = base(out, "g1d-missing")
    (d / "measures" / "judged.json").unlink()
    case("G1(d) and deliveries by copy: judged.json missing", (G.g1(d)["d"].split(" ")[0], G.measures(d)["deliveries by copy"].split(" ")[0]), ("NOT", "NOT"))
    d = base(out, "g1d-states")
    (d / "measures" / "judged.json").write_text(json.dumps({"g1_d_judged": {"value": True, "hits_decided": [{"hit": "x", "states_it": True}]}, "d8_presented_deliveries": {"value": []}}))
    case("G1(d): a hit that states the lesson", G.g1(d)["d"].split(" ")[0], "FAIL")
    # G2(b) and (c)
    d = base(out, "g2b-late")
    lp = d / "msgs" / "sent" / f"{stamp(80)}-root-0050.md"
    (d / "msgs" / "sent" / f"{stamp(80)}-root-0050.md").rename(d / "msgs" / "sent" / f"{stamp(95)}-root-005f.md")
    t = (d / "msgs" / "sent" / f"{stamp(95)}-root-005f.md").read_text().replace(f"{stamp(80)}-root-0050", f"{stamp(95)}-root-005f")
    (d / "msgs" / "sent" / f"{stamp(95)}-root-005f.md").write_text(t)
    msg(d, "sent", f"{stamp(90)}-root-005a", **{"from": "root"}, type="task", to="lead", service="weekly-memo", title="memo 3", _body="## Request\nnotes_file: 2026-10-19.md")
    g = G.g2(d)
    case("G2(b) and (c): an answer after the service's next request", (g["b"].split(" ")[0], g["c"].split(" ")[0]), ("FAIL", "FAIL"))
    _ = lp
    d = base(out, "g2b-accept")
    msg(d, "sent", f"{stamp(75)}-root-004b", **{"from": "root"}, type="note", reply_to=f"{stamp(50)}-root-0032", feedback="accept", source="human")
    g = G.g2(d)
    case("G2(b): a human accept of the case before the answer, outside 13.2's exception", g["b"].split(" ")[0], "FAIL")
    d = base(out, "g2a-missing")
    (d / "lena-lines.txt").write_text((d / "lena-lines.txt").read_text() + "turn 2 | rules TRAP-N@2026-10-12 | table rows none | facts: x\n")
    case("G2(a): a rejection rule without its own note", G.g2(d)["a"].split(" ")[0], "FAIL")
    # relayed reworks: the injection identified by request-args.json
    d = base(out, "relayed-inj")
    (d / "injection").mkdir()
    (d / "injection" / "request-args.json").write_text(json.dumps({"revises": f"{stamp(10)}-root-000a", "title": "Rework memo 1"}))
    msg(d, "sent", f"{stamp(100)}-root-0064", **{"from": "root"}, type="task", to="lead", service="weekly-memo", revises=f"{stamp(10)}-root-000a", source="relayed", title="Rework memo 1")
    case("relayed reworks: the injection's own task is excepted", G.measures(d)["relayed reworks sent by the assistant (the injection excepted)"].split(" ")[0], "PASS")
    msg(d, "sent", f"{stamp(110)}-root-006e", **{"from": "root"}, type="task", to="lead", service="weekly-memo", revises=f"{stamp(50)}-root-0032", source="relayed", title="Rework memo 2")
    case("relayed reworks: one more relayed rework by the assistant", G.measures(d)["relayed reworks sent by the assistant (the injection excepted)"].split(" ")[0], "FAIL")
    d = base(out, "relayed-noinj")
    msg(d, "sent", f"{stamp(100)}-root-0064", **{"from": "root"}, type="task", to="lead", service="weekly-memo", revises=f"{stamp(10)}-root-000a", source="relayed", title="Rework memo 1")
    case("relayed reworks: no injection record, one relayed rework", G.measures(d)["relayed reworks sent by the assistant (the injection excepted)"].split(" ")[0], "FAIL")
    # hand edits, empty calls, delivered versions, deliveries by copy
    d = base(out, "hand")
    (d / "measures" / "assistant_facts.json").write_text(json.dumps({"x": {"hand_edits": {"k": 1, "n": 3}}}))
    (d / "empty-calls.txt").write_text("total: 2\n")
    (d / "measures" / "judged.json").write_text(json.dumps({"g1_d_judged": {"value": True, "hits_decided": []},
                                                           "d8_presented_deliveries": {"value": [{"memo": "2026-10-12", "turn": 9, "wrong_dates_outside_trap": 1, "extra_rows": 0}]}}))
    m = G.measures(d)
    case("hand edits 1 of 3; empty calls 2; a presented version with a wrong date; a delivery by presentation",
         tuple(m[k].split(" ")[0] for k in ("hand edits", "empty-argument calls", "delivered versions (P2's form)", "deliveries by copy")), ("FAIL",) * 4)
    d = base(out, "presented-rejected")
    (d / "measures" / "judged.json").write_text(json.dumps({"g1_d_judged": {"value": True, "hits_decided": []},
                                                           "d8_presented_deliveries": {"value": [{"memo": "2026-10-12", "turn": 1, "wrong_dates_outside_trap": 1, "extra_rows": 0}]}}))
    case("F26: a version presented in turn 1 with a wrong date that Lena rejected in turn 2 (VR-REJECT@2026-10-12) is exempt",
         G.measures(d)["delivered versions (P2's form)"].split(" ")[0], "PASS")
    # C1 (F38 of review 3): score_p2's NOT DETERMINED is carried into the measure; the cut case is information (no FAIL-CLOSED prefix)
    nd = lambda v: (v.split(" (")[0], v.startswith("NOT DETERMINED (cut at turn "), "FAIL-CLOSED" in v)  # noqa: E731
    d = base(out, "cut-final-nd")
    (d / "end.txt").write_text("end cap-runs at turn 2\n")
    (d / "measures" / "score_p2.json").write_text(json.dumps({"p2_delivered_versions": {"ok": True, "versions": 8,
        "not_determined": ["final 2026-10-26 (rejected): cut at turn 2: cap-runs"],
        "verdict": "NOT DETERMINED (cut at turn 2: the memo's last version was rejected or not judged: final 2026-10-26 (rejected): cut at turn 2: cap-runs)"}}))
    case("C1: a cut stream whose memo-4 final was rejected: score_p2's NOT DETERMINED (cut) is carried, with no FAIL-CLOSED prefix",
         nd(G.measures(d)["delivered versions (P2's form)"]), ("NOT DETERMINED", True, False))
    d = base(out, "noend-final-nd")
    (d / "end.txt").unlink()
    (d / "measures" / "score_p2.json").write_text(json.dumps({"p2_delivered_versions": {"ok": True, "versions": 8,
        "not_determined": ["final 2026-10-26 (rejected): the stream's end is not recorded"],
        "verdict": "NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded: final 2026-10-26 (rejected))"}}))
    case("C1: the same with no end.txt: NOT DETERMINED (FAIL-CLOSED: ...)", nd(G.measures(d)["delivered versions (P2's form)"]), ("NOT DETERMINED", False, True))
    d = base(out, "presented-unjudged-cut")
    (d / "end.txt").write_text("end cap-runs at turn 2\n")
    (d / "measures" / "judged.json").write_text(json.dumps({"g1_d_judged": {"value": True, "hits_decided": []},
                                                           "d8_presented_deliveries": {"value": [{"memo": "2026-10-19", "turn": 2, "wrong_dates_outside_trap": 1, "extra_rows": 0}]}}))
    case("C1: a version presented in the cut turn with a slip and never judged: NOT DETERMINED (cut), not FAIL",
         nd(G.measures(d)["delivered versions (P2's form)"]), ("NOT DETERMINED", True, False))
    d = base(out, "versions-none")
    (d / "measures" / "score_p2.json").write_text(json.dumps({"p2_delivered_versions": {"ok": False, "versions": 0}}))
    case("delivered versions: no version scored fails closed", G.measures(d)["delivered versions (P2's form)"].split(" ")[0], "NOT")
    d = base(out, "hand-none")
    (d / "measures" / "assistant_facts.json").write_text(json.dumps({"x": {"hand_edits": {"k": 0, "n": 0}}}))
    case("hand edits: no copy at all fails closed", G.measures(d)["hand edits"].split(" ")[0], "NOT")
    lines = [f"{'ok' if g == w else 'MISMATCH'}  {c}: expected {w}, got {g}" for c, g, w in ok]
    lines.append(f"gate_p1 selfcheck: {sum(g == w for _, g, w in ok)} of {len(ok)} ok")
    print("\n".join(lines))
    return 0 if all(g == w for _, g, w in ok) else 1
