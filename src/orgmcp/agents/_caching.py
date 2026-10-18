"""RED skeleton (step A-agents)."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Protocol, runtime_checkable

from ..kernel import Clock, JsonObject, OrgLayout
from ._tree import TreeDirectory
from .api import AgentDirectory, CharterReader

CACHE_TRUST = 2.0


@runtime_checkable
class DirectoryProbe(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        raise NotImplementedError


@runtime_checkable
class CharterStamps(Protocol):
    def stamp(self, addr: str) -> tuple[int, int]:
        raise NotImplementedError


class FsDirectoryProbe(DirectoryProbe):
    def __init__(self, paths: OrgLayout) -> None:
        raise NotImplementedError("red: A-agents")

    def mtime(self, addr: str, name: str) -> int:
        raise NotImplementedError("red: A-agents")


class FsCharterStamps(CharterStamps):
    def __init__(self, paths: OrgLayout) -> None:
        raise NotImplementedError("red: A-agents")

    def stamp(self, addr: str) -> tuple[int, int]:
        raise NotImplementedError("red: A-agents")


class CachingAgentDirectory(TreeDirectory):
    def __init__(self, inner: AgentDirectory, probe: DirectoryProbe, clock: Clock) -> None:
        raise NotImplementedError("red: A-agents")

    def exists(self, addr: str) -> bool:
        raise NotImplementedError("red: A-agents")

    def children(self, addr: str) -> list[str]:
        raise NotImplementedError("red: A-agents")


class LenientCharterReader(CharterReader):
    def __init__(self, inner: CharterReader, stamps: CharterStamps, problems: MutableMapping[str, str]) -> None:
        raise NotImplementedError("red: A-agents")

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        raise NotImplementedError("red: A-agents")

    def memory(self, addr: str) -> str:
        raise NotImplementedError("red: A-agents")
