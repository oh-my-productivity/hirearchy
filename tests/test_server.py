import asyncio

from orgmcp.core import ROOT
from orgmcp.server import build_server


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_tools_are_bound_to_identity(org):
    human = build_server(org, ROOT)
    out = call(human, "delegate", to="ceo", title="Plan", goal="Make a plan", acceptance="plan.md exists", budget=4)
    assert "delegated" in out
    task_id = out.split()[1]

    ceo = build_server(org, "ceo")
    org.begin_run("ceo")
    assert "Make a plan" in call(ceo, "inbox")
    assert "Open tasks assigned to you" in call(ceo, "whoami")
    assert "wrote ceo/work/plan.md" in call(ceo, "write", path="ceo/work/plan.md", content="# Plan")
    assert "reported done" in call(ceo, "report", task_id=task_id, status="done", summary="Done.",
                                   artifacts=["ceo/work/plan.md"])
    org.end_run("ceo", ok=True)

    assert "Done." in call(human, "inbox")  # and marks it read
    assert org.unread(ROOT) == 0
    assert "ceo [Chief executive]" in call(human, "status")


def test_rule_violations_are_reported_as_tool_errors(org):
    eng = build_server(org, "ceo/eng")
    try:
        call(eng, "write", path="../MEMORY.md", content="x")
    except Exception as exc:  # FastMCP raises ToolError carrying our message
        assert "own directory" in str(exc)
    else:
        raise AssertionError("expected a permission error")


def test_tool_list(org):
    names = {t.name for t in asyncio.run(build_server(org, "ceo").list_tools())}
    assert names == {
        "whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health",
    }
