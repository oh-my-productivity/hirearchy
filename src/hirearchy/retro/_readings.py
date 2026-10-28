"""The readings of the retro brief (design 4.3): what was said (D1), what got past a check (D2), the rejections with no criterion yet (D3), the alarms and the causes
to settle (D4), the work asked for again and again (D5) and the idle or stranded agents (D6). Each is a pure function over narrow views that returns a ``Section``.

A section is capped: its block (the short form the user reads) shows at most ``BLOCK_LINES`` lines and then ``- and {j} more (Details)``; Details show at most
``DETAIL_LINES`` and then say how to list them all. A service whose record cannot be read has a line of its own, after the cap, in every section it would be read for."""

from __future__ import annotations

from collections.abc import Sequence

from ..reflection import CostAlarm, RepeatAlarm
from ._shapes import RELATIONS, ShapeGroup
from ._texts import (
    BLOCK_LINES, BLOCK_MORE, BLOCK_WORDS, DETAIL_LINES, DETAIL_MORE, HEADINGS, NONE, UNREADABLE, cause_question, day, quoted,
)
from ._views import HealthFlag, Passed, Said, ServiceAlarms
from .api import RetroThresholds, Section

Unreadable = Sequence[tuple[str, str]]  # (service, why) of the services whose record could not be read

ONE_OFF = "one-off"


def _capped(lines: Sequence[str], limit: int, more: str) -> tuple[str, ...]:
    kept = list(lines[:limit])
    return tuple(kept + ([more.format(j=len(lines) - limit)] if len(lines) > limit else []))


def _section(
    key: str, block: Sequence[str], details: Sequence[str], unreadable: Unreadable, counts: tuple[tuple[str, int | str], ...], *, show: bool = True,
) -> Section:
    """The section ``key``: its block lines (``()`` when the block does not show it) and its details, capped, then the lines of the services that could not be read."""
    broken = [UNREADABLE.format(service=service or ONE_OFF, error=error) for service, error in unreadable]
    shown = (_capped(block, BLOCK_LINES, BLOCK_MORE) + tuple(broken) or (NONE,)) if show else ()
    lines = _capped(details, DETAIL_LINES, DETAIL_MORE) + tuple(broken)
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
