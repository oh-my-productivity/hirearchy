"""The facts one brief is derived from (``Facts``) and the pure readers of the event log (design 4.3 D10, 4.5): the team's refused proposals, the refusals counted by the rule
``observe`` uses, and the ``write`` calls. The team's own text is never kept: a refusal is a kind and an ``op``."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from ..kernel import parse_time
from ..reflection import gate_refusal_kind
from ._changes import ChangeFacts
from ._views import (
    EffectFacts, HealthFlag, OneOffCase, Passed, PlaybookFacts, ProposalFacts, Refusal, Said, ServiceAlarms, ServiceFailures, Sourced, SpendFacts, Tracked, WriteFact,
)


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


@dataclass(frozen=True)
class Facts:
    """Everything one brief is derived from, read once (``BriefSources.read``): the narrow views of the readings and of the signals, and the facts the changes and the effects
    are read from. Nothing here is a text a team wrote."""

    verdicts: int = 0  # the deliveries judged by a human verdict in the window of the brief, and the cases they belong to (the heading)
    cases: int = 0
    said: tuple[Said, ...] = ()
    accepts: int = 0
    passed: tuple[Passed, ...] = ()
    alarms: tuple[ServiceAlarms, ...] = ()
    one_offs: tuple[OneOffCase, ...] = ()
    offers: Mapping[str, frozenset[tuple[str, ...]]] = field(default_factory=dict)  # a top-level agent -> the criteria keys of the services it offers
    estimates: Mapping[str, int] = field(default_factory=dict)  # a top-level agent -> the estimate of its team's runs
    flags: tuple[HealthFlag, ...] = ()
    last_checks: Mapping[str, str] = field(default_factory=dict)  # an agent -> the service it is the last check of
    owners: Mapping[str, tuple[str, ...]] = field(default_factory=dict)  # an agent -> the services it owns
    sourced: tuple[Sourced, ...] = ()
    unknown_sources: int = 0
    proposals: ProposalFacts = field(default_factory=ProposalFacts)
    oldest_event: datetime | None = None
    playbooks: tuple[PlaybookFacts, ...] = ()
    spend: tuple[SpendFacts, ...] = ()
    changes: ChangeFacts = field(default_factory=ChangeFacts)
    tracked: tuple[Tracked, ...] = ()
    failures: tuple[ServiceFailures, ...] = ()
    effects: EffectFacts = field(default_factory=EffectFacts)
    unreadable: tuple[tuple[str, str], ...] = ()  # (service, why) of the records that could not be read
