"""Membership of the team: ``hire`` and ``retire``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..hierarchy import Hiring, Retirement
from ..kernel import ROOT, OrgError, Provider, norm
from ..services import AmendmentBasis, ServiceCatalog, ServiceEvidence
from ._ports import StructureGuard, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


HIRE_OPENER = "Create a direct report (only if your charter allows hiring)."
# Root's variant (design 11.4, L18): root's hire is refused over MCP (``RootStructureGuard``), so the description points to the extension.
ROOT_HIRE_OPENER = (
    "Root's hire is refused: a new agent changes the organization, so the user approves it in a plan: propose_org(blueprint=<an extension with "
    'add_agents>, extend="current"), show its PLAN FOR YOU block, then apply_org after their approval. (Your agents use hire for their own '
    "reports; at the terminal the user can run hirearchy hire.)"
)
# The parameter lines of ``hire`` (the same for root and for an agent): the description is shown byte for byte (golden).
HIRE_PARAMS = """\
        name: lowercase-dashed (becomes the address <you>/<name>). role: a short job title.
        charter: markdown with purpose, responsibilities, decision rights, what to escalate, quality bar.
        model: kiro model id (optional; unset = the organization's default model, claude-sonnet-5.5). tools: kiro built-in tools to grant, only ones you have yourself
        (e.g. "read", "write", "shell"). can_hire: whether the report may build its own team; only root (the user) or an approved plan can grant it.
        max_children: the most direct reports it may have (for an agent hiring: at most its own); a report without can_hire gets 0.
        workspace: directory the report works in (must be inside yours).
        inputs: absolute folders the report may only READ (never change); a manager can give only folders inside its
        own inputs or workspace. A report with `read` and no workspace/inputs reads nothing outside the org.
        A new report has no budget until you delegate a task to it.
        """


class HiringTools(ToolGroup):
    def __init__(
        self, hiring: Provider[Hiring], retirement: Provider[Retirement], catalog: Provider[ServiceCatalog], evidence: Provider[ServiceEvidence],
        guard: StructureGuard,
    ) -> None:
        self._hiring = hiring
        self._retirement = retirement
        self._catalog = catalog
        self._evidence = evidence
        self._guard = guard

    def _kept(self, me: str, name: str) -> str:
        """Root retiring a top-level agent: what its services keep, and what is still open in them (design 5.10). Read before the retirement moves
        the services; advisory, so a record that cannot be read says nothing."""
        addr = norm(name)
        if me != ROOT or addr == ROOT or "/" in addr:
            return ""
        try:
            services = self._catalog().service_names(addr)
            open_ = [(service, self._open(self._evidence().amendment_basis(addr, service))) for service in services]
        except (OrgError, OSError):
            return ""
        if not services:
            return ""
        still = "".join(f" Still open in `{service}`: {parts}." for service, parts in open_ if parts)
        return (
            f"\nKept with {addr}: {', '.join(services)}. Defining one of them again for {addr} continues its contract, playbook and cases "
            f"(when a request of it has a result).{still} Tell the user."
        )

    @staticmethod
    def _open(basis: AmendmentBasis) -> str:
        """The rejections without an answer and the deliveries without a verdict, as one list (``""`` when none)."""
        parts = [f"rejection {r.assertion} (message {r.note}) has no answer" for r in basis.rejections if not r.answered]
        if basis.unrated:
            parts.append(f"{len(basis.unrated)} delivered request(s) without a verdict: {', '.join(basis.unrated)}")
        return "; ".join(parts)

    def register(self, mcp: FastMCP, me: str) -> None:
        def hire(
            name: str,
            role: str,
            charter: str,
            model: str | None = None,
            tools: list[str] | None = None,
            can_hire: bool = False,
            max_children: int = 5,
            workspace: str | None = None,
            inputs: list[str] | None = None,
        ) -> str:
            self._guard.hire(me)
            addr = self._hiring().hire(me, name, role, charter, model=model, tools=tools or [], can_hire=can_hire,
                                       max_children=max_children, workspace=workspace, inputs=inputs)
            return f"hired {addr}"

        mcp.tool(description=f"{ROOT_HIRE_OPENER if me == ROOT else HIRE_OPENER}\n\n{HIRE_PARAMS}")(hire)

        @mcp.tool()
        def retire(name: str, reason: str) -> str:
            """Remove a direct report and its team (name: its short name or full address, e.g. "eng" or "ceo/eng").

        Their open tasks are reported to you as failed, and the team's unspent budget is returned to you.
        """
            self._guard.retire(me, name)
            kept = self._kept(me, name)  # before the retirement: it moves the services away
            r = self._retirement().retire_team(me, name, reason)
            refund = f"; {r.refunded} unspent run(s) of budget returned to {r.refunded_to}" if r.refunded else ""
            return f"retired {r.addr}{refund}{kept}"
