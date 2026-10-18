"""``ThreadLocalTraceScope``: the collection is per thread (ARCHITECTURE.md 10.1, risk 12: preserved exactly, not "fixed")."""

from __future__ import annotations

import threading

import pytest

from orgmcp.kernel import TraceTap
from orgmcp.telemetry import TraceScope
from orgmcp.telemetry._trace_scope import ThreadLocalTraceScope


def test_it_is_both_the_scope_and_the_tap() -> None:
    scope = ThreadLocalTraceScope()
    assert isinstance(scope, TraceScope) and isinstance(scope, TraceTap)


def test_a_delivery_in_another_thread_is_not_collected_by_the_block_of_this_one() -> None:
    """The ``progress`` tool runs its work in a worker thread: whatever that thread delivers is not seen by the wrapper that runs in the
    loop thread. This is how it always was; the test documents it."""
    scope = ThreadLocalTraceScope()
    with scope.collect() as seen:
        scope.note("here")
        worker = threading.Thread(target=lambda: scope.note("there"))
        worker.start()
        worker.join()
    assert seen == ["here"]


def test_each_thread_collects_its_own() -> None:
    scope = ThreadLocalTraceScope()
    results: dict[str, list[str | None]] = {}
    barrier = threading.Barrier(2)

    def work(name: str) -> None:
        with scope.collect() as seen:
            barrier.wait()
            for i in range(50):
                scope.note(f"{name}{i}")
            barrier.wait()
        results[name] = seen

    threads = [threading.Thread(target=work, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results["a"] == [f"a{i}" for i in range(50)] and results["b"] == [f"b{i}" for i in range(50)]


def test_two_scopes_do_not_share_their_collections() -> None:
    first, second = ThreadLocalTraceScope(), ThreadLocalTraceScope()
    with first.collect() as seen:
        second.note("not mine")
        first.note("mine")
    assert seen == ["mine"]
