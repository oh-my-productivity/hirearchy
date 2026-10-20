"""The organizations the screens of the dashboard are taken of: the demo organization of ``dash_fixtures`` (every state of an agent, requests, a service,
events) and an empty one. Used by the colocated tests of ``orgmcp.dashboard`` through ``src/orgmcp/dashboard/tests/_worlds.py``, which may not import
the ``Org`` facade itself (the layers contract); this module may (E1-e moves it, with ``dash_fixtures``, into ``tests/testkit``).

The scheduler is told to look running (pid 7000) or stopped through the ports of the composition root, so no process is looked for.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from orgmcp.core import Org
from orgmcp.daemon import SchedulerState

from .dash_fixtures import DEMO_NOW, demo_org
from .scheduler import scheduler_is

__all__ = ["DEMO_NOW", "demo", "empty", "scratch"]


@contextmanager
def scratch() -> Iterator[Path]:
    """A directory with a short path (``/tmp/dg...``): the run logs of the demo name the directory of the organization, and the screen of a run log
    must show it on one line whatever the temporary directory of the machine is (``/var/folders/...`` is too long for the pane)."""
    base = Path(tempfile.mkdtemp(prefix="dg", dir="/tmp"))
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


def demo(process_overrides: Callable[[Mapping[type, object]], object], base: Path) -> SimpleNamespace:
    """The organization ``acme`` of ``dash_fixtures`` at ``base``, with its scheduler running (``process_overrides``: where the fake status is put)."""
    scheduler_is(process_overrides, SchedulerState("running", 7000, "2026-10-18 10:00:00Z"))
    return demo_org(base)


def empty(process_overrides: Callable[[Mapping[type, object]], object], base: Path) -> Org:
    """An organization with only its root, with its scheduler stopped (``process_overrides``: where the fake status is put)."""
    scheduler_is(process_overrides, SchedulerState("stopped"))
    return Org.init(base / "empty", "m")
