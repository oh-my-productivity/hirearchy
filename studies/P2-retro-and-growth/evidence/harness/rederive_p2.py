#!/usr/bin/env python3
"""P2 independent re-derivation (protocol 13; F-G0-4; P2-E, P2-S, P2-X3, the gate's item 2).

Written from the design's TEXT only: docs/design/org-growth-phase-2.md sections 3 (definitions), 4 (4.2 the ledger, 4.4 effectiveness, 4.5
labels, 4.5a items, 4.9 thresholds), 7 (7.1, 7.2, 7.5), 10.1 (added words), 21 and 22; the Phase 1 design 3 (text tokens, lineage, the
subjects of a rejection) through P1's own independent `rederive_watch.py` (unchanged; its `Mail` and `Criteria` give cases, deliveries,
rejection ids, subjects, lineage and criterion ids); the 0a/0a.2/0b texts for records and tiers. The author did NOT open src/hirearchy/ of
either product (harness/CHANGES.md). The file formats were read from kept P1 evidence and from the self-check's throwaway orgs. It imports
no product code; Python 3.11 with PyYAML.

    python3 -B rederive_p2.py <stream evidence dir> --out <dir> [--as-of ISO] [--since ISO] [--t0 ISO]

The stream evidence dir is copy_org_evidence.sh's: msgs/, services-all/<owner>--<name>/{service,playbook}/, org-copy/ (the org's files
without .git), charter-history.txt, org-files/retros.json. Writes into <dir>:
  shapes.json     the one-off cases and D5's shape groups (section 3) with the relation that joined them
  signals.json    7.1, 7.2 and 7.5 as of --as-of (default: the end): each candidate with its key, evidence, time reached, and the 7.2
                  estimate (c, f, r, p, net); `service_due` and `checker_due` (protocol 11 item 2)
  d7.json, d8.json  D7's outcomes and D8's labels for the window (--since, --as-of], as tuples
  edits.json      the unprompted charter edits after --t0 (section 3 with L21's three non-edit cases), each pair with its reason
  ledger.json     the ledger's records checked against the recording rule (4.2) and the lapse rule
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2lib as L  # noqa: E402
import rederive_watch as RW  # noqa: E402  (P1's, unchanged)

DEFAULTS = {"after_verdicts": 3, "window": 3, "carry": 3, "items": 3, "shape_cases": 3, "shape_overlap": 0.6, "criterion_cases": 3,
            "escapes": 2, "window_cases": 10, "saturation": 0.45, "added_words": 3, "accepted_cases": 3}
BASE_RUNS = {"reviewer": 1}  # 7.2: c = the template's base_runs (1 for reviewer) + 1 run of the owner


def iso(d):
    return d.isoformat() if d else None


# ------------------------------------------------------------------------------------------------------------------ loading
class Org:
    def __init__(self, ev: Path):
        self.ev = ev
        self.copy = ev / "org-copy"
        self.msgs = L.evidence_msgs(ev)
        self.sent = {k: m for k, m in self.msgs.items() if m.get("from") == L.ROOT}
        self.thresholds = self._thresholds()
        self.agents = self._agents()
        allsv = sorted(p.name for p in (ev / "services-all").glob("*--*") if p.is_dir())
        self.services = [x for x in allsv if not x.split("--", 1)[1].startswith(".retired")]
        self.retired_services = [x for x in allsv if x.split("--", 1)[1].startswith(".retired")]
        ledger = ev / "org-files" / "retros.json"
        self.ledger = json.loads(ledger.read_text()) if ledger.is_file() else {"briefs": [], "asked": []}

    def _thresholds(self) -> dict:
        t = dict(DEFAULTS)
        om = self.copy / "ORG.md"
        if om.is_file():
            meta, _ = L.split_fm(om.read_text(errors="replace"))
            r = meta.get("retro") if isinstance(meta.get("retro"), dict) else {}
            for k, v in (r or {}).items():
                if k in t:
                    try:
                        t[k] = type(DEFAULTS[k])(float(v)) if isinstance(DEFAULTS[k], float) else int(v)
                    except (TypeError, ValueError):
                        pass
            t["items"] = min(t["items"], 3)
        return t

    def _agents(self) -> dict[str, dict]:
        out = {}
        for f in sorted(self.copy.rglob("AGENT.md")) if self.copy.is_dir() else []:
            rel = f.relative_to(self.copy)
            retired = ".retired" in rel.parts
            addr = "/".join(rel.parts[:-1])
            meta, body = L.split_fm(f.read_text(errors="replace"))
            out[addr] = {"meta": meta, "body": body, "retired": retired}
        return out

    def live_agent(self, addr):
        a = self.agents.get(addr)
        return a if a and not a["retired"] else None

    def is_verifier(self, addr: str) -> bool:
        a = self.agents.get(addr)
        if not a:
            return False
        m = a["meta"]
        if "kind" in m:
            return m.get("kind") == "verifier"
        return str(m.get("role", "")) in L.VERIFIER_TITLES

    def view(self, svc_dir: str) -> Path:
        """A P1-shaped view of one service (msgs, service/, playbook/), for rederive_watch's loaders."""
        d = Path(tempfile.mkdtemp(prefix="view-", dir=str(self.ev)))
        (d / "msgs").symlink_to(self.ev / "msgs")
        src = self.ev / "services-all" / svc_dir
        for k in ("service", "playbook"):
            if (src / k).is_dir():
                (d / k).symlink_to(src / k)
            else:
                (d / k).mkdir()
        return d

    def world(self, svc_dir: str, as_of: datetime | None):
        owner, name = svc_dir.split("--", 1)
        owner = owner.replace("-", "/") if not self.live_agent(owner) and self.live_agent(owner.replace("-", "/")) else owner
        v = self.view(svc_dir)
        try:
            w = RW.load_world(v, name)
        finally:
            for k in ("msgs", "service", "playbook"):
                p = v / k
                p.unlink() if p.is_symlink() else p.rmdir()
            v.rmdir()
        w.owner = owner
        return w.as_of(as_of) if as_of else w


# ------------------------------------------------------------------------------------------------------------------ section 3: shapes
def title_skeleton(title: str) -> tuple[str, ...]:
    return tuple(t for t in L.text_tokens(title) if not re.search(r"\d", t))


def criteria_lines(m: L.Msg) -> list[str]:
    return [ln for ln in m.section("Acceptance criteria") if ln.strip()]


def criteria_key(lines: list[str]) -> tuple[str, ...]:
    return tuple(sorted(re.sub(r"\d+", "#", L.line_key(ln)) for ln in lines))


def criteria_tokens(lines: list[str]) -> set[str]:
    return {t for ln in lines for t in L.text_tokens(ln) if not re.search(r"\d", t)}


def human_verdicts(org: Org, task_ids: set[str], as_of=None) -> list[L.Msg]:
    out = [m for m in org.sent.values() if m.get("type") == "note" and m.get("feedback") and m.get("reply_to") in task_ids
           and L.tier(m.meta) == "human" and (as_of is None or m.time <= as_of)]
    return sorted(out, key=lambda m: m.id)


def one_off_cases(org: Org, as_of=None) -> list[dict]:
    tasks = {k: m for k, m in org.sent.items() if m.get("type") == "task" and not m.get("service") and (as_of is None or m.time <= as_of)}
    head = {}
    for tid in sorted(tasks):
        t, seen = tasks[tid], set()
        while t.get("revises") and t.get("revises") in tasks and t.get("revises") not in seen and tasks[t.get("revises")].get("to") == t.get("to"):
            seen.add(t.id)
            t = tasks[t.get("revises")]
        head[tid] = t.id
    cases = []
    for h in sorted(set(head.values())):
        m = tasks[h]
        members = {t for t, hd in head.items() if hd == h}
        hv = human_verdicts(org, members, as_of)
        lines = criteria_lines(m)
        cases.append({"head": h, "assignee": m.get("to"), "title": str(m.get("title", "")), "skeleton": title_skeleton(str(m.get("title", ""))),
                      "criteria": lines, "key": criteria_key(lines), "tokens": criteria_tokens(lines), "judged": bool(hv),
                      "judged_at": iso(hv[0].time) if hv else None, "tasks": sorted(members)})
    return cases


