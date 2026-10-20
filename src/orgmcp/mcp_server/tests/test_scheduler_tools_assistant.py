# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import pytest
from testkit.reach.orgmcp.core import ROOT
from testkit.mcp_server_world import StartRecorder, build_server, resolve_binding


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    (work / "<folder-with-your-files>").mkdir(parents=True)  # the documents example's input folder
    (work / "<folder-with-your-data>").mkdir()  # the analysis example's input folder
    monkeypatch.chdir(work)
    return work


def test_start_tool_defaults_to_until_done(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    out = call(server, "start")  # empty org: nothing to run, so nothing is started
    assert out.startswith("not started: there is nothing to run") and not (org.root / ".runtime" / "scheduler.pid").exists()


def test_start_tool_passes_until_done_to_the_scheduler(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    starts = StartRecorder()
    server = build_server(*resolve_binding(), starts=starts)
    seen = {}
    starts.use(lambda m, u: seen.update(max=m, until_done=u) or 4242)
    assert "exits by itself when the work is done" in call(server, "start", max_runs=2)
    assert seen == {"max": 2, "until_done": True}
    assert "runs until stop()" in call(server, "start", until_done=False)
    assert seen["until_done"] is False
