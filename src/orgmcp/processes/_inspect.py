"""RED skeleton (step A-processes): the process table read through ``ps`` and the system calls."""

from __future__ import annotations

from orgmcp.kernel import Environment

from .api import ProcessInfo, ProcessInspector


class PsProcessInspector(ProcessInspector):
    def __init__(self, environment: Environment) -> None:
        raise NotImplementedError

    def info(self, pid: int) -> ProcessInfo | None:
        raise NotImplementedError

    def command_line(self, pid: int) -> str | None:
        raise NotImplementedError

    def start_time(self, pid: int) -> str | None:
        raise NotImplementedError

    def is_session_leader(self, pgid: int) -> bool | None:
        raise NotImplementedError

    def is_alive(self, pid: int) -> bool:
        raise NotImplementedError

    def own_ids(self) -> tuple[int, int]:
        raise NotImplementedError
