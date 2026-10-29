"""The readings of the retro brief (design 4.3): what was said (D1), what got past a check (D2), the rejections with no criterion yet (D3), the alarms and the causes
to settle (D4), the work asked for again and again (D5) and the idle or stranded agents (D6). Each is a pure function over narrow views that returns a ``Section``.

A section is capped: its block (the short form the user reads) shows at most ``BLOCK_LINES`` lines and then ``- and {j} more (Details)``; Details show at most
``DETAIL_LINES`` and then say how to list them all. A service whose record cannot be read has a line of its own, after the cap, in every section it would be read for."""

from __future__ import annotations

from collections.abc import Sequence

from datetime import datetime

from ..reflection import CostAlarm, RepeatAlarm
from ..services import listed_added_words
from . import _texts as texts
from ._changes import Changes
from ._effect import NOT_EVALUATED, Evaluated
from ._shapes import RELATIONS, ShapeGroup
from ._texts import (
    BLOCK_LINES, BLOCK_MORE, BLOCK_WORDS, DETAIL_LINES, DETAIL_MORE, HEADINGS, NONE, UNREADABLE, cause_question, day, quoted,
)
from ._views import Fate, HealthFlag, Passed, PlaybookFacts, ProposalFacts, Said, ServiceAlarms, Sourced, SpendFacts, WatchRetire
from .api import Item, RetroThresholds, Section

Unreadable = Sequence[tuple[str, str]]  # (service, why) of the services whose record could not be read

ONE_OFF = "one-off"


def _capped(lines: Sequence[str], limit: int, more: str) -> tuple[str, ...]:
    kept = list(lines[:limit])
    return tuple(kept + ([more.format(j=len(lines) - limit)] if len(lines) > limit else []))


def _section(
    key: str, block: Sequence[str], details: Sequence[str], unreadable: Unreadable, counts: tuple[tuple[str, int | str], ...], *, show: bool = True,
    tail: Sequence[str] = (), block_lines: int = BLOCK_LINES,
) -> Section:
    """The section ``key``: its block lines (``()`` when the block does not show it) and its details, capped, then the lines of the services that could not be
    read (in both) and the ``tail`` (in Details only), which the cap never hides."""
    broken = tuple(UNREADABLE.format(service=service or ONE_OFF, error=error) for service, error in unreadable)
    shown = (_capped(block, block_lines, BLOCK_MORE) + broken or (NONE,)) if show else ()
    lines = _capped(details, DETAIL_LINES, DETAIL_MORE) + tuple(tail) + broken
    return Section(key, HEADINGS[key], shown, lines or (NONE,), counts)


def _ids(ids: Sequence[str]) -> str:
    return ", ".join(ids)


def _name(service: str) -> str:
    return service or ONE_OFF


def answer_of(row: Said) -> str:
    """The answer to a rejection as Phase 1 13 defines it: the version that adds or removes criteria, ``no lasting rule``, ``same as R2``, ``one-off``, or
    ``no answer yet``."""
    if not row.service:
        return "one-off"
    if (a := row.answering) is not None:
        if a.removes and a.adds:
            return f"removed {_ids(a.removes)} (replaced by {_ids(a.adds)})"
        if a.removes:
            return f"removed {_ids(a.removes)}"
        if a.adds:
            return f"{_ids(a.adds)} added (v{a.version})"
        return f"clarified {_ids(row.about)} (v{a.version})" if row.about else f"answered (v{a.version})"
    if row.link == "none":
        return "no lasting rule"
    if row.same_as:
        return f"same as {row.same_as}"
    if row.link == "confirmed" and row.about:
        return f"about {_ids(row.about)}"
    return "no answer yet"


def d1_said(rows: Sequence[Said], accepts: int, unreadable: Unreadable) -> Section:
    """D1 What you said: every human rejection with the user's words and its answer; the accepts are counted, not listed."""
    tail = [f"- and {accepts} accepts"] if accepts else []
    block = [f'- {_name(r.service)} {r.ref}: "{quoted(r.words, BLOCK_WORDS)}" ({answer_of(r)})' for r in rows]
    details = [f'- {_name(r.service)} {r.ref} (case {r.case}, {day(r.when)}): "{r.words}" ({answer_of(r)})' for r in rows]
    return _section("d1", block + tail, details + tail, unreadable, (("rejections", len(rows)), ("accepts", accepts)))


