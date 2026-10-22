"""``wire_kiro``: the runtime has the ten kiro ports, built from the layout, the charters, the access ports and the one environment of the runtime."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import pytest
import hirearchy.kiro
from hirearchy.agents import CharterReader
from hirearchy.agents.testing import MemoryAgents
from hirearchy.app import Org, wire_kiro, wiring
from hirearchy.app.wire_cli import run_cli
from hirearchy.daemon._watch import STARTUP_SECONDS
from hirearchy.kernel import ROOT, Environment
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.kiro import (
    READINESS_TIMEOUT, ConfinementPolicy, KiroCli, KiroHomeAudit, KiroPlaces, KiroStateDirs, McpServerLocator, ProfileProvisioner, ProfileStore,
    RunCommandBuilder, RuntimeReadiness,
)
from hirearchy.kiro._cli import SubprocessKiroCli
from hirearchy.kiro._confinement import KiroConfinementPolicy
from hirearchy.kiro._env import run_environment
from hirearchy.kiro._mcp_locator import VenvMcpServerLocator
from hirearchy.kiro._places import StateDirPlaces
from hirearchy.kiro._profiles import FsProfileStore
from hirearchy.kiro._provisioner import OrgProfileProvisioner
from hirearchy.kiro._readiness import KiroReadiness
from hirearchy.kiro._runner import KiroRunCommandBuilder
from hirearchy.kiro._state import FsKiroState
from hirearchy.kiro.testing import MemoryProfileStore, StaticMcpServerLocator
from hirearchy.settings import DEFAULT_MODEL

LAUNCH = str((Path(hirearchy.kiro.__file__).parent / "_launch.py").resolve())


def charter(**meta: object) -> str:
    return "---\n" + "".join(f"{k}: {json.dumps(v)}\n" for k, v in {"role": "R", **meta}.items()) + "---\nbody\n"


def test_the_runtime_has_the_real_kiro_parts(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.confinement_policy, KiroConfinementPolicy) and isinstance(runtime.confinement_policy, ConfinementPolicy)
    assert isinstance(runtime.profile_store, FsProfileStore) and isinstance(runtime.profile_store, ProfileStore)
    assert isinstance(runtime.profile_provisioner, OrgProfileProvisioner) and isinstance(runtime.profile_provisioner, ProfileProvisioner)
    assert isinstance(runtime.mcp_locator, VenvMcpServerLocator) and isinstance(runtime.mcp_locator, McpServerLocator)
    assert isinstance(runtime.run_command_builder, KiroRunCommandBuilder) and isinstance(runtime.run_command_builder, RunCommandBuilder)
    assert isinstance(runtime.kiro_places, StateDirPlaces) and isinstance(runtime.kiro_places, KiroPlaces)
    assert isinstance(runtime.kiro_state_dirs, FsKiroState) and isinstance(runtime.kiro_state_dirs, KiroStateDirs)
    assert isinstance(runtime.kiro_home_audit, FsKiroState) and isinstance(runtime.kiro_home_audit, KiroHomeAudit)
    assert isinstance(runtime.kiro_cli, SubprocessKiroCli) and isinstance(runtime.kiro_cli, KiroCli)
    assert isinstance(runtime.runtime_readiness, KiroReadiness) and isinstance(runtime.runtime_readiness, RuntimeReadiness)


def test_building_the_ports_touches_nothing(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "org")
    for port in (
        runtime.profile_provisioner, runtime.run_command_builder, runtime.profile_store, runtime.kiro_places, runtime.kiro_state_dirs,
        runtime.kiro_home_audit, runtime.kiro_cli, runtime.runtime_readiness,
    ):
        assert port is not None
    assert not (tmp_path / "org").exists()
    assert not runtime.kiro_places.roots()[0].exists() and not runtime.kiro_places.roots()[1].exists()


def test_the_places_follow_the_environment_of_the_runtime(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "org", {Environment: DictEnvironment({"HIREARCHY_STATE_DIR": str(tmp_path / "state")}, home=tmp_path / "home")})
    state = Path(str(tmp_path / "state")).resolve()
    assert runtime.kiro_places.roots() == (state / "kiro-home", state / "kiro-cwd")
    assert runtime.kiro_places.home().parent == state / "kiro-home"


def test_the_profile_store_is_under_the_kiro_home_and_asks_the_environment_for_it_on_every_use(tmp_path: Path) -> None:
    environment = DictEnvironment(home=tmp_path / "one")
    runtime = wiring.open_runtime(tmp_path / "org", {Environment: environment})
    first = runtime.kiro_places.home() / "agents"
    runtime.profile_store.write("hirearchy-a-123456", {"name": "first"})
    environment._home = tmp_path / "two"  # the home directory changes between two calls
    second = runtime.kiro_places.home() / "agents"
    assert second != first and "two" in second.parts
    assert runtime.profile_store.read("hirearchy-a-123456") is None
    runtime.profile_store.write("hirearchy-a-123456", {"name": "second"})
    assert (first / "hirearchy-a-123456.json").is_file() and (second / "hirearchy-a-123456.json").is_file()
    assert not (tmp_path / "one" / ".kiro").exists() and not (tmp_path / "two" / ".kiro").exists()


def test_the_default_store_follows_the_home_of_the_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = wiring.open_runtime(tmp_path / "org")
    monkeypatch.setenv("HOME", str(tmp_path / "first"))
    first = runtime.kiro_places.home() / "agents"
    runtime.profile_store.write("hirearchy-a-123456", {"name": "x"})
    monkeypatch.setenv("HOME", str(tmp_path / "second"))
    assert runtime.profile_store.read("hirearchy-a-123456") is None
    assert (first / "hirearchy-a-123456.json").is_file() and "first" in first.parts


def test_the_provisioner_is_the_one_of_the_organization_of_the_runtime(tmp_path: Path) -> None:
    home, org = tmp_path / "home", tmp_path / "team" / "org"
    runtime = wiring.open_runtime(org, {Environment: DictEnvironment(home=home), McpServerLocator: StaticMcpServerLocator()})
    name = runtime.profile_provisioner.ensure_profile(["shell"])
    assert name.startswith("hirearchy-team-org-") and name.endswith("-shell")
    profile = json.loads((runtime.kiro_places.home() / "agents" / f"{name}.json").read_text(encoding="utf-8"))
    assert profile["mcpServers"]["hirearchy"]["env"] == {"ORG_ROOT": str(org), "ORG_REQUIRE_AGENT": "1"}
    assert profile["mcpServers"]["hirearchy"]["command"] == "/venv/bin/hirearchy"
    assert not (home / ".kiro").exists()


def test_the_run_command_builder_reads_the_charters_the_access_ports_and_the_environment_of_the_runtime(tmp_path: Path) -> None:
    org, home = tmp_path / "org", tmp_path / "home"
    org.mkdir()
    (org / "ORG.md").write_text("---\ndefault_model: m-org\n---\nrules\n", encoding="utf-8")
    charters = MemoryAgents()
    charters.put("dev/AGENT.md", charter(tools=["shell"], model="m-dev"))
    charters.put("ops/AGENT.md", charter(tools=[]))
    runtime = wiring.open_runtime(
        org, {CharterReader: charters, Environment: DictEnvironment({"KEEP": "me"}, home=home), McpServerLocator: StaticMcpServerLocator()}
    )
    dev, ops = runtime.run_command_builder.build("dev", "P"), runtime.run_command_builder.build("ops", "P")
    profile = runtime.profile_provisioner.profile_name(["shell"])
    assert dev.argv == (
        sys.executable, "-I", "-S", LAUNCH, "--start-deadline", "60", "--",
        "kiro-cli", "chat", "--no-interactive", "--agent", profile, "--model", "m-dev", "--v3", "--require-mcp-startup", "--output-format", "stream-json",
    )
    assert ops.argv[ops.argv.index("--model") + 1] == "m-org"
    places = runtime.kiro_places
    assert dev.cwd == places.scratch("dev") and ops.cwd == places.scratch("ops") and dev.cwd.is_dir() and not any(dev.cwd.iterdir())
    assert dict(dev.env) == {**run_environment({"KEEP": "me"}, places.home()), "ORG_ROOT": str(org), "ORG_AGENT": "dev"}
    assert dev.env["KIRO_HOME"] == str(places.home()) and dev.env["KEEP"] == "me"
    assert (places.home() / "agents" / f"{profile}.json").is_file()


def test_run_command_builder_uses_the_environment_of_the_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``hirearchy run --kiro BIN`` builds its command over the environment of the runtime, not over a new one of the process."""
    monkeypatch.setenv("ONLY_IN_THE_PROCESS", "1")
    org = tmp_path / "org"
    org.mkdir()
    (org / "ORG.md").write_text("---\nmax_depth: 4\n---\nrules\n", encoding="utf-8")
    charters = MemoryAgents()
    charters.put("dev/AGENT.md", charter(tools=[]))
    runtime = wiring.open_runtime(
        org, {CharterReader: charters, Environment: DictEnvironment({"ONLY_IN_THE_RUNTIME": "1"}, home=tmp_path / "home"), McpServerLocator: StaticMcpServerLocator()}
    )
    command = wire_kiro.run_command_builder(runtime, "my-kiro", runtime.profile_provisioner).build("dev", "P")
    assert command.env["ONLY_IN_THE_RUNTIME"] == "1" and "ONLY_IN_THE_PROCESS" not in command.env
    assert command.argv[7] == "my-kiro" and command.cwd == runtime.kiro_places.scratch("dev")


