"""The text of the quality view (0b 9.2): pure functions from a record and its thresholds to lines.

Only root's own words are quoted (a case's title, a counted human-tier verdict's words); text an agent wrote (lessons, playbook reasons and lines, result
bodies, agents' task titles, file names) never appears, and artifact paths and model names go through ``shown_name`` (I8). A rate goes through ``ratio``,
so a zero denominator reads ``n/a`` and is never a pass (I3)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from fractions import Fraction
from typing import TypeVar

from ..kernel import ROOT, JsonObject, clip_line, msg_time
from ..reflection import (
    Case, Cause, CharterMark, ContractMark, ItemWatch, Mark, ModelMark, PlaybookMark, QualityThresholds, ServiceRecord, TopUpMark, case_spend, cost_alarm,
    attribution, failure_class, repeat_alarm, shown_name, user_cost, watch_entry,
)
from ._quality_facts import (
    EscapeRow, FirstLine, HeldTask, MovedPast, QualityView, RecordView, approved_of, delivery_facts, escape_rows, first_lines, verifiers,
)

T = TypeVar("T")

LIMIT = 10  # the cases, escapes and ids a block lists; the rest are counted
TIMELINE_SHOWN = 15
TITLE_CHARS = 80
WORDS_CHARS = 160
PATH_CHARS = 200  # an artifact path, as the deliverable note shows a folder
NAME_CHARS = 120

_RUNS_HEAD = (
    "  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: the contract's "
    "{budget} per request, or more where your hand-downs raised it (runs used + held + new, at that moment)):"
)
_ONE_OFF_RUNS_HEAD = (
    "  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: each task's own "
    "budget, or more where your hand-downs raised it (runs used + held + new, at that moment)):"
)
_NO_HISTORY = "unknown (no org history: the organization is not a git repository, or git is missing)"
_SKIPPED = "{n} version(s) not compared: larger than 64 KiB, unreadable or not parseable"
_TRUNCATED = "older changes may be missing: only the newest 40 commits are read, within 5 s"
_TOP_UPS = {
    "human": "human rework {id}", "relayed": "your relayed rework {id}", "unrecorded": "rework {id} (tier not recorded)", "granted": "your grant {id}",
}
_REWORKS = {"human": "human rework", "relayed": "your relayed rework"}


def ratio(k: int, n: int) -> str:
    """``"{k} of {n}"``; ``"n/a (0 of 0)"`` when there is nothing to divide by (I3: a zero denominator is never a pass)."""
    return f"n/a ({k} of {n})" if n == 0 else f"{k} of {n}"


def two_decimals(value: Fraction) -> str:
    """``value`` (not negative) with two decimals, rounded half up, computed exactly (no float)."""
    hundredths = (value.numerator * 200 + value.denominator) // (2 * value.denominator)
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def _newest(items: Sequence[T]) -> tuple[Sequence[T], int]:
    """The ``LIMIT`` newest of ``items`` (the last ones, oldest first) and how many earlier ones are left out."""
    return items[-LIMIT:], max(0, len(items) - LIMIT)


def _ids(ids: Sequence[str]) -> str:
    """At most ten ids (the newest), then ``and {k} more``."""
    shown, more = _newest(ids)
    return ", ".join(shown) + (f", and {more} more" if more else "")


def _time(when: datetime | None) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M") if when is not None else "time unknown"


# ------------------------------------------------------------------------------------------------------------------------ causes (5.3)


def cause_text(cause: Cause) -> str:
    """The words of an escape's cause (5.3), with the types it may also be and the relayed rework the user may have judged."""
    d = cause.detail
    if cause.type == "relayed-error":
        text = f"relayed-error (the rejected delivery is your relayed rework {d[0]})"
    elif cause.type == "relayed-carry-over":
        text = (
            f"relayed-carry-over (your relayed rework {d[0]} delivered {shown_name(d[1], PATH_CHARS)} after the delivery the user judged, "
            "and the rejected delivery lists it too)"
        )
    elif cause.type == "reviewer-miss":
        text = (
            f"reviewer-miss (the user's confirmed link {d[0]} names {', '.join(d[1:])}, which contract v{cause.version} of the task had; "
            "the team reported done)"
        )
    elif cause.rule == "answer":
        missing = [c for c in d[1:] if c not in cause.removes]
        clauses = []
        if missing:
            clauses.append(f"{', '.join(missing)}, which contract v{cause.version} of the task did not have")
        if cause.removes:
            clauses.append(f"{', '.join(cause.removes)}, which the answering contract v{cause.answering} removes")
        text = f"contract-gap (the user's answer, link {d[0]}, names {', and '.join(clauses)})"
    elif cause.type == "contract-gap":
        text = f"contract-gap (the user's words say \"{d[0]}\")"
    elif cause.rule == "unreadable":
        text = f"untyped (the contract could not be read: {d[0]})"
    else:
        text = f"untyped ({d[0] if d else 'no rule matched'})"
    if cause.also:
        text += f"; also {', '.join(cause.also)}"
    if cause.before_verdict:
        text += f"; your relayed rework {cause.before_verdict} delivered after it and before the verdict: the user may have judged that version"
    return text


