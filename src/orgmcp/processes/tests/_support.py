"""Helpers shared by the tests of ``processes`` (no test lives here)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import cast

import pytest
from _pytest.mark import ParameterSet

from orgmcp.processes.testing import ProcessWorld


def env() -> dict[str, str]:
    """The environment of the test process, for a child that needs ``PATH``."""
    return dict(os.environ)


def eventually(condition: Callable[[], bool], timeout: float = 10.0) -> bool:
    """Poll ``condition`` until it holds; real processes need a moment to be reaped by their new parent."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


# While a step is red: the implementations (by factory name) whose contract tests are expected to fail, per Protocol.
RED: dict[str, frozenset[str]] = {
    "ProcessHandle": frozenset({"real_world"}),
    "ProcessSpawner": frozenset({"real_world"}),
    "ProcessInspector": frozenset({"real_world"}),
    "ProcessSignaller": frozenset({"real_world"}),
    "OrphanJudge": frozenset({"real_world", "fake_world"}),
}


def implementations(protocol: type, factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The parameters of a contract fixture: one per implementation, strict xfail for those that are still red."""
    red = RED.get(protocol.__name__, frozenset())
    return [
        pytest.param(f, id=f.__name__, marks=[pytest.mark.xfail(strict=True, reason="red: A-processes")] if f.__name__ in red else [])
        for f in factories
    ]


def make_world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    """The fixture body of every contract suite: build the world of one implementation, close it afterwards."""
    world = cast(Callable[[Path], ProcessWorld], request.param)(tmp_path)
    try:
        yield world
    finally:
        world.close()
