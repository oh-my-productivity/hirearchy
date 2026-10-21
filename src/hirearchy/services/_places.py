"""Where the files of a service are, in the layout of an organization on disk."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgLayout
from ._protocols import ServicePlaces

RETIRED_DIR = ".retired"  # where the services that were taken out of use are kept, below ``<owner>/services``


class OrgServicePlaces(ServicePlaces):
    """``<owner>/services/<name>/{SERVICE.md,PLAYBOOK.md,history/}`` below the directory of the owner."""

    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def services_dir(self, owner: str) -> Path:
        return self._layout.agent_dir(owner) / "services"

    def service_dir(self, owner: str, name: str) -> Path:
        return self.services_dir(owner) / name

    def contract_file(self, owner: str, name: str) -> Path:
        return self.service_dir(owner, name) / "SERVICE.md"

    def playbook_file(self, owner: str, name: str) -> Path:
        return self.service_dir(owner, name) / "PLAYBOOK.md"

    def history_file(self, owner: str, name: str, kind: str, version: int) -> Path:
        return self.service_dir(owner, name) / "history" / f"{kind}.v{version}.md"

    def retired_dir(self, owner: str, name: str, stamp: str) -> Path:
        return self.service_dir(owner, RETIRED_DIR) / f"{name}-{stamp}"

    def rel(self, path: Path) -> str:
        return self._layout.rel(path)
