"""``OrgProfileProvisioner``: names and bytes of the profiles are those ``main`` wrote (golden files captured from the scheduler functions of ``main``)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import OrgPaths
from hirearchy.kiro import ConfinementPolicy, McpServerLocator, ProfileProvisioner
from hirearchy.kiro._confinement import KiroConfinementPolicy
from hirearchy.kiro._provisioner import OrgProfileProvisioner
from hirearchy.kiro.testing import CountingProfileStore, MemoryProfileStore, StaticMcpServerLocator

from ._support import golden

ORG = Path("/golden/org")
NAMES = cast(list[dict[str, object]], golden("names.json"))
PROFILES = cast(dict[str, dict[str, object]], golden("profiles.json"))
BIN = {"command": "<BIN>", "args": ["mcp"]}


def provisioner(root: Path = ORG, store: MemoryProfileStore | None = None) -> OrgProfileProvisioner:
    return OrgProfileProvisioner(OrgPaths(root), store or MemoryProfileStore(), KiroConfinementPolicy(), StaticMcpServerLocator(BIN))


def test_it_is_a_provisioner() -> None:
    assert isinstance(provisioner(), ProfileProvisioner)


@pytest.mark.parametrize("case", NAMES, ids=lambda case: f"{case['root']}|{','.join(cast(list[str], case['tools']))}")
def test_the_name_is_the_one_main_computed(case: dict[str, object]) -> None:
    assert provisioner(Path(cast(str, case["root"]))).profile_name(cast(list[str], case["tools"])) == case["name"]


@pytest.mark.parametrize("label", sorted(PROFILES))
def test_the_profile_has_the_name_and_the_bytes_main_wrote(label: str) -> None:
    shape = cast(dict[str, object], PROFILES[label]["args"])
    kw: dict[str, object] = {}
    if "workspace" in shape:
        kw["workspace"] = Path(cast(str, shape["workspace"]))
    if "inputs" in shape:
        kw["inputs"] = [Path(p) for p in cast(list[str], shape["inputs"])]
    if "confine" in shape:
        kw["confine"] = shape["confine"]
    store = MemoryProfileStore()
    name = provisioner(ORG, store).ensure_profile(cast(list[str], shape["tools"]), **kw)  # type: ignore[arg-type]
    assert name == PROFILES[label]["name"]
    assert store.files == {name: PROFILES[label]["text"]}


class RecordingPolicy(ConfinementPolicy):
    def __init__(self) -> None:
        self.calls: list[tuple[Path, list[str], Path | None, list[Path]]] = []

    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        self.calls.append((org_root, list(tools), workspace, list(inputs)))
        return ["shell"], {"read": {"allowedPaths": []}}


class CountingLocator(McpServerLocator):
    def __init__(self) -> None:
        self.asked = 0

    def command(self) -> dict[str, object]:
        self.asked += 1
        return dict(BIN)


def test_the_policy_is_asked_with_the_organization_the_sorted_tools_the_workspace_and_the_inputs() -> None:
    policy, root = RecordingPolicy(), Path("/some/where/org")
    OrgProfileProvisioner(OrgPaths(root), MemoryProfileStore(), policy, StaticMcpServerLocator()).ensure_profile(
        ["write", "shell", "read", "read"], workspace=Path("/ws"), inputs=[Path("/in")], confine=True)
    assert policy.calls == [(root, ["read", "shell", "write"], Path("/ws"), [Path("/in")])]


def test_the_policy_is_not_asked_for_a_shared_profile() -> None:
    policy = RecordingPolicy()
    OrgProfileProvisioner(OrgPaths(ORG), MemoryProfileStore(), policy, StaticMcpServerLocator()).ensure_profile(["read"], workspace=Path("/ws"))
    assert policy.calls == []


def test_the_locator_is_asked_once_per_profile_and_its_answer_is_in_the_profile() -> None:
    locator, store = CountingLocator(), MemoryProfileStore()
    OrgProfileProvisioner(OrgPaths(ORG), store, KiroConfinementPolicy(), locator).ensure_profile(["read"])
    assert locator.asked == 1 and '"command": "<BIN>"' in store.files["hirearchy-golden-org-26994b-read"]


def test_a_profile_that_is_there_costs_no_write() -> None:
    store = CountingProfileStore(MemoryProfileStore())
    made = OrgProfileProvisioner(OrgPaths(ORG), store, KiroConfinementPolicy(), StaticMcpServerLocator(BIN))
    for _ in range(3):
        made.ensure_profile(["shell"])
    assert store.writes == ["hirearchy-golden-org-26994b-shell"]


def test_the_server_that_moved_makes_the_next_call_rewrite_the_profile() -> None:
    store = CountingProfileStore(MemoryProfileStore())
    first = OrgProfileProvisioner(OrgPaths(ORG), store, KiroConfinementPolicy(), StaticMcpServerLocator({"command": "/old/hirearchy", "args": ["mcp"]}))
    second = OrgProfileProvisioner(OrgPaths(ORG), store, KiroConfinementPolicy(), StaticMcpServerLocator({"command": "/new/hirearchy", "args": ["mcp"]}))
    assert first.ensure_profile([]) == second.ensure_profile([])
    assert len(store.writes) == 2


def test_the_root_as_given_is_in_the_profile_and_the_resolved_root_is_in_the_name(tmp_path: Path) -> None:
    real = tmp_path / "real" / "org"
    real.mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "real")
    linked = tmp_path / "link" / "org"
    store = MemoryProfileStore()
    name = provisioner(linked, store).ensure_profile([])
    assert name == provisioner(real, MemoryProfileStore()).profile_name([])  # the same directory: the same profile
    assert f"for {linked};" in store.files[name] and f'"ORG_ROOT": "{linked}"' in store.files[name]
