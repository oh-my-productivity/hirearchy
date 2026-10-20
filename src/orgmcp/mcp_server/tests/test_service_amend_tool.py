# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.core import ROOT
from testkit.mcp_server_world import build_server
from testkit.services_world import call, contract_meta, define, fails


@pytest.fixture
def svc(org):
    define(org, notes="Mind the sources.", locked=True, playbook="Steps: search, write.")
    return org


def test_the_mcp_tool_amends_with_optional_fields(svc):
    root = build_server(svc, ROOT)
    schema = {t.name: t for t in __import__("asyncio").run(root.list_tools())}["define_service"].inputSchema
    assert schema["required"] == ["owner", "name"]
    assert {"add_acceptance", "remove_acceptance"} <= set(schema["properties"])
    out = call(root, "define_service", owner="ceo", name="weekly-brief", add_acceptance=["Never longer than one page"])
    assert "v1 -> v2" in out and "3. Never longer than one page" in out
    assert "no change" in fails(root, "define_service", owner="ceo", name="weekly-brief")
    assert "already a criterion" in fails(root, "define_service", owner="ceo", name="weekly-brief",
                                           add_acceptance=["Never longer than one page"])
    call(root, "define_service", owner="ceo", name="weekly-brief", remove_acceptance=["At most 600 words"])
    assert contract_meta(svc)[0]["acceptance"] == ["Every factual claim has a source URL", "Never longer than one page"]
