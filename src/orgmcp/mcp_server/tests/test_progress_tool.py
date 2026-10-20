# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio
import os
import sys

import pytest
import testkit
from testkit.legacy.orgmcp.cli import main
from testkit.legacy.orgmcp.core import ROOT
from testkit.legacy.orgmcp.scheduler import Scheduler, describe_scheduler
from testkit.legacy.orgmcp.server import build_server, resolve_binding

from orgmcp.progress import describe_progress

FAKE = str(testkit.FAKE_AGENT)


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


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


def test_progress_tool_and_cli_take_the_wait(org, task, capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    tool = next(t for t in asyncio.run(server.list_tools()) if t.name == "progress")
    assert set(tool.inputSchema["properties"]) == {"task_id", "wait_seconds"}
    out = call(server, "progress", wait_seconds=300)  # stopped scheduler: answers at once
    assert out.startswith("Not waiting") and f"(task {task.id})" in out
    main(["--root", str(org.root), "progress", task.id, "--wait", "300"])
    cli = capsys.readouterr().out
    assert cli.startswith("Not waiting") and "scheduler: stopped" in cli


# ------------------------------------------------------------------------------------ until done
def fake_runner(mode="work"):
    def build(o, addr, prompt):
        return [sys.executable, FAKE], o.dir(addr), {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    return build


def test_status_and_progress_show_the_finished_scheduler_until_new_work_arrives(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    Scheduler(org, fake_runner("work"), echo=lambda _: None).serve(until_done=True)
    assert describe_progress(org).splitlines()[-1] == "scheduler: stopped (finished: no open tasks)"
    server = build_server(org, ROOT)
    assert "scheduler: stopped (finished: no open tasks)" in call(server, "status")
    org.delegate(ROOT, "ceo", "More", "g", "a", budget=3)  # new work: the old reason no longer holds
    assert describe_scheduler(org) == "scheduler: stopped"
    assert describe_progress(org).splitlines()[-1].startswith("scheduler: stopped - open tasks do not move")
