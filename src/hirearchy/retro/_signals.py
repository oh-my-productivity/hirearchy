"""The growth signals of the retro brief (design 7.1, 7.2; pure). Each is a function over narrow views that returns candidate items.

A signal reads only human-tier evidence (the user's own verdicts), runtime facts (runs, times, the agents' tree and limits) and root's own tasks; its inputs are the typed
views of ``_views`` and none holds a lesson, a memory, a note or a report of a team, so a text a team wrote can never nominate an item (7.7). No call it builds lowers a
criterion or a budget: a service is added with the criteria the user's own tasks had, a check adds an instruction or a checker, and a budget only goes up."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from fractions import Fraction

from ..kernel import strip_markers
from ..services import line_key, listed_added_words
from ._readings import answer_of
from ._shapes import ShapeGroup, criteria_key, title_skeleton
from ._texts import cause_question, day, quoted
from ._views import FailedCase, HealthFlag, Passed, Said, ServiceFailures, Sourced, TakenFix
from .api import Item, RetroThresholds

REF = "B{n}.{k}"  # where the call and the revert carry the id of the item, which the brief writes
CALL = 'propose_org(blueprint=<the blueprint of this item>, extend="current")'
SLACK = Fraction(5, 4)  # the largest case of a repeated task, plus 25%
FIX_RUNS = 3  # the runs of an in-team fix when it finds the defect (the author's fix, the re-check, the owner's routing)
LINE_MAX = 300
ASK_NONE = 'About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.'  # Phase 1's question when root has no reading yet


def _json(value: Mapping[str, object]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _dates(whens: Sequence[object]) -> str:
    return ", ".join(sorted({day(w) for w in whens}))  # type: ignore[arg-type]


# ----------------------------------------------------------------------------------------------------------------- 7.1 repeated one-off work


def _name(skeleton: Sequence[str]) -> str:
    words = [t for t in skeleton if t.isalpha()][:3]
    return "-".join(words) if words else "repeated-task"


def service_items(
    found: Sequence[ShapeGroup], offers: Mapping[str, frozenset[tuple[str, ...]]], taken: frozenset[str], estimates: Mapping[str, int], thresholds: RetroThresholds,
) -> tuple[Item, ...]:
    """The ``service`` candidates: a shape group with at least ``shape_cases`` cases that carry the user's verdict, whose assignee is a top-level agent that offers no
    service with the group's criteria key, and that is not the effect of an item already taken (``taken`` holds the keys)."""
    items: list[Item] = []
    for group in found:
        judged = [c for c in group.cases if c.judged]
        keys = {criteria_key(c.criteria) for c in group.cases}
        key = f"service|{group.assignee}|{group.head}"
        if len(judged) < thresholds.shape_cases or "/" in group.assignee or key in taken or keys & set(offers.get(group.assignee, ())):
            continue
        head = group.cases[0]
        lines = (max(group.cases, key=lambda c: c.id) if group.relations == ("overlap",) else head).criteria
        name = _name(title_skeleton(head.title))
        known = [c.runs for c in group.cases if not c.runs_unknown]
        estimate = estimates.get(group.assignee, 1)
        budget = max(math.ceil(Fraction(max(known)) * SLACK), estimate) if known else estimate
        cost = f"up to {budget} runs per request" + ("" if known else " (no run count of these tasks could be read: the team's estimate)")
        ids = tuple(c.id for c in group.cases)
        reason = f"{REF}: {len(group.cases)} one-off tasks of one shape"
        entry = {
            "owner": group.assignee, "name": name, "description": quoted(head.goal or head.title, 300),
            "inputs": [{"name": "request", "description": "what this request is about", "required": True}],
            "acceptance": [{"text": strip_markers(line), "from_tasks": list(ids)} for line in lines if strip_markers(line)],
            "deliverable": {"description": "<ASK THE USER: what one request produces>", "path": "<ASK THE USER: where it goes>"}, "budget": budget,
        }
        question = (
            f'Make the repeated task "{" ".join(title_skeleton(head.title))}" a standing service of {group.assignee}? You asked for it {len(group.cases)} times '
            f"({_dates([c.created for c in group.cases])}). It costs nothing to set up; each request uses up to {budget} runs, and is sent only when you ask."
        )
        items.append(Item(
            "service", key, ids, len(judged), 2,
            "a one-off task has no contract to clarify (rung 1); a standing service gives these tasks one contract and lets the client's verdicts improve it",
            question, CALL, 'propose_org(blueprint=<the revert blueprint of this item>, extend="current"): it retires the service and keeps its record (defining it again continues it)',
            cost, "spends within the plan: no run until you ask; lowers no criterion: the service's checks are the ones your tasks had",
            {"service": f"{group.assignee}/{name}"}, (), min(ids), _json({"reason": reason, "extend": {"add_services": [entry]}}),
            _json({"reason": f"revert of {REF}", "extend": {"retire_services": [{"owner": group.assignee, "service": name, "reason": f"revert of {REF}"}]}}),
        ))
    return tuple(items)


