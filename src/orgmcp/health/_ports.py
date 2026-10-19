"""The ports ``health`` defines for what it consumes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, Message, OrgLayout


@runtime_checkable
class RunCount(Protocol):
    def count(self, addr: str) -> int:
        """The runs the agent has used: its visible run logs (what its budget was charged)."""
        ...


@runtime_checkable
class ConfigSource(Protocol):
    def config(self) -> JsonObject:
        """The settings of ORG.md (its frontmatter over the defaults)."""
        ...


@runtime_checkable
class CharterStamp(Protocol):
    def modified(self, addr: str) -> datetime:
        """When the agent's ``AGENT.md`` was last written (aware, UTC); ``FileNotFoundError`` when there is none."""
        ...


@runtime_checkable
class HireDates(Protocol):
    def hired(self, addr: str) -> datetime:
        """When the agent was hired: the ``created`` of its charter, else the time its charter file was written."""
        ...


@runtime_checkable
class ClientRework(Protocol):
    def driven(self, tasks: Sequence[Message], results: Mapping[str, Message]) -> set[str]:
        """Ids of the received reworks (tasks with ``revises``) among ``tasks`` that stem from the client of a service case, given the
        latest result of each task the agent has answered."""
        ...


class FsCharterStamp(CharterStamp):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def modified(self, addr: str) -> datetime:
        return datetime.fromtimestamp(os.stat(self._paths.agent_dir(addr) / "AGENT.md").st_mtime, timezone.utc)


class CallableConfig(ConfigSource):
    """The settings as a function gives them (the dashboard's ``Org`` reads a damaged ORG.md as the defaults, and caches the parse)."""

    def __init__(self, config: Callable[[], JsonObject]) -> None:
        self._config = config

    def config(self) -> JsonObject:
        return self._config()


class CallableRunCount(RunCount):
    """The runs used as a function counts them (the dashboard's ``Org`` caches the count per change of the ``runs`` directory)."""

    def __init__(self, count: Callable[[str], int]) -> None:
        self._count = count

    def count(self, addr: str) -> int:
        return self._count(addr)
