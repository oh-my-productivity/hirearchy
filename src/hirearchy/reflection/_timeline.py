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
        out: list[tuple[int, datetime]] = []
        for version, meta in self._store.playbook_history(owner, service):
            revised = meta.get("revised")
            when = parse_time(revised) if revised else None
            if when is not None and version > 0:
                out.append((version, when))
        return sorted(out)
