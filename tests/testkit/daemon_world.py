"""The scheduler process as the tests call it: ``scheduler_state(org)``, ``describe_scheduler(org)``, ``start_scheduler(org, ...)``, ``stop_scheduler(org)``,
``waiting_on_user(org, ...)``, over the ports of the runtime of the organization (``scheduler_status``, ``scheduler_control``, ``waiting_on_user``)."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from orgmcp.attention import Waiting
from orgmcp.daemon import SchedulerState


def scheduler_state(org: Any) -> SchedulerState:
    return org.runtime.scheduler_status.state()  # type: ignore[no-any-return]


def describe_scheduler(org: Any) -> str:
    return org.runtime.scheduler_status.describe()  # type: ignore[no-any-return]


def start_scheduler(org: Any, max_runs: int | None = None, until_done: bool = False) -> int:
    return org.runtime.scheduler_control.start(max_runs, until_done)  # type: ignore[no-any-return]


def stop_scheduler(org: Any, wait: float = 15.0) -> str:
    return org.runtime.scheduler_control.stop(wait)  # type: ignore[no-any-return]


def waiting_on_user(org: Any, *, running: Collection[str] | None = None, blocked: Collection[str] = (), can_start: bool = True) -> Waiting | None:
    return org.runtime.waiting_on_user.analyze(running=running, blocked=blocked, can_start=can_start)  # type: ignore[no-any-return]