def _passed_line(e: Passed) -> str:
    ids = _ids([*e.refs, *e.criteria])
    if e.verifier:
        return f"- {e.service}: {e.signer} passed {e.case}; you rejected it ({ids})"
    return f"- {e.service}: {e.signer} delivered {e.case} (no check of the team signed it); you rejected it ({ids})"


def d2_passed(rows: Sequence[Passed], unreadable: Unreadable) -> Section:
    """D2 What got past a check: every escape with its signer, whether that signer is a check, and the cause with its other types."""
    block = [_passed_line(e) for e in rows]
    details = [f"{_passed_line(e)}; cause {e.cause}" + (f", also {_ids(e.also)}" if e.also else "") for e in rows]
    checks = sum(e.verifier for e in rows)
    return _section("d2", block, details, unreadable, (("escapes", len(rows)), ("passed_by_a_check", checks), ("no_check_signed", len(rows) - checks)), show=True)


def d3_unlinked(rows: Sequence[Said], unreadable: Unreadable) -> Section:
    """D3 Rejections with no criterion yet: the assertions whose link is not confirmed or whose criteria are all gone."""
    lines: list[str] = []
    for r in rows:
        if not r.service:
            continue
        if r.link == "none":
            state = "no lasting rule"
        elif r.link != "confirmed":
            state = "unconfirmed"
        elif r.current_about:
            continue
        else:
            state = f"about removed {_ids(r.removed_about)} only" if r.removed_about else "about no criterion"
        lines.append(f'- {r.service} {r.ref}: "{r.words}" ({state})')
    return _section("d3", (), lines, unreadable, (("without_a_criterion", len(lines)),), show=False)


def _repeat_line(service: str, alarm: RepeatAlarm) -> str:
    classes = dict(alarm.classes)
    fired = []
    for subject in alarm.fired:
        earlier = [i for i in classes.get(subject, ()) if i != subject]
        cases = next((len(c) for s, c in alarm.cases if s == subject), 0)
        fired.append(f"{subject}" + (f" (and its earlier wording {_ids(earlier)})" if earlier else "") + f" in {cases} of {len(alarm.window)} judged cases")
    return f"- {service}: repeat alarm fires: {'; '.join(fired)}"


def _cost_line(service: str, alarm: CostAlarm) -> str:
    return f"- {service}: cost alarm fires: " + "; ".join(f"{c.case} used {c.user_cost} runs against {c.user_approved} approved" for c in alarm.cases)


def d4_alarms(rows: Sequence[ServiceAlarms], escapes: Sequence[Passed], unreadable: Unreadable) -> Section:
    """D4 Alarms and causes to settle: per service the two alarms (a firing one with its N, else both states with the judged cases), then every escape whose
    cause is untyped or disputed, each with its one question."""
    lines: list[str] = []
    firing = 0
    for r in rows:
        fires = [text for state, text in ((r.repeat.state, _repeat_line(r.service, r.repeat)), (r.cost.state, _cost_line(r.service, r.cost))) if state == "fires"]
        firing += len(fires)
        lines += fires or [
            f"- {r.service}: repeat alarm {r.repeat.state} ({r.repeat.judged} judged cases); cost alarm {r.cost.state} ({r.cost.judged} judged cases)",
        ]
    untyped = [e for e in escapes if e.cause == "untyped"]
    disputed = [e for e in escapes if e.cause != "untyped" and e.also]
    lines += [f"- {cause_question(e.refs[0] if e.refs else e.delivery, e.service, e.when, e.words, e.cause, e.also)}" for e in escapes if e in untyped or e in disputed]
    return _section("d4", (), lines, unreadable, (("alarms_firing", firing), ("untyped_causes", len(untyped)), ("disputed_causes", len(disputed))), show=False)