# ----------------------------------------------------------------------------------------------------------------- 7.2 concentrated failures


def _number(cid: str) -> int:
    return int(cid[1:]) if cid[1:].isdigit() else 0


def _merged(classes: Sequence[frozenset[str]]) -> list[frozenset[str]]:
    """The lineage classes with those that meet joined (two rejections fail one criterion when their classes meet)."""
    merged: list[frozenset[str]] = []
    for cls in classes:
        joined = cls
        for other in [m for m in merged if m & joined]:
            joined |= other
            merged.remove(other)
        merged.append(joined)
    return merged


def net_estimate(p: Fraction, r: Fraction | None, c: int, f: int) -> Fraction | None:
    """The net run saving per request of a checker (never a gate): ``p × r − c − p × f``; None when ``r`` (the runs after a first rejection) is unknown."""
    return None if r is None else p * r - c - p * f


def _fmt(x: Fraction) -> str:
    return str(int(x)) if x.denominator == 1 else f"{float(x):.1f}"


def _net_words(net: Fraction | None) -> str:
    if net is None:
        return "net run saving unknown (no run count of the rework could be read)"
    if net >= 0:
        return f"net run saving per request: about {float(net):.1f}"
    return f"about {float(-net):.1f} more runs per request than the rework it saves"


def checker_items(services: Sequence[ServiceFailures], thresholds: RetroThresholds) -> tuple[Item, ...]:
    """The ``checker-fix`` and ``checker-add`` candidates of every service: a criterion class failed in at least ``criterion_cases`` cases, or a verifier signed at least
    ``escapes`` escapes. A check that signed the failing deliveries gets one more instruction; with none (or after an instruction that did not hold) a checker is added."""
    items: list[Item] = []
    for s in services:
        wanted: dict[str, tuple[frozenset[str], str, tuple[FailedCase, ...], TakenFix | None]] = {}
        for cls in _merged([c for case in s.window for c in case.classes]):
            cases = tuple(c for c in s.window if any(k & cls for k in c.classes))
            signers = [c.signer for c in cases if c.verifier]
            verifier = min(sorted(set(signers)), key=lambda v: (-signers.count(v), v)) if signers else ""
            if len(cases) >= thresholds.criterion_cases:
                wanted.setdefault(f"{verifier}|{max(cls, key=_number)}", (cls, verifier, cases, None))
        for verifier in sorted({c.signer for c in s.window if c.escape and c.verifier}):
            escapes = tuple(c for c in s.window if c.escape and c.verifier and c.signer == verifier)
            named = [k for c in escapes for k in c.classes]
            if len(escapes) >= thresholds.escapes and named:
                top = min(_merged(named), key=lambda m: (-sum(1 for c in escapes if any(k & m for k in c.classes)), max(m, key=_number)))
                wanted.setdefault(f"{verifier}|{max(top, key=_number)}", (top, verifier, escapes, None))
        for cls, verifier, cases, _ in wanted.values():
            made = taken = next((t for t in s.taken if t.verifier == verifier and t.klass in cls), None)
            if made is not None and not made.recurred_case:
                continue  # taken and not recurred: the effect is seen, nothing more to offer
            item = _fix(s, cls, verifier, cases) if verifier and taken is None else _add(s, cls, cases, taken, thresholds)
            items.append(item)
    return tuple(items)


