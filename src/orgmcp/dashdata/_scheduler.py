"""``EventSchedulerViews``: is a scheduler running, since when, how it was started, how long ago it last beat."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from ..daemon import ExitMarker, SchedulerState, SchedulerStatus
from ..eventlog import EventFile, EventReader
from ..kernel import JsonObject, clip_line, parse_time
from ._data import SchedulerView
from ._ports import DashClock, EventFileStamps, SchedulerViews
from .api import DashboardState


class FsEventFileStamps(EventFileStamps):
    def stamp(self, file: EventFile) -> tuple[int, int] | None:
        try:
            st = file.path.stat()
        except OSError:
            return None
        return (st.st_size, st.st_mtime_ns)


class EventSchedulerViews(SchedulerViews):
    """The state of the scheduler is asked at most every ``ttl`` seconds; what its event file says (when it started, in which mode, its last
    heartbeat, why it exited) is read from the head and the tail of that file, and again only when the file changed."""

    def __init__(self, status: SchedulerStatus, reader: EventReader, stamps: EventFileStamps, marker: ExitMarker, state: DashboardState,
                 clock: DashClock, ttl: float = 3.0) -> None:
        self._status = status
        self._reader = reader
        self._stamps = stamps
        self._marker = marker
        self._state = state
        self._clock = clock
        self.ttl = ttl
        self._sched: tuple[float, SchedulerState] | None = None
        self._facts: dict[Path, tuple[tuple[int, int], dict[str, object]]] = {}

    def view(self, now: datetime) -> SchedulerView:
        t = self._clock.monotonic()
        if self._sched is None or t - self._sched[0] > self.ttl:
            try:
                st = self._status.state()
            except Exception:  # noqa: BLE001
                st = SchedulerState("stopped")
            self._sched = (t, st)
        st = self._sched[1]
        view = SchedulerView(st.state, st.pid, st.since, detail=st.detail)
        try:
            files = self._files()
        except Exception:  # noqa: BLE001
            files = []
        if st.state == "running" and st.pid is not None:
            mine = [f for f in files if f[1] == st.pid]
            if mine:
                facts = self._file_facts(mine[0][2])
                view.mode = cast("str | None", facts.get("mode"))
                start = cast("datetime | None", facts.get("start"))
                if start:
                    view.uptime_s = (now - start).total_seconds()
                beat = self._feed_heartbeat(st.pid) or cast("datetime | None", facts.get("beat"))
                if beat:
                    view.heartbeat_age_s = max(0.0, (now - beat).total_seconds())
        else:
            for _, _, file in files[:3]:
                facts = self._file_facts(file)
                if facts.get("exit"):
                    view.last_exit = cast("str", facts["exit"])
                    break
            if not view.last_exit:
                view.last_exit = self._marker.read() or None
        return view

    def _files(self) -> list[tuple[int, int, EventFile]]:
        """(start_epoch_ms, pid, file) of every scheduler event file, newest process first."""
        out = [(f.start_ms, f.pid, f) for f in self._reader.files() if f.proc == "scheduler"]
        return sorted(out, key=lambda x: (x[0], str(x[2].path)), reverse=True)

    def _feed_heartbeat(self, pid: int) -> datetime | None:
        feed = self._state.feed
        if feed is None:
            return None
        for ev in reversed(feed.events):
            if ev.get("kind") == "scheduler.heartbeat" and ev.get("pid") == pid:
                return parse_time(ev.get("ts"))
        return None

    def _file_facts(self, file: EventFile) -> dict[str, object]:
        """start / mode / last heartbeat / exit reason of one scheduler event file, re-read only when it changed."""
        key = self._stamps.stamp(file)
        if key is None:
            return {}
        hit = self._facts.get(file.path)
        if hit is not None and hit[0] == key:
            return hit[1]
        tail: list[JsonObject] = self._reader.tail(file)
        head = self._reader.head(file)
        start = head if head and head.get("kind") == "scheduler.start" else next(
            (e for e in tail if e.get("kind") == "scheduler.start"), None)
        beats = [e for e in tail if e.get("kind") == "scheduler.heartbeat"]
        exits = [e for e in tail if e.get("kind") == "scheduler.exit"]
        facts: dict[str, object] = {
            "mode": start.get("mode") if start else None,
            "start": parse_time(start.get("ts")) if start else None,
            "beat": parse_time(beats[-1].get("ts")) if beats else None,
            "exit": clip_line(exits[-1].get("reason"), 160) if exits else None,
        }
        self._facts[file.path] = (key, facts)
        return facts
