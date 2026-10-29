# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio
import os
import sys

import pytest
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.mcp_server_world import build_server, resolve_binding

ROOT_TOOLS = {
    "whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health",
    "create_org", "start", "stop", "propose_org", "apply_org", "progress", "quality", "retro", "blueprint_example", "observe",
    "services", "define_service", "request", "feedback", "acknowledge_playbook",  # the client's service tools: root and managers
}


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


def tool_names(server) -> set[str]:
    return {t.name for t in asyncio.run(server.list_tools())}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def setup_server(tmp_path, monkeypatch):
    """A root server bound (by ORG_ROOT) to a directory that does not exist yet."""
    target = tmp_path / "fresh" / "org"
    monkeypatch.setenv("ORG_ROOT", str(target))
    binding, me = resolve_binding()
    return build_server(binding, me), target


# ---------------------------------------------------------------- setup mode
def test_setup_mode_exposes_all_tools_plus_create_org(setup_server):
    server, target = setup_server
    assert not target.exists()
    assert tool_names(server) == ROOT_TOOLS


def test_setup_mode_other_tools_say_what_to_do(setup_server):
    server, target = setup_server
    expected = f"no organization at {target} yet: call create_org(mission=...) first"
    for tool, args in [("inbox", {}), ("delegate", dict(to="a", title="t", goal="g", acceptance="a")),
                       ("report", dict(task_id="x", status="done", summary="s")), ("send", dict(to="a", body="b")),
                       ("read", {}), ("write", dict(path="a", content="b")), ("health", {}), ("start", {}),
                       ("stop", {})]:
        assert expected in fails(server, tool, **args), tool
    assert not target.exists()  # nothing was created by the failing calls


def test_setup_mode_root_hire_and_retire_are_refused_in_favour_of_the_plan(setup_server):
    """Root's hire and retire are refused before the organization is asked for (design 13, Q3): the refusal is the same in setup mode."""
    server, target = setup_server
    assert "refused: a new agent changes the organization" in fails(server, "hire", name="a", role="r", charter="c")
    assert "refused: retiring a changes the organization" in fails(server, "retire", name="a", reason="r")
    assert not target.exists()


def test_the_setup_text_names_propose_org_and_apply_org(setup_server):
    """Root's hire is refused (design 13), so the first step after create_org points to the plan, not to a hire (design 11.2)."""
    server, target = setup_server
    for tool in ("whoami", "status"):
        out = call(server, tool)
        assert "then propose_org and apply_org a plan, and start() the scheduler." in out
        assert "hire a team" not in out


def test_setup_mode_whoami_and_status_describe_the_setup(setup_server):
    server, target = setup_server
    for tool in ("whoami", "status"):
        out = call(server, tool)
        assert str(target) in out and "create_org(mission=" in out and "scheduler: stopped" in out


def test_create_org_then_every_tool_works_in_the_same_server(setup_server):
    server, target = setup_server
    out = call(server, "create_org", mission="Study octopuses", default_model="claude-opus-5.5")
    assert str(target) in out and (target / "ORG.md").is_file()
    assert Org(target).config["default_model"] == "claude-opus-5.5" and "Study octopuses" in Org(target).rules()
    assert "root (human)" in call(server, "status")
    assert Org(target).hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True) == "ceo"  # (root's MCP hire is refused: the facade is the programs' path)
    assert "delegated" in call(server, "delegate", to="ceo", title="T", goal="g", acceptance="a", budget=3)
    assert "Address: `root`" in call(server, "whoami") and "scheduler: stopped" in call(server, "whoami")
    assert "(no new messages)" in call(server, "inbox")


def test_create_org_refuses_a_default_model_below_the_floor(setup_server):
    server, target = setup_server
    message = fails(server, "create_org", mission="Study octopuses", default_model="claude-haiku-4.5")
    assert "cannot create the organization: default_model: " in message and "allowed: claude-sonnet-5.5, claude-opus-5.5" in message
    assert not (target / "ORG.md").exists()
    assert str(target) in call(server, "create_org", mission="Study octopuses", default_model="claude-opus-5.5")  # the second try works