# ------------------------------------------------------------------------------------------------------------------------ the lines of a block


def _cases_line(view: RecordView) -> str:
    cases = view.record.cases
    states = {s: sum(1 for c in cases if c.state == s) for s in ("done", "failed", "blocked", "open")}
    if view.stalled_error:
        stalled = f"stalled: unknown ({view.stalled_error})"
    else:
        stalled = f"stalled {sum(1 for c in cases if c.state == 'open' and view.stalled.get(c.id, False))}"
    text = f"  cases: {len(cases)} (done {states['done']}, failed {states['failed']}, blocked {states['blocked']}, open {states['open']} ({stalled}))"
    left = sum(1 for c in cases if c.tasks[-1].id in view.left_blocked)
    return text + (f"; {left} blocked and moved past without a verdict" if left else "")


def _first_summary(firsts: Sequence[FirstLine]) -> str:
    count = {o: sum(1 for f in firsts if f.outcome == o) for o in ("accepted", "rejected", "none", "neither", "never")}
    superseded = sum(1 for f in firsts if f.outcome == "none" and f.superseded is not None)
    text = f"  first deliveries: {count['accepted']} accepted, {count['rejected']} rejected, {count['none']} without a verdict"
    if superseded:
        text += f" ({superseded} superseded by a rework before a verdict)"
    if count["neither"]:
        text += f", {count['neither']} judged after the file changed (neither)"
    if count["never"]:
        text += f"; {count['never']} never delivered"
    return text


def _first_line(first: FirstLine) -> str:
    head, outcome = f"    {first.case.id}: ", first.outcome
    if outcome == "never":
        return f"{head}never delivered ({first.case.state})"
    verdict = first.delivery.decisive if first.delivery is not None else None
    if outcome in ("accepted", "rejected"):
        words = clip_line(verdict.note, WORDS_CHARS) if verdict is not None else ""
        return f'{head}{outcome}: "{words}"' if words else f"{head}{outcome} (no words)"
    if outcome == "neither":
        return f"{head}judged after the file changed (neither): the user's verdict came after the file was changed"
    if first.superseded is None:
        return f"{head}no verdict"
    source, id_ = first.superseded.source, first.superseded.id
    if source is None:
        return f"{head}no verdict (superseded by rework {id_} (tier not recorded))"
    return f"{head}no verdict (superseded by {_REWORKS.get(source, 'rework')} {id_})"


