"""RED skeleton (B-strays): the probe of a workspace."""

from __future__ import annotations

from collections.abc import Mapping

from ..access import AccessScopes
from ..agents import CharterReader
from ._ports import MtimeReader
from .api import StrayProbe


class WorkspaceStrayProbe(StrayProbe):
    def __init__(self, scopes: AccessScopes, charters: CharterReader, mtimes: MtimeReader) -> None:
        self._scopes = scopes
        self._charters = charters
        self._mtimes = mtimes

    def probe(self, addr: str) -> dict[str, float]:
        raise NotImplementedError("red: B-strays")

    def found_since(self, before: Mapping[str, float], after: Mapping[str, float]) -> list[str]:
        raise NotImplementedError("red: B-strays")
