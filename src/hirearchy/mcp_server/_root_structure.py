"""Root's structural calls over MCP, refused in favour of the extension (design 13; owner question Q3).

A new agent, a retire, a first definition of a service, a charter write and a change of ``max_depth`` change the organization, so the user approves
them in a plan: ``propose_org(..., extend="current")`` and ``apply_org``. The terminal (``hirearchy hire`` ...) and the ``Org`` facade are the human's
and the programs' own acts and are not refused here. An agent is never refused: what bounds an agent is the envelope (the rules of ``hierarchy``,
``access`` and ``orgfiles``).
"""

from __future__ import annotations

from ..kernel import ROOT, OrgError, norm
from ._ports import StructureGuard

ROOT_HIRE = (
    "refused: a new agent changes the organization, so the user approves it in a plan: propose_org(blueprint=<an extension with add_agents>, "
    'extend="current"), show its PLAN FOR YOU block, then apply_org(..., approved=True, plan_id=...). (At the terminal the user can run '
    "hirearchy hire.) Nothing was created."
)
ROOT_RETIRE = (
    "refused: retiring {addr} changes the organization, so the user approves it in a plan: propose_org(blueprint=<an extension with retire: "
    '[{{agent: {addr}, reason: ...}}]>, extend="current"), show its PLAN FOR YOU block, then apply it after their approval. Nothing was retired.'
)


class RootStructureGuard(StructureGuard):
    """Refuses root, only root, the calls of ``ROOT_*``; every other actor passes."""

    def hire(self, me: str) -> None:
        if me == ROOT:
            raise OrgError(ROOT_HIRE)

    def retire(self, me: str, name: str) -> None:
        if me == ROOT:
            raise OrgError(ROOT_RETIRE.format(addr=norm(name)))
