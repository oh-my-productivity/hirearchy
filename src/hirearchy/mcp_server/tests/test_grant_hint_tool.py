# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

from testkit.reach.hirearchy.core import ROOT
from testkit.mcp_server_world import build_server


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_the_send_reply_carries_the_grant_hint(org):
    root = build_server(org, ROOT)
    out = call(root, "send", to="ceo", body="runs for you", budget=1)
    assert "with 1 run(s) of budget" in out
    assert "`ceo` now has 1 run(s) and 0 outstanding delegation(s): with 1 run(s) and 0 outstanding delegation(s) it cannot delegate anything" in out
    assert "grant at least 1 more (a budget of 2)" in out
    out = call(root, "send", to="ceo", body="runs for you", budget=4)
    assert "now has 5 run(s)" in out and "hand down at most 4 run(s)" in out
    assert "now has" not in call(root, "send", to="ceo", body="just a note")


def test_a_manager_granting_to_its_report_also_gets_the_hint(org):
    org.hire("ceo", "lead2", "Lead", "x", can_hire=True)
    org.send(ROOT, "ceo", "runs", budget=6)
    out = call(build_server(org, "ceo"), "send", to="ceo/lead2", body="go", budget=2)
    assert "`ceo/lead2` now has 2 run(s) and 0 outstanding delegation(s); with one more delegation it can hand down at most 1 run(s)." in out
    assert "now has" not in call(build_server(org, "ceo/lead2"), "send", to="ceo", body="back", budget=1)  # to the parent: no hint
