"""The event switch: ``events`` in ORG.md, re-read only when the file changes."""

from __future__ import annotations

from ..kernel import split_frontmatter
from ._stamp import OrgDocumentStamp
from .api import EventSwitch, OrgDocumentStore


def _falsy(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("false", "no", "off", "0")
    return value is False or (isinstance(value, int) and value == 0)


class StampedEventSwitch(EventSwitch):
    def __init__(self, stamps: OrgDocumentStamp, documents: OrgDocumentStore) -> None:
        self._stamps = stamps
        self._documents = documents
        self._stamp: tuple[int, int] | None = None  # (mtime_ns, size) of ORG.md the answer was read from
        self._enabled = True

    def enabled(self) -> bool:
        try:
            stamp = self._stamps.stamp()
        except OSError:
            return False
        if stamp != self._stamp:
            try:
                meta, _ = split_frontmatter(self._documents.read_raw())
                self._enabled = not _falsy(meta.get("events", True))
            except Exception:  # noqa: BLE001 - unreadable settings mean the default (on)
                self._enabled = True
            self._stamp = stamp
        return self._enabled
