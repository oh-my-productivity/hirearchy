"""In-memory fakes of the ``settings`` ports, and the registry the contract suites iterate over.

A fake passes the same contract suite as the real adapter (``tests/test_contract_*.py``), so a consumer's unit test may use it
instead of an ORG.md on disk.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import JsonObject, OrgPaths
from ..kernel.testing import fs_atomic_writer
from ._caching import CachingOrgSettings
from ._fs import FsOrgSettings
from ._stamp import FsOrgDocumentStamp, OrgDocumentStamp
from ._switch import StampedEventSwitch
from .api import EventSwitch, OrgDocumentStore, OrgSettings


class MemoryOrgSettings(OrgSettings, OrgDocumentStore, OrgDocumentStamp):
    """ORG.md kept as text in memory. ``text`` is None while the file does not exist; every write is a change of the stamp."""

    def __init__(self, text: str | None = None) -> None:
        self.text = text

    def set_text(self, text: str | None, notice: bool = True) -> None:
        """Replace the document; ``notice=False`` is a change the stamp does not show (same size, same time)."""
        raise NotImplementedError("red: A-settings")

    def stamp(self) -> tuple[int, int]:
        raise NotImplementedError("red: A-settings")

    def exists(self) -> bool:
        raise NotImplementedError("red: A-settings")

    def read_raw(self) -> str:
        raise NotImplementedError("red: A-settings")

    def write_raw(self, text: str) -> None:
        raise NotImplementedError("red: A-settings")

    def config(self) -> JsonObject:
        raise NotImplementedError("red: A-settings")

    def rules(self) -> str:
        raise NotImplementedError("red: A-settings")

    def default_model(self) -> str:
        raise NotImplementedError("red: A-settings")

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        raise NotImplementedError("red: A-settings")

    def message_cap(self) -> int:
        raise NotImplementedError("red: A-settings")


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class SettingsHarness:
    settings: OrgSettings
    put: Callable[[str], None]  # ORG.md becomes this text (a change the stamp shows)
    remove: Callable[[], None]  # ORG.md is deleted
    lenient: bool = False  # a missing or unreadable ORG.md means the defaults instead of an error


@dataclass(frozen=True)
class DocumentHarness:
    store: OrgDocumentStore
    stored: Callable[[], str | None]  # the text that is stored, None when there is no document
    put: Callable[[str], None]  # put a document there, behind the store's back


@dataclass(frozen=True)
class SwitchHarness:
    switch: EventSwitch
    put: Callable[[str], None]  # ORG.md becomes this text (a change the stamp shows)
    put_unnoticed: Callable[[str], None]  # same size, same time: the stamp does not change
    remove: Callable[[], None]


def fs_org_settings(tmp_path: Path) -> SettingsHarness:
    raise NotImplementedError("red: A-settings")


def memory_org_settings(tmp_path: Path) -> SettingsHarness:
    raise NotImplementedError("red: A-settings")


def caching_org_settings(tmp_path: Path) -> SettingsHarness:
    raise NotImplementedError("red: A-settings")


def fs_org_document_store(tmp_path: Path) -> DocumentHarness:
    raise NotImplementedError("red: A-settings")


def memory_org_document_store(tmp_path: Path) -> DocumentHarness:
    raise NotImplementedError("red: A-settings")


def fs_event_switch(tmp_path: Path) -> SwitchHarness:
    raise NotImplementedError("red: A-settings")


def memory_event_switch(tmp_path: Path) -> SwitchHarness:
    raise NotImplementedError("red: A-settings")


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgSettings: [fs_org_settings, memory_org_settings, caching_org_settings],
    OrgDocumentStore: [fs_org_document_store, memory_org_document_store],
    EventSwitch: [fs_event_switch, memory_event_switch],
}