def _criterion(s: ServiceFailures, cls: frozenset[str]) -> tuple[str, str]:
    cid = max(cls, key=_number)
    return cid, s.criteria.get(cid, "")


def _fix(s: ServiceFailures, cls: frozenset[str], verifier: str, cases: tuple[FailedCase, ...]) -> Item:
    cid, text = _criterion(s, cls)
    head = f"Check {cid} of {s.service} item by item on every request: "
    tail = ". A deliverable that fails it is a FAIL, whatever else passes."
    line = head + quoted(text, LINE_MAX - len(head) - len(tail)) + tail
    signed = [c for c in cases if c.verifier and c.signer == verifier]
    ids = tuple(c.case for c in cases)
    question = (
        f'Tell {verifier} to check {cid} ("{quoted(text)}") item by item on every request of {s.service}? It passed {len(signed)} deliveries you then rejected on it '
        f"({_dates([c.when for c in signed])}). No extra run."
    )
    return Item(
        "checker-fix", f"checker-fix|{s.service}|{verifier}|{cid}", ids, len(cases), 2,
        "the criterion is already in the contract (rung 1 done); the check that passed these deliveries gets one more instruction", question, CALL,
        'propose_org(blueprint=<the revert blueprint of this item>, extend="current"): it takes the line out again', "0 runs per request",
        "spends nothing beyond the plan; lowers no criterion (it adds an instruction)", {"agent": verifier, "line": line}, (), min(ids),
        _json({"reason": f"{REF}: {len(cases)} cases failed {cid}", "extend": {"add_charter_lines": [{"agent": verifier, "line": line}]}}),
        _json({"reason": f"revert of {REF}", "extend": {"remove_charter_lines": [{"agent": verifier, "line": line}]}}),
    )


def _add(s: ServiceFailures, cls: frozenset[str], cases: tuple[FailedCase, ...], taken: TakenFix | None, thresholds: RetroThresholds) -> Item:
    cid, text = _criterion(s, cls)
    o = s.owner_facts
    template = o.verifier_template or "reviewer"
    base = dict(o.template_runs).get(template, 2)
    c = base + 1  # the runs it adds to every request: its own pass and the owner's routing
    known = [x.rework_runs for x in cases if x.rework_runs is not None]
    r = Fraction(sum(known), len(known)) if known else None
    p = Fraction(len(cases), max(s.judged, len(cases)))
    net = net_estimate(p, r, c, FIX_RUNS)
    ids = tuple(x.case for x in cases)
    name = f"{cid.lower()}-checker"
    why = (
        f"the instruction to {taken.verifier} ({taken.ref}) did not hold: it recurred in case {taken.recurred_case}" if taken is not None
        else "no check of the team signed these deliveries, so there is no check to instruct (rung 2); more workers do not catch a defect (rung 3)"
    )
    budget = max(o.old_budget + c, o.team_estimate + base + 2)
    agent: dict[str, object] = {"parent": o.owner, "name": name, "template": template}
    if "read" in o.tools:
        agent["tools"] = ["read"]
    agent["charter_extra"] = f"Check {cid} of {s.service} on every request: {text}. Report criteria met n of m like every check."
    extend: dict[str, object] = {"add_agents": [agent]}
    undo: dict[str, object] = {"retire": [{"agent": f"{o.owner}/{name}", "reason": f"revert of {REF}"}], "budgets": [{"owner": o.owner, "service": s.service, "budget": o.old_budget}]}
    if o.children >= o.max_children or not o.can_hire:
        limit: dict[str, object] = {"agent": o.owner, "max_children": o.children + 1}
        back: dict[str, object] = {"agent": o.owner, "max_children": o.max_children}
        if not o.can_hire:
            limit["can_hire"], back["can_hire"] = True, False
        extend["limits"], undo["limits"] = [limit], [back]
    extend["budgets"] = [{"owner": o.owner, "service": s.service, "budget": budget}]
    extra = [f"net {float(net):.1f} = {_fmt(p)} × {_fmt(r)} − {c} − {_fmt(p)} × {FIX_RUNS}, from {len(cases)} of {max(s.judged, len(cases))} cases"] if net is not None and r is not None else []
    if "read" not in o.tools:
        extra.append(f"{o.owner} holds no read, so the checker can check only what the team's reports quote to it")
    question = (
        f'Add a checker to {s.service} for {cid} ("{quoted(text)}")? You rejected {len(cases)} deliveries on it ({_dates([x.when for x in cases])}). '
        f"It costs about {c} more runs per request; {_net_words(net)}."
    )
    return Item(
        "checker-add", f"checker-add|{s.service}|{cid}", ids, len(cases), 4, why, question, CALL,
        'propose_org(blueprint=<the revert blueprint of this item>, extend="current"): it retires the checker and puts the limits and the budget back', f"about {c} runs per request",
        f"spends about {c} runs per request beyond the plan: the change's PLAN FOR YOU shows the new budget, and you approve it there; lowers no criterion",
        {"owner": o.owner}, tuple(extra), min(ids), _json({"reason": f"{REF}: {len(cases)} cases failed {cid}", "extend": extend}),
        _json({"reason": f"revert of {REF}", "extend": undo}),
    )


