"""The verdict on the process recorded for a run of a dead scheduler."""

from __future__ import annotations

from collections.abc import Mapping

from .api import OrphanJudge, ProcessInspector, ProcessTableError


class PsOrphanJudge(OrphanJudge):
    """Is the process recorded for a run of a dead scheduler still ours, and alive?

    * ``gone``: no such process (or a zombie): nothing to kill.
    * ``foreign``: the pid now belongs to something else (other start time, not a session leader): never touched.
    * ``ours``: alive, started at the recorded time, and the leader of its own session and process group, which is
      exactly how the scheduler starts runs. Only then may the group be killed.
    * ``doubt``: alive but unverifiable (no start time recorded, or ``ps`` failed): not killed, and the agent
      does not get a second run while it lives.
    """

    def __init__(self, inspector: ProcessInspector) -> None:
        self._inspector = inspector

    def judge(self, record: Mapping[str, object]) -> str:
        pgid = record.get("pgid")
        if not isinstance(pgid, int) or isinstance(pgid, bool) or pgid <= 1 or pgid in self._inspector.own_ids():
            return "foreign"
        try:
            info = self._inspector.info(pgid)
        except ProcessTableError:
            return "doubt"
        if info is None or info.state.startswith("Z"):
            return "gone"
        recorded = record.get("lstart")
        if not isinstance(recorded, str) or not recorded:
            return "doubt"
        if recorded != info.started:
            return "foreign"
        leader = self._inspector.is_session_leader(pgid)
        if leader is None:
            return "doubt"
        return "ours" if leader else "foreign"