def test_an_override_of_the_store_is_the_one_the_provisioner_writes_to(tmp_path: Path) -> None:
    store = MemoryProfileStore()
    runtime = wiring.open_runtime(tmp_path, {ProfileStore: store, McpServerLocator: StaticMcpServerLocator()})
    name = runtime.profile_provisioner.ensure_profile([])
    assert list(store.files) == [name] and not (tmp_path / "home").exists()
    assert runtime.profile_store is store


def test_the_default_model_is_the_built_in_one_without_a_setting(tmp_path: Path) -> None:
    org = tmp_path / "org"
    org.mkdir()
    (org / "ORG.md").write_text("---\nmax_depth: 4\n---\nrules\n", encoding="utf-8")
    charters = MemoryAgents()
    charters.put("dev/AGENT.md", charter())
    runtime = wiring.open_runtime(org, {CharterReader: charters, ProfileStore: MemoryProfileStore(), McpServerLocator: StaticMcpServerLocator()})
    command = runtime.run_command_builder.build("dev", "P")
    assert command.argv[command.argv.index("--model") + 1] == DEFAULT_MODEL


def test_the_launcher_is_the_running_interpreter_isolated_and_the_script_of_the_kiro_package() -> None:
    assert wire_kiro.launcher() == (sys.executable, "-I", "-S", LAUNCH)


