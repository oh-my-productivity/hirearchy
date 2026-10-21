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
        return Path(args.root or self._locator.find_root()).expanduser().resolve()

    def open(self, args: Arguments, mutating: bool = False) -> Path:
        root = self.named(args)
        if mutating:
            self._announce(root)
        self._opened = self._opener.open(root)
        return self._opened.root

    def present(self, args: Arguments) -> bool:
        try:
            self._opened = self._opener.open(self.named(args))
        except OrgError:
            return False
        return True

    def create(self, path: str) -> Path:
        root = Path(path).expanduser().resolve()
        self._announce(root)
        self._opened = self._opener.prepare(root)
        return root

    def ports(self) -> OrgPorts:
        if self._opened is None:
            raise OrgError("no organization is open")
        return self._opened

    def _announce(self, root: Path) -> None:
        self._out.warn(f"org: {root}")
