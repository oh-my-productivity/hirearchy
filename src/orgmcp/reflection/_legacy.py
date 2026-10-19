"""The old module-level names of the cases, statistics, digest and prompt sections of ``orgmcp.services``, as thin adapters over the classes of the package.

They lived in ``services`` (``services.cases(org, ...)``) until step C-reflection moved them here; ``services`` still answers to the old names through
its ``__getattr__`` (until step E3 removes both), and the callers that were not converted yet say ``reflection.cases(org, ...)``. Every function takes the
``Org`` it is given (a feature may not import the facade, so it is duck-typed) and works over the ports that ``Org`` has *now* (``_assembly``).

``_case_line`` and ``_verdict_chain`` are the private names the dashboard and the tests still use.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ..kernel import Message
from ._assembly import digest_of, history_of, reports_of, sections_of
from ._digest import CLIP_LESSON, CLIP_NOTE, DIGEST_CASES, DIGEST_CHARS, MAX_VERDICTS, case_line, verdict_chain
from .api import Case

Org = Any  # the facade (a feature may not import it): the functions below take whatever has its methods

_case_line = case_line
_verdict_chain = verdict_chain

__all__ = [
    "CLIP_LESSON", "CLIP_NOTE", "DIGEST_CASES", "DIGEST_CHARS", "MAX_VERDICTS", "case_of", "case_total", "cases", "playbook_timeline",
    "prompt_sections", "reflection_digest", "services_text",
]


def playbook_timeline(org: Org, owner: str, service: str) -> list[tuple[int, datetime]]:
    """(version, when it was written) of every playbook version the service has had, oldest first."""
    return history_of(org).playbook_timeline(owner, service)


def cases(org: Org, owner: str, service: str) -> list[Case]:
    """Every case of ``owner``'s service, oldest first: requests plus their rework chains, with results and feedback.

    Runs: all run logs of the owner's subtree from the first request to the final result (or now), ending early where
    the client's next task to the same owner begins - the same window rule as ``progress`` - so overlapping cases do
    not count a run twice. Requests from before the service was (last) created from scratch are not part of it.
    """
    return history_of(org).cases(owner, service)


def reflection_digest(org: Org, owner: str, service: str) -> str | None:
    """Evidence since the current playbook was revised, as a compact markdown block; None when there is none.

    New evidence = a case that finished, or feedback that was given, after the playbook's ``revised`` time (without a
    playbook: any finished case or feedback). The block lists the most recent cases with new evidence (state, runs
    used of the budget given, reworks, the client's verdict and note, lessons - each clipped), then one line of
    statistics per playbook version. About 3000 characters at most.
    """
    return digest_of(org).reflection_digest(owner, service)


def case_of(org: Org, task: Message) -> Case | None:
    """The case a service task belongs to (None for a task that is not a service request, or an unknown one)."""
    return history_of(org).case_of(task)


def case_total(org: Org, task: Message) -> str:
    """The whole case in one sentence: runs used by the chain against the runs handed down, and the contract's budget.

    ``case total: 19 runs used of 27 handed down (contract: 15 per request)``; when the chain was handed down more than
    the contract gives one request, it adds that the case exceeds the budget and that the user must be told. Empty for a
    task that is not a service request.
    """
    return reports_of(org).case_total(task)


def services_text(org: Org, actor: str) -> str:
    """The `services` tool/CLI output: what ``actor`` can request from its direct reports, and what it offers."""
    return reports_of(org).services_text(actor)


def prompt_sections(org: Org, addr: str, batch: Sequence[Message]) -> str:
    """The sections of an owner's run prompt: its services, the playbook of each service it has an open request for,
    and (when the batch holds a new request, or the client's rejection of a delivery) what to reflect on first. Empty
    for an agent that owns no service.

    Each section starts and ends with a newline, to be appended after the notice and before "# New messages".
    """
    return sections_of(org).prompt_sections(addr, batch)