def _judged_line(view: RecordView) -> str:
    r = view.record
    f = delivery_facts(r)
    text = f"  judged by the user: {ratio(f.judged, f.total)} deliveries; without a verdict: {len(f.unjudged)} case(s)"
    if f.unjudged:
        text += f" ({_ids(f.unjudged)}): never counted as accepted"
    if f.relayed_only:
        text += f" ({len(f.relayed_only)} with only your own relayed verdict)"
    if f.unseen_relayed:
        text += f"; {len(f.unseen_relayed)} later relayed delivery(ies) the user was not given ({_ids(f.unseen_relayed)})"
    if r.files_error:
        return text + f"; not as delivered: unknown ({r.files_error})"
    text += f"; not as delivered: {len(f.not_as_delivered)}"
    if f.not_as_delivered:
        text += f" ({_ids([d.task.id for d in f.not_as_delivered])})"
    if f.neither:
        text += f"; {len(f.neither)} judged after the file changed: neither pass nor escape ({_ids([d.task.id for d in f.neither])})"
    if f.not_as_delivered and not r.history.known:
        text += " (compared with the team's current files: no org history)"
    return text


def _legacy_line(view: RecordView) -> list[str]:
    f = delivery_facts(view.record)
    parts = []
    if f.legacy:
        parts.append(f"legacy verdicts (no source: read as the user's, the 0a rule): {f.legacy}")
    if f.not_on_a_delivery:
        parts.append(
            f"verdicts not on a delivery (on a blocked or failed result, or before the done result): {len(f.not_on_a_delivery)} ({_ids(f.not_on_a_delivery)})",
        )
    return ["  " + "; ".join(parts)] if parts else []


def _escape_lines(view: RecordView) -> list[str]:
    r = view.record
    rows = escape_rows(r)
    f = delivery_facts(r)
    head = "  escapes (the team reported done, then the user rejected it): "
    if not rows:
        return [f"{head}none (judged: {ratio(f.judged, f.total)})"]
    shown, more = _newest(rows)
    lines = [f"{head}{len(rows)}", *(_escape_row(row, not r.service) for row in shown)]
    return lines + ([f"    and {more} earlier escape(s)"] if more else [])


def _escape_row(row: EscapeRow, one_off: bool) -> str:
    who = f"signed off by {row.delivery.signer}: {cause_text(row.cause)}"
    return f"    rejected case {row.case.id} ({row.case.owner}), {who}" if one_off else f"    {row.assertion} case {row.case.id}, {who}"


def _verifier_lines(view: RecordView) -> list[str]:
    r = view.record
    if not r.deliveries:
        return ["  verifiers: none (no delivery yet)"]
    found = verifiers(r)
    if not found:
        owners = r.owner if r.service else ", ".join(dict.fromkeys(c.owner for c in r.cases))
        return [f"  verifiers: none (every delivery was signed off by {owners} itself)"]
    lines = ["  verifiers:"]
    for v in found:
        text = f"    {v.addr}: escapes {ratio(v.escapes, v.judged)} judged"
        if v.counted:
            text += " (" + ", ".join(f"{n} {kind}" for kind, n in v.counted) + ")"
        if v.not_its:
            text += "; not its: " + ", ".join(f"{n} {kind}" for kind, n in v.not_its)
        if v.addr in view.fails_errors:
            fails = f"unknown ({view.fails_errors[v.addr]})"
        else:
            rechecks, rework = view.fails.get(v.addr, (0, 0))
            fails = f"{rechecks} re-check(s), {rework} author rework run(s)"
        lines.append(f"{text}; PASS precision {ratio(v.judged - v.escapes, v.judged)}; its FAILs before delivery: {fails}")
    return lines


def _top_ups(case: Case) -> str:
    if not case.top_ups.items:
        return "none"
    return ", ".join(f"+{t.amount} " + _TOP_UPS.get(t.kind, "rework {id}").format(id=t.id) for t in case.top_ups.items)


def _case_line(view: RecordView, case: Case) -> list[str]:
    r = view.record
    who = "" if r.service else f" ({case.owner})"
    head = f'    {case.id} "{clip_line(case.title, TITLE_CHARS)}"{who}: '
    tail = f"; top-ups: {_top_ups(case)}" + ("; window cut by a later request" if case.cut else "")
    if case.runs_unknown:
        return [f"{head}runs not counted ({case.runs_unknown}){tail}"]
    used, approved = user_cost(case), approved_of(r, case)
    shown = f"n/a (budget 0)" if approved <= 0 else f"({two_decimals(Fraction(used, approved))}x)"
    charged = f", {case.credited} not charged (model-service throttle)" if case.credited else ""
    lines = [f"{head}{used} of {approved} approved {shown}{charged}{tail}"]
    if case.relayed_runs:
        lines.append(f"      your relayed reworks: {case.relayed_runs} run(s), your own spend; total {case_spend(case)}")
    return lines


