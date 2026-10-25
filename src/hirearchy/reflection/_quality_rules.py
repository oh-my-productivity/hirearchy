"""The pure rules of the quality view: deliveries, who signed them off, the verdicts that are on none, the cases without a verdict (0b 3, 4.3, 4.4),
the thresholds of its alarms and the alarms themselves (6).

They read values (cases, messages), never files. ``reflection.api`` re-exports them from its end, because this module needs the types above them."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from fractions import Fraction

from ..kernel import Message, link_ids
from .api import (
    Case, CostAlarm, CostCase, Delivery, QualityThresholds, RepeatAlarm, ServiceRecord, Verdict, case_spend, user_approved, user_cost,
)


def signer_of(owner: str, task_id: str, done_id: str, owner_sent: Sequence[Message], owner_received: Sequence[Message], reports: Collection[str]) -> str:
    """The agent that signed off the delivery of ``task_id`` (pure; 0a 5.5, moved from ``health``): the sender of the latest ``done`` result that
    ``owner`` received from one of its direct ``reports``, answering a task ``owner`` sent after ``task_id`` and received before ``done_id`` (the id
    of the owner's own ``done``); ``owner`` itself when there is none."""
    later = {m.id for m in owner_sent if m.type == "task" and m.id > task_id}
    signed = [
        r for r in owner_received
        if r.type == "result" and r.status == "done" and r.sender in reports and r.reply_to in later and r.id < done_id
    ]
    return max(signed, key=lambda r: r.id).sender if signed else owner


def deliveries_of(case: Case, results: Mapping[str, Message], signers: Mapping[str, str]) -> tuple[Delivery, ...]:
    """The deliveries of ``case`` (pure), oldest first: its tasks whose latest result in ``results`` (task id to result, as the client received
    them) is ``done``. A verdict is on a delivery only when its note is newer than the delivery's result: one given on an earlier (blocked) result,
    or before the result arrived, is on none (``not_on_a_delivery``). ``signers`` maps a task id to its signer; the case's owner signs when
    the map has none."""
    out = []
    for step, t in enumerate(case.tasks):
        done = results.get(t.id)
        if done is None or done.status != "done":
            continue
        verdicts = tuple(v for v in case.verdicts if v.task_id == t.id and v.message.id > done.id)
        later = next((x.id for x in case.tasks if x.id > done.id), "")
        superseded = "" if any(v.tier == "human" for v in verdicts) else later
        out.append(Delivery(case.id, t, done, step, signers.get(t.id, case.owner), verdicts, superseded))
    return tuple(out)


def _given(case: Case, deliveries: Sequence[Delivery]) -> Delivery | None:
    """The delivery of ``case`` the user was given: the one flagged ``given``, else the latest (OQ-2)."""
    mine = [d for d in deliveries if d.case == case.id]
    return next((d for d in mine if d.given), mine[-1] if mine else None)


def unjudged_cases(cases: Sequence[Case], deliveries: Sequence[Delivery], *, relayed_only: bool = False) -> tuple[str, ...]:
    """The ids of the cases in state ``done`` whose given delivery has no human-tier verdict on it, counted or voided (pure; D18, OQ-2): defined by
    the ``Delivery`` alone, never by ``rated``, which counts any tier. With ``relayed_only``, only those whose given delivery has a relayed- or
    agent-tier verdict (the assistant or an agent judged it, the user did not)."""
    out = []
    for c in cases:
        d = _given(c, deliveries) if c.state == "done" else None
        if d is None or any(v.tier == "human" for v in d.verdicts):
            continue
        if not relayed_only or d.verdicts:
            out.append(c.id)
    return tuple(out)


def not_on_a_delivery(case: Case, deliveries: Sequence[Delivery]) -> tuple[Message, ...]:
    """The notes of the human-tier verdicts of ``case`` that are on no delivery (pure; D4): given on a blocked or failed result, on a task with no
    result, or before the ``done`` result arrived. Counted apart, never read as the verdict on a later delivery. Oldest first."""
    on_one = {v.message.id for d in deliveries for v in d.verdicts}
    return tuple(v.message for v in case.verdicts if v.tier == "human" and v.message.id not in on_one)


_THRESHOLD_KEYS = "min_judged, repeat_window, repeat_failures, cost_ratio"
_WHOLE = "a whole number of at least 1"


def _count(value: object) -> int | None:
    """``value`` as a whole number of at least 1: an int (not a bool), an integral float or a string of digits; else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number: int | None = value
    elif isinstance(value, float):
        number = int(value) if value.is_integer() else None  # inf and nan are not integral
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        number = int(value)
    else:
        number = None
    return number if number is not None and number >= 1 else None


def _ratio(value: object) -> tuple[Fraction, str] | None:
    """``value`` as a ratio above 0 with the text it was written as: an int or finite float (not a bool) or a decimal string; else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+(\.[0-9]+)?", value):
        text = value
    else:
        return None
    ratio = Fraction(text)
    return (ratio, text) if ratio > 0 else None


def quality_thresholds(config: Mapping[str, object]) -> tuple[QualityThresholds, tuple[str, ...]]:
    """The thresholds of the alarms from the optional ``quality:`` mapping of ORG.md's frontmatter ``config``, and the notes for what was ignored
    (pure; design 6, 14). A value that fails keeps its default and adds a note; an unknown key and a ``quality`` that is no mapping are ignored with a
    note. ``repeat_failures`` is checked against the ``repeat_window`` in force; its default is clamped to a window below 2."""
    if "quality" not in config:
        return QualityThresholds(), ()
    raw = config["quality"]
    if not isinstance(raw, Mapping):
        return QualityThresholds(), ("quality in ORG.md is not a mapping: the defaults are used.",)
    notes: list[str] = []
    applied = False

    def counted(key: str, default: int, what: str, ceiling: int | None = None) -> int:
        nonlocal applied
        if key not in raw:
            return default
        value = _count(raw[key])
        if value is None or (ceiling is not None and value > ceiling):
            notes.append(f"quality.{key} in ORG.md is not {what}: the default {default} is used.")
            return default
        applied = True
        return value

    min_judged = counted("min_judged", 3, _WHOLE)
    window = counted("repeat_window", 3, _WHOLE)
    default_failures = min(2, window)
    if "repeat_failures" not in raw and window < 2:
        notes.append(f"quality.repeat_failures: the default 2 is above repeat_window {window}, so {default_failures} is used.")
    failures = counted("repeat_failures", default_failures, f"a whole number from 1 to {window}", ceiling=window)
    ratio, text = Fraction("1.25"), "1.25"
    if "cost_ratio" in raw:
        read = _ratio(raw["cost_ratio"])
        if read is None:
            notes.append(f"quality.cost_ratio in ORG.md is not a number above 0: the default {text} is used.")
        else:
            (ratio, text), applied = read, True
    notes += [f"quality.{key} in ORG.md is not a threshold: ignored (the thresholds are {_THRESHOLD_KEYS})." for key in raw if str(key) not in _THRESHOLD_KEYS.split(", ")]
    return QualityThresholds(min_judged, window, failures, ratio, text, "ORG.md" if applied else "defaults"), tuple(notes)


# ------------------------------------------------------------------------------------------------------------------------ the alarms (6)


def judged_cases(record: ServiceRecord) -> tuple[Case, ...]:
    """The cases of ``record`` with at least one judged delivery (a counted human-tier verdict), ordered by the id of their latest counted verdict
    (pure): the order in which the user last judged them."""
    latest: dict[str, str] = {}
    for d in record.deliveries:
        if d.judged:
            latest[d.case] = max(latest.get(d.case, ""), *(v.message.id for v in d.counted))
    by_id = {c.id: c for c in record.cases}
    return tuple(by_id[case] for case in sorted(latest, key=latest.__getitem__) if case in by_id)


def _number(subject: str) -> tuple[int, int, str]:
    """The order of the ids in the view: ``R`` ids first, then ``C`` ids, each by its number."""
    return (0 if subject.startswith("R") else 1, int(subject[1:]) if subject[1:].isdigit() else 0, subject)


def _rejections(record: ServiceRecord, cases: Sequence[Case]) -> list[tuple[str, Verdict, str, tuple[str, ...], str]]:
    """The counted human-tier rejections on the deliveries of ``cases``: ``(case, verdict, assertion, what the assertion is about, its link)``, oldest
    first. A rejection that is on no delivery, or whose verdict the file's change voided, is not among them."""
    wanted = {c.id for c in cases}
    by_verdict = {a.verdict.message.id: a for a in record.assertions}
    found = [
        (d.case, v, a.id, a.about, a.link) for d in record.deliveries if d.case in wanted for v in d.counted
        if v.verdict == "reject" and (a := by_verdict.get(v.message.id)) is not None
    ]
    return sorted(found, key=lambda item: item[1].message.id)


def _reading(v: Verdict) -> tuple[str, ...]:
    """The ids the assistant's reading of a rejection names that no human link confirms, in the order the rejection recorded them (pure): a relayed link's
    ids (the effective link), or, when a human link is the effective one, the rejection's own ``criterion`` ids that the link does not name. ``none`` is no id."""
    if v.links_tier == "human":
        confirmed = set(v.links)
        return tuple(x for x in link_ids(v.message) if x != "none" and x not in confirmed)
    return tuple(x for x in v.links if x != "none")


def _not_counted(record: ServiceRecord, cases: Sequence[Case]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """The readings the repeat alarm ignores in ``cases`` (DR2-3): for a rejection, its ``R<k>`` and the ids that its relayed reading names and no human link
    confirms, in the order the rejection recorded them. A human link that names another criterion does not hide the reading."""
    found: dict[str, tuple[str, ...]] = {}
    for _, v, assertion, _, _ in _rejections(record, cases):
        reading = _reading(v)
        if reading:
            found.setdefault(assertion, reading)
    return tuple(sorted(found.items(), key=lambda item: _number(item[0])))


def repeat_alarm(record: ServiceRecord, t: QualityThresholds) -> RepeatAlarm:
    """The repeat alarm of ``record`` (pure; 6): the last ``t.repeat_window`` judged cases, and the subjects that failed in at least ``t.repeat_failures``
    of them. The subjects of a case are, for each counted human-tier rejection, its assertion ``R<k>``, the ``C<k>`` of its human link notes, what the
    assertion is about (a "same as R<j>" resolved) and the ``R<j>`` its human link names; a criterion that only a relayed reading names is no subject
    and is listed in ``not_counted``, under every state, unless a human link confirms it."""
    judged = judged_cases(record)
    if not record.service:
        return RepeatAlarm("does not apply", len(judged))  # root's one-off tasks name no criterion ids
    if len(judged) < t.min_judged:
        return RepeatAlarm("n/a", len(judged), not_counted=_not_counted(record, judged))
    window = judged[-t.repeat_window:]
    in_case: dict[str, set[str]] = {c.id: set() for c in window}
    for case, v, assertion, about, _ in _rejections(record, window):
        in_case[case] |= {assertion, *v.confirmed, *about}
        if v.links_tier == "human":
            in_case[case] |= {x for x in v.links if x[:1] == "R" and x[1:].isdigit()}
    count = Counter(subject for subjects in in_case.values() for subject in subjects)
    subjects = tuple(sorted(count.items(), key=lambda item: _number(item[0])))
    fired = tuple(subject for subject, n in subjects if n >= t.repeat_failures)
    where = tuple((subject, tuple(case for case, found in in_case.items() if subject in found)) for subject in fired)
    return RepeatAlarm("fires" if fired else "no", len(judged), tuple(in_case), subjects, fired, where, _not_counted(record, window))


def over_cost(case: Case, approved: int, ratio: Fraction) -> bool:
    """Is the user's cost of ``case`` (``user_cost``) strictly above ``ratio`` times ``approved``, the runs the user approved for it (pure; exact, no
    division: 1.25 x 20 is 25, and 25 runs are not above it)?"""
    return Fraction(user_cost(case)) > ratio * approved


def cost_alarm(record: ServiceRecord, t: QualityThresholds) -> CostAlarm:
    """The cost alarm of ``record`` (pure; 6, D-E5-6): it compares the user's runs of each case with the runs the user approved (the contract's budget,
    raised by the user's hand-downs; a one-off case's own budget), the two figures ``case_total`` compares, and shows the assistant's relayed runs and
    the total apart. A case whose runs are not counted, or whose approved runs are 0 or below, is skipped by name (under every state); with fewer judged
    cases than ``t.min_judged``, or when nothing is left to compare, the state is ``n/a``, never ``no``."""
    judged = len(judged_cases(record))
    compared: list[tuple[Case, int]] = []
    skipped: list[tuple[str, str]] = []
    for case in record.cases:
        approved = user_approved(case, record.budget if record.service else case.tasks[0].budget)
        if case.runs_unknown:
            skipped.append((case.id, "runs not counted"))
        elif approved <= 0:
            skipped.append((case.id, "budget 0"))
        else:
            compared.append((case, approved))
    if judged < t.min_judged or not compared:
        return CostAlarm("n/a", judged, len(compared), (), tuple(skipped))
    fired = tuple(CostCase(c.id, user_cost(c), a, c.relayed_runs, case_spend(c)) for c, a in compared if over_cost(c, a, t.cost_ratio))
    return CostAlarm("fires" if fired else "no", judged, len(compared), fired, tuple(skipped))
