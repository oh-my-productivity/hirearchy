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
from orgmcp.core import Org, OrgError
from orgmcp.daemon.testing import FixedSchedulerCommand, RecordingSchedulerCommand
from orgmcp.scheduler import (
    _looks_like_scheduler_of, describe_scheduler, ensure_kiro_profile, kiro_profile_name, kiro_runner,
    scheduler_state, start_scheduler, stop_scheduler,
)
from orgmcp.server import build_server, resolve_binding


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)


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


def test_command_line_verification():
    root = Path("/orgs/one")
    ok = [
        "/v/bin/python /v/bin/orgmcp --root /orgs/one run",
        "/v/bin/orgmcp --root /orgs/one run --max-runs 3",
        "/usr/bin/python3 -m orgmcp run --until-idle",  # started from inside the org (no --root)
        "python3 /x/serve.py run /orgs/one",
    ]
    bad = [
        "sleep 60", "vim /orgs/one/ORG.md", "/v/bin/orgmcp mcp", "/v/bin/orgmcp --root /orgs/two run",
        "/v/bin/orgmcp --root org run", "python -m http.server run", "",
    ]
    assert all(_looks_like_scheduler_of(c, root) for c in ok)
    assert not any(_looks_like_scheduler_of(c, root) for c in bad)


def test_command_line_verification_follows_symlinks_and_rejects_other_dirs(tmp_path):
    real = tmp_path / "real" / "org"
    real.mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "real")  # like /tmp -> /private/tmp: the command line has one spelling, the org another
    other = tmp_path / "other"
    other.mkdir()
    assert _looks_like_scheduler_of(f"/v/bin/orgmcp --root {link}/org run --until-idle", real)
    assert _looks_like_scheduler_of(f"/v/bin/orgmcp --root={link}/org run", real)
    assert not _looks_like_scheduler_of(f"/v/bin/orgmcp --root {other} run", real)
    assert not _looks_like_scheduler_of(f"/v/bin/orgmcp --root {link}/org mcp", real)


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


# ------------------------------------------------------------------ CLI
def org_lines(capsys) -> list[str]:
    return [line for line in capsys.readouterr().err.splitlines() if line.startswith("org: ")]


def test_mutating_cli_commands_print_the_org_first(org, tmp_path, capsys):
    root = str(org.root)
    target = tmp_path / "newly"
    main(["init", str(target), "--mission", "m"])
    assert org_lines(capsys) == [f"org: {target.resolve()}"]

    for argv in (
        ["hire", "ceo", "dev", "--role", "Dev", "--charter", "Code."],
        ["task", "ceo", "--title", "T", "--goal", "g", "--acceptance", "a"],
        ["send", "ceo", "hello"],
        ["resume", "ceo"],
        ["review"],
        ["run", "--once"],
        ["inbox"],
    ):
        main(["--root", root, *argv])
        assert org_lines(capsys) == [f"org: {org.root}"], argv


def test_read_only_cli_commands_stay_quiet(org, capsys):
    for argv in (["status"], ["health"], ["review", "--dry-run"], ["inbox", "--keep"]):
        main(["--root", str(org.root), *argv])
        assert org_lines(capsys) == [], argv


def test_org_line_uses_the_discovered_org_and_comes_before_errors(org, monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(org.root)  # cwd discovery is unchanged
    main(["send", "ceo", "hi"])
    assert org_lines(capsys) == [f"org: {org.root}"]
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path / "nowhere"), "send", "ceo", "hi"])
    err = capsys.readouterr().err
    assert err.index("org: ") < err.index("error: ")


def test_module_entry_point_matches_the_script():
    done = subprocess.run([sys.executable, "-m", "orgmcp", "--help"], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and "usage: orgmcp" in done.stdout