def _runs_lines(view: RecordView) -> list[str]:
    r = view.record
    head = _RUNS_HEAD.format(budget=r.budget) if r.service else _ONE_OFF_RUNS_HEAD
    if not r.cases:
        return [f"{head} none"]
    shown, more = _newest(r.cases)
    lines = [head]
    for case in shown:
        lines += _case_line(view, case)
    return lines + ([f"    and {more} earlier case(s), counted above"] if more else [])


def _repeat_text(view: RecordView, t: QualityThresholds) -> str:
    a = repeat_alarm(view.record, t)
    if a.state == "does not apply":
        return "does not apply (one-off tasks name no criterion ids)"
    if a.state == "fires":
        text = "FIRES: " + "; ".join(f"{s} failed in {len(ids)} of the last {len(a.window)} judged cases (cases {', '.join(ids)})" for s, ids in a.cases)
    elif a.state == "no":
        text = f"no ({len(a.window)} judged cases; counted: {', '.join(s for s, _ in a.subjects) or 'none'})"
    else:
        text = f"n/a ({a.judged} of {t.min_judged} judged cases)"
    if a.not_counted:
        text += "; not counted: " + ", ".join(f"{r}'s reading {', '.join(ids)} (not confirmed)" for r, ids in a.not_counted)
    return text


def _cost_text(view: RecordView, t: QualityThresholds) -> str:
    a = cost_alarm(view.record, t)
    if a.state == "fires":
        text = "FIRES: " + ", ".join(
            f"case {c.case} {c.user_cost} of {c.user_approved} approved ({two_decimals(c.ratio)}x)"
            + (f"; your relayed reworks {c.relayed_runs}, total {c.total}" if c.relayed_runs else "")
            for c in a.cases
        )
    elif a.state == "no":
        text = f"no (0 of {a.compared} cases above {t.cost_ratio_text}x)"
    elif a.judged < t.min_judged:
        text = f"n/a ({a.judged} of {t.min_judged} judged cases)"
    else:
        text = "n/a (0 of 0 cases compared)"
    skipped = [f"{_ids([c for c, why in a.skipped if why == reason])} ({reason})" for reason in ("runs not counted", "budget 0") if any(w == reason for _, w in a.skipped)]
    return text + (f"; skipped: {', '.join(skipped)}" if skipped else "")


def _alarm_lines(view: RecordView, t: QualityThresholds) -> list[str]:
    return ["  alarms:", f"    repeat: {_repeat_text(view, t)}", f"    cost: {_cost_text(view, t)}"]


def _mark_line(mark: Mark) -> str:
    return f"    {_time(getattr(mark, 'when', None))} {mark.text}"


def _timeline_lines(view: RecordView) -> list[str]:
    r = view.record
    shown, more = r.timeline[-TIMELINE_SHOWN:], max(0, len(r.timeline) - TIMELINE_SHOWN)
    lines = ["  timeline (bar changes, UTC; marked, never used to split the counts):", *(_mark_line(m) for m in shown)]
    if more:
        lines.append(f"    and {more} earlier")
    h = r.history
    listed = any(isinstance(m, (CharterMark, ModelMark)) for m in r.timeline)
    remarks = [f"({_SKIPPED.format(n=h.skipped)})"] if h.known and h.skipped else []
    if h.known and h.truncated:
        remarks.append(f"({_TRUNCATED})")
    base = "" if listed else (_NO_HISTORY if not h.known else "none")
    if base or remarks:
        lines.append("    charter edits and model changes: " + " ".join(x for x in (base, *remarks) if x))
    return lines


def _watch_lines(view: RecordView) -> list[str]:
    """One line, in 14.3's words, when the record's watch holds an item that is not ``kept`` (design 14.4): ids and counts, never an item's words."""
    shown = [watch_entry(w) for w in view.record.watch if w.state != "kept"]
    return [f"  playbook watch: {', '.join(shown)}"] if shown else []