def test_the_places_use_the_platform_of_the_process(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "org", {Environment: DictEnvironment(home=tmp_path / "home")})
    state = "Library/Application Support/hirearchy" if sys.platform == "darwin" else ".local/state/hirearchy"
    assert runtime.kiro_places.roots()[0] == (tmp_path / "home" / state / "kiro-home").resolve()


def test_readiness_fits_in_the_start_window() -> None:
    """Three kiro-cli calls of ``READINESS_TIMEOUT`` and 2.5 s for the scheduler process to start Python and check the state must end inside the
    seconds the ``start`` tool waits for a new scheduler (docs/design/kiro-runtime-v3.md section 9)."""
    assert 3 * READINESS_TIMEOUT + 2.5 <= STARTUP_SECONDS


def test_nothing_is_written_to_the_users_kiro_agents(tmp_path: Path, isolated_kiro: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Building a run and ``kiro-profile`` write the profiles into the kiro home of the organization, never into ``~/.kiro/agents`` (the fixture's HOME)."""
    org = Org.init(tmp_path / "org", "mission")
    org.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    command = org.runtime.run_command_builder.build("ceo", "P")
    run_cli(["--root", str(org.root), "kiro-profile", "--tools", "shell"])
    written = capsys.readouterr().out
    places = org.runtime.kiro_places
    assert not (Path.home() / ".kiro" / "agents").exists() and not (isolated_kiro / ".kiro").exists()
    assert str(places.home() / "agents") in written
    assert sorted(p.suffix for p in (places.home() / "agents").iterdir()) == [".json", ".json"] and command.cwd == places.scratch("ceo")


@pytest.mark.parametrize(
    "port", [ConfinementPolicy, ProfileStore, ProfileProvisioner, McpServerLocator, RunCommandBuilder, KiroPlaces, KiroStateDirs, KiroHomeAudit, KiroCli, RuntimeReadiness]
)
def test_every_kiro_port_is_provided(port: type) -> None:
    assert port in wiring.providers()
    assert cast(object, port) in wiring.runtime_ports().values()
