#!/usr/bin/env python3
"""P1 scoring step (step 12): the manager's scoring rulings applied OVER the frozen harness, never inside it.

    python3 -B score_p1.py <EV> <label> [<label> ...]

Nothing under EV/harness/ is edited; the frozen modules are imported read-only (sys.dont_write_bytecode) and, where a ruling says so, ONE
reader is substituted in memory. Every output goes to EV/scoring/<label>/. What it does, per stream, each step tied to its ruling:

 1. memo input (manager-decision-memo-input-name.md, items 2-3, and its addendum): the stream's memo input name and value form, read from
    root's first request (the input whose value's base name is 2026-10-05.md) and cross-checked against SERVICE.md v1's inputs ->
    measures/memo-input.txt. When the name is `notes_file` and the value a bare file name, the frozen memo reader runs as is; otherwise
    guarantees.memo_of_task is replaced, in memory, by the same reader with that one name substituted and the date read from the value's base
    name. requests-by-turn is recomputed from root's sent mail -> measures/requests-by-turn.rederived.txt (the frozen file is not edited).
    Fail-closed (item 3): every memo whose first request exists in root's sent mail must be in the memo-to-case map; a missing one makes every
    part that needs the map (G1, G2 (a)-(c)) NOT DETERMINED.
 2. lena-lines line form (manager-decision-stage-1-gate.md item 2): for F1 and I1 a normalised copy, `rules ` inserted after `turn <n> | `
    where missing and nothing else -> measures/lena-lines.normalised.txt (+ .diff, + a note); guarantees.lena_turns reads it in memory.
    Fail-closed, every stream: when the frozen parser reads fewer Lena turns than lena-lines.txt has `turn <n> |` lines, G2(a) is NOT
    DETERMINED, never PASS.
 3. `since` precision (manager-decision-stage-1-gate.md item 1): over the frozen comparison output (the frozen rederive_watch.run_stream's
    watch-mismatches.txt, reproduced into scoring/<label>/frozen/watch/), a `since` mismatch is cleared when the product's and the
    re-derivation's values are equal after both are truncated to whole seconds in UTC; every cleared line is listed with both values
    (watch-ruled/since-cleared.txt); every other line stands (watch-ruled/watch-mismatches.txt, with the frozen count line recomputed).
 4. guarantees.py's g1/g2 (frozen) on the stream with 1-3 applied -> guarantees/.
 5. assistant_facts.py (frozen) with the memo input's name substituted in its one reader (Case.task, assistant_facts.py:238) when the name is
    not notes_file -> measures/ (item 2 of the memo-input ruling).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sys
from datetime import timezone
from pathlib import Path

sys.dont_write_bytecode = True
EV = Path(sys.argv[1]).resolve()
H = EV / "harness"
sys.path.insert(0, str(H))
import rederive_watch as rw  # noqa: E402  (frozen)
import guarantees as gu  # noqa: E402  (frozen)

MEMOS = gu.MEMOS
FROZEN_MEMO_OF_TASK = gu.memo_of_task
FROZEN_LENA_TURNS = gu.lena_turns


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def fm(text: str):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def root_requests(D: Path, name: str):
    """Root's new requests (type task, no revises) in msgs/sent, each (id, value of the memo input, memo date)."""
    out = []
    for f in sorted((D / "msgs" / "sent").glob("*.md")):
        head, body = fm(f.read_text(errors="replace"))
        if not re.search(r"^type:\s*task\s*$", head, re.M) or re.search(r"^revises:\s*\S", head, re.M):
            continue
        m = re.search(rf"^- {re.escape(name)}:\s*(\S+)", body, re.M)
        if m:
            d = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(m.group(1)))
            out.append((f.stem, m.group(1), d.group(1) if d else None))
    return out


