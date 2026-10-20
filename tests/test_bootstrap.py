"""W1: bootstrap (setup mode, create_org), scheduler control from MCP, isolated per-org profiles, CLI `org:` line."""

import asyncio
import json
import os
import subprocess
import sys

import pytest

from orgmcp.core import ROOT, Org, OrgError
from orgmcp.scheduler import ensure_kiro_profile
from orgmcp.server import OrgBinding, build_server, resolve_binding

ROOT_TOOLS = {
    "whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health",
    "create_org", "start", "stop", "propose_org", "apply_org", "progress", "blueprint_example", "observe",
    "services", "define_service", "request", "feedback",  # the client's service tools: root and managers
}
AGENT_TOOLS = ROOT_TOOLS - {"create_org", "start", "stop", "propose_org", "apply_org", "progress", "blueprint_example", "observe"}


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
                       ("hire", dict(name="a", role="r", charter="c")), ("retire", dict(name="a", reason="r")),
                       ("read", {}), ("write", dict(path="a", content="b")), ("health", {}), ("start", {}),
                       ("stop", {})]:
        assert expected in fails(server, tool, **args), tool
    assert not target.exists()  # nothing was created by the failing calls


def test_setup_mode_whoami_and_status_describe_the_setup(setup_server):
    server, target = setup_server
    for tool in ("whoami", "status"):
        out = call(server, tool)
        assert str(target) in out and "create_org(mission=" in out and "scheduler: stopped" in out


def test_create_org_then_every_tool_works_in_the_same_server(setup_server):
    server, target = setup_server
    out = call(server, "create_org", mission="Study octopuses", default_model="claude-haiku-4.5")
    assert str(target) in out and (target / "ORG.md").is_file()
    assert Org(target).config["default_model"] == "claude-haiku-4.5" and "Study octopuses" in Org(target).rules()
    assert "root (human)" in call(server, "status")
    assert "hired ceo" in call(server, "hire", name="ceo", role="Chief", charter="Lead.", can_hire=True)
    assert "delegated" in call(server, "delegate", to="ceo", title="T", goal="g", acceptance="a", budget=3)
    assert "Address: `root`" in call(server, "whoami") and "scheduler: stopped" in call(server, "whoami")
    assert "(no new messages)" in call(server, "inbox")


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


def test_no_fallback_to_the_org_in_the_working_directory_when_org_root_is_set(org, tmp_path, monkeypatch):
    monkeypatch.chdir(org.root)  # cwd IS an org...
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "other"))  # ...but the server is bound elsewhere
    binding, me = resolve_binding()
    assert binding.root == (tmp_path / "other").resolve()
    server = build_server(binding, me)
    assert "no organization at" in fails(server, "inbox")


def test_org_created_by_someone_else_becomes_usable_without_restart(setup_server):
    server, target = setup_server
    assert "no organization" in fails(server, "inbox")
    Org.init(target, "made by the CLI")
    assert "(no new messages)" in call(server, "inbox")


def test_agent_servers_still_fail_fast_without_an_org(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "missing"))
    monkeypatch.setenv("ORG_AGENT", "ceo")
    with pytest.raises(OrgError, match="not an organization"):
        resolve_binding()
    with pytest.raises(OrgError, match="no organization at"):
        build_server(OrgBinding(tmp_path / "missing"), "ceo")


def test_old_style_env_is_unchanged(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    monkeypatch.setenv("ORG_AGENT", "ceo")
    binding, me = resolve_binding()
    assert me == "ceo" and binding.get().root == org.root
    server = build_server(binding, me)
    assert tool_names(server) == AGENT_TOOLS  # no create_org/start/stop for agents
    assert "Chief executive" in call(server, "whoami") and "scheduler" not in call(server, "whoami")
    assert "scheduler" not in call(server, "status")
    assert "member of a file-based organization" in server.instructions


def test_root_server_on_an_existing_org(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    assert tool_names(server) == ROOT_TOOLS
    assert "ceo [Chief executive]" in call(server, "status") and "scheduler: stopped" in call(server, "status")


def test_non_root_tools_do_not_include_scheduler_control(org):
    assert tool_names(build_server(org, "ceo")) == AGENT_TOOLS


# ------------------------------------------------------------- instructions
def test_root_instructions_name_the_path_and_the_rules(org, setup_server):
    text = build_server(org, ROOT).instructions
    assert str(org.root) in text and "only this organization" in text
    assert "never claim" in text.lower() and "instead of substituting" in text
    server, target = setup_server
    assert str(target) in server.instructions and "create_org(mission=...)" in server.instructions


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
        params = StdioServerParameters(command=sys.executable, args=["-m", "orgmcp", "mcp"], env=env)
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


# --------------------------------------------------------------- fail closed
def run_mcp(env_extra: dict, drop=()) -> subprocess.CompletedProcess:
    env = {**os.environ, **env_extra}
    for var in drop:
        env.pop(var, None)
    return subprocess.run([sys.executable, "-m", "orgmcp", "mcp"], env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=60)


def test_require_agent_refuses_to_act_as_root(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    monkeypatch.setenv("ORG_REQUIRE_AGENT", "1")
    with pytest.raises(OrgError, match="ORG_REQUIRE_AGENT"):
        resolve_binding()
    monkeypatch.setenv("ORG_AGENT", "root")  # naming root does not help
    with pytest.raises(OrgError, match="ORG_REQUIRE_AGENT"):
        resolve_binding()
    monkeypatch.setenv("ORG_AGENT", "ceo")
    assert resolve_binding()[1] == "ceo"
    monkeypatch.setenv("ORG_REQUIRE_AGENT", "0")  # explicit off
    monkeypatch.delenv("ORG_AGENT")
    assert resolve_binding()[1] == ROOT


def test_a_profile_used_outside_the_scheduler_fails_closed(org, tmp_path):
    agents = tmp_path / "agents"
    name = ensure_kiro_profile([], agents, org=org)
    server = json.loads((agents / f"{name}.json").read_text())["mcpServers"]["orgmcp"]
    # What kiro does when a subagent borrows the profile: the server's own env, no ORG_AGENT.
    done = subprocess.run([server["command"], *server["args"]], env={**os.environ, **server["env"]},
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    assert done.returncode != 0 and "ORG_REQUIRE_AGENT" in done.stderr and "Refusing to act as root" in done.stderr
    assert not done.stdout  # nothing was served
    # The scheduler's run adds ORG_AGENT through the process environment and the same entry works.
    ok = subprocess.run([server["command"], *server["args"]], env={**os.environ, **server["env"], "ORG_AGENT": "ceo"},
                        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    assert ok.returncode == 0 and "ORG_REQUIRE_AGENT" not in ok.stderr


def test_old_style_server_process_still_starts(org):
    done = run_mcp({"ORG_ROOT": str(org.root), "ORG_AGENT": "ceo"}, drop=["ORG_REQUIRE_AGENT"])
    assert done.returncode == 0 and "error" not in done.stderr.lower()
    done = run_mcp({"ORG_ROOT": str(org.root)}, drop=["ORG_REQUIRE_AGENT", "ORG_AGENT"])  # root, existing org
    assert done.returncode == 0 and "error" not in done.stderr.lower()


def test_agent_process_without_org_fails_fast(tmp_path):
    done = run_mcp({"ORG_ROOT": str(tmp_path / "nope"), "ORG_AGENT": "ceo"})
    assert done.returncode == 1 and "not an organization" in done.stderr