# ----------------------------------------------------------------------------------------------------------------- 7.4 idle or stranded agents


def idle_items(
    flags: Sequence[HealthFlag], last_checks: Mapping[str, str], owners: Mapping[str, tuple[str, ...]],
) -> tuple[tuple[Item, ...], tuple[str, ...]]:
    """The ``retire`` and ``reclaim`` candidates of the agents ``health`` flagged ``idle`` or ``stranded_budget``, and the D6 lines for the ones it does not suggest: an
    agent that is the last check of a service, or that owns one (its service waits for requests), is kept; a stranded agent below the top level is a line that names its parent."""
    items: list[Item] = []
    lines: list[str] = []
    for f in flags:
        held = f.held or 0
        if f.flag == "idle":
            if f.addr in last_checks:
                lines.append(f"- {f.addr}: idle, kept: last check of {last_checks[f.addr]}")
            elif owners.get(f.addr):
                lines.append(f"- {f.addr}: idle, owns {', '.join(owners[f.addr])}: kept")
            else:
                items.append(Item(
                    "retire", f"retire|{f.addr}", (f.addr,), 0, 7,
                    f"{f.addr} has no open task and no activity for {f.idle_for}; nothing cheaper applies to an agent with no work",
                    f"Retire {f.addr} (idle for {f.idle_for})? Its unspent runs come back.", CALL,
                    "an extension that adds the agent again with the same role (its charter stays in the retired tree)", f"returns its {held} unspent runs",
                    "spends nothing; lowers no criterion", {"agent": f.addr}, (), f.addr,
                    _json({"reason": f"{REF}: idle for {f.idle_for}", "extend": {"retire": [{"agent": f.addr, "reason": f"idle for {f.idle_for} ({REF})"}]}}),
                ))
        elif f.flag == "stranded_budget":
            if "/" in f.addr:
                lines.append(f"- {f.addr}: stranded, holds {held} unspent runs: ask {f.addr.rsplit('/', 1)[0]}")
            else:
                items.append(Item(
                    "reclaim", f"reclaim|{f.addr}", (f.addr,), 0, 0, "", f"Take back the {held} unspent runs {f.addr} holds?", f"reclaim(report={f.addr})",
                    f"send(to={f.addr}, budget={held})", f"returns {held} runs", "spends nothing; lowers no criterion", {"agent": f.addr}, (), f.addr,
                ))
    return tuple(items), tuple(lines)


# ----------------------------------------------------------------------------------------------------------------- 7.5 a criterion that rests on root's words


