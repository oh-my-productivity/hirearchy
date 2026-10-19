"""``wire_kiro``: the runtime has the five kiro ports, built from the layout, the charters, the access ports and the environment of the runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from orgmcp.agents import CharterReader
from orgmcp.agents.testing import MemoryAgents
from orgmcp.app import wiring
from orgmcp.kernel import Environment
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.kiro import ConfinementPolicy, McpServerLocator, ProfileProvisioner, ProfileStore, RunCommandBuilder
from orgmcp.kiro._confinement import KiroConfinementPolicy
from orgmcp.kiro._mcp_locator import VenvMcpServerLocator
from orgmcp.kiro._profiles import FsProfileStore
from orgmcp.kiro._provisioner import OrgProfileProvisioner
from orgmcp.kiro._runner import KiroRunCommandBuilder
from orgmcp.kiro.testing import MemoryProfileStore, StaticMcpServerLocator
from orgmcp.settings import DEFAULT_MODEL


def charter(**meta: object) -> str:
    return "---\n" + "".join(f"{k}: {json.dumps(v)}\n" for k, v in {"role": "R", **meta}.items()) + "---\nbody\n"


def test_the_runtime_has_the_real_kiro_parts(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.confinement_policy, KiroConfinementPolicy) and isinstance(runtime.confinement_policy, ConfinementPolicy)
    assert isinstance(runtime.profile_store, FsProfileStore) and isinstance(runtime.profile_store, ProfileStore)
    assert isinstance(runtime.profile_provisioner, OrgProfileProvisioner) and isinstance(runtime.profile_provisioner, ProfileProvisioner)
    assert isinstance(runtime.mcp_locator, VenvMcpServerLocator) and isinstance(runtime.mcp_locator, McpServerLocator)
    assert isinstance(runtime.run_command_builder, KiroRunCommandBuilder) and isinstance(runtime.run_command_builder, RunCommandBuilder)


def test_building_the_ports_touches_nothing(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "org")
    for port in (runtime.profile_provisioner, runtime.run_command_builder, runtime.profile_store):
        assert port is not None
    assert not (tmp_path / "org").exists()


def test_the_profile_store_asks_the_environment_for_the_home_on_every_use(tmp_path: Path) -> None:
    environment = DictEnvironment(home=tmp_path / "one")
    runtime = wiring.open_runtime(tmp_path / "org", {Environment: environment})
    runtime.profile_store.write("orgmcp-a-123456", {"name": "first"})
    environment._home = tmp_path / "two"  # the home directory changes between two calls
    assert runtime.profile_store.read("orgmcp-a-123456") is None
    runtime.profile_store.write("orgmcp-a-123456", {"name": "second"})
    assert (tmp_path / "one" / ".kiro" / "agents" / "orgmcp-a-123456.json").is_file()
    assert (tmp_path / "two" / ".kiro" / "agents" / "orgmcp-a-123456.json").is_file()


def test_the_default_store_follows_the_home_of_the_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = wiring.open_runtime(tmp_path / "org")
    monkeypatch.setenv("HOME", str(tmp_path / "first"))
    runtime.profile_store.write("orgmcp-a-123456", {"name": "x"})
    monkeypatch.setenv("HOME", str(tmp_path / "second"))
    assert runtime.profile_store.read("orgmcp-a-123456") is None
    assert (tmp_path / "first" / ".kiro" / "agents" / "orgmcp-a-123456.json").is_file()


def test_the_provisioner_is_the_one_of_the_organization_of_the_runtime(tmp_path: Path) -> None:
    home, org = tmp_path / "home", tmp_path / "team" / "org"
    runtime = wiring.open_runtime(org, {Environment: DictEnvironment(home=home), McpServerLocator: StaticMcpServerLocator()})
    name = runtime.profile_provisioner.ensure_profile(["shell"])
    assert name.startswith("orgmcp-team-org-") and name.endswith("-shell")
    profile = json.loads((home / ".kiro" / "agents" / f"{name}.json").read_text(encoding="utf-8"))
    assert profile["mcpServers"]["orgmcp"]["env"] == {"ORG_ROOT": str(org), "ORG_REQUIRE_AGENT": "1"}
    assert profile["mcpServers"]["orgmcp"]["command"] == "/venv/bin/orgmcp"


def test_the_run_command_builder_reads_the_charters_the_access_ports_and_the_environment_of_the_runtime(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\ndefault_model: m-org\n---\nrules\n", encoding="utf-8")
    charters = MemoryAgents()
    charters.put("dev/AGENT.md", charter(tools=["shell"], model="m-dev"))
    charters.put("ops/AGENT.md", charter(tools=[]))
    runtime = wiring.open_runtime(
        tmp_path, {CharterReader: charters, Environment: DictEnvironment({"KEEP": "me"}, home=tmp_path / "home"), McpServerLocator: StaticMcpServerLocator()}
    )
    dev, ops = runtime.run_command_builder.build("dev", "P"), runtime.run_command_builder.build("ops", "P")
    assert dev.argv[:4] == ("kiro-cli", "chat", "--no-interactive", "--agent") and dev.argv[-2:] == ("--model", "m-dev")
    assert ops.argv[-2:] == ("--model", "m-org") and ops.cwd == tmp_path / "ops"
    assert dict(dev.env) == {"KEEP": "me", "ORG_ROOT": str(tmp_path), "ORG_AGENT": "dev"}
    assert (tmp_path / "home" / ".kiro" / "agents" / f"{dev.argv[4]}.json").is_file()


def test_an_override_of_the_store_is_the_one_the_provisioner_writes_to(tmp_path: Path) -> None:
    store = MemoryProfileStore()
    runtime = wiring.open_runtime(tmp_path, {ProfileStore: store, McpServerLocator: StaticMcpServerLocator()})
    name = runtime.profile_provisioner.ensure_profile([])
    assert list(store.files) == [name] and not (tmp_path / "home").exists()
    assert runtime.profile_store is store


def test_the_default_model_is_the_built_in_one_without_a_setting(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\nmax_depth: 4\n---\nrules\n", encoding="utf-8")
    charters = MemoryAgents()
    charters.put("dev/AGENT.md", charter())
    runtime = wiring.open_runtime(tmp_path, {CharterReader: charters, ProfileStore: MemoryProfileStore(), McpServerLocator: StaticMcpServerLocator()})
    assert runtime.run_command_builder.build("dev", "P").argv[-2:] == ("--model", DEFAULT_MODEL)


@pytest.mark.parametrize("port", [ConfinementPolicy, ProfileStore, ProfileProvisioner, McpServerLocator, RunCommandBuilder])
def test_every_kiro_port_is_provided(port: type) -> None:
    assert port in wiring.providers()
    assert cast(object, port) in wiring.runtime_ports().values()