def memo_input(D: Path, out: Path) -> dict:
    first = None
    for f in sorted((D / "msgs" / "sent").glob("*.md")):
        head, body = fm(f.read_text(errors="replace"))
        if not re.search(r"^type:\s*task\s*$", head, re.M):
            continue
        blk = re.search(r"^## Request\n(.*?)(?:\n## |\Z)", body, re.S | re.M)
        for m in re.finditer(r"^- ([A-Za-z_][\w-]*):\s*(\S+)", blk.group(1) if blk else "", re.M):
            if os.path.basename(m.group(2)) == "2026-10-05.md":
                first = (f.stem, m.group(1), m.group(2))
                break
        if first:
            break
    v1 = next(iter(sorted((D / "service").glob("history--SERVICE.v1.md"))), None)
    v1_inputs = re.findall(r"^- name:\s*(\S+)", fm(v1.read_text())[0], re.M) if v1 else []
    name, value = (first[1], first[2]) if first else (None, None)
    frozen_ok = name == "notes_file" and value is not None and re.match(r"^\d{4}-\d{2}-\d{2}", value) is not None
    info = {"first_request": first[0] if first else None, "name": name, "value": value, "service_v1_inputs": v1_inputs,
            "name_in_v1": name in v1_inputs, "frozen_reader_reads_it": frozen_ok,
            "reader": "frozen (notes_file, bare file name)" if frozen_ok else
            f"substituted in memory: name {name!r}, date from the value's base name (manager-decision-memo-input-name.md + addendum)"}
    (out / "memo-input.txt").write_text(
        f"memo input of {D.name} (manager-decision-memo-input-name.md, item 2; addendum for a path value)\n"
        f"root's first request: {info['first_request']}\nname: {name}\nvalue: {value}\n"
        f"SERVICE.md v1 inputs: {', '.join(v1_inputs) or '(none)'}; the name is in v1: {info['name_in_v1']}\n"
        f"frozen reader (notes_file: <date>) reads it: {frozen_ok}\nreader used: {info['reader']}\n")
    return info


def substituted_memo_of_task(name: str):
    def memo_of_task(body: str) -> str:  # guarantees.py:66-68 with the one name substituted, the date from the value's base name
        m = re.search(rf"{re.escape(name)}:\s*(\S+)", body or "")
        if not m:
            return ""
        d = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(m.group(1)))
        return d.group(1) if d else ""
    return memo_of_task


def requests_rederived(D: Path, name: str, out: Path) -> None:
    """after_turn.sh:86-97's reading (root's new requests by memo, as of each turn's after_turn), recomputed from the copied mail: a request
    counts for turn N when its id stamp is before turn N's first quality snapshot start (quality/calls.txt), else before the turn's end + 20 s."""
    reqs = root_requests(D, name)
    snaps = {t: s for t, s, _ in rw.snapshot_times(D)}
    tt = gu.turn_times(D)
    lines = [f"# requests-by-turn, re-derived by the scorer from msgs/sent (input name {name!r}; manager-decision-memo-input-name.md item 2); "
             "the frozen requests-by-turn.txt is not edited", ""]
    for n in sorted(tt):
        cut = snaps.get(f"turn-{n:02d}") or (tt[n][1] + gu.BOUNDARY)
        got = list(dict.fromkeys(d for i, _, d in reqs if d and rw.stamp_of(i) < cut))
        lines.append(f"turn {n:02d}: root's new requests by notes file: {' '.join(got) or '(none)'}; memo 4's request (2026-10-26.md) sent: "
                     f"{'yes' if '2026-10-26' in got else 'no'}  (cut-off {rw.iso(cut)})")
    lines += ["", "requests (id, value, memo): " + "; ".join(f"{i} {v} {d}" for i, v, d in reqs)]
    (out / "requests-by-turn.rederived.txt").write_text("\n".join(lines) + "\n")


