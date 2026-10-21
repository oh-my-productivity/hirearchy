# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.hirearchy.core import ROOT

ENG = "ceo/eng"


def test_retire_tool_reports_the_refund(org):
    import asyncio

    from testkit.mcp_server_world import build_server

    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=4)
    result = asyncio.run(build_server(org, "ceo").call_tool("retire", {"name": ENG, "reason": "done"}))
    blocks = result[0] if isinstance(result, tuple) else result
    text = "\n".join(getattr(b, "text", "") for b in blocks)
    assert "retired ceo/eng" in text and "4 unspent run(s)" in text and "returned to ceo" in text
