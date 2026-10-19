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
        raise NotImplementedError("red: B-eligibility")

    def mtime(self, addr: str, name: str) -> int:
        raise NotImplementedError("red: B-eligibility")


class FsLedgerShape(LedgerShape):
    def __init__(self, paths: OrgLayout) -> None:
        raise NotImplementedError("red: B-eligibility")

    def damaged(self, name: str) -> bool:
        raise NotImplementedError("red: B-eligibility")