def d5_repeated(found: Sequence[ShapeGroup], unreadable: Unreadable, thresholds: RetroThresholds) -> Section:
    """D5 Work you ask for again and again: every shape group of two or more one-off tasks with what joined them and how many carry the user's verdict."""
    lines: list[str] = []
    largest = 0
    words = {"title": "their titles", "criteria": "their criteria", "overlap": "the overlap of their criteria"}
    for g in found:
        judged = sum(c.judged for c in g.cases)
        largest = max(largest, judged)
        by = " and ".join(words[r] for r in RELATIONS if r in g.relations)
        ids = _ids([c.id for c in g.cases])
        more = len(g.cases) - 1
        nested = f"; assignee {g.assignee} is not a top-level agent" if "/" in g.assignee else ""
        lines.append(f'- {g.assignee}: "{g.cases[0].title}" and {more} more ({ids}), joined by {by}: {judged} of {thresholds.shape_cases} with your verdict{nested}')
        if judged < len(g.cases):
            lines.append(f"  {len(g.cases) - judged} more without your verdict, not counted")
    return _section("d5", (), lines, unreadable, (("shape_groups", len(found)), ("largest_group_judged", largest)), show=False)


def d6_health(flags: Sequence[HealthFlag], notes: Sequence[str]) -> Section:
    """D6 Idle or stranded agents: each flagged agent with the analyzer's reason and the runs it holds, then the notes the signal adds (an agent that is kept, and why)."""
    lines = [f"- {f.addr} ({f.flag}): {f.reason}" + (f"; holds {f.held} unspent runs" if f.held is not None else "") for f in flags] + list(notes)
    return _section("d6", (), lines, (), (("flagged", len(flags)),), show=False)


# ------------------------------------------------------------------------------------------------------------------------ D9 to D14


def _source_line(c: Sourced) -> str:
    if c.kind == "default":
        return texts.DEFAULT_LINE
    if c.kind == "tasks":
        return texts.TASKS_LINE.format(dates=c.tasks_dates) if c.tasks_dates else texts.TASKS_LINE_NO_DATES
    asked = texts.AMENDED_LINE.format(asked=c.asked) if c.kind == "amendment" else texts.ASKED_LINE.format(asked=c.asked) if c.asked else ""
    return texts.FROM_LINE.format(quote=" ".join(c.quote.split()), asked=asked, added=listed_added_words(c.added))


def d9_criteria(rows: Sequence[Sourced], unknown: int, unreadable: Unreadable) -> Section:
    """D9 Criteria and your words: every current criterion with a recorded source, its source, the words root added and the judged cases it was exercised in;
    the criteria with no recorded source are counted in one line."""
    lines = [
        f'- {c.service} {c.id} "{quoted(c.text)}": {_source_line(c)}; exercised in {c.exercised} judged cases, {c.accepted} accepted' for c in rows
    ]
    return _section("d9", (), lines, unreadable, (("sourced", len(rows)), ("unknown_source", unknown)), show=False, tail=[texts.NO_SOURCE.format(k=unknown)] if unknown else [])


def d10_proposals(facts: ProposalFacts, since: datetime | None, oldest: datetime | None) -> Section:
    """D10 Your team's own proposals: the refusals of the evidence gate to a ``revise_playbook`` call as ``{actor} on {service}: {kind} ({op})`` (no text of the
    team), then the refusals of every tool since ``since`` counted as ``observe`` counts them, and a line when the event log does not reach back to ``since``."""
    rows = [f"- {r.actor} on {r.service}: {r.kind} ({r.op})" for r in facts.rows]
    by_tool = f" ({', '.join(f'{tool} {n}' for tool, n in facts.by_tool)})" if facts.by_tool else ""
    tail = [f"- Refusals since {day(since) if since else 'the organization started'}: {facts.refused}{by_tool}"]
    if oldest is not None and since is not None and since < oldest:
        tail.append(texts.EXPIRED.format(date=day(oldest)))
    return _section("d10", rows, rows, (), (("proposals_refused", len(rows)), ("refusals", facts.refused)), tail=tail, block_lines=3)


def _retire_line(service: str, r: WatchRetire) -> str:
    refined = texts.REFINED.format(refs=_ids(r.refined_refs), replaced=", ".join(f"{old} with {new}" for old, new in r.replaced))
    direct = texts.DIRECT.format(refs=_ids(r.direct_refs), criterion=r.direct_criterion)
    if r.direct_refs and r.refined_refs:
        return f"- {service}: {r.item} retired by the watch in v{r.version}: {direct}; and {refined}"
    if r.refined_refs:
        return f"- {service}: {r.item} retired by the watch in v{r.version} {refined}"
    return f"- {service}: {r.item} retired by the watch in v{r.version}: {direct}."


