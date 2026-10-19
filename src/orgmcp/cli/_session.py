"""The organization a command line is about: named, announced when it changes, opened."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError
from ..locator import OrgLocator
from ._ports import Arguments, OrgOpener, OrgPorts, OrgSession, Output


class AnnouncingOrgSession(OrgSession):
    """Opens the organization that ``--root`` (else the working directory) names. A command that changes it announces it first (standard error, so the
    standard output stays clean), before anything is read or written, also when the path turns out not to be an organization."""

    def __init__(self, locator: OrgLocator, opener: OrgOpener, out: Output) -> None:
        self._locator = locator
        self._opener = opener
        self._out = out
        self._opened: OrgPorts | None = None

    def named(self, args: Arguments) -> Path:
        raise NotImplementedError

    def open(self, args: Arguments, mutating: bool = False) -> Path:
        raise NotImplementedError

    def present(self, args: Arguments) -> bool:
        raise NotImplementedError

    def create(self, path: str) -> Path:
        raise NotImplementedError

    def ports(self) -> OrgPorts:
        raise NotImplementedError

    def _announce(self, root: Path) -> None:
        raise NotImplementedError
