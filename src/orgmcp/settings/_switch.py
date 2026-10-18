"""The event switch: ``events`` in ORG.md, re-read only when the file changes."""

from __future__ import annotations

from ._stamp import OrgDocumentStamp
from .api import EventSwitch, OrgDocumentStore


class StampedEventSwitch(EventSwitch):
    def __init__(self, stamps: OrgDocumentStamp, documents: OrgDocumentStore) -> None:
        self._stamps = stamps
        self._documents = documents

    def enabled(self) -> bool:
        raise NotImplementedError("red: A-settings")
