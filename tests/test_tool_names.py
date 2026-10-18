"""F2: kiro exposes MCP tools by plain name, so a built-in `read`/`write` shadows orgmcp's tool of the same name.
An agent whose charter holds the built-in gets orgmcp's tool as `org_read` / `org_write`; everyone else is unchanged."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from orgmcp.core import ROOT, Org
from orgmcp.server import build_server, resolve_binding

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


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


# ------------------------------------------------------------------------------------------------ prompts

def files_of(org, who):
    return org.run_prompt(who, []).split("- Files:")[1].split("# New messages")[0]


def test_write_only_agent_is_told_org_write_and_plain_read(team):
    text = team.run_prompt("wr", [])
    files = files_of(team, "wr")
    assert "orgmcp tools (shown as `@orgmcp/org_write`, `@orgmcp/read`, ...)" in files
    assert "the orgmcp write tool is `@orgmcp/org_write` for you: use it for MEMORY.md and org files" in files
    assert "Read org files with `@orgmcp/read`." in files and "org_read" not in files
    assert '`@orgmcp/org_write`(path="wr/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`)' in text
    assert '`@orgmcp/write`(' not in text


def test_read_only_agent_is_told_org_read_and_plain_write(team):
    text = team.run_prompt("rd", [])
    files = files_of(team, "rd")
    assert "orgmcp tools (shown as `@orgmcp/write`, `@orgmcp/org_read`, ...)" in files and "(orgmcp `write` only)" in files
    assert "written with `@orgmcp/write`, never with the built-in `write`." in files
    assert "ABSOLUTE path" in files and "`@orgmcp/org_read` for you" in files and "org_write" not in files
    assert '`@orgmcp/write`(path="rd/MEMORY.md", ...)' in text


def test_no_prompt_text_of_an_aliased_agent_names_the_hidden_tool_as_usable(team):
    for who in ("dev", "wr"):
        text = team.run_prompt(who, [])
        assert "`@orgmcp/write`(" not in text and "save it with `@orgmcp/write`" not in text
    assert "(it hides `@orgmcp/read`)" not in team.run_prompt("dev", [])


def test_stray_notice_uses_the_name_the_agent_has(team):
    team.save_ledger("strays", {"dev": {"paths": ["/x/dev"], "told": False}})
    notice = team.stray_notice("dev")
    assert "`@orgmcp/org_write`" in notice and "`@orgmcp/write`" not in notice
    team.save_ledger("strays", {"plain": {"paths": ["/x/plain"], "told": False}})
    assert "`@orgmcp/write`" in team.stray_notice("plain")  # not reachable in practice (no built-in write): text unchanged


# Prompts of agents WITHOUT built-in read/write as produced by main before this change (sha256[:16] of the prompt with
# the sandbox path replaced by T): the new text must be byte-identical.
def test_prompts_of_agents_without_built_in_read_write_are_byte_identical_to_before(tmp_path):
    tmp_path = tmp_path.resolve()
    ws = tmp_path / "ws"
    ws.mkdir()
    inp = tmp_path / "in"
    inp.mkdir()
    org = Org.init(tmp_path / "o", "m")
    org.hire(ROOT, "plain", "P", "x")
    org.hire(ROOT, "sh", "S", "x", tools=["shell"], workspace=str(ws))
    org.hire(ROOT, "ro", "S", "x", inputs=[str(inp)])
    got = {a: hashlib.sha256(org.run_prompt(a, []).replace(str(tmp_path), "T").encode()).hexdigest()[:16] for a in ("plain", "sh", "ro")}
    assert got == EXPECTED_HASHES


EXPECTED_HASHES = {'plain': '9702a6f35d3507be', 'sh': '68c442a5689fafa2', 'ro': 'f0e00465fe120e01'}


# ------------------------------------------------------------------------------------------------- README

def test_readme_states_the_names_and_the_confinement_after_round_f():
    section = README.split("### Workspaces, inputs and confinement")[1].split("## Security notes")[0]
    assert "`org_write`" in section and "`org_read`" in section and "shadow" in section
    assert "workspace + inputs + the organization" in section
    assert '"write": {"allowedPaths": ["/ws/**"], "deniedPaths": ["/org", "/org/**"]}' in section  # write: org denied
    assert 'read":  {"allowedPaths": ["/ws", "/ws/**", "/inputs", "/inputs/**", "/org", "/org/**"], "deniedPaths": []}' in section
    assert "**absolute** path" in section and "Neither reaches the org directory" not in section
