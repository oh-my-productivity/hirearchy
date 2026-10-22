"""``KiroRunCommandBuilder`` asks the provisioner for a profile of the grant and the access of every agent (V3: all are confined)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from hirearchy.access.testing import StaticAccess
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.kiro import FILE_TOOLS, ProfileProvisioner, RunCommandBuilder
from hirearchy.kiro._runner import KiroRunCommandBuilder


class RecordingProvisioner(ProfileProvisioner):
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def profile_name(self, tools: Sequence[str]) -> str:
        return "profile-" + "-".join(tools)

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None
    ) -> str:
        self.calls.append((list(tools), {k: v for k, v in (("workspace", workspace), ("inputs", inputs)) if v}))
        return self.profile_name(tools)


def builder(access: StaticAccess, provisioner: RecordingProvisioner, kiro_bin: str = "kiro-cli") -> KiroRunCommandBuilder:
    return KiroRunCommandBuilder(kiro_bin, OrgPaths(access.root), access.agents, access, access, provisioner, DictEnvironment({"A": "1"}))


def test_it_is_a_run_command_builder() -> None:
    assert isinstance(builder(StaticAccess(), RecordingProvisioner()), RunCommandBuilder)
    assert FILE_TOOLS == ("read", "write")


def test_the_binary_is_the_one_it_was_given() -> None:
    access = StaticAccess()
    access.put_agent("dev", {"role": "R"})
    assert builder(access, RecordingProvisioner(), "/opt/kiro/bin/kiro-cli").build("dev", "P").argv[0] == "/opt/kiro/bin/kiro-cli"


def test_an_agent_with_the_built_in_read_or_write_asks_for_a_profile_with_its_access() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["write", "shell"], "workspace": "/w/dev", "inputs": ["/w/in"]})
    command = builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [(["write", "shell"], {"workspace": Path("/w/dev"), "inputs": [Path("/w/in")]})]
    assert command.argv[4] == "profile-write-shell"


def test_every_agent_asks_with_its_workspace_and_inputs() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["shell", "web_search"], "workspace": "/w/dev"})
    builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [(["shell", "web_search"], {"workspace": Path("/w/dev")})]


def test_a_charter_without_tools_asks_for_the_profile_without_tools() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": None})
    builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [([], {})]


def test_a_former_legacy_charter_asks_for_its_confined_profile() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("old", {"role": "R", "tools": ["read", "shell"]})  # built-in read, no workspace, no ``inputs`` key
    builder(access, provisioner).build("old", "P")
    assert provisioner.calls == [(["read", "shell"], {})]  # the provisioner confines it to the organization


def test_the_tools_are_passed_in_the_order_of_the_charter() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["web_search", "read"], "inputs": []})
    builder(access, provisioner).build("dev", "P")
    assert provisioner.calls[0][0] == ["web_search", "read"]
