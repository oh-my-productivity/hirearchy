"""Helpers shared by the tests of ``processes`` (no test lives here)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest

from hirearchy.processes.testing import ProcessWorld


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


def make_world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    """The fixture body of every contract suite: build the world of one implementation, close it afterwards."""
    world = cast(Callable[[Path], ProcessWorld], request.param)(tmp_path)
    try:
        yield world
    finally:
        world.close()