def d11_playbooks(rows: Sequence[PlaybookFacts], unreadable: Unreadable) -> Section:
    """D11 Playbooks: per service the words against the cap, the live items by state, the retire candidates and the mirror items (a rule the contract already
    carries), then every item the watch retired with the reason in 10.4's words (a refinement was rejected, a direct rejection, or both)."""
    lines: list[str] = []
    for p in rows:
        parts = [f"{p.words} of {p.cap} words", "items: " + ", ".join(f"{n} {state}" for state, n in p.states) if p.states else "no playbook items"]
        if p.candidates:
            parts.append(f"{len(p.candidates)} retire candidate{'s' if len(p.candidates) != 1 else ''} ({_ids(p.candidates)})")
        if p.mirrors:
            k = len(p.mirrors)
            parts.append(f"{k} mirror item{'s' if k != 1 else ''} repeat{'s' if k == 1 else ''} {p.mirror_words} words of the contract ({_ids(p.mirrors)})")
        lines.append(f"- {p.service}: " + "; ".join(parts))
        lines += [_retire_line(p.service, r) for r in p.retires]
    return _section("d11", (), lines, unreadable, (("playbooks", len(rows)), ("watch_retires", sum(len(p.retires) for p in rows))), show=False)


def d12_spend(rows: Sequence[SpendFacts], unreadable: Unreadable) -> Section:
    """D12 Spend: per service the cases since the window start, the runs they used against the runs approved per request, and the cases above that; the approved
    runs are root's hand-downs in 2a (the user's own approvals are not recorded)."""
    lines = [
        f"- {s.service}: {s.cases} cases" + (f", {s.runs} runs used against {s.approved} approved per request; {s.above} cases above it" if s.cases else "") for s in rows
    ]
    return _section("d12", (), [texts.APPROVED_BASIS, *lines], unreadable, (("cases", sum(s.cases for s in rows)), ("cases_above_approval", sum(s.above for s in rows))), show=False)


def _fate(f: Fate) -> str:
    if f.state == "taken":
        return "taken" + (f" ({f.seen})" if f.seen else "")
    return "lapsed: no change" if f.state == "lapsed" else f.state


def d13_last(fates: Sequence[Fate], last_id: str | None) -> Section:
    """D13 The last brief: each item of the last brief as taken (with the effect seen), lapsed (no change) or still open."""
    if last_id is None:
        lines = ["- no earlier brief"]
    elif not fates:
        lines = [f"- {last_id} offered no item"]
    else:
        lines = [f"- {f.id} {f.kind}: {_fate(f)}" for f in fates]
    return _section("d13", (), lines, (), (("items", len(fates)), ("taken", sum(f.state == "taken" for f in fates)), ("lapsed", sum(f.state == "lapsed" for f in fates))), show=False)


def d14_held(held: Sequence[Item]) -> Section:
    """D14 Held back: the candidates beyond the cap of 3 with their weight."""
    return _section("d14", (), [f"- {i.kind} {i.key} (weight {i.weight})" for i in held], (), (("held_back", len(held)),), show=False)


def d7_held(rows: Sequence[Evaluated], unreadable: Unreadable) -> Section:
    """D7 Did past changes hold: one line per change with its outcome (4.4), in the block and in Details."""
    lines = [f"- {e.text}: {e.outcome}" for e in rows]
    counts = (("changes", len(rows)), ("recurred", sum(e.outcome.startswith("recurred") for e in rows)), ("not_evaluated", sum(e.outcome == NOT_EVALUATED for e in rows)))
    return _section("d7", lines, lines, unreadable, counts)


def d8_changes(found: Changes, since: datetime | None) -> Section:
    """D8 Changes to your organization: every structural change after ``since`` with who made it (its label), then the count of the unprompted charter edits, which the
    cap never hides; without a git history the charter and limit lines read ``unknown``."""
    lines = [f"- {c.line}" for c in found.changes] + ([f"- {found.charter_line}"] if found.charter_line else []) or [NONE]
    since_text = day(since) if since is not None else "the organization started"
    count = (("changes", len(found.changes)), ("unprompted_charter_edits", found.unprompted if found.unprompted is not None else "unknown"))
    block = _capped(lines, BLOCK_LINES, BLOCK_MORE) + (f"- Unprompted charter edits: {found.unprompted_text}",)
    details = _capped(lines, DETAIL_LINES, DETAIL_MORE) + (f"- Unprompted charter edits since {since_text}: {found.unprompted_text}",)
    return Section("d8", HEADINGS["d8"], block, details, count)
