"""W1: bootstrap (setup mode, create_org), scheduler control from MCP, isolated per-org profiles, CLI `org:` line."""

import asyncio
import dataclasses
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from orgmcp.cli import main
from orgmcp.core import ROOT, Org, OrgError
from orgmcp.daemon.testing import FixedSchedulerCommand, RecordingSchedulerCommand
from orgmcp.scheduler import (
    describe_scheduler,
    ensure_kiro_profile,
    kiro_profile_name,
    kiro_runner,
    scheduler_state,
    start_scheduler,
    stop_scheduler,
)
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


@pytest.fixture
def reap_schedulers():
    """Never leave a scheduler behind, whatever a test did."""
    orgs: list[Org] = []
    yield orgs
    for o in orgs:
        try:
            os.kill(int((o.root / ".runtime" / "scheduler.pid").read_text()), signal.SIGKILL)
        except (OSError, ValueError):
            pass


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


# ------------------------------------------------------------ start / stop
def test_start_and_stop_a_detached_scheduler(org, reap_schedulers, monkeypatch):
    reap_schedulers.append(org)
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    server = build_server(*resolve_binding())
    assert "scheduler: stopped" in call(server, "status")
    out = call(server, "start", max_runs=0, until_done=False)  # the real scheduler command; at most 0 runs, so kiro is never started
    pid = int(re.search(r"pid (\d+)", out).group(1))
    assert (org.root / ".runtime" / "scheduler.pid").read_text().strip() == str(pid)
    assert re.search(rf"scheduler: running \(pid {pid}, since \d{{4}}-", call(server, "status"))
    assert f"pid {pid}" in call(server, "whoami")
    assert os.getsid(pid) == pid  # detached: its own session
    assert (org.root / ".runtime" / "scheduler.log").is_file()
    assert ".runtime/scheduler.log" in (org.root / ".gitignore").read_text().split()
    again = fails(server, "start")
    assert "already running" in again and str(pid) in again
    stopped = call(server, "stop")
    assert f"stopped (pid {pid})" in stopped
    deadline = time.time() + 5
    while scheduler_state(org).state != "stopped" and time.time() < deadline:
        time.sleep(0.05)
    assert "scheduler: stopped" in call(server, "status")
    assert call(server, "stop") == "no scheduler is running for this org"
    assert not (org.root / ".runtime" / "scheduler.pid").exists()  # the scheduler shut down cleanly
    call(server, "start", max_runs=0, until_done=False)  # and can be started again
    call(server, "stop")


def test_start_passes_max_runs_and_logs_to_the_runtime_dir(org, reap_schedulers):
    reap_schedulers.append(org)
    seen = {}
    spy = RecordingSchedulerCommand(org.runtime.scheduler_command)
    org.runtime = dataclasses.replace(org.runtime, scheduler_command=spy)
    start_scheduler(org, max_runs=3)
    seen["cmd"] = spy.issued[0]
    assert seen["cmd"][-5:] == ["--root", str(org.root), "run", "--max-runs", "3"]
    assert Path(seen["cmd"][0]).name == "orgmcp"
    assert "scheduler started" in (org.root / ".runtime" / "scheduler.log").read_text()
    stop_scheduler(org)


def test_start_reports_a_scheduler_that_dies_at_once(org):
    dies = FixedSchedulerCommand([sys.executable, "-c", "import sys; print('boom'); sys.exit(3)"])
    org.runtime = dataclasses.replace(org.runtime, scheduler_command=dies)
    with pytest.raises(OrgError, match=r"exited at once \(exit 3\)[\s\S]*boom"):
        start_scheduler(org)


def test_start_refuses_a_negative_cap(org):
    with pytest.raises(OrgError, match="max_runs"):
        start_scheduler(org, -1)


@pytest.fixture
def foreign_process():
    proc = subprocess.Popen(["sleep", "60"])
    yield proc
    proc.kill()
    proc.wait()


def test_stop_never_signals_a_foreign_pid(org, foreign_process):
    pidfile = org.root / ".runtime" / "scheduler.pid"
    pidfile.write_text(str(foreign_process.pid))  # stale pidfile whose pid was reused by something else
    assert scheduler_state(org).state == "unverified"
    with pytest.raises(OrgError, match="not verified to be this org's scheduler"):
        stop_scheduler(org)
    with pytest.raises(OrgError, match="not starting"):
        start_scheduler(org)
    assert foreign_process.poll() is None  # not signalled
    assert "not trusted" in describe_scheduler(org) and str(foreign_process.pid) in describe_scheduler(org)
    assert pidfile.read_text() == str(foreign_process.pid)  # and the pidfile was left alone


