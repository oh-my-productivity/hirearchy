"""The ports ``health`` defines for what it consumes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import NamedTuple, Protocol, runtime_checkable

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


class SignedDelivery(NamedTuple):
    """One delivery of a service case, as health counts it."""

    signer: str  # the agent that signed it off: the last report to be done before the owner, else the owner
    judged: bool  # the human client gave a verdict on it after the owner's ``done``
    escape: bool  # judged, and one of those verdicts is a reject (a later accept does not undo it)
    counted: bool  # for an escape: its cause counts against the verifier that signed it off (``reviewer-miss``, ``untyped``); true otherwise
    cause: str  # the escape's cause (``contract-gap``, ``relayed-error``, ...); "" unless an escape


class Signed(NamedTuple):
    items: tuple[SignedDelivery, ...]
    unknown: str  # the services whose contract could not be read, ``{service}: {error}`` joined by ``; `` ("" when none): their escapes are ``untyped``


@runtime_checkable
class SignedDeliveries(Protocol):
    def deliveries(self, owner: str) -> Signed:
        """Every delivery of the cases of ``owner``'s services, and of the one-off tasks assigned to it, with who signed it off, whether the client
        judged it and, for an escape, its cause."""
        ...


class EscapeCounts(NamedTuple):
    escapes: int  # judged deliveries the client rejected after ``done``
    judged: int  # deliveries the human client gave a verdict on
    rechecks: int  # re-checks the agent had to make after a FAIL
    rework_runs: int  # runs of the authors that those FAILs cost
    not_its: tuple[tuple[str, int], ...] = ()  # judged escapes that are not the verifier's, by cause (``contract-gap``, ``relayed-error``, ...)
    unknown: str = ""  # the services whose escapes could not be typed (``{service}: {error}`` joined by ``; ``); "" when none


@runtime_checkable
class EscapeCounter(Protocol):
    def counts(self, addr: str) -> EscapeCounts:
        """The escapes of ``addr``: the human client's verdicts on the service deliveries it owned or signed off, and the re-checks and author
        rework runs a FAIL of its own cost (all four numbers are 0 for an agent that took no part in a service delivery)."""
        ...


class FsCharterStamp(CharterStamp):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def modified(self, addr: str) -> datetime:
        return datetime.fromtimestamp(os.stat(self._paths.agent_dir(addr) / "AGENT.md").st_mtime, timezone.utc)