def test_create_org_works_in_an_existing_empty_directory(tmp_path, monkeypatch):
    target = tmp_path / "empty"
    target.mkdir()
    (target / ".DS_Store").write_text("")
    monkeypatch.setenv("ORG_ROOT", str(target))
    server = build_server(*resolve_binding())
    call(server, "create_org", mission="m")
    assert (target / "ORG.md").is_file()


def test_create_org_refuses_a_non_empty_directory(tmp_path, monkeypatch):
    target = tmp_path / "docs"
    target.mkdir()
    (target / "notes.txt").write_text("precious")
    monkeypatch.setenv("ORG_ROOT", str(target))
    server = build_server(*resolve_binding())
    assert "not empty" in fails(server, "create_org", mission="m") and "notes.txt" in fails(server, "create_org", mission="m")
    assert sorted(p.name for p in target.iterdir()) == ["notes.txt"]
    assert "not empty" in call(server, "status") or "no organization" in fails(server, "inbox")


def test_create_org_refuses_when_the_org_exists_and_says_it_is_ready(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    msg = fails(server, "create_org", mission="again")
    assert "already exists" in msg and "ready to use" in msg
    assert "Test mission" in org.rules()  # untouched


def test_create_org_twice_in_one_server_is_refused(setup_server):
    server, target = setup_server
    call(server, "create_org", mission="first")
    assert "already exists" in fails(server, "create_org", mission="second")
    assert "first" in Org(target).rules() and "second" not in Org(target).rules()


def test_create_org_needs_a_mission(setup_server):
    server, target = setup_server
    assert "mission" in fails(server, "create_org", mission="  ")
    assert not target.exists()


def test_create_org_path_must_match_the_bound_root(setup_server, tmp_path):
    server, target = setup_server
    other = tmp_path / "elsewhere"
    assert "bound to" in fails(server, "create_org", mission="m", path=str(other))
    assert not other.exists() and not target.exists()
    call(server, "create_org", mission="m", path=str(target))  # the same path is fine
    assert (target / "ORG.md").is_file()


def test_unbound_server_requires_an_absolute_path_and_binds_it_once(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    binding, me = resolve_binding()
    assert binding.root is None and me == ROOT
    server = build_server(binding, me)
    assert "path=<absolute path>" in call(server, "status")
    assert "path" in fails(server, "create_org", mission="m")
    assert "absolute" in fails(server, "create_org", mission="m", path="relative/org")
    assert list(work.iterdir()) == []
    target = tmp_path / "chosen"
    call(server, "create_org", mission="m", path=str(target))
    assert "root (human)" in call(server, "status")
    other = tmp_path / "another"
    assert "already exists" in fails(server, "create_org", mission="m", path=str(other))  # bound for its lifetime
    assert not other.exists()


def test_unbound_server_never_binds_an_existing_org_it_was_not_given(org, tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    server = build_server(*resolve_binding())
    msg = fails(server, "create_org", mission="m", path=str(org.root))
    assert "not bound" in msg and "ORG_ROOT" in msg
    assert "no organization found" in fails(server, "inbox")  # still not using it


def test_org_created_by_someone_else_becomes_usable_without_restart(setup_server):
    server, target = setup_server
    assert "no organization" in fails(server, "inbox")
    Org.init(target, "made by the CLI")
    assert "(no new messages)" in call(server, "inbox")


def test_unbound_instructions_say_path_is_needed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert "create_org(mission=..., path=" in build_server(*resolve_binding()).instructions


# ------------------------------------------------- MCP over stdio, for real
def test_mcp_process_starts_without_an_org_and_creates_one(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    target = tmp_path / "boot" / "org"
    env = {**os.environ, "ORG_ROOT": str(target)}
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        env.pop(var, None)

    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "hirearchy", "mcp"], env=env)
        async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
            init = await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            before = await session.call_tool("inbox", {})
            made = await session.call_tool("create_org", {"mission": "Over the wire"})
            after = await session.call_tool("status", {})
            return init.instructions, tools, before, made, after

    instructions, tools, before, made, after = asyncio.run(go())
    assert tools == ROOT_TOOLS and str(target) in instructions
    assert before.isError and "call create_org" in before.content[0].text
    assert not made.isError and (target / "ORG.md").is_file()
    assert not after.isError and "root (human)" in after.content[0].text