def shape_groups(cases: list[dict], overlap: float) -> list[dict]:
    parent = list(range(len(cases)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    why = defaultdict(set)
    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            a, b = cases[i], cases[j]
            if a["assignee"] != b["assignee"]:
                continue
            rel = None
            if a["skeleton"] and a["skeleton"] == b["skeleton"]:
                rel = "title"
            elif a["key"] and a["key"] == b["key"]:
                rel = "criteria"
            elif len(a["tokens"]) >= 3 and len(b["tokens"]) >= 3:
                jac = len(a["tokens"] & b["tokens"]) / len(a["tokens"] | b["tokens"])
                if jac >= overlap:
                    rel = "overlap"
            if rel:
                parent[find(i)] = find(j)
                why[(i, j)].add(rel)
    groups = defaultdict(list)
    for i in range(len(cases)):
        groups[find(i)].append(i)
    out = []
    for root, idx in groups.items():
        if len(idx) < 2:
            continue
        rels = sorted({r for (i, j), rs in why.items() if i in idx and j in idx for r in rs})
        members = [cases[i] for i in sorted(idx, key=lambda i: cases[i]["head"])]
        judged = [c for c in members if c["judged"]]
        out.append({"assignee": members[0]["assignee"], "heads": [c["head"] for c in members], "judged": [c["head"] for c in judged],
                    "relations": rels, "titles": [c["title"] for c in members], "criteria_key": list(members[-1]["key"]),
                    "reached_at": sorted(c["judged_at"] for c in judged)[2] if len(judged) >= 3 else None})
    return sorted(out, key=lambda g: g["heads"][0])


# ------------------------------------------------------------------------------------------------------------------ services
def service_versions(org: Org, svc_dir: str) -> list[tuple[dict, str]]:
    d = org.ev / "services-all" / svc_dir / "service"
    seen = {}
    for f in sorted(d.glob("*.md")) if d.is_dir() else []:
        meta, body = L.split_fm(f.read_text(errors="replace"))
        if "version" in meta and "acceptance" in meta:
            seen.setdefault(int(meta["version"]), (meta, body))
    return [seen[v] for v in sorted(seen)]


def service_key(org: Org, svc_dir: str) -> tuple[str, ...]:
    vs = service_versions(org, svc_dir)
    acc = vs[-1][0].get("acceptance") if vs else []
    return criteria_key([str(x) for x in acc or []])


# ------------------------------------------------------------------------------------------------------------------ 7.1
def service_from(cases: list[dict], t: dict, top_fn, offers_fn) -> list[dict]:
    """7.1, pure: a shape group fires with >= shape_cases judged cases, a top-level live assignee (`top_fn`), and no service of that
    assignee with the group's criteria key (`offers_fn`; a taken `service` item's effect is such a service, a renamed one included)."""
    out = []
    for g in shape_groups(cases, t["shape_overlap"]):
        a = g["assignee"]
        top = bool(top_fn(a))
        offers = offers_fn(a, tuple(g["criteria_key"]))
        fires = len(g["judged"]) >= t["shape_cases"] and top and not offers
        out.append({"kind": "service", "key": f"service|{a}|{min(g['heads'])}", "evidence": g["heads"], "weight": len(g["judged"]),
                    "rung": 2, "fires": fires, "reached_at": g["reached_at"] if top else None, "assignee_top_level": top,
                    "covered_by": offers, "group": g,
                    "d5": None if top else f"assignee {a} is not a top-level agent"})
    return out


def signal_service(org: Org, as_of=None) -> list[dict]:
    def top(a):
        return "/" not in str(a) and org.live_agent(a) is not None

    def offers(a, key):
        return [s for s in org.services if s.split("--", 1)[0] == a and service_key(org, s) == key
                and (as_of is None or created_of(org, s) is None or created_of(org, s) <= as_of)]
    return service_from(one_off_cases(org, as_of), org.thresholds, top, offers)


def created_of(org: Org, svc_dir: str):
    vs = service_versions(org, svc_dir)
    return L.parse_time(vs[0][0].get("created")) if vs else None


# ------------------------------------------------------------------------------------------------------------------ 7.2
def signer_of(org: Org, owner: str, delivery_result_id: str) -> str:
    """Delivery.signer (7.2): the direct report whose `done` the owner received last before the delivery, else the owner."""
    best = None
    for m in org.msgs.values():
        if m.get("type") == "result" and m.get("to") == owner and str(m.get("status")) == "done" and m.id < delivery_result_id:
            frm = str(m.get("from", ""))
            if frm.startswith(owner + "/") and "/" not in frm[len(owner) + 1:]:
                if best is None or m.id > best.id:
                    best = m
    return str(best.get("from")) if best else owner


def run_logs(org: Org) -> list[tuple[str, datetime]]:
    out = []
    for f in (org.copy.rglob("runs/*.log") if org.copy.is_dir() else []):
        rel = f.relative_to(org.copy)
        out.append(("/".join(rel.parts[:-2]), L.parse_time(f.stem)))
    return sorted((a, t) for a, t in out if t)


def checker_from_mail(mail, service: str, owner: str, t: dict, signer_fn, verifier_fn, estimate_fn=None,
                      fix_recurred: frozenset = frozenset()) -> dict:
    """7.2, pure over P1's Mail: per lineage class the cases (among the last window_cases judged human-tier cases) with a human rejection,
    not pending, whose subjects meet the class; per verifier the escapes it signed. `signer_fn(rejection)` is Delivery.signer of the
    rejected delivery; `verifier_fn(addr)` is is_verifier; `fix_recurred` holds the verifiers whose taken checker-fix recurred (then
    checker-add). Relayed and agent verdicts are not in mail.rejections (human tier only) and weigh 0."""
    judged = [c for c in mail.cases() if any(v.tier == "human" for d in mail.deliveries(c) for v in mail.verdicts_on(*d))]
    window = judged[-t["window_cases"]:]
    escapes = defaultdict(set)  # verifier -> cases whose failing delivery it signed
    counted = []  # (case, rejection, subjects, answer time, signer)
    for case in window:
        for rej in [r for r in mail.rejections if mail.case_of(r.task) == case]:
            signer = signer_fn(rej)
            if verifier_fn(signer):
                escapes[signer].add(case)
            if mail.pending(rej.id):
                continue
            counted.append((case, rej, mail.subjects(rej.id), mail.answer_time(rej.id), signer))
    # each lineage class (design 3: C<k> and its lineage as of now), and the cases whose rejection's subjects meet it
    now = max([c.defined for c in mail.crit.contracts] + [x[3] for x in counted if x[3]], default=None)
    cids = sorted({x for _, _, s, _, _ in counted for x in s if x.startswith("C")} | set(mail.crit.current()), key=RW.id_num)
    classes = {}
    for cid in cids:
        cls = frozenset({cid} | (mail.crit.lineage(cid, now) if now else set()))
        k = classes.setdefault(cls, {"cases": {}, "signers": {}, "rejections": []})
        for case, rej, subj, at, signer in counted:
            if subj & cls:
                if case not in k["cases"] or (at and at < k["cases"][case]):
                    k["cases"][case] = at
                    k["signers"][case] = signer
                if mail.rid[rej.id] not in k["rejections"]:
                    k["rejections"].append(mail.rid[rej.id])
    out = []
    current = set(mail.crit.current())
    for cls, k in classes.items():
        if not k["cases"]:
            continue
        rep = max((c for c in cls if c in current), key=RW.id_num, default=max(cls, key=RW.id_num))
        n = len(k["cases"])
        fires = n >= t["criterion_cases"]
        times = sorted(x for x in k["cases"].values() if x)
        reached = iso(times[t["criterion_cases"] - 1]) if fires and len(times) >= t["criterion_cases"] else None
        signed = defaultdict(int)
        for s in k["signers"].values():
            if verifier_fn(s):
                signed[s] += 1
        V = sorted(signed, key=lambda s: (-signed[s], s))[0] if signed else None
        kind = "checker-fix" if V and V not in fix_recurred else "checker-add"
        kk = {"cases": set(k["cases"]), "signers": k["signers"]}
        est = estimate_fn(kk, len(window)) if (fires and kind == "checker-add" and estimate_fn) else None
        out.append({"kind": kind, "key": f"{kind}|{service}|" + (f"{V}|{rep}" if kind == "checker-fix" else rep), "rung": 2 if kind == "checker-fix" else 4,
                    "class": sorted(cls, key=RW.id_num), "evidence": sorted(k["cases"]), "weight": n, "fires": fires,
                    "reached_at": reached, "signers": k["signers"], "estimate": est, "via": "class"})
    for V, cs in sorted(escapes.items()):  # (b): >= escapes escapes signed by one verifier -> checker-fix on V
        if len(cs) >= t["escapes"] and not any(c["kind"] == "checker-fix" and f"|{V}|" in c["key"] and c["fires"] for c in out):
            best = max((c for c in out if set(c["evidence"]) & cs), key=lambda c: (len(set(c["evidence"]) & cs), c["key"]), default=None)
            rep = best["key"].rsplit("|", 1)[1] if best else "none"
            out.append({"kind": "checker-fix", "key": f"checker-fix|{service}|{V}|{rep}", "rung": 2, "class": best["class"] if best else [],
                        "evidence": sorted(cs), "weight": len(cs), "fires": True, "reached_at": None, "signers": {}, "estimate": None,
                        "via": "escapes"})
    # protocol 13.2 reading 8 (adopted after the dry run showed the product's behaviour; a design-silence note for step 12): classes that
    # hold the same failing cases are one candidate, named by its newest current criterion
    best = {}
    for c in out:
        k = (c["kind"], tuple(c["evidence"]))
        if c["fires"] and (k not in best or RW.id_num(c["key"].rsplit("|", 1)[1]) > RW.id_num(best[k]["key"].rsplit("|", 1)[1])):
            best[k] = c
    merged = [c for c in out if not c["fires"]] + list(best.values())
    return {"service": service, "owner": owner, "window": window, "candidates": sorted(merged, key=lambda c: c["key"])}


def signal_checker(org: Org, svc_dir: str, as_of=None) -> dict:
    t = org.thresholds
    w = org.world(svc_dir, as_of)
    mail = RW.Mail(w)

    def signer(rej):
        res = mail.rejected_result(rej)
        return signer_of(org, w.owner, res.id) if res else w.owner
    return checker_from_mail(mail, w.service, w.owner, t, signer, org.is_verifier, lambda k, n: estimate(org, mail, w, k, n))


def estimate(org, mail, w, k, n_window) -> dict:
    """7.2's net-run-saving estimate: c = base_runs(reviewer) + 1; f = 3; r = mean runs of the owner's subtree after each failing case's
    first rejection, within the case's window (up to the case's last result: the runs `Case.runs` counts for that case); p = failing
    cases / window cases."""
    logs = run_logs(org)
    heads = sorted(mail.cases())
    rs = []
    for case in sorted(k["cases"]):
        rej = sorted((r for r in mail.rejections if mail.case_of(r.task) == case), key=lambda r: r.id)
        if not rej:
            continue
        start = rej[0].t
        results = [r.t for tid in mail.tasks_of(case) for r in mail.results_of.get(tid, [])]
        end = max(results) if results else datetime(2100, 1, 1, tzinfo=timezone.utc)
        rs.append(sum(1 for a, t in logs if (a == w.owner or a.startswith(w.owner + "/")) and start < t <= end))
    c, f = BASE_RUNS["reviewer"] + 1, 3
    p = len(k["cases"]) / n_window if n_window else 0.0
    r = sum(rs) / len(rs) if rs else None
    net = (p * r - c - p * f) if r is not None else None
    return {"c": c, "f": f, "r": r, "p": p, "k": len(k["cases"]), "n": n_window, "net": net,
            "rendered": f"net {net:.1f} = {p:.1f} × {r:g} − {c} − {p:.1f} × {f}, from {len(k['cases'])} of {n_window} cases" if net is not None else None}


# ------------------------------------------------------------------------------------------------------------------ 7.5
def criterion_sources(org: Org, svc_dir: str) -> dict[str, dict]:
    vs = service_versions(org, svc_dir)
    if not vs:
        return {}
    contracts = [RW.Contract(int(m["version"]), L.parse_time(m.get("defined") or m.get("created")), tuple(str(x) for x in m.get("acceptance") or []),
                             str(m.get("defined_by", "root")), str(m.get("answers", "") or ""), str(m.get("about", "") or ""),
                             str(m.get("words", "") or "")) for m, _ in vs]
    crit = RW.Criteria(contracts)
    out = {}
    v1 = vs[0][0]
    srcs = v1.get("sources") or []
    for i, text in enumerate(v1.get("acceptance") or []):
        cid = crit.ids[str(text)]
        s = srcs[i] if i < len(srcs) and isinstance(srcs[i], dict) else {}
        if "from" in s:
            out[cid] = {"text": str(text), "source": "user", "quote": str(s["from"]), "asked": s.get("asked")}
        elif s.get("default"):
            out[cid] = {"text": str(text), "source": "default"}
        elif "from_tasks" in s:
            out[cid] = {"text": str(text), "source": "tasks", "tasks": s["from_tasks"]}
        else:
            out[cid] = {"text": str(text), "source": "unknown"}
    for m, _ in vs[1:]:
        v = int(m["version"])
        for cid in crit.added(v):
            text = next(t for t, i in crit.ids.items() if i == cid)
            if m.get("words"):
                out[cid] = {"text": text, "source": "amendment", "quote": str(m["words"]), "asked": str(m.get("about") or "") or None}
            else:
                out.setdefault(cid, {"text": text, "source": "unknown"})
    cur = crit.current()
    return {k: v for k, v in out.items() if k in cur}


def clarify_from(srcs: dict[str, dict], mail, contract_of: dict, service: str, t: dict, asked: frozenset = frozenset()) -> list[dict]:
    """7.5, pure: a criterion with source user or amendment and >= added_words added words, or with source tasks, fires once it was
    exercised in >= accepted_cases accepted judged human cases, and only while its key was never an item (`asked`). default and unknown
    never fire. `fires_rule` is the rule without the once-per-key part (P2-W(e) reads its time)."""
    crit = mail.crit
    out = []
    for cid, s in sorted(srcs.items(), key=lambda kv: RW.id_num(kv[0])):
        if s["source"] in ("default", "unknown"):
            continue
        added = [] if s["source"] == "tasks" else L.added_words(s["text"], s["quote"], s.get("asked"))
        accepted, exercised, reached = 0, 0, None
        for case in mail.cases():
            for task, res in mail.deliveries(case):
                hv = [v for v in mail.verdicts_on(task, res) if v.tier == "human"]
                if not hv or cid not in set(crit.per.get(contract_of.get(task.id, 0), [])):
                    continue
                exercised += 1
                if hv[0].verdict == "accept":
                    accepted += 1
                    if accepted == t["accepted_cases"]:
                        reached = iso(hv[0].t)
        rule = (s["source"] == "tasks" or len(added) >= t["added_words"]) and accepted >= t["accepted_cases"]
        key = f"clarify|{service}|{cid}|{L.line_key(s['text'])[:40]}"
        out.append({"kind": "clarify", "key": key, "criterion": cid, "source": s["source"], "added": added, "exercised": exercised,
                    "accepted": accepted, "fires_rule": rule, "fires": rule and key not in asked, "reached_at": reached,
                    "evidence": [f"{service}/{cid}"], "weight": 0, "rung": 1})
    return out


def signal_clarify(org: Org, svc_dir: str, as_of=None) -> list[dict]:
    srcs = criterion_sources(org, svc_dir)
    w = org.world(svc_dir, as_of)
    mail = RW.Mail(w)
    contract_of = {k: int(m.get("contract") or 0) for k, m in org.sent.items() if m.get("type") == "task"}
    asked = frozenset(k for r in org.ledger.get("briefs") or [] if as_of is None or (L.parse_time(r.get("at")) or as_of) < as_of
                      for k in [i["key"] for i in r.get("items") or []])
    return clarify_from(srcs, mail, contract_of, w.service, org.thresholds, asked)


# ------------------------------------------------------------------------------------------------------------------ section 3: unprompted charter edits
def parse_history(path: Path) -> list[dict]:
    """charter-history.txt (`git log -p --reverse --no-renames --format='COMMIT %H %ct %s' -- '*/AGENT.md'`) -> commits with their files' diffs."""
    commits, cur = [], None
    for ln in path.read_text(errors="replace").splitlines() if path.is_file() else []:
        m = re.match(r"^COMMIT ([0-9a-f]{40}) (\d+) ?(.*)$", ln)
        if m:
            cur = {"sha": m.group(1), "t": datetime.fromtimestamp(int(m.group(2)), timezone.utc), "subject": m.group(3), "files": {}}
            commits.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^diff --git a/(\S+) b/(\S+)$", ln)
        if m:
            f = {"path": m.group(2), "new": False, "deleted": False, "minus": [], "plus": []}
            cur["files"][m.group(2)] = f
            continue
        if not cur["files"]:
            continue
        f = list(cur["files"].values())[-1]
        if ln.startswith("new file mode"):
            f["new"] = True
        elif ln.startswith("deleted file mode"):
            f["deleted"] = True
        elif ln.startswith("+") and not ln.startswith("+++"):
            f["plus"].append(ln[1:])
        elif ln.startswith("-") and not ln.startswith("---"):
            f["minus"].append(ln[1:])
    return commits


TAG = re.compile(r"\[change ([0-9a-f]+)\]\s*$")
LIMITS_LINE = re.compile(r"up to (\d+) direct reports; may hire: (yes|no)\. \[change ([0-9a-f]+)\]\s*$")


def unprompted_edits(commits: list[dict], t0: datetime | None, applied: set[str], org: Org | None = None) -> list[dict]:
    """Section 3 (G7/L21): a change between two committed versions of one AGENT.md, after t0, other than tagged added-section lines of an
    applied extension and the can_hire/max_children values its limits line names. Not edits: a pair whose second side is a deletion; the
    first version at an address that had an earlier, retired agent (the history restarts); every path under .retired/."""
    out = []
    history = defaultdict(list)  # path -> [commit index of each version]
    for i, c in enumerate(commits):
        for p, f in c["files"].items():
            history[p].append((i, f))
    for p, versions in history.items():
        if ".retired/" in p or p.startswith(".retired"):
            continue
        prev_deleted = True
        for i, f in versions:
            c = commits[i]
            if f["deleted"]:
                prev_deleted = True
                continue
            if f["new"] or prev_deleted:  # a first version (a hire), or a re-created address: a new history
                prev_deleted = False
                continue
            if t0 is not None and c["t"] <= t0:
                continue
            reasons = []
            limits_named = {}
            for ln in f["plus"]:
                m = LIMITS_LINE.search(ln)
                if m and m.group(3) in applied:
                    limits_named = {"max_children": m.group(1), "can_hire": "true" if m.group(2) == "yes" else "false"}
            changed = []
            for side, lines in (("-", f["minus"]), ("+", f["plus"])):
                for ln in lines:
                    if not ln.strip():
                        continue
                    tm = TAG.search(ln)
                    if tm and tm.group(1) in applied:
                        continue
                    km = re.match(r"^(max_children|can_hire):\s*(\S+)\s*$", ln)
                    if km and km.group(1) in limits_named:
                        if side == "-" or limits_named[km.group(1)] == km.group(2).lower():
                            continue
                    if ln.strip() == "## Added by your changes" and any(TAG.search(x) and TAG.search(x).group(1) in applied for x in f["plus"] + f["minus"]):
                        continue
                    changed.append(side + ln)
            if changed:
                out.append({"path": p, "commit": c["sha"], "t": iso(c["t"]), "subject": c["subject"], "changed": changed[:12]})
    return out


# ------------------------------------------------------------------------------------------------------------------ D8 (4.5)
def applied_reasons(commits: list[dict], gitlog: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"root: applied extension ([0-9a-f]+) \((.*?)\): \+", gitlog):
        out[m.group(1)] = m.group(2)
    for c in commits:
        m = re.match(r"root: applied extension ([0-9a-f]+) \((.*?)\): \+", c["subject"])
        if m:
            out[m.group(1)] = m.group(2)
    return out


def item_of(reason: str | None) -> str | None:
    m = re.match(r"^(B\d+\.\d+):", reason or "")
    return m.group(1) if m else None


RETIRED_DIR = re.compile(r"^(.*?)-\d{8}T\d{6}(?:\d{6})?$")


def events_of(ev: Path) -> list[dict]:
    """The event log's records (events/<day>/*.jsonl in the evidence copy, or the org's .runtime/events), each with its UTC time."""
    out = []
    roots = [ev / "events", ev / "org-copy" / ".runtime" / "events"]
    for r in roots:
        for f in sorted(r.rglob("*.jsonl")) if r.is_dir() else []:
            for ln in f.read_text(errors="replace").splitlines():
                try:
                    e = json.loads(ln)
                except Exception:
                    continue
                e["_t"] = L.parse_time(e.get("ts"))
                out.append(e)
        if out:
            break
    return out


def parent_writes(events: list[dict]) -> list[tuple[str, str, datetime]]:
    """(actor, AGENT.md path, time) of every successful `write` tool call (design 4.5: `path` is kept by the summarizer)."""
    out = []
    for e in events:
        if e.get("kind") == "tool.call" and e.get("tool") in ("write", "org_write") and not e.get("error") and e.get("ok", True) is not False:
            p = str((e.get("args") or {}).get("path", ""))
            if p.endswith("AGENT.md") and e["_t"]:
                out.append((str(e.get("actor", "")), p, e["_t"]))
    return out


def git_texts(ev: Path):
    """A reader of committed file versions from the evidence copy's git bundle (org-git.bundle): fn(sha, path) -> text or None."""
    import atexit
    import shutil
    b = ev / "org-git.bundle"
    if not b.is_file():
        return None
    d = tempfile.mkdtemp(prefix="p2-bundle-", dir="/tmp")
    atexit.register(shutil.rmtree, d, True)
    if subprocess.run(["git", "clone", "-q", str(b), f"{d}/r"], capture_output=True).returncode != 0:
        return None

    def show(sha, path):
        p = subprocess.run(["git", "-C", f"{d}/r", "show", f"{sha}:{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None
    return show


ADDED_HEAD = "## Added by your changes"


def split_added(body: str) -> tuple[list[str], str]:
    """The lines under `## Added by your changes` (to the next heading) and the rest of the body."""
    lines, rest, on = [], [], False
    for ln in body.splitlines():
        if ln.strip() == ADDED_HEAD:
            on = True
            continue
        if on and ln.startswith("#"):
            on = False
        (lines if on else rest).append(ln)
    return [x for x in lines if x.strip()], "\n".join(rest).strip()


def charter_pair_label(addr: str, old: str, new: str, t1: datetime, t2: datetime, applied: set[str], writes, horizon) -> tuple[str, str | None]:
    """Design 4.5's labels of one charter pair (two committed versions): `change` (only tagged added-section lines of an applied
    extension and the can_hire/max_children its limits line names), `by parent` (a nested charter; differences only in the body outside
    the added section, in `role` or a lower `max_children`; a `write` by the parent on that AGENT.md between the commits), `by parent, or
    outside the tools` (the same differences, but the window is beyond the event log's horizon or events are off), `outside the tools`
    (anything else). Returns (label, id): the plan id for `change`, the parent for the `by parent` labels."""
    mo, bo = L.split_fm(old)
    mn, bn = L.split_fm(new)
    ao, rest_o = split_added(bo)
    an, rest_n = split_added(bn)
    ko, kn = [L.line_key(x) for x in ao], [L.line_key(x) for x in an]
    changed_added = [x for x in an if L.line_key(x) not in ko] + [x for x in ao if L.line_key(x) not in kn]
    tags = {TAG.search(x).group(1) if TAG.search(x) else None for x in changed_added}
    named = {}
    for x in an:
        m = LIMITS_LINE.search(x)
        if m and m.group(3) in applied:
            named = {"max_children": int(m.group(1)), "can_hire": m.group(2) == "yes"}
    fm_diff = sorted(k for k in set(mo) | set(mn) if mo.get(k) != mn.get(k))
    fm_other = [k for k in fm_diff if not (k in named and mn.get(k) == named[k])]
    body_changed = rest_o != rest_n
    ext = (tags and None not in tags and tags <= applied) or (fm_diff and not fm_other)
    if ext and not fm_other and not body_changed and None not in tags:
        ids = sorted(t for t in tags if t) or sorted(TAG.search(x).group(1) for x in an if TAG.search(x) and TAG.search(x).group(1) in applied)
        return "change", (ids[0] if ids else None)
    if "/" not in addr:
        return "outside the tools", None
    parent = addr.rsplit("/", 1)[0]
    lower = all(k == "role" or (k == "max_children" and isinstance(mn.get(k), int) and isinstance(mo.get(k), int) and mn[k] <= mo[k])
                for k in fm_other)
    if changed_added or not lower:
        return "outside the tools", None
    # the log's horizon against the older commit's time at whole seconds (protocol 13.2 reading 1: commit times are whole seconds, events
    # microseconds; an event in the same second as the commit is within the window's reach)
    if horizon is None or horizon.replace(microsecond=0) > t1:
        return "by parent, or outside the tools", parent
    if any(a == parent and p.endswith(f"{addr}/AGENT.md") and t1 <= t <= t2 + timedelta(seconds=1) for a, p, t in writes):
        return "by parent", parent
    return "outside the tools", None


def d8(org: Org, since: datetime | None, until: datetime | None, applied: set[str], reasons: dict[str, str], commits: list[dict],
       show=None, events: list[dict] | None = None) -> list[dict]:
    """D8 (design 4.5): every structural change in (since, until] with its label, as tuples (kind, subject, date, label, id, item):
    agents added and retired, services added and retired, charter pairs. Retired agents' and services' creations are listed too (a
    structural change of the window, design 3 and 4.3 D8: "every structural change")."""
    def inwin(t):
        return t is not None and (since is None or t > since) and (until is None or t <= until)
    items = ledger_items(org)

    def item_for(pid, kind_ok):
        it = item_of(reasons.get(pid))
        return it if it and items.get(it, {}).get("kind") in kind_ok else None
    out = []
    retired_tb = {}  # plan id -> taken back
    for f in sorted(org.copy.rglob("RETIRED.md")) if org.copy.is_dir() else []:
        meta, _ = L.split_fm(f.read_text(errors="replace"))
        if "(not applied)" in str(meta.get("approved_in") or ""):
            retired_tb[str(meta["approved_in"]).split()[1]] = True
    for addr, a in sorted(org.agents.items()):
        m = a["meta"]
        t = L.parse_time(m.get("created"))
        rel = addr
        if a["retired"]:
            parts = addr.split("/")
            i = parts.index(".retired")
            top = parts[i + 1]
            name = RETIRED_DIR.match(top).group(1) if RETIRED_DIR.match(top) else top
            topm = org.agents.get("/".join(parts[:i + 2]), {}).get("meta", {})
            hb = str(topm.get("hired_by") or "root")
            rel = "/".join(([name] if hb in ("", "root") else [hb, name]) + parts[i + 2:])
        if inwin(t):
            ap = str(m.get("approved_in") or "")
            if ap.startswith("plan "):
                lab = ("plan", None, None)
            elif ap.startswith("change ") and ("(not applied)" in ap or ap.split()[1] in retired_tb):
                lab = ("taken back", ap.split()[1], None)
            elif ap.startswith("change "):
                pid = ap.split()[1]
                it = item_for(pid, ("checker-add", "worker"))
                it = it if it and (items[it]["kind"] == "worker" or org.is_verifier(addr)) else None
                lab = ("change", pid, it)
            elif "## Assignment (from the approved plan)" in a["body"]:
                lab = ("plan", None, None)
            elif str(m.get("hired_by", "")) not in ("", "root"):
                lab = ("inside the plan", str(m.get("hired_by")), None)
            else:
                lab = ("by root, outside a plan", None, None)
            out.append({"kind": "agent added", "subject": rel, "date": t.date().isoformat(), "label": lab[0], "id": lab[1], "item": lab[2]})
        if a["retired"]:
            if len(addr.split("/")) != addr.split("/").index(".retired") + 2:
                continue  # a member of a retired team: the team's top carries the retire
            rf = org.copy / Path(addr) / "RETIRED.md"
            rm = L.split_fm(rf.read_text(errors="replace"))[0] if rf.is_file() else None
            tr = L.parse_time((rm or {}).get("retired")) if rm else None
            if rm is None:
                continue  # a tree retired before Phase 2 has no record: `retired {date}`, no label (not in the script)
            if inwin(tr):
                ap = str(rm.get("approved_in") or "")
                if "(not applied)" in ap:
                    lab = ("taken back", ap.split()[1], None)
                elif ap.startswith("change "):
                    lab = ("change", ap.split()[1], item_for(ap.split()[1], ("retire",)))
                elif str(rm.get("by", "root")) != "root":
                    lab = ("inside the plan", str(rm.get("by")), None)
                else:
                    lab = ("by root, outside a plan", None, None)
                out.append({"kind": "agent retired", "subject": rel, "date": tr.date().isoformat(), "label": lab[0], "id": lab[1], "item": lab[2]})
    for s in org.services + org.retired_services:
        vs = service_versions(org, s)
        if not vs:
            continue
        m = vs[0][0]
        t = L.parse_time(m.get("created"))
        if not inwin(t):
            continue
        ap = str(m.get("approved_in") or "")
        owner, name = s.split("--", 1)
        if name.startswith(".retired--"):
            dn = name[len(".retired--"):]
            name = RETIRED_DIR.match(dn).group(1) if RETIRED_DIR.match(dn) else dn
        if ap.startswith("plan "):
            lab = ("plan", None, None)
        elif ap.startswith("change ") and ap.split()[1] in retired_tb:
            lab = ("taken back", ap.split()[1], None)
        elif ap.startswith("change "):
            pid = ap.split()[1]
            lab = ("change", pid, item_of(reasons.get(pid)))
        elif str(m.get("defined_by", "root")) != "root":
            lab = ("inside the plan", str(m.get("defined_by")), None)
        else:
            lab = ("by root, outside a plan", None, None)
        out.append({"kind": "service added", "subject": f"{owner}/{name}", "date": t.date().isoformat(), "label": lab[0], "id": lab[1], "item": lab[2]})
    for f in sorted(org.copy.glob("**/services/.retired/*/RETIRED.md")) if org.copy.is_dir() else []:
        rm = L.split_fm(f.read_text(errors="replace"))[0]
        tr = L.parse_time(rm.get("retired"))
        owner = str(f.relative_to(org.copy).parent.parent.parent.parent)
        dn = f.parent.name
        name = RETIRED_DIR.match(dn).group(1) if RETIRED_DIR.match(dn) else dn
        if not inwin(tr):
            continue
        ap = str(rm.get("approved_in") or "")
        if "(not applied)" in ap:
            lab = ("taken back", ap.split()[1], None)
        elif ap.startswith("change "):
            lab = ("change", ap.split()[1], item_of(reasons.get(ap.split()[1])))
        elif str(rm.get("by", "root")) != "root":
            lab = ("inside the plan", str(rm.get("by")), None)
        else:
            lab = ("by root, outside a plan", None, None)
        out.append({"kind": "service retired", "subject": f"{owner}/{name}", "date": tr.date().isoformat(), "label": lab[0], "id": lab[1], "item": lab[2]})
    events = events if events is not None else events_of(org.ev)
    horizon = min((e["_t"] for e in events if e.get("_t")), default=None)
    writes = parent_writes(events)
    prev = {}
    for c in commits:
        for p, f in c["files"].items():
            last = prev.get(p)
            prev[p] = None if f["deleted"] else c
            if f["new"] or f["deleted"] or last is None or ".retired" in p or not inwin(c["t"]):
                continue
            addr = p[:-len("/AGENT.md")]
            if show:
                old, new = show(last["sha"], p), show(c["sha"], p)
            else:
                old = new = None
            if old is not None and new is not None:
                lab, pid = charter_pair_label(addr, old, new, last["t"], c["t"], applied, writes, horizon)
            else:  # no bundle: the diff's reading (tagged lines and named limits only; any other change outside the tools)
                tags = {TAG.search(x).group(1) for x in f["plus"] + f["minus"] if TAG.search(x)}
                untagged = [x for x in f["plus"] + f["minus"] if x.strip() and not TAG.search(x) and x.strip() != ADDED_HEAD
                            and not re.match(r"^(max_children|can_hire):", x)]
                lab, pid = ("change", sorted(tags)[0]) if tags and tags <= applied and not untagged else ("outside the tools", None)
            out.append({"kind": "charter changed", "subject": addr, "date": c["t"].date().isoformat(), "label": lab, "id": pid, "item": None,
                        "t1": iso(last["t"]), "t2": iso(c["t"])})  # the pair's commit times (PF-0's signature reads t1)
    return out


UNPROMPTED_LABELS = ("by parent", "outside the tools", "by parent, or outside the tools")


def parse_product_d8(lines: list[str]) -> list[dict]:
    """The product's D8 detail lines into the same tuples (formats read from the throwaway orgs' briefs: `- agent X added (date): ...`,
    `- agent X retired (date): ...`, `- service X added|retired (date): ...`, `- charter of X changed: <what> (date): ...`)."""
    out = []
    for ln in lines:
        m = re.match(r"^- (agent|service) (\S+) (added|retired) \((\d{4}-\d{2}-\d{2})\): (.*)$", ln)
        c = re.match(r"^- charter of (\S+) changed: .*? \((\d{4}-\d{2}-\d{2})\): (.*)$", ln)
        if m:
            kind, subj, date, lab = f"{m.group(1)} {m.group(3)}", m.group(2), m.group(4), m.group(5)
        elif c:
            kind, subj, date, lab = "charter changed", c.group(1), c.group(2), c.group(3)
        else:
            continue
        lm = re.match(r"^from your change ([0-9a-f]+)(?:, item (B\d+\.\d+))?$", lab)
        row = {"kind": kind, "subject": subj, "date": date, "id": None, "item": None, "raw": ln}
        if lm:
            out.append({**row, "label": "change", "id": lm.group(1), "item": lm.group(2)})
        elif lab.startswith("from the plan you approved"):
            out.append({**row, "label": "plan"})
        elif lab.startswith("inside the plan, by "):
            out.append({**row, "label": "inside the plan", "id": lab.split("by ", 1)[1]})
        elif lab.startswith("by root, outside a plan"):
            out.append({**row, "label": "by root, outside a plan"})
        elif lab.startswith("taken back: the change "):
            out.append({**row, "label": "taken back", "id": lab.split("the change ", 1)[1].split()[0]})
        elif lab.startswith("outside the tools"):
            out.append({**row, "label": "outside the tools"})
        elif re.match(r"^by (\S+), or outside the tools", lab):
            out.append({**row, "label": "by parent, or outside the tools", "id": re.match(r"^by (\S+),", lab).group(1)})
        elif re.match(r"^by (\S+)$", lab):
            out.append({**row, "label": "by parent", "id": lab[3:]})
        else:
            out.append({**row, "label": lab})
    return out


# ------------------------------------------------------------------------------------------------------------------ D7 (4.4)
def d7_amendments(org: Org, svc_dir: str, since, until) -> list[dict]:
    w = org.world(svc_dir, until)
    mail = RW.Mail(w)
    contract_of = {k: int(m.get("contract") or 0) for k, m in org.sent.items() if m.get("type") == "task"}
    return amendment_outcomes(mail, w.service, contract_of, org.thresholds["window"], since)


def d7_outcome(recurred, n: int, window: int):
    """4.4's outcome, in its order: recurred (the first later related rejection), not recurred in n >= window exercised cases, else
    INCONCLUSIVE (n of window)."""
    if recurred:
        return ("recurred", recurred[0], recurred[1])
    if n >= window:
        return ("not recurred", n, None)
    return ("INCONCLUSIVE", n, window)


def amendment_outcomes(mail, service: str, contract_of: dict, window: int, since) -> list[dict]:
    """D7 for contract amendments (4.4's first row), pure over P1's Mail: target = the added ids as their lineage classes as of the
    version's `defined`; exercised = later judged human-tier deliveries whose request carried a contract version holding the target;
    recurred = a later human rejection, not pending, whose subjects meet the target."""
    out = []
    for c in mail.crit.contracts:
        added = mail.crit.added(c.version)
        if c.version < 2 or not added:
            continue
        target = set()
        for a in added:
            target |= {a} | mail.crit.lineage(a, c.defined)
        recurred, n = None, 0
        for rej in sorted(mail.rejections, key=lambda r: r.id):
            if rej.t > c.defined and not mail.pending(rej.id) and mail.subjects(rej.id) & target:
                recurred = (mail.case_of(rej.task), mail.rid[rej.id], rej.t)
                break
        for case in mail.cases():
            for task, res in mail.deliveries(case):
                hv = [v for v in mail.verdicts_on(task, res) if v.tier == "human"]
                if hv and task.t > c.defined and set(added) <= set(mail.crit.per.get(contract_of.get(task.id, 0), [])):
                    n += 1
        outcome = d7_outcome(recurred, n, window)
        changed_in_window = (since is None or c.defined > since) or (recurred and (since is None or recurred[2] > since))
        out.append({"change": f"{service} contract v{c.version} adds {', '.join(added)}", "outcome": outcome[0],
                    "n": outcome[1] if outcome[0] != "recurred" else None, "case": outcome[1] if outcome[0] == "recurred" else None,
                    "rid": outcome[2] if outcome[0] == "recurred" else None, "time": iso(c.defined), "in_window": bool(changed_in_window)})
    return out


def parse_product_d7(lines: list[str]) -> list[dict]:
    out = []
    for ln in lines:
        m = re.match(r"^- (.*?): (recurred in case (\S+) \((R\d+)\)|not recurred in (\d+) cases where it was exercised|INCONCLUSIVE \((\d+) of (\d+) exercised cases\)|no target recorded: not evaluated)$", ln)
        if not m:
            continue
        ch = m.group(1)
        if m.group(3):
            out.append({"change": ch, "outcome": "recurred", "case": m.group(3), "rid": m.group(4), "n": None})
        elif m.group(5):
            out.append({"change": ch, "outcome": "not recurred", "n": int(m.group(5)), "case": None, "rid": None})
        elif m.group(6):
            out.append({"change": ch, "outcome": "INCONCLUSIVE", "n": int(m.group(6)), "case": None, "rid": None})
        else:
            out.append({"change": ch, "outcome": "no target", "n": None, "case": None, "rid": None})
    return out


def d7_key(change: str):
    """A D7 change's identity, for comparing the product's line with the re-derivation's (formats read from the throwaway orgs)."""
    m = re.match(r"^(\S+) contract v(\d+) adds ", change)
    if m:
        return ("contract", m.group(1), int(m.group(2)))
    m = re.match(r"^(agent|service) (\S+) added \((\d{4}-\d{2}-\d{2})\)", change)
    if m:
        return (m.group(1), m.group(2))
    m = re.match(r"^charter of (\S+) changed: .*?\((\d{4}-\d{2}-\d{2})\)", change)
    if m:
        return ("charter", m.group(1), m.group(2))
    return ("other", change)


def ledger_items(org: Org) -> dict[str, dict]:
    out = {}
    for r in org.ledger.get("briefs") or []:
        for it in r.get("items") or []:
            out[f"{r['id']}.{it['n']}"] = {**it, "brief": r["id"], "at": r.get("at")}
    return out


def d7_structural(org: Org, since, until, commits, reasons) -> list[dict]:
    """4.4's rows for structural changes and charter edits that are an item's effect (a change of no item: `no target recorded`; the first
    plan's agents are left to D8, 22.2)."""
    t = org.thresholds
    items = ledger_items(org)
    recs = org.ledger.get("briefs") or []
    cur = next((i for i, r in enumerate(recs) if until and L.parse_time(r.get("at")) and abs((L.parse_time(r["at"]) - until).total_seconds()) < 1e-3), None)
    carry_since = L.parse_time(recs[max(0, cur - t["carry"])]["since"]) if cur is not None and recs else since
    changes = []  # (kind, subject, date, time, item)
    for addr, a in org.agents.items():
        ap = str(a["meta"].get("approved_in") or "")
        tm = L.parse_time(a["meta"].get("created"))
        if ap.startswith("change ") and "(not applied)" not in ap and tm:
            changes.append(("agent", addr, tm, item_of(reasons.get(ap.split()[1])) if org.is_verifier(addr) else None))
    for s in org.services:
        vs = service_versions(org, s)
        if vs and str(vs[0][0].get("approved_in") or "").startswith("change "):
            pid = str(vs[0][0]["approved_in"]).split()[1]
            owner, name = s.split("--", 1)
            changes.append(("service", f"{owner}/{name}", L.parse_time(vs[0][0].get("created")), item_of(reasons.get(pid))))
    seen = defaultdict(int)
    for c in commits:
        for p, f in c["files"].items():
            seen[p] += 1
            if f["new"] or f["deleted"] or seen[p] == 1 or ".retired" in p:
                continue
            tags = {TAG.search(x).group(1) for x in f["plus"] + f["minus"] if TAG.search(x)}
            its = sorted({item_of(reasons.get(x)) for x in tags} - {None})
            changes.append(("charter", p[:-len("/AGENT.md")], c["t"], its[0] if its else None))
    out = []
    for kind, subj, tm, item in changes:
        if until and tm > until:
            continue
        it = items.get(item) if item else None
        if not it:
            outcome, n, case = "no target", None, None
        else:
            svc = it["key"].split("|")[1] if it["kind"] != "service" else subj.split("/", 1)[-1] if kind == "service" else str(it.get("effect", {}).get("service", "")).split("/", 1)[-1]
            sd = next((s for s in org.services if s.split("--", 1)[1] == svc), None)
            n, case, outcome = 0, None, None
            if sd:
                w = org.world(sd, until)
                mail = RW.Mail(w)
                target = set()
                if it["kind"] in ("checker-add", "checker-fix"):
                    c0 = it["key"].rsplit("|", 1)[1]
                    target = {c0} | mail.crit.lineage(c0, tm)
                for cs in mail.cases():
                    for task, res in mail.deliveries(cs):
                        if task.t > tm and any(v.tier == "human" for v in mail.verdicts_on(task, res)):
                            n += 1
                if target:
                    for rej in sorted(mail.rejections, key=lambda r: r.id):
                        if rej.t > tm and not mail.pending(rej.id) and mail.subjects(rej.id) & target:
                            case = (mail.case_of(rej.task), mail.rid[rej.id], rej.t)
                            break
            if case:
                outcome = "recurred"
            elif n >= t["window"]:
                outcome = "not recurred"
            else:
                outcome = "INCONCLUSIVE"
        include = (since is None or tm > since) or (outcome == "INCONCLUSIVE" and (carry_since is None or tm > carry_since)) \
            or (outcome == "recurred" and (since is None or case[2] > since))
        out.append({"key": [kind, subj] + ([tm.date().isoformat()] if kind == "charter" else []), "item": item, "outcome": outcome,
                    "n": n if outcome in ("not recurred", "INCONCLUSIVE") else None, "case": case[0] if case else None,
                    "rid": case[1] if case else None, "time": iso(tm), "in_window": bool(include)})
    return out


# ------------------------------------------------------------------------------------------------------------------ the ledger (4.2)
def verdict_count(org: Org, after: datetime | None, upto: datetime) -> int:
    """Deliveries (service and one-off) whose first counted human-tier verdict was created in (after, upto]."""
    firsts = {}
    for m in sorted(org.sent.values(), key=lambda m: m.id):
        if m.get("type") == "note" and m.get("feedback") and L.tier(m.meta) == "human" and not m.get("confirms"):
            firsts.setdefault(m.get("reply_to"), m.time)
    return sum(1 for t in firsts.values() if (after is None or t > after) and t <= upto)


def ledger_check(org: Org) -> dict:
    recs = org.ledger.get("briefs") or []
    rows = []
    prev = None
    for r in recs:
        at = L.parse_time(r.get("at"))
        n = verdict_count(org, L.parse_time(prev.get("at")) if prev else None, at) if at else None
        rows.append({"id": r.get("id"), "at": r.get("at"), "verdicts_since_last": n, "recorded_ok": prev is None or (n or 0) >= 1,
                     "items": len(r.get("items") or []), "cap_ok": len(r.get("items") or []) <= 3})
        prev = r
    return {"records": rows, "asked": len(org.ledger.get("asked") or [])}


# ------------------------------------------------------------------------------------------------------------------ the ledger's rules (4.2, 4.5, 4.5a)
KIND_ORDER = ["answer", "cause", "clarify", "checker-fix", "service", "checker-add", "worker", "reclaim", "retire"]
RUNG = {"clarify": 1, "cause": 1, "answer": 1, "checker-fix": 2, "service": 2, "worker": 3, "checker-add": 4, "retire": 7, "reclaim": 8}


def effect_facts(org: Org) -> dict:
    """The files' facts that 4.5's effect test reads: services (owner, name, created, approved_in, criteria key), agents (address, parent,
    created, approved_in, is_verifier), the added-section lines of every live charter, retired trees, human links and answering versions."""
    services = []
    for s in org.services:
        vs = service_versions(org, s)
        if vs:
            owner, name = s.split("--", 1)
            services.append({"owner": owner, "name": name, "created": L.parse_time(vs[0][0].get("created")),
                             "approved_in": str(vs[0][0].get("approved_in") or ""), "key": service_key(org, s)})
    agents, lines, retired = [], {}, {}
    for addr, a in org.agents.items():
        if a["retired"]:
            rf = org.copy / Path(addr) / "RETIRED.md"
            if rf.is_file():
                retired[addr] = L.parse_time(L.split_fm(rf.read_text(errors="replace"))[0].get("retired"))
            continue
        agents.append({"addr": addr, "parent": addr.rsplit("/", 1)[0] if "/" in addr else "root", "created": L.parse_time(a["meta"].get("created")),
                       "approved_in": str(a["meta"].get("approved_in") or ""), "verifier": org.is_verifier(addr)})
        lines[addr] = [L.line_key(TAG.sub("", x)) for x in split_added(a["body"])[0]]
    links, answers, removals = [], [], []
    for m in org.sent.values():
        if m.get("type") == "note" and not m.get("feedback") and m.get("criterion") is not None and m.get("reply_to") and L.tier(m.meta) == "human":
            ids = m.get("criterion")
            ids = [str(x) for x in (ids if isinstance(ids, list) else re.split(r"[,\s]+", str(ids)))]
            links.append({"rejection": str(m.get("reply_to")), "t": m.time, "ids": [x.upper() for x in ids if x]})
    for s in org.services:
        for meta, _ in service_versions(org, s):
            if meta.get("answers"):
                answers.append({"rejection": str(meta["answers"]), "t": L.parse_time(meta.get("defined"))})
    for s in org.services:
        try:
            crit = RW.Criteria([RW.Contract(int(m["version"]), L.parse_time(m.get("defined") or m.get("created")),
                                            tuple(str(x) for x in m.get("acceptance") or [])) for m, _ in service_versions(org, s)])
        except Exception:
            continue
        for c in crit.contracts:
            for cid in crit.removed(c.version):
                removals.append({"service": s.split("--", 1)[1], "criterion": cid, "t": c.defined})
    rid_note = {}
    for s in org.services:
        try:
            mail = RW.Mail(org.world(s, None))
        except Exception:
            continue
        rid_note.update({(s.split("--", 1)[1], r): vid for vid, r in mail.rid.items()})
    return {"services": services, "agents": agents, "lines": lines, "retired": retired, "links": links, "answers": answers,
            "removals": removals, "rid_note": rid_note}


def effect_seen(item: dict, after: datetime, until: datetime | None, facts: dict, shape_key: tuple | None = None) -> bool | None:
    """4.5's effect of an item, checked in the files in (after, until]. None when the harness does not derive that kind's effect."""
    def inw(t):
        return t is not None and t > after - timedelta(seconds=1) and (until is None or t <= until)  # created/defined: whole seconds
    k, eff = item["kind"], item.get("effect") or {}
    if k == "service":
        owner, _, name = str(eff.get("service", "")).partition("/")
        return any(s["approved_in"].startswith("change ") and inw(s["created"]) and s["owner"] == owner and
                   (s["name"] == name or (shape_key is not None and s["key"] == shape_key)) for s in facts["services"])
    if k == "checker-add":
        owner = str(eff.get("owner", ""))
        return any(a["parent"] == owner and a["verifier"] and a["approved_in"].startswith("change ") and inw(a["created"]) for a in facts["agents"])
    if k == "checker-fix":
        v, line = str(eff.get("agent", "")), str(eff.get("line", ""))
        return (L.line_key(line) in facts["lines"].get(v, [])) if line else None
    if k == "clarify":
        svc, cid = str(eff.get("service", "")), str(eff.get("criterion", "")).upper()
        return any(r["service"] == svc and r["criterion"] == cid and inw(r["t"]) for r in facts["removals"]) or \
            any(cid in x["ids"] and inw(x["t"]) for x in facts["links"])
    if k in ("cause", "answer"):
        rid = item["key"].split("|", 1)[1]
        notes = {n for (s, r), n in facts["rid_note"].items() if r == rid}
        return any(x["rejection"] in notes and inw(x["t"]) for x in facts["links"]) or any(a["rejection"] in notes and inw(a["t"]) for a in facts["answers"])
    if k == "retire":
        addr = item["key"].split("|", 1)[1]
        return any(t and inw(t) and (p.rsplit("/", 1)[-1].startswith(addr.rsplit("/", 1)[-1] + "-")) for p, t in facts["retired"].items())
    if k == "worker":
        lead = item["key"].split("|")[-1].rsplit("/", 1)[0]
        return any(a["parent"] == lead and inw(a["created"]) for a in facts["agents"])
    return None


def order_key(item: dict, weight: int):
    ev = sorted(str(x) for x in item.get("evidence") or [])
    return (-weight, RUNG.get(item["kind"], 9), ev[0] if ev else "", KIND_ORDER.index(item["kind"]) if item["kind"] in KIND_ORDER else 99, item["key"])


def ledger_rules(records: list[dict], facts: dict, cap: int = 3, weight_of=None, shape_keys: dict | None = None) -> dict:
    """4.2 and 4.5a over the ledger's records, re-derived: per pair (B_i, B_i+1) each item of B_i is taken (its effect seen in
    (B_i.at, B_i+1.at]) or lapsed; per record the suppression rule (a key an earlier record offered comes back only with an evidence id that
    earlier item lacked; a clarify key never; a cause key at most after two lapses), the cap (at most `cap` items; held back only when the
    items fill the cap), and the order of 4.5a item 5 (weight, rung, oldest evidence, kind, key) over the record's items."""
    weight_of = weight_of or (lambda it: 0 if it["kind"] in ("clarify", "retire", "reclaim") else (1 if it["kind"] in ("cause", "answer") else len(it.get("evidence") or [])))
    out = {"pairs": [], "suppression": [], "cap": [], "order": [], "lapsed_counts": []}
    lapses = defaultdict(int)
    for a, b in zip(records, records[1:]):
        ta, tb = L.parse_time(a["at"]), L.parse_time(b["at"])
        states = {}
        for it in a.get("items") or []:
            s = effect_seen(it, ta, tb, facts, (shape_keys or {}).get(it["key"]))
            states[f"{a['id']}.{it['n']}"] = "taken" if s else ("lapsed" if s is False else "not derived")
        out["pairs"].append({"from": a["id"], "to": b["id"], "items": states})
    lapsed_before = {}
    for j, r in enumerate(records):
        for it in r.get("items") or []:
            lapsed_before[(r["id"], it["n"])] = lapses[it["key"]]
        if j + 1 < len(records):
            for it in r.get("items") or []:
                if out["pairs"][j]["items"].get(f"{r['id']}.{it['n']}") == "lapsed":
                    lapses[it["key"]] += 1
    for j, r in enumerate(records):
        its = r.get("items") or []
        for it in its:
            if "lapsed" in it and it["lapsed"] != lapsed_before[(r["id"], it["n"])]:
                out["lapsed_counts"].append(f"{r['id']}.{it['n']}: lapsed {it['lapsed']}, re-derived {lapsed_before[(r['id'], it['n'])]}")
            for e in records[:j]:
                for x in e.get("items") or []:
                    if x["key"] != it["key"]:
                        continue
                    if it["kind"] == "clarify":
                        out["suppression"].append(f"{r['id']}.{it['n']}: clarify key {it['key']} offered again (first in {e['id']})")
                    elif it["kind"] != "cause" and set(it.get("evidence") or []) <= set(x.get("evidence") or []):
                        out["suppression"].append(f"{r['id']}.{it['n']}: {it['key']} offered again without new evidence (as in {e['id']})")
            if it["kind"] == "cause" and lapsed_before[(r["id"], it["n"])] >= 2:
                out["suppression"].append(f"{r['id']}.{it['n']}: cause {it['key']} offered after two lapses")
        if len(its) > cap or (r.get("held_back") and len(its) < cap):
            out["cap"].append(f"{r['id']}: {len(its)} items, {len(r.get('held_back') or [])} held back (cap {cap})")
        want = [x["key"] for x in sorted(its, key=lambda it: order_key(it, weight_of(it)))]
        got = [x["key"] for x in sorted(its, key=lambda x: x["n"])]
        if want != got:
            out["order"].append(f"{r['id']}: items in the order {got}, 4.5a gives {want}")
    return out


# ------------------------------------------------------------------------------------------------------------------ main
def git_log_text(ev: Path) -> str:
    p = ev / "org-git-log.txt"
    return p.read_text(errors="replace") if p.is_file() else ""


def run(ev: Path, out: Path, as_of=None, since=None, t0=None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    org = Org(ev)
    commits = parse_history(ev / "charter-history.txt")
    reasons = applied_reasons(commits, git_log_text(ev))
    applied = set(reasons)
    sig = {"thresholds": org.thresholds, "service": signal_service(org, as_of), "checker": [], "clarify": []}
    for s in org.services:
        if service_versions(org, s):
            sig["checker"].append(signal_checker(org, s, as_of))
            sig["clarify"].extend(signal_clarify(org, s, as_of))
    sig["service_due"] = any(c["fires"] for c in sig["service"])
    sig["checker_due"] = any(c["fires"] and c["kind"] == "checker-add" for s in sig["checker"] for c in s["candidates"])
    (out / "signals.json").write_text(L.jdump(sig))
    (out / "shapes.json").write_text(L.jdump({"cases": one_off_cases(org, as_of), "groups": shape_groups(one_off_cases(org, as_of), org.thresholds["shape_overlap"])}))
    show = git_texts(ev)
    events = events_of(ev)
    d8rows = d8(org, since, as_of, applied, reasons, commits, show, events)
    (out / "d8.json").write_text(L.jdump(d8rows))
    d7 = [{**x, "key": ["contract", x["change"].split(" contract ")[0], int(re.search(r" v(\d+) ", x["change"]).group(1))]}
          for s in org.services if service_versions(org, s) for x in d7_amendments(org, s, since, as_of)]
    d7 += d7_structural(org, since, as_of, commits, reasons)
    (out / "d7.json").write_text(L.jdump(d7))
    edits = unprompted_edits(commits, t0, applied, org)
    (out / "edits.json").write_text(L.jdump({"t0": iso(t0), "applied": sorted(applied), "count": len(edits), "edits": edits,
                                            "commits": len(commits),
                                            "d8_unprompted": [x for x in d8(org, t0, as_of, applied, reasons, commits, show, events)
                                                              if x["kind"] == "charter changed" and x["label"] in UNPROMPTED_LABELS]}))
    recs = [r for r in org.ledger.get("briefs") or [] if as_of is None or L.parse_time(r["at"]) <= as_of]
    judged = {c["key"]: c["weight"] for c in sig["service"]}
    shape_keys = {c["key"]: tuple(c["group"]["criteria_key"]) for c in sig["service"]}
    wfn = lambda it: judged.get(it["key"], len(it.get("evidence") or [])) if it["kind"] == "service" else (  # noqa: E731
        0 if it["kind"] in ("clarify", "retire", "reclaim") else (1 if it["kind"] in ("cause", "answer") else len(it.get("evidence") or [])))
    (out / "ledger.json").write_text(L.jdump({**ledger_check(org), "rules": ledger_rules(recs, effect_facts(org), org.thresholds["items"], wfn, shape_keys)}))
    return {"signals": sig, "edits": len(edits)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stream")
    ap.add_argument("--out", required=True)
    ap.add_argument("--as-of")
    ap.add_argument("--since")
    ap.add_argument("--t0")
    a = ap.parse_args()
    r = run(Path(a.stream), Path(a.out), L.parse_time(a.as_of), L.parse_time(a.since), L.parse_time(a.t0))
    print(f"rederive_p2: service_due {r['signals']['service_due']} checker_due {r['signals']['checker_due']}; unprompted charter edits {r['edits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
