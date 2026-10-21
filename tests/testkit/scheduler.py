"""Tests that need the scheduler to look a certain way to the views (running, unverified ...) without starting one say so through its port.

``SchedulerStatus`` is what ``observability`` (``now``, ``check``) asks; a test replaces it with ``FakeSchedulerStatus`` instead of patching a module
function. The organizations a test already holds are given; every organization opened afterwards (by the command line, the dashboard, the MCP server)
gets the fake through the process overrides of the composition root (``wiring.overriding``, the ``process_overrides`` fixture).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from hirearchy.daemon import SchedulerState, SchedulerStatus
from hirearchy.daemon.testing import FakeSchedulerStatus


def scheduler_is(process_overrides: Callable[[Mapping[type, object]], object], state: SchedulerState, *orgs: Any) -> FakeSchedulerStatus:
    """The scheduler is in ``state`` for ``orgs`` and for every organization opened until the end of the test (``process_overrides``: the fixture)."""
    status = FakeSchedulerStatus(state)
    process_overrides({SchedulerStatus: status})
    for org in orgs:
        org.runtime = dataclasses.replace(org.runtime, scheduler_status=status)
    return status
