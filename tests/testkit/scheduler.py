"""Tests that need the scheduler to look a certain way to the views (running, unverified ...) without starting one say so through its port.

``SchedulerStatus`` is what ``observability`` (``now``, ``check``) asks; a test replaces it with ``FakeSchedulerStatus`` instead of patching a module
function. The organizations a test already holds are given; every organization opened afterwards (by the command line, the dashboard, the MCP server)
gets the fake from the table of providers of the composition root.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from orgmcp.app import wiring
from orgmcp.daemon import SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import FakeSchedulerStatus


def scheduler_is(monkeypatch: pytest.MonkeyPatch, state: SchedulerState, *orgs: Any) -> FakeSchedulerStatus:
    """The scheduler is in ``state`` for ``orgs`` and for every organization opened until the end of the test."""
    status = FakeSchedulerStatus(state)
    monkeypatch.setattr(wiring, "_providers", {**wiring.providers(), SchedulerStatus: lambda _: status})
    for org in orgs:
        monkeypatch.setattr(org, "runtime", dataclasses.replace(org.runtime, scheduler_status=status))
    return status
