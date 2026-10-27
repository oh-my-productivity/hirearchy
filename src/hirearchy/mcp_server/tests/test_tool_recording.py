# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio
import dataclasses
import json
import os
import shutil
import sys

import pytest
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.mcp_server_world import build_server, telemetry


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    telemetry.reset()
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


def call(server, tool, **args):
    return asyncio.run(server.call_tool(tool, args))


# ------------------------------------------------------------------------------------------------- tool.call
def agent_server(org, me="ceo"):
    return build_server(org, me)


def test_tool_calls_are_recorded_with_actor_run_and_summary(org, monkeypatch):
    monkeypatch.setenv("ORG_RUN_ID", "ceo@20260101T000000000000")
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    call(server, "whoami")
    call(server, "delegate", to="ceo/eng", title="Build it", goal="g" * 3000, acceptance="a" * 200, budget=2)
    calls = read_events(org, "tool.call")
    assert [c["tool"] for c in calls] == ["whoami", "delegate"]
    who, deleg = calls
    assert who["ok"] is True and who["error"] is None and who["error_type"] is None and who["ms"] >= 0
    assert who["proc"] == "mcp" and who["actor"] == "ceo" and who["run"] == "ceo@20260101T000000000000"
    assert who["trace"] == task.id  # the one trace of the caller's batch
    assert deleg["args"] == {"to": "ceo/eng", "title": "Build it", "budget": 2, "goal_chars": 3000, "acceptance_chars": 200}
    assert deleg["trace"] == task.id


