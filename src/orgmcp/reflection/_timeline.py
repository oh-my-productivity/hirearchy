"""When each version of a playbook was written, from the history the store keeps."""

from __future__ import annotations

from datetime import datetime

from ..kernel import parse_time
from ._ports import PlaybookHistory, PlaybookTimelines


class StorePlaybookTimelines(PlaybookTimelines):
    """The versions the store has kept (and the current one) that say when they were revised, oldest first."""

    def __init__(self, store: PlaybookHistory) -> None:
        self._store = store

    def timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        raise NotImplementedError  # red: C-reflection