def _attribution_line(view: RecordView) -> str:
    cut = sum(1 for c in view.record.cases if c.cut)
    tail = "; their later runs count for that request" if cut else ""
    return f"  run attribution is by time window (08 3.3): {cut} case(s) had their window cut by a later request{tail}."


def _block(view: RecordView, t: QualityThresholds, heading: str) -> list[str]:
    firsts = first_lines(view.record)
    shown, more = _newest(firsts)
    lines = [heading, _cases_line(view), _first_summary(firsts), *(_first_line(f) for f in shown)]
    if more:
        lines.append(f"    and {more} earlier case(s), counted above")
    lines += [_judged_line(view), *_legacy_line(view), *_escape_lines(view), *_verifier_lines(view), *_runs_lines(view), *_alarm_lines(view, t)]
    return lines + [*_timeline_lines(view), *_watch_lines(view), _attribution_line(view)]


def service_block(view: RecordView, t: QualityThresholds) -> list[str]:
    """The block of a service root requests (9.2), without blank lines: its heading, then cases, first deliveries, verdict counts, escapes, verifiers,
    runs per case, the alarms, the timeline and the run attribution."""
    r = view.record
    playbook = f"playbook v{r.playbook}" if r.playbook else "no playbook"
    heading = f"{r.service} (offered by {r.owner}; client: you, human; unit: case; contract v{r.contract}, {playbook}; approved {r.budget} runs per request)"
    return _block(view, t, heading)


def one_off_block(view: RecordView, t: QualityThresholds) -> list[str]:
    """The block of the tasks root gave without a service (9.2): the lines of a service block, with each task's own budget as the approval, the assignee
    on each case and escape line, no ``R<k>``, and no criterion ids for the repeat alarm to read."""
    return _block(view, t, "One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)")


def nested_line(view: RecordView) -> str:
    """The line of a service an agent requests (its client is an agent: its verdicts are hypotheses, never counted)."""
    r = view.record
    verdicts = sum(len(c.verdicts) for c in r.cases)
    return f"- {r.service} (offered by {r.owner}; client {r.client}): {len(r.cases)} case(s), {len(r.deliveries)} delivered, {verdicts} agent verdict(s)"


def header_lines(t: QualityThresholds, notes: Sequence[str]) -> list[str]:
    """The title, the thresholds in force and each note about them (6, 16), one per line."""
    where = "from ORG.md quality:" if t.source == "ORG.md" else "the defaults"
    return [
        "Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).",
        f"Thresholds: {where} (tunable): alarms need {t.min_judged} judged cases; repeat: one id failing in {t.repeat_failures} of the last "
        f"{t.repeat_window} judged cases; cost: a case above {t.cost_ratio_text}x its approved runs.",
        *notes,
    ]


def _held_line(addr: str, held: HeldTask) -> str:
    who = f'you ("{clip_line(held.task.title, TITLE_CHARS)}")' if held.task.sender == ROOT else held.task.sender
    since = f"{'you have' if held.task.sender == ROOT else f'{held.task.sender} has'} sent {addr} {held.sent_since} task(s) since"
    status = f"left blocked: {since}" if held.left_blocked else "blocked, nothing sent since"
    return f"    task {held.task.id} from {who}, blocked {_time(msg_time(held.blocked))}: {status}"


def moved_past_lines(moved: Sequence[MovedPast]) -> list[str]:
    """The moved-past section (4.5): the agents with a task left blocked, each with every task it holds, or ``none``."""
    if not moved:
        return ["Blocked tasks moved past without a verdict: none."]
    lines = ["Blocked tasks moved past without a verdict (while one stays blocked, its assignee's later results return no runs):"]
    for m in moved:
        if m.error:
            lines.append(f"  {m.addr}: blocked tasks cannot be read ({m.error})")
            continue
        if m.held is None:
            holds = f"holds an unknown number of runs ({m.held_error})"
        else:
            holds = f"holds {m.held} run(s)" if m.held > 0 else f"holds no run (budget {m.held})"
        lines += [f"  {m.addr} {holds}:", *(_held_line(m.addr, h) for h in m.tasks)]
    return lines


