"""The cause of an escape, typed by rule, and its attribution (0b section 5): pure functions over the case, the delivery and what the contract says.

``reflection.api`` re-exports them from its end, because this module needs the types above them."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from ..kernel import Message, artifact_paths, link_ids, verdict_tier
from ..services import BASE_DELIVERED_HEADING
from .api import LASTING_WORDS, Assertion, Case, Cause, Delivery, Verdict

_NO_RULE = "the user said it is no lasting rule"


def _named(verdict: Verdict | None, assertion: Assertion) -> tuple[str, ...]:
    """The criteria the human client named for the escape, in order, each once: those of the verdict's human-tier link notes, then those of the
    assertion's resolved link ("the same as R<j>") when it is confirmed."""
    ids = list(verdict.confirmed) if verdict is not None else []
    if assertion.link == "confirmed":
        ids += [x for x in assertion.about if x.startswith("C")]
    return tuple(dict.fromkeys(ids))


def _link_note(verdict: Verdict | None, first: str) -> str:
    """The latest human-tier link note that names ``first``, else the latest human-tier link note, else the verdict's own note: the evidence a rule cites."""
    if verdict is None:
        return ""
    human = [m for m in verdict.link_notes if verdict_tier(m) == "human"]
    naming = [m for m in human if first in link_ids(m)]
    chosen = naming or human
    return chosen[-1].id if chosen else verdict.message.id


def _judged_result(case: Case, results: Mapping[str, Message], before: str) -> str:
    """The result id ``J`` of the latest delivery of the case whose first human-tier verdict was recorded before ``before`` (a task id); the head
    task's id when there is none. A verdict is on a delivery only when it follows its ``done`` result."""
    found = case.tasks[0].id
    for t in case.tasks:
        r = results.get(t.id)
        if r is None or r.status != "done":
            continue
        first = min((v.message.id for v in case.verdicts if v.task_id == t.id and v.tier == "human" and v.message.id > r.id), default=None)
        if first is not None and first < before:
            found = max(found, r.id)
    return found


def _carry_over(delivery: Delivery, case: Case, results: Mapping[str, Message]) -> tuple[str, str] | None:
    """Rule 2: the relayed rework and the artifact it shares with the rejected delivery, or None. The rejected task is not relayed and its body does
    not tell the lead to restore the version the client judged; a relayed rework sent after that version (and before the task) has a ``done`` result
    that lists an artifact the rejected delivery lists too."""
    task = delivery.task
    if task.source == "relayed" or BASE_DELIVERED_HEADING in task.body:
        return None
    judged = _judged_result(case, results, task.id)
    shared = set(artifact_paths(delivery.result.body))
    for r in case.tasks:
        result = results.get(r.id)
        if r.source != "relayed" or not judged < r.id < task.id or result is None or result.status != "done":
            continue
        path = next((p for p in artifact_paths(result.body) if p in shared), None)
        if path is not None:
            return r.id, path
    return None


def _before_verdict(delivery: Delivery, case: Case, results: Mapping[str, Message], verdict: Verdict | None) -> str:
    """The latest relayed rework of the case whose ``done`` result lies between the rejected delivery's result and the decisive verdict ("" for none)."""
    if verdict is None:
        return ""
    found = [
        r.id for r in case.tasks
        if r.source == "relayed" and r.id != delivery.task.id and (x := results.get(r.id)) is not None and x.status == "done"
        and delivery.result.id < x.id < verdict.message.id
    ]
    return found[-1] if found else ""


def _lasting_word(words: str, lasting: Sequence[str]) -> str | None:
    """The first word of ``lasting`` that ``words`` contains (case-insensitively, on word boundaries), else None."""
    return next((w for w in lasting if re.search(rf"\b{re.escape(w)}\b", words, re.IGNORECASE)), None)


def cause_of(
    delivery: Delivery, case: Case, assertion: Assertion, carried: frozenset[str] | None, answer_removes: tuple[str, ...],
    results: Mapping[str, Message], lasting: Sequence[str] = LASTING_WORDS, *, version: int | None = None, answering: int = 0,
) -> Cause:
    """The cause of the escape ``delivery`` (pure; 0b 5.1): the first rule that matches gives the type and the rule.

    ``assertion`` is the decisive verdict's ``R<k>``; ``carried`` the criteria of the contract version the rejected task carried (``None`` when that
    version is not stored); ``answer_removes`` the ids the version that answered the rejection removes; ``results`` the latest result of each task
    of the case; ``lasting`` rule 5's words. The caller, which read the stored versions, gives ``version`` (the carried contract version; default
    the task's recorded one) and ``answering`` (the answering version) for the view's texts. 1 the rejected delivery answers a relayed task; 2 a
    relayed rework delivered a file the judged delivery had and the lead was not told to restore it; 3 a named criterion the task carried and
    the client kept; 4 one it did not carry, or that the answer removes; 5 a lasting word in the client's words; 6 nothing."""
    v = delivery.decisive
    n = delivery.task.contract or 0 if version is None else version
    named = _named(v, assertion)
    matched: list[tuple[str, str, tuple[str, ...]]] = []  # (rule, type, detail), in rule order
    if delivery.task.source == "relayed":
        matched.append(("relayed task", "relayed-error", (delivery.task.id,)))
    if (carry := _carry_over(delivery, case, results)) is not None:
        matched.append(("carry-over", "relayed-carry-over", carry))
    unreadable = bool(named) and carried is None
    if named and carried is not None:
        kept = [c for c in named if c in carried and c not in answer_removes]
        gap = [c for c in named if c not in carried or c in answer_removes]
        if kept:
            matched.append(("link", "reviewer-miss", (_link_note(v, kept[0]), *kept)))
        if gap:
            matched.append(("answer", "contract-gap", (_link_note(v, gap[0]), *gap)))
    if not unreadable and v is not None and (word := _lasting_word(v.note, lasting)) is not None:
        matched.append(("words", "contract-gap", (word,)))
    before = _before_verdict(delivery, case, results, v)
    if not matched:
        if unreadable:
            return Cause("untyped", "unreadable", (f"contract v{n} is not stored",), before_verdict=before, version=n, answering=answering)
        return Cause("untyped", "none", (_NO_RULE,) if assertion.link == "none" else (), before_verdict=before, version=n, answering=answering)
    rule, kind, detail = matched[0]
    removes = tuple(c for c in named if c in answer_removes) if rule == "answer" else ()
    also = tuple(dict.fromkeys(k for _, k, _ in matched[1:] if k != kind))
    return Cause(
        kind, rule, detail, tuple(r for r, _, _ in matched), also, before_verdict=before, version=n, answering=answering, removes=removes,
    )


def attribution(cause: Cause) -> str:
    """Whose possible miss an escape is (pure; I5): ``counted`` for ``reviewer-miss`` and ``untyped`` (the verifier's possible misses), ``not its`` for
    ``contract-gap``, ``relayed-error`` and ``relayed-carry-over``. The view's verifier line and health's ``low_quality`` both call it."""
    return "counted" if cause.type in ("reviewer-miss", "untyped") else "not its"


def failure_class(cause: Cause) -> str | None:
    """The failure class a rule can derive for an escape (pure; 0b 4.4): ``off_spec`` for ``reviewer-miss``; no other class is derived here (``None``)."""
    return "off_spec" if cause.type == "reviewer-miss" else None
