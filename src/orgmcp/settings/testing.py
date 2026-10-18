"""In-memory fakes of the ``settings`` ports, and the registry the contract suites iterate over.

A fake passes the same contract suite as the real adapter (``tests/test_contract_*.py``), so a consumer's unit test may use it
instead of an ORG.md on disk.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import JsonObject, OrgPaths
from ..kernel.testing import fs_atomic_writer
from ._caching import CachingOrgSettings
from ._config import config_default_model, config_message_cap, config_number, parse_config, parse_rules
from ._fs import FsOrgSettings
from ._stamp import FsOrgDocumentStamp, OrgDocumentStamp
from ._switch import StampedEventSwitch
from .api import EventSwitch, OrgDocumentStore, OrgSettings


class MemoryOrgSettings(OrgSettings, OrgDocumentStore, OrgDocumentStamp):
    """ORG.md kept as text in memory. ``text`` is None while the file does not exist; every write is a change of the stamp."""

    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self._version = 0

    def set_text(self, text: str | None, notice: bool = True) -> None:
        """Replace the document; ``notice=False`` is a change the stamp does not show (the time stays, the size may change)."""
        self.text = text
        if notice:
            self._version += 1

    def stamp(self) -> tuple[int, int]:
        if self.text is None:
            raise FileNotFoundError("ORG.md")
        return (self._version, len(self.text.encode("utf-8")))

    def exists(self) -> bool:
        return self.text is not None

    def read_raw(self) -> str:
        if self.text is None:
            raise FileNotFoundError("ORG.md")
        return self.text

    def write_raw(self, text: str) -> None:
        self.set_text(text)

    def config(self) -> JsonObject:
        return parse_config(self.read_raw())

    def rules(self) -> str:
        return parse_rules(self.read_raw())

    def default_model(self) -> str:
        return config_default_model(self.config())

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        return config_number(self.config(), key, kind)

    def message_cap(self) -> int:
        return config_message_cap(self.config())


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
    put_unnoticed: Callable[[str], None]  # written without a change of the modification time (the size may change)
    remove: Callable[[], None]


@dataclass(frozen=True)
class _Disk:
    """ORG.md of a temporary organization directory, with modification times that the tests control."""

    put: Callable[[str], None]  # moves the time forward by a millisecond (so the stamp changes whatever the filesystem's granularity)
    put_unnoticed: Callable[[str], None]  # keeps the modification time
    remove: Callable[[], None]
    text: Callable[[], str | None]


def _disk(root: Path) -> _Disk:
    path, clock = root / "ORG.md", [1_700_000_000_000_000_000]

    def put_unnoticed(text: str) -> None:
        path.write_text(text, encoding="utf-8")
        os.utime(path, ns=(clock[0], clock[0]))

    def put(text: str) -> None:
        clock[0] += 1_000_000
        put_unnoticed(text)

    def remove() -> None:
        path.unlink(missing_ok=True)

    def text() -> str | None:
        return path.read_text(encoding="utf-8") if path.is_file() else None

    return _Disk(put, put_unnoticed, remove, text)


def fs_org_settings(tmp_path: Path) -> SettingsHarness:
    disk = _disk(tmp_path)
    return SettingsHarness(FsOrgSettings(OrgPaths(tmp_path), fs_atomic_writer(tmp_path).writer), disk.put, disk.remove)


def memory_org_settings(tmp_path: Path) -> SettingsHarness:
    fake = MemoryOrgSettings()
    return SettingsHarness(fake, fake.write_raw, lambda: fake.set_text(None))


def caching_org_settings(tmp_path: Path) -> SettingsHarness:
    disk, paths = _disk(tmp_path), OrgPaths(tmp_path)
    inner = FsOrgSettings(paths, fs_atomic_writer(tmp_path).writer)
    return SettingsHarness(CachingOrgSettings(inner, FsOrgDocumentStamp(paths), {}), disk.put, disk.remove, lenient=True)


def fs_org_document_store(tmp_path: Path) -> DocumentHarness:
    disk = _disk(tmp_path)
    return DocumentHarness(FsOrgSettings(OrgPaths(tmp_path), fs_atomic_writer(tmp_path).writer), disk.text, disk.put)


def memory_org_document_store(tmp_path: Path) -> DocumentHarness:
    fake = MemoryOrgSettings()
    return DocumentHarness(fake, lambda: fake.text, fake.set_text)


def fs_event_switch(tmp_path: Path) -> SwitchHarness:
    disk, paths = _disk(tmp_path), OrgPaths(tmp_path)
    documents = FsOrgSettings(paths, fs_atomic_writer(tmp_path).writer)
    return SwitchHarness(StampedEventSwitch(FsOrgDocumentStamp(paths), documents), disk.put, disk.put_unnoticed, disk.remove)


def memory_event_switch(tmp_path: Path) -> SwitchHarness:
    fake = MemoryOrgSettings()
    return SwitchHarness(
        StampedEventSwitch(fake, fake), fake.write_raw, lambda text: fake.set_text(text, notice=False), lambda: fake.set_text(None)
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgSettings: [fs_org_settings, memory_org_settings, caching_org_settings],
    OrgDocumentStore: [fs_org_document_store, memory_org_document_store],
    EventSwitch: [fs_event_switch, memory_event_switch],
}
