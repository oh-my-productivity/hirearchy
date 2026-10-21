"""``ArchivedRunTotal``: the runs ever used, retired agents included."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents.testing import AgentsHarness, fs_agents, memory_agents
from hirearchy.review._ports import RunTotal
from hirearchy.review._runs import ArchivedRunTotal
from hirearchy.runs.testing import RunsHarness, fs_runs, memory_runs


@pytest.fixture(params=["fs", "memory"])
def parts(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[RunTotal, AgentsHarness, RunsHarness]:
    agents = fs_agents(tmp_path) if request.param == "fs" else memory_agents(tmp_path)
    runs = fs_runs(tmp_path) if request.param == "fs" else memory_runs(tmp_path)
    total = ArchivedRunTotal(agents.directory, runs.reader, agents.archive)
    assert isinstance(total, RunTotal)
    return total, agents, runs


def hire(agents: AgentsHarness, runs: RunsHarness, addr: str, logs: int) -> None:
    agents.put(f"{addr}/AGENT.md", "---\nrole: R\n---\n# R\n")
    runs.add_agent(addr)
    for i in range(logs):
        runs.put_log(addr, f"2026010{1 + i}T000000000000.log", "")


def test_an_organization_without_runs_has_none(parts: tuple[RunTotal, AgentsHarness, RunsHarness]) -> None:
    assert parts[0].total() == 0


def test_the_run_logs_of_every_agent_are_summed(parts: tuple[RunTotal, AgentsHarness, RunsHarness]) -> None:
    total, agents, runs = parts
    hire(agents, runs, "ceo", 2)
    hire(agents, runs, "ceo/eng", 3)
    hire(agents, runs, "ops", 0)
    assert total.total() == 5


def test_the_run_logs_inside_retired_trees_count_too(parts: tuple[RunTotal, AgentsHarness, RunsHarness]) -> None:
    total, agents, runs = parts
    hire(agents, runs, "ceo", 2)
    agents.put(".retired/ceo-S/runs/20260101T000000000001.log", "x")
    agents.put(".retired/ceo-S/eng/runs/20260101T000000000002.log", "x")
    agents.put(".retired/ceo-S/work/x.log", "x")  # not a run
    assert total.total() == 4
