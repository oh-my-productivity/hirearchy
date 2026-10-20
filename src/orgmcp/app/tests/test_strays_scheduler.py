"""The scheduler's stray check goes through the stray ports of the runtime: the probe before and after a run, ``found_since`` for what is new,
the registry for what is remembered. The log line, the echo and a probe that fails never stops a run (tests/test_finish)."""

from __future__ import annotations

import dataclasses
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from orgmcp.app import Org
from orgmcp.strays import StrayProbe, StrayRegistry
from testkit.health_world import Scheduler

class ScriptedProbe(StrayProbe):
    """Probes ``{"/p": 1.0}`` before the run and ``{"/p": 2.0, ...}`` after it; finds what it is told."""

    def __init__(self, found: list[str], fail: bool = False) -> None:
        self.found, self.fail = found, fail
        self.probes: list[str] = []
        self.compared: list[tuple[Mapping[str, float], Mapping[str, float]]] = []

    def probe(self, addr: str) -> dict[str, float]:
        self.probes.append(addr)
        if self.fail:
            raise OSError("boom")
        return {"/p": float(len(self.probes))}

    def found_since(self, before: Mapping[str, float], after: Mapping[str, float]) -> list[str]:
        self.compared.append((before, after))
        return self.found


class RecordingRegistry(StrayRegistry):
    def __init__(self) -> None:
        self.recorded: list[tuple[str, list[str]]] = []

    def record(self, addr: str, paths: Sequence[str]) -> None:
        self.recorded.append((addr, list(paths)))

    def take_notice(self, addr: str) -> str:
        return ""


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "dev", "Developer", "Code.", tools=["write"], workspace=str(tmp_path / "ws"))
    (tmp_path / "ws").mkdir()
    made.send("root", "dev", "go", budget=5)
    return made


def run_once(org: Org, lines: list[str]) -> None:
    def build(o: Org, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
        return [sys.executable, "-c", "pass"], o.workspace_of(addr), dict(os.environ)  # type: ignore[return-value]

    sched = Scheduler(org, build, echo=lines.append)
    sched.tick()
    deadline = time.time() + 20
    while sched.runs and time.time() < deadline:
        sched.reap()
        time.sleep(0.02)
    assert not sched.runs


def test_the_probe_is_the_one_of_the_runtime_and_runs_before_and_after_the_run(org: Org) -> None:
    probe = ScriptedProbe([])
    org.runtime = dataclasses.replace(org.runtime, stray_probe=probe, stray_registry=RecordingRegistry())
    run_once(org, [])
    assert probe.probes == ["dev", "dev"] and probe.compared == [({"/p": 1.0}, {"/p": 2.0})]


def test_what_is_found_is_logged_echoed_and_recorded_in_the_registry_of_the_runtime(org: Org) -> None:
    found = [f"/ws/dev/{n}" for n in range(7)]
    registry = RecordingRegistry()
    org.runtime = dataclasses.replace(org.runtime, stray_probe=ScriptedProbe(found), stray_registry=registry)
    lines: list[str] = []
    run_once(org, lines)
    assert registry.recorded == [("dev", found)]
    shown = ", ".join(found[:5])
    assert f"dev: warning: org files in its workspace (built-in write shadows orgmcp write?): {shown}" in lines
    log = next((org.root / "dev" / "runs").glob("*.log")).read_text(encoding="utf-8")
    assert f"# warning: dev created org files in its workspace with the built-in `write` (not in the org, so they are not its memory): {shown}" in log
    assert org.ledger("strays") == {}  # the scheduler no longer writes the ledger itself


def test_nothing_found_records_nothing(org: Org) -> None:
    registry = RecordingRegistry()
    org.runtime = dataclasses.replace(org.runtime, stray_probe=ScriptedProbe([]), stray_registry=registry)
    run_once(org, [])
    assert registry.recorded == []


def test_a_failing_probe_of_the_runtime_is_logged_once_and_records_nothing(org: Org) -> None:
    probe = ScriptedProbe(["/ws/dev"], fail=True)
    registry = RecordingRegistry()
    org.runtime = dataclasses.replace(org.runtime, stray_probe=probe, stray_registry=registry)
    lines: list[str] = []
    run_once(org, lines)
    assert any("stray check failed" in x for x in lines) and probe.probes == ["dev"] and registry.recorded == []
