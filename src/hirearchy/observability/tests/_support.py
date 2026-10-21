"""Helpers shared by the tests of ``observability`` (no test lives here)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import cast

import pytest
from _pytest.mark.structures import ParameterSet

from hirearchy.kernel import JsonObject
from hirearchy.observability.testing import ObservabilityWorld, stamp

__all__ = ["at", "dump", "expected", "implementations", "items", "kinds", "request", "stamp", "table"]

EXPECTED = Path(__file__).with_name("expected")



def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters, named by the factory."""
    return [pytest.param(f, id=f.__name__) for f in factories]


def expected(name: str) -> str:
    """The text of ``expected/<name>``: captured from the module ``observe.py`` before the package existed."""
    return (EXPECTED / name).read_text(encoding="utf-8")


def dump(data: object) -> str:
    """The JSON the command line prints (``cli_obs._dump``): keys in order, indented, ISO times."""
    return json.dumps(data, indent=2, default=str) + "\n"


def kinds(events: Sequence[JsonObject]) -> list[object]:
    return [e["kind"] for e in events]


def items(view: JsonObject, key: str = "events") -> list[JsonObject]:
    """The list of objects under ``key`` of a view (``events``, ``items``, ``checks`` ...)."""
    return cast("list[JsonObject]", view[key])


def table(view: JsonObject, key: str) -> JsonObject:
    """The object under ``key`` of a view."""
    return cast("JsonObject", view[key])


def at(text: object) -> datetime:
    """The time an ISO string in a view names."""
    return datetime.fromisoformat(str(text))


def request(w: ObservabilityWorld) -> dict[str, str]:
    """A finished request on ``root -> ceo -> ceo/eng``, with its run logs and events (the story of ``obs_fixtures`` in a few lines).

    t=0 root tasks ceo (6 runs); t=3 ceo runs (delegates to eng, one refusal); t=70 eng runs (reports); t=115 ceo runs again (reports done).
    Returns the ids: ``task``, ``sub``, ``res_eng``, ``res``, and the run ids ``run1``, ``run2``, ``run3``."""
    for addr in ("ceo", "ceo/eng"):
        w.agent(addr)
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=6, trace="self", box="read")
    t = task.id
    s1 = w.run_log("ceo", 3, "# exit 0 after 42s\n", end=45)
    sub = w.send("ceo", "ceo/eng", "task", 20, title="Build", budget=3, trace=t, box="read")
    s2 = w.run_log("ceo/eng", 70, "# exit 0 after 30s\n", end=100)
    res_eng = w.send("ceo/eng", "ceo", "result", 95, title="Build", budget=2, status="done", reply_to=sub.id, trace=t, box="read")
    s3 = w.run_log("ceo", 115, "# exit 0 after 15s\n", end=130)
    res = w.send("ceo", "root", "result", 125, title="Ship it", budget=3, status="done", reply_to=task.id, trace=t, box="read")
    w.emit(0, "scheduler.start", proc="scheduler", pid=7000, mode="until_done", max_runs=None, max_parallel=3, version="x")
    r1 = w.run_events("ceo", s1, 3, 42, [task.id], [task.id])
    w.tool(5, "ceo", "inbox", run=r1)
    w.tool(10, "ceo", "delegate", ok=False, ms=3, run=r1, trace=task.id, error="not enough budget: you have 5 run(s) and must keep 2 in reserve",
           args={"to": "ceo/eng", "budget": 9})
    w.tool(20, "ceo", "delegate", run=r1, trace=task.id, args={"to": "ceo/eng", "title": "Build", "budget": 3})
    r2 = w.run_events("ceo/eng", s2, 70, 30, [sub.id], [task.id])
    w.tool(90, "ceo/eng", "write", run=r2, trace=task.id, args={"path": "ceo/eng/work/out.md", "content_chars": 5})
    w.tool(95, "ceo/eng", "report", run=r2, trace=task.id, args={"task_id": sub.id, "status": "done"})
    r3 = w.run_events("ceo", s3, 115, 15, [res_eng.id], [task.id])
    w.tool(125, "ceo", "report", run=r3, trace=task.id, args={"task_id": task.id, "status": "done"})
    w.emit(131, "scheduler.exit", proc="scheduler", pid=7000, reason="finished: no open tasks", runs_started=3)
    return {"task": task.id, "sub": sub.id, "res_eng": res_eng.id, "res": res.id, "run1": r1, "run2": r2, "run3": r3}
