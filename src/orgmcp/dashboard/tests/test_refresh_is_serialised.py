"""One refresh at a time. The five queries share one cache that is not thread-safe (``DashCache``), and the app is what serialises them: a request for a
refresh while one is running does not start a second worker, it asks for exactly one more when the first has been shown."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable

import pytest

from orgmcp.dashboard._app import DashApp
from orgmcp.dashboard.testing import fixed_queries
from orgmcp.dashdata import Snapshot

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-dashboard")


class Gate:
    """A ``snapshot`` that waits at the door until it is opened, and counts how many are inside at once."""

    def __init__(self, real: Callable[[], Snapshot]) -> None:
        self.real = real
        self.open = threading.Event()
        self.inside = 0
        self.most = 0
        self.calls = 0
        self.lock = threading.Lock()

    def __call__(self) -> Snapshot:
        with self.lock:
            self.calls += 1
            self.inside += 1
            self.most = max(self.most, self.inside)
        try:
            self.open.wait(10)
            time.sleep(0.01)
            return self.real()
        finally:
            with self.lock:
                self.inside -= 1


def test_requests_during_a_refresh_wait_for_it_and_are_one_more_refresh() -> None:
    queries = fixed_queries()
    gate = Gate(queries.snapshot)
    queries.snapshot = gate  # type: ignore[method-assign]

    async def go() -> None:
        app = DashApp(queries, interval=3600)
        async with app.run_test(size=(100, 30)) as pilot:
            for _ in range(100):  # the first refresh is inside the door
                if gate.calls:
                    break
                await asyncio.sleep(0.01)
            assert gate.calls == 1
            await pilot.press("r", "r", "r")
            assert gate.calls == 1 and gate.most == 1
            gate.open.set()
            await app.settle(pilot)
            assert gate.calls == 2 and gate.most == 1  # (three requests while busy are one more refresh, not three)
            assert app.refreshes == 2 and app.last_error is None

    asyncio.run(go())


def test_a_timer_tick_is_a_request_like_any_other() -> None:
    queries = fixed_queries()
    gate = Gate(queries.snapshot)
    queries.snapshot = gate  # type: ignore[method-assign]

    async def go() -> None:
        app = DashApp(queries, interval=0.2)
        async with app.run_test(size=(100, 30)) as pilot:
            await asyncio.sleep(0.7)  # several ticks while the first refresh is held at the door
            assert gate.calls == 1 and gate.most == 1
            gate.open.set()
            await app.settle(pilot)
            assert gate.most == 1

    asyncio.run(go())
