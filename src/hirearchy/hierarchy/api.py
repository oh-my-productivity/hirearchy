"""The public surface of ``hierarchy``: the rules that change who is in the agent tree.

``Hiring`` lets an agent create a direct report (a name that is valid, a charter that grants no more than the hirer has, the limits of the
hirer and of the organization), ``Retirement`` removes a direct report and its team (the tasks the team owes are failed upward, the unspent
runs go back to the parent as a note that wakes nobody, the directory is archived). Both write through ``agents`` and ``delivery``; neither
touches a file of its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple, Protocol, runtime_checkable

__all__ = [
    "Hiring",
    "Retired",
    "Retirement",
]


class Retired(NamedTuple):
    addr: str
    refunded: int  # runs of unspent team budget returned to ``refunded_to``
    refunded_to: str | None


@runtime_checkable
class Hiring(Protocol):
    def hire(
        self,
        actor: str,
        name: str,
        role: str,
        charter: str,
        *,
        model: str | None = None,
        tools: Sequence[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
        inputs: Sequence[str] | None = None,
        approved: bool = False,
        kind: str | None = None,
        approved_in: str | None = None,
    ) -> str:
        """Create the direct report ``name`` of ``actor`` and return its address; emit ``agent.hire`` (with the model the new agent will run
        with). ``name`` is lowercase letters, digits and dashes (at most 32), not a reserved word, not already taken; ``tools`` are sorted and
        deduplicated; ``model=None`` leaves the charter unpinned, so the organization's default applies. A hirer other than root needs
        ``can_hire`` in its charter, fewer reports than its ``max_children``, and may grant no tool, workspace or input that it does not have
        itself; an unconfined ``read`` is never handed down by a confined hirer (the report then gets ``inputs: []``). ``max_children`` is a whole
        number >= 0 for every hirer (root included), else ``OrgError``; a report without ``can_hire`` gets 0, whoever hires it. A hirer other than
        root may not grant ``can_hire`` (and may not give a report a ``max_children`` above its own) unless ``approved``: the decision of a person,
        passed only by the blueprint applier (an approved plan), the CLI and the ``Org`` facade, never by an MCP tool; ``approved`` skips that grant
        check and no other. ``kind`` (``manager``, ``author``, ``verifier``) and ``approved_in`` (``plan {plan_id}``, ``change {plan_id}``: the approval
        the hire rests on) are written into the charter's frontmatter after ``created`` when given, and left out when not; only the plan
        appliers pass them. ``OrgError`` for every refusal."""
        ...


@runtime_checkable
class Retirement(Protocol):
    def retire(self, actor: str, name: str, reason: str) -> str:
        """``retire_team(actor, name, reason).addr``."""
        ...

    def retire_team(self, actor: str, name: str, reason: str, approved_in: str = "") -> Retired:
        """Retire the direct report ``name`` (short name or full address; root may retire any agent by full address) and its team.

        Every task the team owes to somebody outside it is answered with a ``failed`` result, the directory is archived, the team's unspent runs
        (``max(0, sum of the budgets of its agents)``; nothing when the parent is root, who has no limit) go to the parent as a runtime note that
        carries them and wakes nobody, and ``agent.retire`` is emitted. The archive comes before the refund: a crash in between loses the refund
        rather than counting it twice. ``OrgError`` for root, an agent that does not exist and an agent that is not a direct report.

        The retired tree gets a ``RETIRED.md`` (``retired``, ``by``, ``reason`` and, when given, ``approved_in``: ``change {plan_id}``, passed only
        by the extension applier). A record that cannot be written after the move leaves the tree retired; ``agent.retire`` then carries
        ``record="failed"``."""
        ...
