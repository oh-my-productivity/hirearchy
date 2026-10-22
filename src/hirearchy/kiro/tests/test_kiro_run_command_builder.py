"""``KiroRunCommandBuilder`` asks the provisioner for a profile of the grant and the access of every agent (V3: all are confined), and checks the
kiro state in the order of docs/design/kiro-runtime-v3.md 13.2: tools, places, placement, the private home, its audit, the profile, the fresh scratch."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from hirearchy.access.testing import StaticAccess
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.kiro import FILE_TOOLS, KiroRunRefused, ProfileProvisioner, RunCommandBuilder
from hirearchy.kiro._runner import KiroRunCommandBuilder
from hirearchy.kiro.testing import LAUNCHER, FixedKiroPlaces, MemoryKiroState


class Trace:
    """What the builder did, in order, across its collaborators."""

    def __init__(self) -> None:
        self.steps: list[str] = []


class TracedState(MemoryKiroState):
    def __init__(self, trace: Trace, fail: OSError | None = None) -> None:
        super().__init__()
        self._trace = trace
        self._fail = fail

    def private_dir(self, path: Path) -> None:
        self._trace.steps.append("private_dir")
        if self._fail is not None:
            raise self._fail
        super().private_dir(path)

    def planted(self, home: Path) -> list[str]:
        self._trace.steps.append("planted")
        return super().planted(home)

    def fresh(self, path: Path) -> None:
        self._trace.steps.append("fresh")
        super().fresh(path)


class RecordingProvisioner(ProfileProvisioner):
    def __init__(self, trace: Trace | None = None, refuse: str | None = None) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self._trace = trace or Trace()
        self._refuse = refuse

    def profile_name(self, tools: Sequence[str]) -> str:
        return "profile-" + "-".join(tools)

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None
    ) -> str:
        self._trace.steps.append("ensure_profile")
        if self._refuse is not None:
            raise KiroRunRefused(f"kiro: {self._refuse}")
        self.calls.append((list(tools), {k: v for k, v in (("workspace", workspace), ("inputs", inputs)) if v}))
        return self.profile_name(tools)


BASE = Path("/state-base")  # the fixed places lie below it: kiro-home, kiro-cwd


def builder(
    access: StaticAccess, provisioner: RecordingProvisioner, kiro_bin: str = "kiro-cli", *, state: MemoryKiroState | None = None,
    places: FixedKiroPlaces | None = None, environment: DictEnvironment | None = None,
) -> KiroRunCommandBuilder:
    state = state or MemoryKiroState()
    return KiroRunCommandBuilder(
        kiro_bin, LAUNCHER, OrgPaths(access.root), access.agents, access, access, provisioner, environment or DictEnvironment({"A": "1"}),
        places or FixedKiroPlaces(BASE), state, state,
    )


def test_it_is_a_run_command_builder() -> None:
    assert isinstance(builder(StaticAccess(), RecordingProvisioner()), RunCommandBuilder)
    assert FILE_TOOLS == ("read", "write")


def test_the_binary_is_the_one_it_was_given_and_the_launcher_comes_first() -> None:
    access = StaticAccess()
    access.put_agent("dev", {"role": "R"})
    argv = builder(access, RecordingProvisioner(), "/opt/kiro/bin/kiro-cli").build("dev", "P").argv
    assert argv[: len(LAUNCHER)] == LAUNCHER
    assert argv[len(LAUNCHER) :][:4] == ("--start-deadline", "60", "--", "/opt/kiro/bin/kiro-cli")


def test_an_agent_with_the_built_in_read_or_write_asks_for_a_profile_with_its_access() -> None:
    access, provisioner = StaticAccess(), RecordingProvisioner()
    access.put_agent("dev", {"role": "R", "tools": ["write", "shell"], "workspace": "/w/dev", "inputs": ["/w/in"]})
    command = builder(access, provisioner).build("dev", "P")
    assert provisioner.calls == [(["write", "shell"], {"workspace": Path("/w/dev"), "inputs": [Path("/w/in")]})]
    assert command.argv[command.argv.index("--agent") + 1] == "profile-write-shell"


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


# ------------------------------------------------------------------------------------------------------------ the order of the checks


def traced(
    *, places: FixedKiroPlaces | None = None, fail: OSError | None = None, refuse: str | None = None
) -> tuple[StaticAccess, Trace, KiroRunCommandBuilder, TracedState]:
    """A builder whose state and provisioner write their calls, in order, to one trace."""
    access, trace = StaticAccess(), Trace()
    state = TracedState(trace, fail)
    return access, trace, builder(access, RecordingProvisioner(trace, refuse), state=state, places=places), state


def test_the_home_is_made_private_and_audited_then_the_profile_is_written_and_the_scratch_made_fresh_last() -> None:
    access, trace, kiro, state = traced()
    access.put_agent("dev", {"role": "R", "tools": ["shell"]})
    command = kiro.build("dev", "P")
    assert trace.steps == ["private_dir", "planted", "ensure_profile", "fresh"]
    assert state.private == [FixedKiroPlaces(BASE).home()] and state.fresh_calls == [command.cwd] == [FixedKiroPlaces(BASE).scratch("dev")]


def test_a_wrong_shape_of_tools_refuses_before_anything_else() -> None:
    access, trace, kiro, _ = traced(places=FixedKiroPlaces(BASE, "the places are bad"))
    access.put_agent("dev", {"role": "R", "tools": "read"})
    with pytest.raises(KiroRunRefused, match=r"^kiro: the charter's tools must be a list of names"):
        kiro.build("dev", "P")
    assert trace.steps == []


def test_a_problem_of_the_places_refuses_before_anything_is_made() -> None:
    access, trace, kiro, _ = traced(places=FixedKiroPlaces(BASE, "the places are bad"))
    access.put_agent("dev", {"role": "R", "tools": ["shell"]})
    with pytest.raises(KiroRunRefused, match="^kiro: the places are bad$"):
        kiro.build("dev", "P")
    assert trace.steps == []


def test_a_workspace_that_holds_the_state_refuses_before_anything_is_made() -> None:
    access, trace, kiro, _ = traced()
    access.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(BASE)})
    with pytest.raises(KiroRunRefused, match=r"^kiro: hirearchy's kiro state .*kiro-home is inside the workspace of dev "):
        kiro.build("dev", "P")
    assert trace.steps == []


def test_the_placement_of_the_running_agent_only_is_checked() -> None:
    access, trace, kiro, _ = traced()
    access.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(BASE)})
    access.put_agent("ops", {"role": "R", "tools": ["shell"]})
    kiro.build("ops", "P")
    assert trace.steps == ["private_dir", "planted", "ensure_profile", "fresh"]


def test_a_planted_entry_refuses_after_the_home_is_made_and_before_a_profile_is_written() -> None:
    access, trace, kiro, state = traced()
    access.put_agent("dev", {"role": "R", "tools": ["shell"]})
    state.plant(FixedKiroPlaces(BASE).home(), "skills")
    with pytest.raises(KiroRunRefused, match="^kiro: the kiro home .* holds configuration kiro-cli would load into every agent: skills;"):
        kiro.build("dev", "P")
    assert trace.steps == ["private_dir", "planted"]
    assert state.fresh_calls == []


def test_a_cloud_cache_is_refused_with_its_own_message_before_a_profile_is_written() -> None:
    access, trace, kiro, state = traced()
    access.put_agent("dev", {"role": "R", "tools": []})
    state.plant(FixedKiroPlaces(BASE).home(), "cloud-cache")
    state.plant(FixedKiroPlaces(BASE).home(), "skills")
    with pytest.raises(KiroRunRefused, match=r"holds cloud-cache/, configuration kiro-cli synced"):
        kiro.build("dev", "P")
    assert trace.steps == ["private_dir", "planted"]


def test_a_profile_that_is_refused_leaves_the_scratch_directory_alone() -> None:
    access, trace, kiro, state = traced(refuse="the path is bad")
    access.put_agent("dev", {"role": "R", "tools": ["write"]})
    with pytest.raises(KiroRunRefused, match="^kiro: the path is bad$"):
        kiro.build("dev", "P")
    assert trace.steps == ["private_dir", "planted", "ensure_profile"] and state.fresh_calls == []


def test_an_io_error_of_the_state_is_not_hidden() -> None:
    access, trace, kiro, _ = traced(fail=OSError("disk full"))
    access.put_agent("dev", {"role": "R", "tools": []})
    with pytest.raises(OSError, match="disk full"):
        kiro.build("dev", "P")
    assert trace.steps == ["private_dir"]


def test_the_environment_is_asked_on_every_run_and_the_home_of_the_places_is_the_kiro_home() -> None:
    access, environment = StaticAccess(), DictEnvironment({"A": "1"})
    access.put_agent("dev", {"role": "R"})
    kiro = builder(access, RecordingProvisioner(), environment=environment)
    assert kiro.build("dev", "P").env["KIRO_HOME"] == str(FixedKiroPlaces(BASE).home())
    environment.set("LATE", "yes")
    assert kiro.build("dev", "P").env["LATE"] == "yes"
