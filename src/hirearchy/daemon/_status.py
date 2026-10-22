"""What the pidfile and the process table say about the scheduler of an organization."""

from __future__ import annotations

from datetime import datetime, timezone

from ..attention import WaitingOnUser
from ..kernel import ROOT, OrgLayout
from ..mail import TaskQuery
from ..processes import ProcessInspector, ProcessTableError
from ._describe import describe_state
from ._files import pidfile_of
from ._ports import Children, SchedulerRecognizer
from ._refusals import SINCE_FORMAT
from .api import REFUSED_START, ExitMarker, SchedulerState, SchedulerStatus


class PidFileSchedulerStatus(SchedulerStatus):
    def __init__(
        self,
        layout: OrgLayout,
        inspector: ProcessInspector,
        recognizer: SchedulerRecognizer,
        children: Children,
        marker: ExitMarker,
        tasks: TaskQuery,
        waiting: WaitingOnUser,
    ) -> None:
        self._layout = layout
        self._inspector = inspector
        self._recognizer = recognizer
        self._children = children
        self._marker = marker
        self._tasks = tasks
        self._waiting = waiting

    def state(self) -> SchedulerState:
        self._children.reap()
        pidfile = pidfile_of(self._layout)
        try:
            pid = int(pidfile.read_text().strip())
            since = datetime.fromtimestamp(pidfile.stat().st_mtime, timezone.utc).strftime(SINCE_FORMAT)
        except (OSError, ValueError):
            return SchedulerState("stopped")
        if pid <= 1:
            return SchedulerState("stopped")
        try:
            info = self._inspector.info(pid)
        except ProcessTableError:
            return SchedulerState("unverified", pid, since, "the process table could not be read")
        if info is None or info.state.startswith("Z"):
            return SchedulerState("stopped")  # stale pidfile: the process is gone
        command = self._inspector.command_line(pid)
        if command and self._recognizer.recognises(command, self._layout.root):
            return SchedulerState("running", pid, since)
        return SchedulerState("unverified", pid, since, f"its command line is {command!r}" if command else "its command line is unknown")

    def describe(self) -> str:
        return describe_state(self.state(), self.exit_reason, self._waiting)

    def exit_reason(self) -> str:
        """Why the scheduler last exited by itself, while that is still true (root has no open task), or a refused start (always); else ''."""
        reason = self._marker.read()
        return reason if reason and (reason.startswith(REFUSED_START) or not self._tasks.outstanding(ROOT)) else ""
