# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio

import pytest
import testkit
from testkit.legacy.orgmcp.core import ROOT
from testkit.legacy.orgmcp.server import build_server, resolve_binding

README = (testkit.REPO / "README.md").read_text(encoding="utf-8")


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def server_for(org, who, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    if who == ROOT:
        monkeypatch.delenv("ORG_AGENT", raising=False)
    else:
        monkeypatch.setenv("ORG_AGENT", who)
    return build_server(*resolve_binding())


def tool_map(server):
    return {t.name: t.description for t in asyncio.run(server.list_tools())}


@pytest.fixture
def team(org, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    inputs = tmp_path / "in"
    inputs.mkdir()
    kw = dict(workspace=str(ws), inputs=[str(inputs)])
    org.hire(ROOT, "plain", "Plain", "x")
    org.hire(ROOT, "sh", "Shell", "x", tools=["shell"], **kw)
    org.hire(ROOT, "rd", "Reader", "x", tools=["read"], **kw)
    org.hire(ROOT, "wr", "Writer", "x", tools=["write"], **kw)
    org.hire(ROOT, "dev", "Dev", "x", tools=["read", "write", "shell"], **kw)
    return org


# ------------------------------------------------------------------------------------------- registration
@pytest.mark.parametrize("who, read_name, write_name", [
    ("plain", "read", "write"),
    ("sh", "read", "write"),
    ("rd", "org_read", "write"),
    ("wr", "read", "org_write"),
    ("dev", "org_read", "org_write"),
    (ROOT, "read", "write"),
])
def test_tool_names_follow_the_charter_tools(team, monkeypatch, who, read_name, write_name):
    names = set(tool_map(server_for(team, who, monkeypatch)))
    assert team.tool_names(who) == {"read": read_name, "write": write_name} if who != ROOT else True
    for plain, name in (("read", read_name), ("write", write_name)):
        assert name in names
        assert (plain in names) == (name == plain)  # the shadowed plain name is not registered
    assert {"whoami", "inbox", "report", "send", "delegate"} <= names  # the rest is unchanged


def test_an_agent_without_built_ins_has_exactly_the_tools_it_had(team, monkeypatch):
    plain = set(tool_map(server_for(team, "plain", monkeypatch)))
    dev = set(tool_map(server_for(team, "dev", monkeypatch)))
    assert plain - dev == {"read", "write"} and dev - plain == {"org_read", "org_write"}


def test_org_write_and_org_read_work_and_describe_themselves(team, monkeypatch):
    server = server_for(team, "dev", monkeypatch)
    tools = tool_map(server)
    assert "@orgmcp/org_write" in tools["org_write"] and "ORGANIZATION file" in tools["org_write"]
    assert "called `org_write` for you" in tools["org_write"]
    assert "@orgmcp/org_read" in tools["org_read"] and "called `org_read` for you" in tools["org_read"]
    assert call(server, "org_write", path="dev/MEMORY.md", content="notes") == "wrote dev/MEMORY.md (organization file)"
    assert team.memory("dev") == "notes"
    call(server, "org_write", path="dev/work/note.md", content="hello")
    assert "hello" in call(server, "org_read", path="dev/work/note.md")
    assert "work/" in call(server, "org_read", path="dev")  # relative org path


def test_plain_tools_keep_their_descriptions(team, monkeypatch):
    tools = tool_map(server_for(team, "plain", monkeypatch))
    assert "shows this tool as @orgmcp/write" in tools["write"] and "called" not in tools["write"]
    assert "shows it as @orgmcp/read" in tools["read"] and "called" not in tools["read"]


# ------------------------------------------------------------------------------------------------- README
def test_readme_states_the_names_and_the_confinement_after_round_f():
    section = README.split("### Workspaces, inputs and confinement")[1].split("## Security notes")[0]
    assert "`org_write`" in section and "`org_read`" in section and "shadow" in section
    assert "workspace + inputs + the organization" in section
    assert '"write": {"allowedPaths": ["/ws/**"], "deniedPaths": ["/org", "/org/**"]}' in section  # write: org denied
    assert 'read":  {"allowedPaths": ["/ws", "/ws/**", "/inputs", "/inputs/**", "/org", "/org/**"], "deniedPaths": []}' in section
    assert "**absolute** path" in section and "Neither reaches the org directory" not in section
