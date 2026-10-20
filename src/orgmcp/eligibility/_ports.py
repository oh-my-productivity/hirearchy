"""The ports ``eligibility`` defines for what it consumes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

import json
import os
from typing import Protocol, runtime_checkable

from ..kernel import OrgLayout


@runtime_checkable
class DirectoryProbe(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>``; -1 when it is not there."""
        ...


@runtime_checkable
class LedgerShape(Protocol):
    def damaged(self, name: str) -> bool:
        """The ledger file holds JSON that is not an object (``LedgerStore.read`` shows such a ledger as empty, hiding the damage)."""
        ...


class FsDirectoryProbe(DirectoryProbe):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def mtime(self, addr: str, name: str) -> int:
        path = self._paths.agent_dir(addr)
        try:
            return os.stat(path / name if name else path).st_mtime_ns
        except OSError:
            return -1


class FsLedgerShape(LedgerShape):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def damaged(self, name: str) -> bool:
        try:
            return not isinstance(json.loads(self._paths.ledger_file(name).read_text(encoding="utf-8")), dict)
        except (OSError, ValueError):
            return False
