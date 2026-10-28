"""The narrow views of the files that the signals read (design 7.7, 14.3): a signal's inputs decide what can nominate an item, so they are typed views
that hold human-tier verdicts, runtime facts (runs, times, the agents' tree) and root's own tasks, and no lessons, memory, notes or reports of a team."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OneOffCase:
    """One of root's one-off tasks as a case (a task root sent without a service, with its reworks): ``id`` is the head task's id, ``assignee`` who got it,
    ``title`` and ``goal`` (the first line of the head's ``## Goal``) are root's own words, ``criteria`` the lines of the head's ``## Acceptance criteria``
    section. ``judged`` is true when the user gave a human-tier verdict on it; ``runs`` are the runs it used (``runs_unknown`` says why they cannot be read)."""

    id: str
    assignee: str
    title: str
    criteria: tuple[str, ...] = ()
    goal: str = ""
    created: datetime | None = None
    judged: bool = False
    runs: int = 0
    runs_unknown: str = ""
