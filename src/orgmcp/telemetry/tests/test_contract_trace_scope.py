"""Contract of ``TraceScope``: the traces noted while a block runs are the ones it collects; blocks nest."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import TraceTap
from orgmcp.telemetry import TraceScope
from orgmcp.telemetry.testing import IMPLEMENTATIONS

from ._red import params as red_params


@pytest.fixture(params=red_params(IMPLEMENTATIONS[TraceScope], green=("stack_trace_scope",)))
def scope(request: pytest.FixtureRequest, tmp_path: Path) -> TraceScope:
    made = cast(Callable[[Path], TraceScope], request.param)(tmp_path)
    assert isinstance(made, TraceScope) and isinstance(made, TraceTap)  # the scope is the tap the deliveries note into
    return made


def tap(scope: TraceScope) -> TraceTap:
    assert isinstance(scope, TraceTap)
    return scope


def test_the_traces_noted_in_the_block_are_collected_in_order(scope: TraceScope) -> None:
    with scope.collect() as seen:
        tap(scope).note("a")
        tap(scope).note(None)
        tap(scope).note("a")
        tap(scope).note("b")
    assert seen == ["a", None, "a", "b"]


def test_nothing_noted_collects_nothing(scope: TraceScope) -> None:
    with scope.collect() as seen:
        pass
    assert seen == []


def test_a_trace_noted_outside_a_block_is_lost_and_does_not_leak_into_the_next(scope: TraceScope) -> None:
    tap(scope).note("before")
    with scope.collect() as seen:
        tap(scope).note("inside")
    tap(scope).note("after")
    assert seen == ["inside"]


def test_a_nested_block_collects_its_own_and_the_outer_one_resumes(scope: TraceScope) -> None:
    with scope.collect() as outer:
        tap(scope).note("o1")
        with scope.collect() as inner:
            tap(scope).note("i1")
        tap(scope).note("o2")
    assert inner == ["i1"] and outer == ["o1", "o2"]


def test_the_block_is_left_cleanly_when_it_raises(scope: TraceScope) -> None:
    with pytest.raises(ValueError):
        with scope.collect():
            tap(scope).note("lost")
            raise ValueError("boom")
    with scope.collect() as seen:
        tap(scope).note("next")
    assert seen == ["next"]