def _record_lines(view: RecordView, t: QualityThresholds) -> list[str]:
    r = view.record
    if not r.error:
        return service_block(view, t)
    return [f"{r.service} (offered by {r.owner}): cannot be read ({r.error})."]


def _nested_section(views: Sequence[RecordView]) -> list[str]:
    head = "Services your agents request (the client is an agent: its verdicts are hypotheses, never counted):"
    return [head, *(nested_line(v) if not v.record.error else f"- {v.record.service} (offered by {v.record.owner}): cannot be read ({v.record.error})." for v in views)]


def quality_text(view: QualityView) -> str:
    """The whole text (9.2): the header block, a block per service root requests, the one-off block, the nested services and the moved-past section,
    one blank line between two of them and none inside, none at either end. Without ``service`` ``No cases yet`` replaces the blocks when nothing was
    requested or given; with it only the blocks of that service appear."""
    t = view.thresholds
    top = [v for v in view.records if v.record.service and v.record.client_kind == "human"]
    nested = [v for v in view.records if v.record.service and v.record.client_kind != "human"]
    off = next((v for v in view.records if not v.record.service), None)
    sections: list[list[str]] = [header_lines(t, view.notes)]
    sections += [_record_lines(v, t) for v in top]
    if view.service is None:
        if off is not None and off.record.error:
            sections.append([f"One-off tasks you gave: cannot be read ({off.record.error})."])
        elif off is not None and off.record.cases:
            sections.append(one_off_block(off, t))
        elif top or nested:
            sections.append(["One-off tasks you gave: none."])
    if nested:
        sections.append(_nested_section(nested))
    if view.service is None and not top and not nested and (off is None or not (off.record.cases or off.record.error)):
        sections.append(["No cases yet: you have requested no service and given no task."])
    sections.append(moved_past_lines(view.moved_past))
    return "\n\n".join("\n".join(lines) for lines in sections)


# ------------------------------------------------------------------------------------------------------------------------ the JSON (9.4)


def _stamp(when: datetime | None) -> str | None:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if when is not None else None


def _mark_data(mark: Mark) -> JsonObject:
    when = _stamp(getattr(mark, "when", None))
    if isinstance(mark, ContractMark):
        return {
            "kind": "contract", "when": when, "version": mark.version, "by": mark.by, "adds": list(mark.adds), "removes": list(mark.removes),
            "basis": mark.basis, "answers": mark.answers if mark.basis == "answers" else None,
            "confirmed": [{"id": i, "link": link} for i, link in mark.confirmed], "not_confirmed": list(mark.not_confirmed),
        }
    if isinstance(mark, PlaybookMark):
        return {
            "kind": "playbook", "when": when, "version": mark.version, "by": mark.by, "basis": mark.basis, "op": mark.op, "item": mark.item,
            "item_kind": mark.item_kind, "restores": mark.restores,
            "evidence": list(mark.evidence), "evidence_other": mark.evidence_other, "changed": mark.changed, "removed": mark.removed,
            "own_words": mark.own_words, "beyond": mark.beyond, "tagged": mark.tagged, "untagged": mark.untagged,
            "cited": [{"id": i, "text": text} for i, text in mark.cited], "lines": [{"text": text, "own_words": own} for text, own in mark.lines],
            "lines_more": mark.lines_more, "agent_written": mark.agent_written,
        }
    if isinstance(mark, CharterMark):
        return {"kind": "charter", "when": when, "addr": mark.addr, "commit": mark.commit}
    if isinstance(mark, ModelMark):
        return {"kind": "model", "when": when, "addr": mark.addr, "key": mark.key, "before": mark.before, "after": mark.after, "commit": mark.commit}
    assert isinstance(mark, TopUpMark)
    return {"kind": "top-up", "when": when, "case": mark.case, "id": mark.id, "source": mark.source, "amount": mark.amount}


