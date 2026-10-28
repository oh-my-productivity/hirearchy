#!/usr/bin/env python3
"""P1 self-check on the kept G0 and E7 mail with a constructed item A (design 18.6: "so the harness's judged(c), D and K are checked on
the flows the study will see").

For each kept stream (G0 m1-s1..s3, E7 s1..s3; read-only), the stream's real mail and contract versions are kept and its free-text
playbook is replaced by a constructed item-format history: v1 (`op: first`, by root, two steps) and v2, an `add` of item A, a rule
`WHY R1; <the first id R1's human link names>` (18.4.1's A), revised 1 s after the first human rework of memo 1's case that root sent
after R1's answer (its "rework run"), or 1 s after the answer when root sent none. Variant A' is the same rule with `WHY <that C id>` only, so that memo 1's case
can be a candidate too and E, D and K exist on a 3-memo stream.

The expected values in selfcheck/p1-kept-mail-expected.json were derived by hand from section 3's definitions and the streams' message
listings (protocol 13.4), before this script's first run; they are never copied from its output. Iteration 3 adds, on G0 m1-s1..s3, the
D14 ledger's completeness check of protocol 6.3 (rederive_watch.py --spend --stream: a ledger without one case of the mail lists it in
`missing_cases`, an entry that names no case of the mail in `extra_cases`).

    python3 -B kept_mail.py [--out DIR]   ->  `kept_mail: <ok> of <n> checks OK`; exit 0 iff all pass
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rederive_watch as rw  # noqa: E402

STUDIES = Path("/Volumes/workspace/hirearchy/studies")
STREAMS = {"G0 m1-s1": "G0-noise-baseline/evidence/m1-s1", "G0 m1-s2": "G0-noise-baseline/evidence/m1-s2",
           "G0 m1-s3": "G0-noise-baseline/evidence/m1-s3", "E7 s1": "E7-org-growth-0a4-recheck/evidence/s1",
           "E7 s2": "E7-org-growth-0a4-recheck/evidence/s2", "E7 s3": "E7-org-growth-0a4-recheck/evidence/s3"}
EXPECTED = Path(__file__).resolve().parent / "selfcheck" / "p1-kept-mail-expected.json"


def constructed(world: rw.World, variant: str) -> tuple[rw.World, str]:
    mail = rw.Mail(world)
    r1 = mail.rejections[0]
    links = mail.human_links(r1.id)
    ans_t = min([x.t for x in links] + ([mail.crit.answering(r1.id).defined] if mail.crit.answering(r1.id) else []))
    cid = next(i for i in links[0].ids if i.upper().startswith("C")) if links else mail.crit.answer_ids(mail.crit.answering(r1.id).version)[0]
    case1 = mail.case_of(r1.task)
    reworks = sorted((t for t in mail.tasks.values() if t.revises and t.source == "human" and t.t > ans_t
                      and mail.case_of(t.id) == case1), key=lambda t: t.id)
    live = (reworks[0].t if reworks else ans_t) + timedelta(seconds=1)
    v1t = world.contracts[0].defined + timedelta(microseconds=1)
    steps = (rw.Item("P1", "step", "Read the request."), rw.Item("P2", "step", "Delegate the memo to the writer."))
    a = rw.Item("P3", "rule", "The memo starts with a one-line 'Summary:' of the meeting.", "always")
    why = ("R1", cid) if variant == "A" else (cid,)
    pb = [rw.PVersion(1, v1t, "root", "first", "", "", steps, {}, (), 0, "", False),
          rw.PVersion(2, live, "lead", "add", "P3", "c", steps + (a,), {"P3": why}, (), 0, "", False)]
    w2 = rw.World(world.service, world.owner, world.client, world.created, world.tasks, world.results, world.verdicts, world.links,
                  world.contracts, pb)
    return w2, rw.iso(live)


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    exp = json.loads(EXPECTED.read_text())
    lines, ok, n = [], 0, 0
    got_all = {}
    for name, rel in STREAMS.items():
        world = rw.load_world(STUDIES / rel)
        for variant in ("A", "A'"):
            w2, live = constructed(world, variant)
            row = next(r for r in rw.Derivation(w2).states(None) if r["item"] == "P3")
            got = {"live_from": live, "state": row["state"], "k": row["k"], "clean": row["clean"], "waiting": row["waiting"],
                   "related": row["related"], "pending": row["pending"],
                   "judged_tasks": [(j["judged_task"] or "")[-4:] for j in row["judged"]],
                   "superseded_before": [j["superseded_before"] for j in row["judged"]],
                   "E": (row["E"] or "")[11:19] or None, "D": (row["D"] or "")[11:19] or None, "K": (row["K"] or "")[11:19] or None}
            got_all[f"{name} {variant}"] = got
            want = exp.get(f"{name} {variant}", {})
            for key, wv in want.items():
                n += 1
                good = got.get(key) == (tuple(wv) if False else wv) or (isinstance(wv, list) and list(got.get(key) or []) == wv)
                ok += good
                lines.append(f"{'OK  ' if good else 'FAIL'} {name} {variant} {key}: got {got.get(key)!r}" + ("" if good else f", want {wv!r}"))
    # protocol 6.3 (P2-M3): the D14 ledger's completeness against the kept G0 mail (3 memos, so 3 cases; the injection is a rework of
    # memo 1's case): a ledger without one case lists it in missing_cases, an entry naming no case is listed in extra_cases
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="p1-spend-"))
    try:
        for name in ("G0 m1-s1", "G0 m1-s2", "G0 m1-s3"):
            sd = STUDIES / STREAMS[name]
            cases = rw.Mail(rw.load_world(sd)).cases()
            entry = {"state": "done", "runs": 10, "budget": 12, "contract_budget": 12, "lena_plan_budget": 12, "lena_grants": [], "d14_used": 10}
            led = tmp / f"{name[-5:]}.json"
            led.write_text(json.dumps({"cases": {**{c: entry for c in cases[1:]}, "20990101T000000000000-root-ffff": entry}}))
            rw.run_spend(led, None, tmp / name[-5:], sd)
            res = json.loads((tmp / name[-5:] / "spend-rederived.json").read_text())
            n += 1
            got = (len(cases), res["missing_cases"], res["extra_cases"])
            want = (3, cases[:1], ["20990101T000000000000-root-ffff"])
            ok += got == want
            lines.append(f"{'OK  ' if got == want else 'FAIL'} {name} spend ledger completeness (6.3): cases, missing, extra: got {got!r}"
                         + ("" if got == want else f", want {want!r}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    lines.append(f"kept_mail: {ok} of {n} checks OK")
    text = "\n".join(lines)
    print(text)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "kept_mail.out").write_text(text + "\n")
        (out / "kept_mail.json").write_text(json.dumps(got_all, indent=1))
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
