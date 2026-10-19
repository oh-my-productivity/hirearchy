"""``KiroRunCommandBuilder`` asks the provisioner exactly as the scheduler's ``kiro_runner`` did: confined only for built-in read/write."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from orgmcp.access.testing import StaticAccess
from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.kiro import FILE_TOOLS, ProfileProvisioner, RunCommandBuilder
from orgmcp.kiro._runner import KiroRunCommandBuilder

from ._support import red


class RecordingProvisioner(ProfileProvisioner):
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def profile_name(self, tools: Sequence[str]) -> str:
        return "profile-" + "-".join(tools)

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None, confine: bool = False
    ) -> str:
        self.calls.append((list(tools), {k: v for k, v in (("workspace", workspace), ("inputs", inputs), ("confine", confine)) if v}))
        return self.profile_name(tools)


def builder(access: StaticAccess, provisioner: RecordingProvisioner, kiro_bin: str = "kiro-cli") -> KiroRunCommandBuilder:
    return KiroRunCommandBuilder(kiro_bin, OrgPaths(access.root), access.agents, access, access, provisioner, DictEnvironment({"A": "1"}))


def test_it_is_a_run_command_builder() -> None:
    assert isinstance(builder(StaticAccess(), RecordingProvisioner()), RunCommandBuilder)
    assert FILE_TOOLS == ("read", "write")


@red
def test_the_binary_is_the_one_it_was_given() -> None:
    access = StaticAccess()
    access.put_agent("dev", {"role": "R"})
    assert builder(access, RecordingProvisioner(), "/opt/kiro/bin/kiro-cli").build("dev", "P").argv[0] == "/opt/kiro/bin/kiro-cli"


@red
def test_an_agent_with_the_built_in_read_or_write_asks_for_a_confined_profile_with_its_access() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["write", "shell"], "workspace": "/w/dev", "inputs": ["/w/in"]})
    command = builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [(["write", "shell"], {"workspace": Path("/w/dev"), "inputs": [Path("/w/in")], "confine": True})]
    assert command.argv[4] == "profile-write-shell"


@red
def test_an_agent_with_neither_asks_for_the_shared_profile_without_access() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["shell", "web_search"], "workspace": "/w/dev"})
    builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [(["shell", "web_search"], {})]


@red
def test_a_charter_without_tools_asks_for_the_shared_profile() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": None})
    builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [([], {})]


@red
def test_a_legacy_charter_asks_for_the_shared_profile() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("old", {"role": "R", "tools": ["read", "shell"]})
    builder(access, provisioner).build("old", "P")
    assert provisioner.calls == [(["read", "shell"], {})]


@red
def test_the_tools_are_passed_in_the_order_of_the_charter() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["web_search", "read"], "inputs": []})
    builder(access, provisioner).build("dev", "P")
    assert provisioner.calls[0][0] == ["web_search", "read"]
