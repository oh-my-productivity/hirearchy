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
        raise NotImplementedError

    def service_dir(self, owner: str, name: str) -> Path:
        raise NotImplementedError

    def contract_file(self, owner: str, name: str) -> Path:
        raise NotImplementedError

    def playbook_file(self, owner: str, name: str) -> Path:
        raise NotImplementedError

    def history_file(self, owner: str, name: str, kind: str, version: int) -> Path:
        raise NotImplementedError

    def retired_dir(self, owner: str, name: str, stamp: str) -> Path:
        raise NotImplementedError

    def rel(self, path: Path) -> str:
        raise NotImplementedError