def _watch_data(w: ItemWatch) -> JsonObject:
    return {
        "item": w.id, "kind": w.kind, "state": w.state, "k": w.k, "r": list(w.r), "clean": w.clean, "waiting": w.waiting, "related": list(w.related),
        "pending": list(w.pending), "since": _stamp(w.watch_start), "carried": w.carried,
    }


def _first_data(first: FirstLine) -> JsonObject | None:
    if first.delivery is None:
        return None
    source = first.superseded.source if first.superseded is not None else None
    return {
        "task": first.delivery.task.id, "outcome": first.outcome, "superseded_by": first.superseded.id if first.superseded is not None else None,
        "superseded_source": None if first.superseded is None else (source or "unrecorded"),
    }


def _case_data(view: RecordView, first: FirstLine) -> JsonObject:
    r, case = view.record, first.case
    counted = not case.runs_unknown
    approved = approved_of(r, case)
    return {
        "id": case.id, "title": case.title, "assignee": case.owner, "state": case.state,
        "stalled": None if view.stalled_error else (case.state == "open" and view.stalled.get(case.id, False)),
        "tasks": len(case.tasks), "budget": r.budget if r.service else case.tasks[0].budget, "user_approved": approved,
        "runs": case.runs if counted else None, "credited": case.credited if counted else None, "relayed_runs": case.relayed_runs if counted else None,
        "spend": case_spend(case) if counted else None, "user_cost": user_cost(case) if counted else None,
        "ratio": two_decimals(Fraction(user_cost(case), approved)) if counted and approved > 0 else None,
        "cut": case.cut, "runs_unknown": case.runs_unknown,
        "top_ups": [{"id": t.id, "source": t.kind, "amount": t.amount} for t in case.top_ups.items], "first": _first_data(first),
    }


def _escape_data(row: EscapeRow) -> JsonObject:
    c, d = row.cause, row.delivery
    return {
        "assertion": row.assertion or None, "case": row.case.id, "task": d.task.id, "verdict": d.decisive.message.id if d.decisive is not None else "",
        "signer": d.signer, "cause": c.type, "rule": c.rule, "rules": list(c.rules), "detail": list(c.detail), "also": list(c.also),
        "before_verdict": c.before_verdict, "attribution": attribution(c), "class": failure_class(c),
    }


def _verifier_data(view: RecordView) -> list[JsonObject]:
    out: list[JsonObject] = []
    for v in verifiers(view.record):
        error = view.fails_errors.get(v.addr, "")
        rechecks, rework = (None, None) if error else view.fails.get(v.addr, (0, 0))
        out.append({
            "addr": v.addr, "judged": v.judged, "escapes": {"counted": dict(v.counted), "not_its": dict(v.not_its)},
            "pass_precision": [v.judged - v.escapes, v.judged], "rechecks": rechecks, "rework_runs": rework, "fails_error": error,
        })
    return out


def _alarm_data(view: RecordView, t: QualityThresholds) -> JsonObject:
    repeat, cost = repeat_alarm(view.record, t), cost_alarm(view.record, t)
    return {
        "repeat": {
            "state": repeat.state, "judged": repeat.judged, "window": list(repeat.window), "subjects": dict(repeat.subjects), "fired": list(repeat.fired),
            "not_counted": {r: list(ids) for r, ids in repeat.not_counted},
        },
        "cost": {
            "state": cost.state, "judged": cost.judged, "compared": cost.compared,
            "cases": [
                {"case": c.case, "user_cost": c.user_cost, "user_approved": c.user_approved, "ratio": two_decimals(c.ratio), "relayed_runs": c.relayed_runs, "total": c.total}
                for c in cost.cases
            ],
            "skipped": [{"case": case, "reason": why} for case, why in cost.skipped],
        },
    }


