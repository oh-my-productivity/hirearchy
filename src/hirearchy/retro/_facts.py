"""The facts that come from the event log (design 4.3 D10, 4.5): the team's refused proposals, the refusals counted by the rule ``observe`` uses, and the ``write`` calls.

Pure functions over the events as ``eventlog`` reads them (JSON objects). The team's own text is never kept: a refusal is a kind and an ``op``."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime

from ..kernel import parse_time
from ..reflection import gate_refusal_kind
from ._views import ProposalFacts, Refusal, WriteFact


def _args(event: Mapping[str, object]) -> Mapping[str, object]:
    args = event.get("args")
    return args if isinstance(args, Mapping) else {}


def proposals_of(events: Iterable[Mapping[str, object]]) -> ProposalFacts:
    """The refused ``revise_playbook`` calls whose refusal is one of the evidence gate's (by its fixed phrase), and the refusals of every tool: a ``tool.call``
    event with ``ok`` false, the rule ``observe`` counts by."""
    rows: list[Refusal] = []
    by_tool: Counter[str] = Counter()
    for event in events:
        if event.get("kind") != "tool.call" or event.get("ok") is not False:
            continue
        tool = str(event.get("tool"))
        by_tool[tool] += 1
        kind = gate_refusal_kind(str(event.get("error") or "")) if tool == "revise_playbook" else None
        if kind is not None:
            args = _args(event)
            rows.append(Refusal(str(event.get("actor") or ""), str(args.get("service") or ""), kind, str(args.get("op") or "")))
    return ProposalFacts(tuple(rows), sum(by_tool.values()), tuple(sorted(by_tool.items())))


def writes_of(events: Iterable[Mapping[str, object]]) -> tuple[WriteFact, ...]:
    """The successful ``write`` tool calls with their path, time and actor (the label ``by {parent}`` of 4.5)."""
    found: list[WriteFact] = []
    for event in events:
        if event.get("kind") != "tool.call" or event.get("tool") != "write" or event.get("ok") is not True:
            continue
        when: datetime | None = parse_time(event.get("ts"))
        path = _args(event).get("path")
        if when is not None and isinstance(path, str):
            found.append(WriteFact(when, str(event.get("actor") or ""), path))
    return tuple(found)
