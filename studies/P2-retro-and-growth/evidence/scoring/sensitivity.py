"""P2 step 12: the labelled sensitivity for the four harness defects the stage gate found (5(a), 5(b), 6.2, 6.3).
REPORTED, NOT ADOPTED (P1's precedent): the frozen verdicts stand. Everything runs on byte copies of EV/R1 and EV/C1 under
/tmp/hirearchy-p2-score/copy/<variant>/ with harness copies under /tmp/hirearchy-p2-score/h-*/ (h-frozen = the frozen harness, verified
against MD5SUMS; h-5a, h-62, h-63, h-all = one exact patch each, patch.py). Nothing under EV/ is written.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EV = Path("/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence")
S = Path("/tmp/hirearchy-p2-score")
AM = {"R1": "2026-10-29T13:10:53Z", "C1": "2026-10-29T14:22:26Z"}
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
OUT = {}


def run(argv, cwd=None):
    r = subprocess.run([str(a) for a in argv], cwd=cwd, env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def fresh(variant: str) -> Path:
    root = S / "copy" / variant
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for l in ("R1", "C1"):
        shutil.copytree(EV / l, root / l, symlinks=True)
        for p in (root / l).rglob("*"):  # re-point the copied watch-views links at the copy, so no reader can reach EV through them
            if p.is_symlink():
                t = os.readlink(p)
                assert t.startswith(str(EV / l) + "/"), (p, t)
                p.unlink()
                p.symlink_to(str(root / l) + t[len(str(EV / l)):])
    return root


def readers(root: Path, h: str, labels=("R1", "C1"), steps=("extract", "watch", "score", "gate")):
    H = S / h
    for l in labels:
        d = root / l
        if "extract" in steps:
            rc, o = run(["python3", "-B", H / "extract_p2.py", d, "--checks"]); assert rc == 0, o[-2000:]
        if "watch" in steps:
            rc, o = run(["zsh", H / "watch_views.sh", d]); assert rc == 0, o[-2000:]
        if "score" in steps:
            rc, o = run(["python3", "-B", H / "score_p2.py", d, "--out", d / "measures", "--am-time", AM[l]]); assert rc == 0, o[-2000:]
        if "gate" in steps:
            rc, o = run(["python3", "-B", H / "gate_p1.py", d]); assert rc == 0, o[-2000:]


def flat(d: Path) -> dict:
    return json.loads((d / "p2" / "gate_p1.json").read_text())["flat"]


def aggregate(root: Path, h: str) -> str:
    rc, o = run(["python3", "-B", S / h / "aggregate.py", root, "--out", root / "aggregate.md"])
    assert rc == 0, o
    return re.search(r"\*\*Phase 2's exit criterion: .*", o).group(0)


# ------------------------------------------------------------------------------------------------ 5(b): rebuild memos/versions
def rebuild_versions(d: Path, team_names: bool) -> dict:
    """The corrected reader of 5(b): every committed version of every .md under the owner's tree with /work/ in its path (extract_mechanical.py
    522-536's rule), with the final-check seat taken only from an agent whose AGENT.md has kind: verifier (none in this script), read from
    the kept org-git.bundle. team_names: also read the team's own file name (`<date>-memo.md`) as the scorer's `memo-<date>.md`."""
    clone = d.parent / f"{d.name}-org"
    if clone.exists():
        shutil.rmtree(clone)
    rc, o = run(["git", "clone", "-q", d / "org-git.bundle", clone]); assert rc == 0, o
    git = lambda *a: subprocess.run(["git", "-C", str(clone), *a], capture_output=True, text=True, env=ENV).stdout  # noqa: E731
    owner = "lead"
    verifiers = []
    for ch in sorted((d / "org-files").glob(f"{owner}-*-AGENT.md")):
        m = re.search(r"^kind:\s*(\S+)", ch.read_text(errors="replace"), re.M)
        if m and m.group(1) == "verifier":
            verifiers.append(ch.name)
    seat = None  # no agent with kind: verifier under the owner (checked above)
    assert not verifiers, verifiers
    vdir = d / "memos" / "versions"
    shutil.rmtree(vdir)
    vdir.mkdir()
    files = [x for x in git("ls-files", owner).split() if x.endswith(".md") and "/work/" in x]
    vlog, renamed = [], {}
    for fpath in files:
        stem = Path(fpath).stem
        name_path = fpath
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-memo", stem)
        if team_names and m:
            stem = f"memo-{m.group(1)}"
            name_path = str(Path(fpath).with_name(stem + ".md"))
            renamed[fpath] = name_path
        hs = git("log", "--reverse", "--format=%h %cI", "--", fpath).strip().splitlines()
        for i, ln in enumerate(hs, 1):
            h, t = ln.split(" ", 1)
            body = git("show", f"{h}:{fpath}")
            (vdir / f"{stem}.v{i}.{h}.md").write_text(body)
            vlog.append(f"{name_path} v{i} {h} {t} md5 {hashlib.md5(body.encode()).hexdigest()}")
    (vdir / "INDEX.txt").write_text("\n".join(vlog) + "\n")
    if renamed:  # the copy log names the team's files; read them by the same mapping
        lp = d / "deliverables-log.txt"
        t = lp.read_text()
        for a, b in renamed.items():
            t = t.replace(a + " -> org-git commit", b + " -> org-git commit")
        lp.write_text(t)
    return {"seat": seat, "verifiers": verifiers, "files": len(files), "versions": len(vlog), "renamed": sorted(renamed)}


def score_summary(d: Path) -> dict:
    sp = json.loads((d / "measures" / "score_p2.json").read_text())
    pv = sp["p2_delivered_versions"]
    vs = sp["versions"]
    return {"versions_scored": len(vs), "copied": pv["versions"], "bad": pv["bad"], "exempt_rejected": pv["exempt_rejected"],
            "not_determined": pv["not_determined"], "score_p2_verdict": pv["verdict"],
            "per_version": [f"{x['memo']} v{x['version']} copied={x['copied']} lena={x['lena']} trap={x['trap']} wrong_outside_trap={len(x['wrong_dates_outside_trap'])} extra={len(x['extra_rows'])}" for x in vs],
            "finals": [f"{f['memo']} trap={f.get('trap')} wrong={len(f.get('wrong_dates') or [])} extra={len(f.get('extra_rows') or [])}" for f in sp["finals"] if "error" not in f]}


def main() -> int:
    # control: the frozen harness on byte copies gives the frozen readings
    root = fresh("frozen")
    readers(root, "h-frozen")
    OUT["control"] = {l: {"verdicts_equal_EV": (root / l / "p2" / "verdicts.txt").read_text() == (EV / l / "p2" / "verdicts.txt").read_text(),
                          "gate_flat_equal_EV": flat(root / l) == flat(EV / l)} for l in ("R1", "C1")}
    OUT["control"]["exit"] = aggregate(root, "h-frozen")

    # 5(a): the empty-call total's format
    root = fresh("5a")
    readers(root, "h-5a", steps=("gate",))
    OUT["5a"] = {l: {"frozen": flat(EV / l)["empty-argument calls"], "corrected": flat(root / l)["empty-argument calls"],
                     "total_line": [x for x in (EV / l / "empty-calls.txt").read_text().splitlines() if x.startswith("total")]} for l in ("R1", "C1")}

    # 5(b): the seat taken for the writer; versions rebuilt from org-git.bundle (b-i: the seat only; b-ii: the seat and the team's file names)
    for variant, names in (("5b-seat", False), ("5b-seat-names", True)):
        root = fresh(variant)
        res = {}
        for l in ("R1", "C1"):
            rb = rebuild_versions(root / l, names)
            readers(root, "h-frozen", labels=(l,), steps=("score", "gate"))
            res[l] = {"rebuild": rb, "frozen": flat(EV / l)["delivered versions (P2's form)"],
                      "corrected": flat(root / l)["delivered versions (P2's form)"], "score": score_summary(root / l)}
        OUT[variant] = res

    # 6.2: the G1(f) view for the second service, with the view's own service named
    root = fresh("62")
    readers(root, "h-62", steps=("watch", "gate"))
    OUT["62"] = {}
    for l in ("R1", "C1"):
        views = {}
        for v in sorted((root / l / "watch").glob("*--*")):
            mm = (v / "watch-mismatches.txt").read_text().splitlines()
            fv = (EV / l / "watch" / v.name / "watch-mismatches.txt")
            views[v.name] = {"service_in_view": json.loads((v / "watch-rederived.json").read_text())["service"],
                             "frozen_service_in_view": json.loads((EV / l / "watch" / v.name / "watch-rederived.json").read_text())["service"],
                             "corrected_total": mm[-1], "frozen_total": fv.read_text().splitlines()[-1]}
        OUT["62"][l] = {"frozen": flat(EV / l)["G1(f)"][:200], "corrected": flat(root / l)["G1(f)"][:300], "views": views}

    # 6.3: a relative EV in rederive_p2.Org.view (the 7.2 window at retro 1, B1)
    root = fresh("63")
    b1 = json.loads((root / "R1" / "org-files" / "retros.json").read_text())["briefs"][0]["at"]
    res = {}
    for tag, h, path in (("relative, frozen", "h-frozen", "R1"), ("absolute, frozen", "h-frozen", str(root / "R1")),
                         ("relative, corrected", "h-63", "R1")):
        out = S / "copy" / "63-out" / re.sub(r"\W+", "-", tag)
        if out.exists():
            shutil.rmtree(out)
        rc, o = run(["python3", "-B", S / h / "rederive_p2.py", path, "--out", out, "--as-of", b1], cwd=root)
        assert rc == 0, o[-2000:]
        sig = json.loads((out / "signals.json").read_text())
        res[tag] = {"checker_due": sig["checker_due"], "service_due": sig["service_due"],
                    "windows": {c["service"]: len(c["window"]) for c in sig["checker"]},
                    "candidates": {c["service"]: [k["key"] for k in c["candidates"]] for c in sig["checker"]}}
    # the p2/ checks with a relative stream path, frozen and corrected
    for tag, h in (("relative, frozen", "h-frozen"), ("relative, corrected", "h-63")):
        rc, o = run(["python3", "-B", S / h / "extract_p2.py", "R1", "--checks"], cwd=root)
        assert rc == 0, o[-2000:]
        res[f"p2/verdicts.txt with a {tag} reader equals EV's"] = (root / "R1" / "p2" / "verdicts.txt").read_text() == (EV / "R1" / "p2" / "verdicts.txt").read_text()
        res[f"p2/verdicts.txt with a {tag} reader"] = (root / "R1" / "p2" / "verdicts.txt").read_text().splitlines()[:8]
    OUT["63"] = res

    # all four corrections at once (h-all, versions rebuilt with the team's names): the exit reading
    root = fresh("all")
    for l in ("R1", "C1"):
        rebuild_versions(root / l, True)
    readers(root, "h-all")
    OUT["all"] = {l: {k: v for k, v in flat(root / l).items() if flat(EV / l).get(k) != v} for l in ("R1", "C1")}
    OUT["all"]["exit"] = aggregate(root, "h-all")
    (S / "sensitivity.json").write_text(json.dumps(OUT, indent=1))
    print(json.dumps(OUT, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
