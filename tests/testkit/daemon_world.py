"""The scheduler process as the tests call it: ``scheduler_state(org)``, ``describe_scheduler(org)``, ``start_scheduler(org, ...)``, ``stop_scheduler(org)``,
``waiting_on_user(org, ...)``, over the ports of the runtime of the organization (``scheduler_status``, ``scheduler_control``, ``waiting_on_user``)."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any

from hirearchy.app import wiring
from hirearchy.attention import Waiting
from hirearchy.daemon import SchedulerState


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


def scheduler_command(root: Path, max_runs: int | None = None, until_done: bool = False) -> list[str]:
    """``<this venv's hirearchy> --root <org> run [--max-runs N] [--until-done]``."""
    return wiring.open_runtime(Path(root)).scheduler_command.argv(max_runs, until_done)  # type: ignore[no-any-return]


def env_server() -> Any:
    """``hirearchy mcp``'s server for the identity of the environment (``ORG_ROOT``, ``ORG_AGENT`` ...): the binding resolved, the server of its tools built."""
    from hirearchy.app import wire_mcp_server

    binding, me = wire_mcp_server.binding_resolver().resolve()
    return wire_mcp_server.server_factory(binding).build(me)