def test_every_refusal_is_recorded_and_the_tool_still_raises_the_same(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    with pytest.raises(Exception) as info:
        call(server, "delegate", to="ceo", title="x", goal="g", acceptance="a")
    assert "direct reports" in str(info.value)
    with pytest.raises(Exception) as bad:
        call(server, "report", task_id="no-such-task", status="done", summary="s")
    assert "no task no-such-task assigned to you" in str(bad.value)
    refused = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert [c["tool"] for c in refused] == ["delegate", "report"]
    assert all(c["error_type"] == "OrgError" and c["error"] for c in refused)
    assert "you can only delegate to your direct reports" in refused[0]["error"]
    assert refused[1]["args"]["task_id"] == "no-such-task" and refused[1]["args"]["status"] == "done"


def test_a_refusal_keeps_the_trace_of_the_task_it_names(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    org.report("ceo", task.id, "done", "ok")
    with pytest.raises(Exception):
        call(agent_server(org), "report", task_id=task.id, status="done", summary="again")
    bad = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert bad[0]["trace"] == task.id and "final" in bad[0]["error"]


def test_unexpected_exceptions_are_recorded_by_class(org):
    import dataclasses

    from hirearchy.overview import OrgTree

    class BrokenTree(OrgTree):  # the tree of the status tool is the port of the runtime, not a method of the facade
        def tree(self) -> str:
            return 1 / 0

    org.runtime = dataclasses.replace(org.runtime, org_tree=BrokenTree())
    server = agent_server(org)
    with pytest.raises(Exception):
        call(server, "status")
    (bad,) = [c for c in read_events(org, "tool.call") if not c["ok"]]
    assert bad["error_type"] == "ZeroDivisionError" and "division" in bad["error"]


def test_bodies_never_reach_the_log_only_their_length(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    org.begin_run("ceo")
    server = agent_server(org)
    secret = "TOPSECRET" + "z" * 4991
    call(server, "send", to="ceo/eng", body=secret, title="t" * 200)
    call(server, "write", path="ceo/work/n.md", content=secret)
    call(server, "report", task_id=task.id, status="done", summary=secret, lessons=secret[:700], artifacts=["ceo/work/n.md"])
    sent, wrote, reported = read_events(org, "tool.call")[:3]
    assert sent["args"]["body_chars"] == 5000 and "body" not in sent["args"]
    assert len(sent["args"]["title"]) == 80 and sent["args"]["to"] == "ceo/eng"
    assert wrote["args"] == {"path": "ceo/work/n.md", "content_chars": 5000, "append": False}
    assert reported["args"]["summary_chars"] == 5000 and reported["args"]["lessons_chars"] == 700
    assert reported["args"]["artifacts"] == ["ceo/work/n.md"]
    for f in event_files(org):
        assert "TOPSECRET" not in f.read_text()


def test_a_tool_call_trace_is_that_of_the_message_it_delivered(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # two traces in the batch: only the call's own effect can tell
    server = agent_server(org)
    call(server, "report", task_id=b.id, status="done", summary="ok")
    call(server, "whoami")
    report, who = read_events(org, "tool.call")
    assert report["trace"] == b.id and who["trace"] is None
    assert a.id != b.id


def test_arg_summaries_by_type():
    out = telemetry.summarize_args({
        "to": "ceo", "budget": 3, "append": True, "n": None, "blob": "x" * 500, "inputs": {"topic": "secret", "k": "v"},
        "acceptance": ["one", "two"], "tools": ["read", "write"], "artifacts": ["a.md"], "obj": object(), "name": "n" * 200,
    })
    assert out["to"] == "ceo" and out["budget"] == 3 and out["append"] is True and "n" not in out
    assert out["blob_chars"] == 500 and "blob" not in out
    assert out["inputs_keys"] == ["topic", "k"] and "secret" not in json.dumps(out)
    assert out["acceptance_n"] == 2 and out["acceptance_chars"] == 6
    assert out["tools"] == ["read", "write"] and out["artifacts"] == ["a.md"]
    assert out["obj_type"] == "object" and len(out["name"]) == 80


def test_every_tool_of_every_role_is_instrumented(org, tmp_path):
    org.define_service(ROOT, "ceo", "weekly", description="A brief.", acceptance=["Short"],
                       deliverable={"description": "one file"}, budget=4)
    servers = {
        "root": build_server(org, ROOT),
        "manager": build_server(org, "ceo"),  # also offers a service: owner tools
        "worker": build_server(org, "ceo/eng"),
    }
    seen = set()
    for who, server in servers.items():
        for tool in server._tool_manager.list_tools():
            assert hasattr(tool.fn, "__wrapped__"), f"{who}: {tool.name} is not recorded"
            seen.add(tool.name)
    for name in ("whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status",
                 "health", "services", "define_service", "request", "feedback", "acknowledge_playbook", "revise_playbook", "create_org", "start",
                 "stop", "blueprint_example", "propose_org", "apply_org", "progress"):
        assert name in seen, name


def test_tools_keep_their_names_signatures_and_docstrings(org):
    import inspect

    tools = {t.name: t for t in build_server(org, "ceo")._tool_manager.list_tools()}
    delegate = tools["delegate"]
    assert delegate.description.startswith("Assign a task to one of your direct reports.")
    assert list(delegate.parameters["properties"]) == ["to", "title", "goal", "acceptance", "inputs", "budget", "revises"]
    assert list(inspect.signature(delegate.fn).parameters) == ["to", "title", "goal", "acceptance", "inputs", "budget", "revises"]
    assert delegate.fn.__name__ == "delegate"


def test_a_tool_added_later_is_recorded_without_extra_work(org):
    server = build_server(org, ROOT)

    @server.tool()
    def observe_stub(view: str = "now", limit: int = 5) -> str:
        """A stand-in for a tool somebody adds to the server later."""
        return f"viewed {view}"

    call(server, "observe_stub", view="trace")
    (ev,) = read_events(org, "tool.call")
    assert ev["tool"] == "observe_stub" and ev["actor"] == "root" and ev["args"] == {"view": "trace", "limit": 5}


def test_the_async_progress_tool_is_recorded(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    call(build_server(org, ROOT), "progress")
    (ev,) = read_events(org, "tool.call")
    assert ev["tool"] == "progress" and ev["ok"] is True and ev["actor"] == "root"


def test_a_server_without_an_organization_still_works_and_writes_nothing(tmp_path):
    target = tmp_path / "later"
    from testkit.mcp_server_world import OrgBinding

    server = build_server(OrgBinding(target), ROOT)
    assert "Setup" in str(call(server, "whoami"))
    assert not target.exists()
    call(server, "create_org", mission="a mission")
    (ev,) = [e for e in read_events(Org(target), "tool.call")]
    assert ev["tool"] == "create_org" and ev["args"] == {"mission_chars": 9}
    assert not any(".runtime/events" in line for line in (target / ".gitignore").read_text().split("\n") if line.startswith("!"))


def test_emission_failure_does_not_change_a_tool_result(org):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "events").write_text("blocked")
    server = build_server(org, ROOT)
    assert "ceo" in str(call(server, "status"))
    with pytest.raises(Exception) as info:
        call(server, "send", to="nobody", body="x")
    assert "no such agent" in str(info.value)


def test_a_real_mcp_server_process_writes_its_own_events_file(org):
    """The stdio server (``hirearchy mcp``) as kiro starts it: ORG_AGENT and ORG_RUN_ID in its environment."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")

    async def session():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "hirearchy", "mcp"],
            env={**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": "ceo", "ORG_RUN_ID": "ceo@20260101T000000000000"},
        )
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                await s.call_tool("whoami", {})
                refused = await s.call_tool("send", {"to": "nobody", "body": "a secret body"})
                assert refused.isError

    asyncio.run(session())
    mcp_files = [f for f in event_files(org) if f.name.startswith("mcp-")]
    assert len(mcp_files) == 1 and f"-{os.getpid()}-" not in mcp_files[0].name
    who, bad = [json.loads(line) for line in mcp_files[0].read_text().splitlines()]
    assert (who["proc"], who["tool"], who["actor"], who["run"], who["trace"]) == ("mcp", "whoami", "ceo", "ceo@20260101T000000000000", task.id)
    assert bad["ok"] is False and bad["error"] == "no such agent: nobody" and bad["args"] == {"to": "nobody", "body_chars": 13, "title": "", "budget": 0}
    assert (who["seq"], bad["seq"]) == (1, 2) and who["pid"] != os.getpid()