def normalise_lena(D: Path, out: Path) -> Path | None:
    src = D / "lena-lines.txt"
    old = src.read_text(errors="replace").splitlines(keepends=True)
    new = [re.sub(r"^(turn \d+ \| )(?!rules? )", r"\1rules ", ln) for ln in old]
    if new == old:
        return None
    dst = out / "lena-lines.normalised.txt"
    dst.write_text("".join(new))
    (out / "lena-lines.normalised.diff").write_text("".join(difflib.unified_diff(old, new, f"{D.name}/lena-lines.txt", str(dst.name))))
    (out / "lena-lines.normalised.note.txt").write_text(
        f"A normalised copy of {D.name}/lena-lines.txt (manager-decision-stage-1-gate.md item 2): `rules ` inserted after `turn <n> | ` where it "
        f"was missing, nothing else changed ({sum(1 for a, b in zip(old, new) if a != b)} lines). The original is not edited. md5 original "
        f"{md5(src)}, copy {md5(dst)}.\n")
    return dst


def since_ruling(frozen_watch: Path, out: Path) -> dict:
    lines = (frozen_watch / "watch-mismatches.txt").read_text().splitlines()
    body = lines[:-1] if lines and re.match(r"^\d+ mismatches \(", lines[-1]) else lines
    kept, cleared = [], []
    pat = re.compile(r"^MISMATCH (\S+) (P\d+) since (pinned|unpinned): re-derived '([^']*)', product '([^']*)'$")
    for ln in body:
        m = pat.match(ln)
        if m:
            a, b = rw.parse_time(m.group(4)), rw.parse_time(m.group(5))
            ta = a.astimezone(timezone.utc).replace(microsecond=0) if a else None
            tb = b.astimezone(timezone.utc).replace(microsecond=0) if b else None
            if ta is not None and ta == tb:
                cleared.append(f"{ln}  -> cleared: both {ta.strftime('%Y-%m-%dT%H:%M:%SZ')} at whole seconds (UTC)")
                continue
        kept.append(ln)
    n_p = sum(1 for m in kept if m.startswith(("MISMATCH", "MISSING")) and " unpinned:" not in m)
    n_u = sum(1 for m in kept if m.startswith("MISMATCH") and " unpinned:" in m)
    n_s = sum(1 for m in kept if m.startswith("SERVICES-MISMATCH"))
    n_r = sum(1 for m in kept if m.startswith("SERVICES-UNREAD"))
    n_l = sum(1 for m in kept if m.startswith("RACE-LOWER"))
    n_x = sum(1 for m in kept if m.startswith("UNREAD"))
    total = (f"{n_p + n_u} mismatches ({n_p} on pinned keys, {n_u} on unpinned keys); {n_s} services mismatches; {n_r} services lines "
             f"unread; {n_l} lower-margin race matches (reported); {n_x} snapshots unread")
    out.mkdir(parents=True, exist_ok=True)
    (out / "watch-mismatches.txt").write_text("\n".join(kept + [total]) + "\n")
    (out / "since-cleared.txt").write_text(
        "# `since` mismatches cleared at whole-second precision in UTC (manager-decision-stage-1-gate.md item 1); each with both values\n"
        + "\n".join(cleared) + f"\n# cleared: {len(cleared)} ({sum(1 for c in cleared if ' pinned:' in c)} pinned, "
        f"{sum(1 for c in cleared if ' unpinned:' in c)} unpinned); frozen file: {frozen_watch / 'watch-mismatches.txt'} md5 "
        f"{md5(frozen_watch / 'watch-mismatches.txt')}\n")
    return {"frozen_total": lines[-1] if lines else "", "ruled_total": total, "cleared": len(cleared),
            "cleared_pinned": sum(1 for c in cleared if " pinned:" in c), "remaining": kept}


def requested_memos(D: Path, name: str) -> set[str]:
    return {d for _, _, d in root_requests(D, name) if d}