def test_stop_refuses_a_scheduler_of_another_org(org, tmp_path):
    other = tmp_path / "other-org"
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "--root", str(other), "run"])
    try:
        (org.root / ".runtime" / "scheduler.pid").write_text(str(proc.pid))
        with pytest.raises(OrgError, match="not verified"):
            stop_scheduler(org)
        assert proc.poll() is None
    finally:
        proc.kill()
        proc.wait()


def test_stale_or_garbage_pidfile_means_stopped_and_does_not_block_start(org, reap_schedulers):
    reap_schedulers.append(org)
    pidfile = org.root / ".runtime" / "scheduler.pid"
    dead = subprocess.Popen(["true"])
    dead.wait()
    for text in (str(dead.pid), "garbage", "", "1", "-5"):
        pidfile.write_text(text)
        assert scheduler_state(org).state == "stopped", text
    pidfile.write_text(str(dead.pid))
    start_scheduler(org, max_runs=0)
    assert scheduler_state(org).state == "running"
    stop_scheduler(org)


# --------------------------------------------------------- isolated profiles
def test_profile_name_is_per_org_lowercase_and_stable(tmp_path):
    a, b = tmp_path / "a" / "org", tmp_path / "b" / "org"
    names = {kiro_profile_name(a, []), kiro_profile_name(b, [])}
    assert len(names) == 2  # same directory name, different org: different profiles
    assert kiro_profile_name(a, []) == kiro_profile_name(str(a), [])
    for name in (*names, kiro_profile_name(a, ["web_fetch", "Read"])):
        assert re.fullmatch(r"orgmcp-[a-z0-9-]+", name), name
    assert re.fullmatch(r"orgmcp-a-org-[0-9a-f]{6}", kiro_profile_name(a, []))
    assert kiro_profile_name(a, ["write", "read"]) == kiro_profile_name(a, ["read", "write"]) == \
        kiro_profile_name(a, []) + "-read-write"
    weird = tmp_path / "My Org!! (Ünï)"
    assert re.fullmatch(r"orgmcp-[a-z0-9-]+-[0-9a-f]{6}", kiro_profile_name(weird, []))


def test_profile_is_internal_and_bound_to_its_org(org, tmp_path):
    agents = tmp_path / "agents"
    agents.mkdir()
    legacy = agents / "orgmcp.json"
    legacy.write_text('{"name": "orgmcp", "legacy": true}')
    name = ensure_kiro_profile(["read", "shell"], agents, org=org)
    assert name == kiro_profile_name(org.root, ["read", "shell"])
    profile = json.loads((agents / f"{name}.json").read_text())
    assert profile["name"] == name
    assert profile["description"].startswith(f"internal: used by the orgmcp scheduler for {org.root}; not a general-purpose agent")
    server = profile["mcpServers"]["orgmcp"]
    assert server["env"] == {"ORG_ROOT": str(org.root), "ORG_REQUIRE_AGENT": "1"}
    assert "ORG_AGENT" not in server["env"]  # identity comes from the scheduler's process environment
    assert server["args"][-1] == "mcp"
    assert profile["tools"] == ["@orgmcp", "read", "shell"] and profile["includeMcpJson"] is False
    assert legacy.read_text() == '{"name": "orgmcp", "legacy": true}'  # the global profile is never touched
    assert sorted(p.name for p in agents.iterdir()) == sorted(["orgmcp.json", f"{name}.json"])


def test_kiro_runner_uses_the_per_org_profile_and_keeps_the_scheduler_env(org, isolated_kiro):
    cmd, _, env = kiro_runner()(org, "ceo", "P")
    name = kiro_profile_name(org.root, [])
    assert cmd[:5] == ["kiro-cli", "chat", "--no-interactive", "--agent", name]
    assert env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)
    assert (isolated_kiro / ".kiro" / "agents" / f"{name}.json").is_file()
    assert not (isolated_kiro / ".kiro" / "agents" / "orgmcp.json").exists()


def test_cli_kiro_profile_writes_the_org_profile(org, isolated_kiro, capsys):
    main(["--root", str(org.root), "kiro-profile", "--tools", "read"])
    name = kiro_profile_name(org.root, ["read"])
    assert (isolated_kiro / ".kiro" / "agents" / f"{name}.json").is_file()
    assert f"wrote ~/.kiro/agents/{name}.json" in capsys.readouterr().out


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
