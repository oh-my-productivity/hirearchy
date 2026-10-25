# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio
import json
import os
import subprocess
import sys

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError
from testkit.mcp_server_world import OrgBinding, build_server, ensure_kiro_profile, resolve_binding

ROOT_TOOLS = {
    "whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health",
    "create_org", "start", "stop", "propose_org", "apply_org", "progress", "quality", "blueprint_example", "observe",
    "services", "define_service", "request", "feedback",  # the client's service tools: root and managers
}
AGENT_TOOLS = ROOT_TOOLS - {"create_org", "start", "stop", "propose_org", "apply_org", "progress", "quality", "blueprint_example", "observe"}


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


def test_no_fallback_to_the_org_in_the_working_directory_when_org_root_is_set(org, tmp_path, monkeypatch):
    monkeypatch.chdir(org.root)  # cwd IS an org...
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "other"))  # ...but the server is bound elsewhere
    binding, me = resolve_binding()
    assert binding.root == (tmp_path / "other").resolve()
    server = build_server(binding, me)
    assert "no organization at" in fails(server, "inbox")


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


# --------------------------------------------------------------- fail closed
def run_mcp(env_extra: dict, drop=()) -> subprocess.CompletedProcess:
    env = {**os.environ, **env_extra}
    for var in drop:
        env.pop(var, None)
    return subprocess.run([sys.executable, "-m", "hirearchy", "mcp"], env=env, stdin=subprocess.DEVNULL,
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
    server = json.loads((agents / f"{name}.json").read_text())["mcpServers"]["hirearchy"]
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
