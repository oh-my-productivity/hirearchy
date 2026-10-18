"""RED skeleton (step A-processes): signals to processes and process groups."""

from __future__ import annotations

from orgmcp.kernel import Clock

from .api import ProcessInspector, ProcessSignaller


class OsProcessSignaller(ProcessSignaller):
    def __init__(self, inspector: ProcessInspector, clock: Clock) -> None:
        raise NotImplementedError

    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        raise NotImplementedError

    def terminate(self, pid: int) -> None:
        raise NotImplementedError
