"""Deletes the day directories of the event log that expired."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta

from ..eventlog import DAY_RE, EVENTS_REL
from ..kernel import Clock, OrgLayout
from ._ports import DropLog
from .api import EventRetention


class FsEventRetention(EventRetention):
    def __init__(self, layout: OrgLayout, clock: Clock, drops: DropLog) -> None:
        self._layout = layout
        self._clock = clock
        self._drops = drops

    def prune(self, keep_days: int, today: datetime | None = None) -> list[str]:
        removed: list[str] = []
        try:
            base = self._layout.root / EVENTS_REL
            cutoff = ((today or self._clock.now()) - timedelta(days=max(1, int(keep_days)))).strftime("%Y-%m-%d")
            for d in sorted(base.iterdir()) if base.is_dir() else []:
                if d.is_dir() and DAY_RE.match(d.name) and d.name < cutoff:
                    shutil.rmtree(d, ignore_errors=True)
                    if not d.exists():
                        removed.append(d.name)
        except Exception as exc:  # noqa: BLE001
            self._drops.drop(f"prune: {type(exc).__name__}: {exc}")
        return removed
