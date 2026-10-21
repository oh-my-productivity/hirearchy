"""Where the files of a service are, as the texts name them (relative to the organization)."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgLayout
from ._ports import ServicePaths


class OrgServicePaths(ServicePaths):
    """``<owner>/services/<name>/...`` below the directory of the owner, relative to the root of the organization."""

    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def rel(self, path: Path | None) -> str:
        return self._layout.rel(path) if path is not None else ""

    def service_dir(self, owner: str, name: str) -> str:
        return self._layout.rel(self._layout.agent_dir(owner) / "services" / name)

    def playbook_file(self, owner: str, name: str) -> str:
        return self._layout.rel(self._layout.agent_dir(owner) / "services" / name / "PLAYBOOK.md")