def score(label: str) -> dict:
    D = EV / label
    S = EV / "scoring" / label
    meas = S / "measures"
    meas.mkdir(parents=True, exist_ok=True)
    rep: dict = {"label": label}
    mi = memo_input(D, meas)
    rep["memo_input"] = mi
    name = mi["name"] or "notes_file"
    requests_rederived(D, name, meas)
    gu.memo_of_task = FROZEN_MEMO_OF_TASK if mi["frozen_reader_reads_it"] else substituted_memo_of_task(name)
    norm = normalise_lena(D, meas)
    gu.lena_turns = (lambda _D, _p=norm: [t for t in map(gu.lena_line, _p.read_text(errors="replace").splitlines()) if t]) if norm \
        else FROZEN_LENA_TURNS
    rep["lena_lines"] = str(norm.relative_to(EV)) if norm else f"{label}/lena-lines.txt (frozen form)"
    sr = since_ruling(S / "frozen" / "watch", S / "watch-ruled")
    rep["since"] = {k: v for k, v in sr.items() if k != "remaining"}
    s = gu.load_stream(D, S / "watch-ruled")
    # fail-closed checks
    src = norm or (D / "lena-lines.txt")
    n_lines = sum(1 for ln in src.read_text(errors="replace").splitlines() if re.match(r"^turn \d+ \|", ln))
    rep["lena_parse"] = {"turn_lines": n_lines, "parsed": len(s.turns)}
    want = requested_memos(D, name)
    rep["memo_map"] = {"requested": sorted(want), "mapped": dict(sorted(s.memo_case.items())), "missing": sorted(want - set(s.memo_case))}
    a, b = gu.g1(s), gu.g2(s)
    notes = []
    if rep["memo_map"]["missing"]:
        why = f"NOT DETERMINED (memo-to-case map misses {', '.join(rep['memo_map']['missing'])}: manager-decision-memo-input-name.md item 3)"
        for k in "abcdef":
            if not str(a[k]["verdict"]).startswith("FAIL"):
                a[k]["verdict"] = why
        for k in "abc":
            b[k]["verdict"] = why
        notes.append(why)
    if n_lines > len(s.turns):
        b["a"]["verdict"] = (f"NOT DETERMINED (the parser read {len(s.turns)} of {n_lines} Lena turns: manager-decision-stage-1-gate.md "
                             f"item 2, fail-closed)")
        notes.append(b["a"]["verdict"])
    a["scorer_notes"] = b["scorer_notes"] = notes
    g = S / "guarantees"
    g.mkdir(parents=True, exist_ok=True)
    for nm, d in (("g1", a), ("g2", b)):
        (g / f"{nm}.json").write_text(json.dumps(d, indent=1, default=str))
        (g / f"{nm}.txt").write_text(gu.render(nm.upper(), d))
    (g / "orders.json").write_text(json.dumps(a.get("orders", {}), indent=1, default=str))
    (g / "roles.txt").write_text(gu.roles_text(a["roles"], s.stream_roles))
    rep["g1"] = {k: a[k]["verdict"] for k in "abcdef"}
    rep["g2"] = {k: b[k]["verdict"] for k in "abc"}
    # assistant_facts with the substituted reader (memo-input ruling item 2), only when the frozen one cannot read the name
    if name != "notes_file":
        import assistant_facts as af  # frozen
        frozen_task = af.Case.task

        def task(self, tid, depth=0, _n=name):  # assistant_facts.py:234-248 with the one name substituted
            m = self.msgs.get(tid)
            if not m or depth > 8:
                return None
            nf = re.search(rf"^- {re.escape(_n)}: (\S+)", m["body"], re.M)
            d = (af.date_in(nf.group(1)) if nf else None) or af.date_in(m["hdr"].get("title", ""))
            if d:
                return d
            for k in ("revises", "reply_to"):
                if m["hdr"].get(k):
                    d = self.task(m["hdr"][k], depth + 1)
                    if d:
                        return d
            return None
        af.Case.task = task
        afo = meas / "assistant_facts-substituted"
        afo.mkdir(exist_ok=True)
        rc = af.main([str(D), "--out", str(afo)]) if hasattr(af, "main") else None
        af.Case.task = frozen_task
        rep["assistant_facts"] = f"re-run with {name!r} substituted -> {afo.relative_to(EV)} (exit {rc})"
    (S / "score_p1-report.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


if __name__ == "__main__":
    for lab in sys.argv[2:]:
        r = score(lab)
        print(json.dumps({k: r[k] for k in ("label", "lena_parse", "memo_map", "g1", "g2")}, default=str))
        print("  since:", r["since"])
