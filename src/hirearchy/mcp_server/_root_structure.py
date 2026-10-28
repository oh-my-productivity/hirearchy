"""Root's structural calls over MCP, refused in favour of the extension (design 13; owner question Q3).

A new agent, a retire, a first definition of a service, a charter write and a change of ``max_depth`` change the organization, so the user approves
them in a plan: ``propose_org(..., extend="current")`` and ``apply_org``. The terminal (``hirearchy hire`` ...) and the ``Org`` facade are the human's
and the programs' own acts and are not refused here. An agent is never refused: what bounds an agent is the envelope (the rules of ``hierarchy``,
``access`` and ``orgfiles``).
"""

from __future__ import annotations

from ..kernel import ROOT, OrgError, OrgLayout, Provider, norm, split_frontmatter
from ..orgfiles import OrgFileWriter
from ..services import ServiceCatalog
from ..settings import OrgSettings, config_number
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
ROOT_NEW_SERVICE = (
    "refused: {owner} offers no service `{name}`, and a new service changes the organization, so the user approves it in a plan: "
    'propose_org(blueprint=<an extension with add_services>, extend="current"). A change to an existing service\'s criteria stays '
    "define_service with the user's words. Nothing was written."
)
ROOT_CHARTER = (
    "refused: a charter changes through a plan the user approves: one line with add_charter_lines, hiring limits with limits, in "
    'propose_org(blueprint=<an extension>, extend="current"). Nothing was written.'
)
ROOT_DEPTH = (
    "refused: max_depth bounds the organization's structure, so the user approves a change of it in a plan: limits: [{org: max_depth, value: N}] in "
    'propose_org(blueprint=<an extension>, extend="current"). Nothing was written.'
)


class RootStructureGuard(StructureGuard):
    """Refuses root, only root, the calls of ``ROOT_*``; every other actor passes."""

    def __init__(
        self, catalog: Provider[ServiceCatalog], writer: Provider[OrgFileWriter], settings: Provider[OrgSettings], layout: Provider[OrgLayout],
    ) -> None:
        self._catalog = catalog
        self._writer = writer
        self._settings = settings
        self._layout = layout

    def hire(self, me: str) -> None:
        if me == ROOT:
            raise OrgError(ROOT_HIRE)

    def retire(self, me: str, name: str) -> None:
        if me == ROOT:
            raise OrgError(ROOT_RETIRE.format(addr=norm(name)))

    def new_service(self, me: str, owner: str, name: str) -> None:
        if me == ROOT and name not in self._catalog().service_names(norm(owner)):
            raise OrgError(ROOT_NEW_SERVICE.format(owner=norm(owner), name=name))

    def write(self, me: str, path: str, content: str, append: bool) -> None:
        if me != ROOT:
            return
        target = self._writer().resolve_write(me, path)  # the path as the writer would have it (its own refusals come first)
        if target.name == "AGENT.md":
            raise OrgError(ROOT_CHARTER)
        if target.name == "ORG.md" and target.parent.resolve() == self._layout().root.resolve() and not append and self._depth_changes(content):
            raise OrgError(ROOT_DEPTH)

    def _depth_changes(self, content: str) -> bool:
        """Whether the ORG.md text ``content`` sets another ``max_depth`` than the one in force. An append never changes the settings block (it is at the
        start of the file); ORG.md that cannot be parsed, now or in the new text, is the floor check's to deal with (root repairs it)."""
        try:
            now = self._settings().number("max_depth", int)
            new = config_number(split_frontmatter(content)[0], "max_depth", int)
        except Exception:  # noqa: BLE001 - YAML that does not parse: nothing reads a depth from it, and root must still be able to repair the file
            return False
        return new != now
