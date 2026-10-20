"""define_service on an existing service is an amendment: omitted fields keep their value; add/remove criteria."""

import pytest

from orgmcp.core import ROOT
from orgmcp.server import build_server

from testkit.services_world import BRIEF, call, cli, contract_meta, define, fails, playbook_meta  # noqa: F401


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


def test_cli_amendment(svc, capsys, tmp_path):
    cli(svc, "define-service", "ceo", "weekly-brief", "--add-acceptance", "Never longer than one page")
    out = capsys.readouterr().out
    assert "v1 -> v2" in out and "3. Never longer than one page" in out
    meta = contract_meta(svc)[0]
    assert meta["acceptance"][-1] == "Never longer than one page" and meta["budget"] == 10 and meta["deliverable"] == BRIEF["deliverable"]

    more = tmp_path / "more.txt"
    more.write_text("First extra\n- Second extra\n")
    cli(svc, "define-service", "ceo", "weekly-brief", "--remove-acceptance", "At most 600 words",
        "--remove-acceptance", "Never longer than one page", "--add-acceptance", f"@{more}")
    assert contract_meta(svc)[0]["acceptance"] == ["Every factual claim has a source URL", "First extra", "Second extra"]

    cli(svc, "define-service", "ceo", "weekly-brief", "--budget", "7", "--no-locked", "--max-words", "250", "--input", "topic*:the topic")
    meta = contract_meta(svc)[0]
    assert meta["budget"] == 7 and meta["locked"] is False and meta["inputs"] == [{"name": "topic", "description": "the topic", "required": True}]
    assert meta["deliverable"] == {**BRIEF["deliverable"], "max_words": 250}  # single deliverable parts merge over the old one
    capsys.readouterr()

    for args, message in (
        (("weekly-brief", "--acceptance", "Whole new", "--add-acceptance", "x y"), "replaces all criteria"),
        (("weekly-brief", "--budget", "7"), "no change"),
        (("brand-new", "--budget", "3"), "needs description"),
    ):
        with pytest.raises(SystemExit):
            cli(svc, "define-service", "ceo", *args)
        assert message in capsys.readouterr().err