def clarify_items(rows: Sequence[Sourced], thresholds: RetroThresholds) -> tuple[Item, ...]:
    """The ``clarify`` candidates (F-P1-3): a criterion with source ``user`` or ``amendment`` and at least ``added_words`` words of root's own, and every one with source
    ``tasks`` (root wrote those lines into its one-off tasks), once it was exercised in ``accepted_cases`` accepted cases. A ``default`` and an ``unknown`` source never fire."""
    items: list[Item] = []
    for c in rows:
        words_of_root = c.kind in ("user", "amendment") and len(c.added) >= thresholds.added_words
        if not (words_of_root or c.kind == "tasks") or c.accepted < thresholds.accepted_cases:
            continue
        text = quoted(c.text)
        if c.kind == "tasks":
            question = f'{c.id} of {c.service} reads "{text}": I wrote it for your one-off tasks. Does it say what you meant?'
        else:
            asked = f', your answer to "{quoted(c.asked)}"' if c.kind == "user" and c.asked else ""
            question = f'{c.id} of {c.service} reads "{text}". It rests on your words "{quoted(c.quote)}"{asked}; the words {listed_added_words(c.added)} are mine. Does it say what you meant?'
        items.append(Item(
            "clarify", f"clarify|{c.service}|{c.id}|{line_key(c.text)[:40]}", (f"{c.service}/{c.id}",), 0, 1, "no rejection names it, so nothing else will ever show it again", question,
            "nothing to record: keep it", "the same call back", "no run", "spends nothing; lowers no criterion (a no leads to your own wording, recorded with your words)",
            {"service": c.service, "criterion": c.id},
            (f'On no: ask what they meant, then define_service(owner, name, remove_acceptance=["{c.id}"], add_acceptance=[<their wording>], words=<their answer, verbatim>)',),
            f"{c.service}/{c.id}",
        ))
    return tuple(items)


# ----------------------------------------------------------------------------------------------------------------- 7.6 causes and unanswered rejections


def cause_items(escapes: Sequence[Passed]) -> tuple[Item, ...]:
    """The ``cause`` candidates: an escape whose cause is untyped, or disputed (its ``also`` types are not empty), with the one question that settles it."""
    items: list[Item] = []
    for e in escapes:
        if e.cause != "untyped" and not e.also:
            continue
        ref = e.refs[0] if e.refs else e.delivery
        steps = (
            f'a gap in the criteria: define_service(..., answers=..., about=..., words=...) if the rejection is not yet answered, or feedback(task_id="{e.delivery}", "reject", confirms=<note>, criterion=[<C>], source="human", note=<their words>)',
            f'a check that missed it: the same link naming the criterion the reviewer passed (the cause is then read as a missed check by rule)',
            'a one-off: the same link with criterion=["none"]',
        )
        items.append(Item(
            "cause", f"cause|{ref}", (ref,), 1, 1, "the cause decides which check to improve, and no one has typed it", cause_question(ref, e.service, e.when, e.words, e.cause, e.also),
            "ask the user; then record their answer as a link (see Details)", "none needed (a later corrected link changes it again)", "no run", "spends nothing; lowers no criterion",
            {"rejection": ref}, steps, e.delivery,
        ))
    return tuple(items)


def answer_items(rows: Sequence[Said]) -> tuple[Item, ...]:
    """The ``answer`` candidates: a human rejection still without an answer (Phase 1's ``unanswered``: no human link and no answering version)."""
    items: list[Item] = []
    for r in rows:
        if not r.service or answer_of(r) != "no answer yet":
            continue
        question = r.question or ASK_NONE
        yes = f'define_service(owner="{r.owner}", name="{r.service}", ..., answers="{r.rejection_id}", about=<the id you asked about>, words=<their answer, verbatim>)'
        no = f'feedback(task_id="{r.task}", verdict="reject", confirms="{r.rejection_id}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>)'
        items.append(Item(
            "answer", f"answer|{r.ref}", (r.ref,), 1, 1, "the rejection has no answer yet, so its next request waits", question, f"on yes: {yes}; on no: {no}",
            "none needed (a later corrected link changes it again)", "no run", "spends nothing; lowers no criterion", {"rejection": r.ref}, (), r.rejection_id or r.ref,
        ))
    return tuple(items)
