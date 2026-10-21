"""Contract of ``ConfinementPolicy``: which paths kiro's built-in ``read``/``write`` may use, for every tool set, workspace and input list.

The expected values in ``golden/confinement.json`` were captured from ``scheduler.file_confinement`` of ``main`` (192 combinations)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.kiro import FILE_TOOLS, ConfinementPolicy
from hirearchy.kiro.testing import IMPLEMENTATIONS

from ._support import golden

ORG = Path("/golden/org")
CASES = cast(list[dict[str, object]], golden("confinement.json"))


@pytest.fixture(params=IMPLEMENTATIONS[ConfinementPolicy], ids=lambda factory: factory.__name__)
def policy(request: pytest.FixtureRequest, tmp_path: Path) -> ConfinementPolicy:
    made: ConfinementPolicy = request.param(tmp_path)
    assert isinstance(made, ConfinementPolicy)
    return made


def ask(policy: ConfinementPolicy, case: dict[str, object]) -> tuple[list[str], dict[str, object]]:
    workspace = case["workspace"]
    return policy.file_confinement(
        ORG, cast(list[str], case["tools"]), Path(cast(str, workspace)) if workspace else None, [Path(p) for p in cast(list[str], case["inputs"])]
    )


def test_every_combination_answers_what_main_answered(policy: ConfinementPolicy) -> None:
    for case in CASES:
        allowed, settings = ask(policy, case)
        assert {"allowedTools": allowed, "toolsSettings": settings} == {"allowedTools": case["allowedTools"], "toolsSettings": case["toolsSettings"]}, case


def test_read_and_write_are_never_in_allowed_tools(policy: ConfinementPolicy) -> None:
    for case in CASES:
        allowed, _ = ask(policy, case)
        assert not set(allowed) & set(FILE_TOOLS)
        assert allowed == [t for t in cast(list[str], case["tools"]) if t not in FILE_TOOLS]  # the others keep their order


def test_only_the_confined_tools_have_settings(policy: ConfinementPolicy) -> None:
    for case in CASES:
        _, settings = ask(policy, case)
        assert set(settings) == set(cast(list[str], case["tools"])) & set(FILE_TOOLS)


def test_write_reaches_only_the_workspace_and_never_the_organization(policy: ConfinementPolicy) -> None:
    _, settings = policy.file_confinement(ORG, ["write"], Path("/golden/ws"), [])
    assert settings == {"write": {"allowedPaths": ["/golden/ws/**"], "deniedPaths": ["/golden/org", "/golden/org/**"]}}
    _, nowhere = policy.file_confinement(ORG, ["write"], None, [])
    assert nowhere["write"] == {"allowedPaths": [], "deniedPaths": ["/golden/org", "/golden/org/**"]}


def test_a_workspace_inside_the_organization_lifts_the_deny(policy: ConfinementPolicy) -> None:
    _, settings = policy.file_confinement(ORG, ["write"], Path("/golden/org/ws"), [])
    assert settings == {"write": {"allowedPaths": ["/golden/org/ws/**"], "deniedPaths": []}}


def test_read_reaches_the_workspace_the_inputs_and_the_organization_each_with_its_subtree(policy: ConfinementPolicy) -> None:
    _, settings = policy.file_confinement(ORG, ["read"], Path("/golden/ws"), [Path("/golden/in-a")])
    assert settings == {"read": {"allowedPaths": ["/golden/ws", "/golden/ws/**", "/golden/in-a", "/golden/in-a/**", "/golden/org", "/golden/org/**"],
                                 "deniedPaths": []}}


def test_a_path_named_twice_is_listed_once(policy: ConfinementPolicy) -> None:
    _, settings = policy.file_confinement(ORG, ["read"], None, [Path("/golden/in-a"), Path("/golden/in-a")])
    assert cast(dict[str, list[str]], settings["read"])["allowedPaths"] == ["/golden/in-a", "/golden/in-a/**", "/golden/org", "/golden/org/**"]


def test_shell_stays_allowed_and_unconfined(policy: ConfinementPolicy) -> None:
    allowed, settings = policy.file_confinement(ORG, ["shell", "read"], None, [])
    assert allowed == ["shell"] and "shell" not in settings


def test_the_organization_root_is_resolved(policy: ConfinementPolicy, tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    _, settings = policy.file_confinement(tmp_path / "link", ["write"], None, [])
    assert cast(dict[str, list[str]], settings["write"])["deniedPaths"] == [str(real.resolve()), f"{real.resolve()}/**"]


def test_the_arguments_are_not_changed(policy: ConfinementPolicy) -> None:
    tools, inputs = ["write", "read"], [Path("/golden/in-a")]
    policy.file_confinement(ORG, tools, Path("/golden/ws"), inputs)
    assert tools == ["write", "read"] and inputs == [Path("/golden/in-a")]