def _record_data(view: RecordView, t: QualityThresholds) -> JsonObject:
    r = view.record
    head: JsonObject = {"owner": r.owner, "service": r.service, "client": r.client, "client_kind": r.client_kind, "unit": r.unit}
    if r.error:
        return {
            **head, "error": r.error, "files_error": "", "stalled_error": "", "contract": 0, "playbook": 0, "budget": None, "cases": [],
            "first_deliveries": {"accepted": 0, "rejected": 0, "no_verdict": 0, "superseded": 0, "neither": 0, "never_delivered": 0},
            "deliveries": _deliveries_data(ServiceRecord("", "", ROOT, "human")), "escapes": [], "verifiers": [], "alarms": {}, "timeline": [], "watch": [], "history": None,
        }
    firsts = first_lines(r)
    count = {o: sum(1 for f in firsts if f.outcome == o) for o in ("accepted", "rejected", "none", "neither", "never")}
    return {
        **head, "error": "", "files_error": r.files_error, "stalled_error": view.stalled_error, "contract": r.contract, "playbook": r.playbook,
        "budget": r.budget if r.service else None, "cases": [_case_data(view, f) for f in firsts],
        "first_deliveries": {
            "accepted": count["accepted"], "rejected": count["rejected"], "no_verdict": count["none"],
            "superseded": sum(1 for f in firsts if f.outcome == "none" and f.superseded is not None), "neither": count["neither"],
            "never_delivered": count["never"],
        },
        "deliveries": _deliveries_data(r), "escapes": [_escape_data(row) for row in escape_rows(r)], "verifiers": _verifier_data(view),
        "alarms": _alarm_data(view, t), "timeline": [_mark_data(m) for m in r.timeline], "watch": [_watch_data(w) for w in r.watch],
        "history": {"known": r.history.known, "truncated": r.history.truncated, "skipped": r.history.skipped},
    }


def _deliveries_data(r: ServiceRecord) -> JsonObject:
    f = delivery_facts(r)
    return {
        "total": f.total, "judged": f.judged, "unjudged_cases": list(f.unjudged), "relayed_only": list(f.relayed_only), "unseen_relayed": list(f.unseen_relayed),
        "not_as_delivered": [{"case": d.case, "task": d.task.id} for d in f.not_as_delivered], "neither": [{"case": d.case, "task": d.task.id} for d in f.neither],
        "legacy_verdicts": f.legacy, "not_on_a_delivery": list(f.not_on_a_delivery),
    }


def _moved_data(m: MovedPast) -> JsonObject:
    return {
        "addr": m.addr, "held": m.held, "held_error": m.held_error, "error": m.error,
        "tasks": [
            {
                "id": h.task.id, "sender": h.task.sender, "title": h.task.title if h.task.sender == ROOT else None, "blocked": _stamp(msg_time(h.blocked)),
                "left_blocked": h.left_blocked, "sent_since": h.sent_since,
            }
            for h in m.tasks
        ],
    }


def quality_data(view: QualityView) -> JsonObject:
    """The same data as the text, as plain JSON values (9.4): every key always present, the text's limits not applied, times as UTC strings, ratios as
    the two-decimal strings the text shows. ``one_off`` is ``None`` when root gave no one-off task, and always with ``service``."""
    t = view.thresholds
    records = view.records
    off = next((v for v in records if not v.record.service), None)
    top = [v for v in records if v.record.service and v.record.client_kind == "human"]
    nested = [v for v in records if v.record.service and v.record.client_kind != "human"]
    return {
        "schema": 1,
        "thresholds": {
            "min_judged": t.min_judged, "repeat_window": t.repeat_window, "repeat_failures": t.repeat_failures, "cost_ratio": t.cost_ratio_text, "source": t.source,
        },
        "notes": list(view.notes), "services": [_record_data(v, t) for v in top],
        "one_off": _record_data(off, t) if off is not None and view.service is None and (off.record.cases or off.record.error) else None,
        "nested": [
            {
                "owner": v.record.owner, "service": v.record.service, "client": v.record.client, "cases": len(v.record.cases),
                "delivered": len(v.record.deliveries), "agent_verdicts": sum(len(c.verdicts) for c in v.record.cases), "error": v.record.error,
            }
            for v in nested
        ],
        "moved_past": [_moved_data(m) for m in view.moved_past],
    }
