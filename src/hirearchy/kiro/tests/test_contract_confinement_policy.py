"""Contract of ``ConfinementPolicy``: the V3 ``tools`` selector and permission rules, and what they let kiro read and write, for every tool set, workspace and input list.

The expected values in ``golden/confinement.json`` (192 combinations) were generated from the policy and checked by hand against
docs/design/kiro-runtime-v3.md 4.3; ``test_confinement_v3.py`` pins the same rules from the design, case by case."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.kiro import ConfinementPolicy
from hirearchy.kiro.testing import IMPLEMENTATIONS

from ._support import golden

ORG = Path("/golden/org")
CASES = cast(list[dict[str, object]], golden("confinement.json"))
ORG_PATTERNS = ["/golden/org", "/golden/org/**"]


@pytest.fixture(params=IMPLEMENTATIONS[ConfinementPolicy], ids=lambda factory: factory.__name__)
def policy(request: pytest.FixtureRequest, tmp_path: Path) -> ConfinementPolicy:
    made: ConfinementPolicy = request.param(tmp_path)
    assert isinstance(made, ConfinementPolicy)
    return made


def ask(policy: ConfinementPolicy, case: dict[str, object]) -> dict[str, object]:
    workspace = case["workspace"]
    c = policy.file_confinement(
        ORG, cast(list[str], case["tools"]), Path(cast(str, workspace)) if workspace else None, [Path(p) for p in cast(list[str], case["inputs"])]
    )
    return {
        "tools": list(c.tools), "rules": list(c.rules), "read": [str(p) for p in c.read],
        "write": None if c.write is None else str(c.write), "problem": c.problem,
    }


def rules(policy: ConfinementPolicy, tools: list[str], workspace: str | None = None, inputs: list[str] | None = None) -> list[dict[str, object]]:
    c = policy.file_confinement(ORG, tools, Path(workspace) if workspace else None, [Path(p) for p in inputs or []])
    return [dict(r) for r in c.rules]


def test_every_combination_answers_the_golden(policy: ConfinementPolicy) -> None:
    for case in CASES:
        assert ask(policy, case) == case["confinement"], case


def test_the_selector_starts_with_at_hirearchy_and_holds_only_granted_tags(policy: ConfinementPolicy) -> None:
    tags = {"read": {"read"}, "write": {"write"}, "shell": {"shell"}, "web_search": {"remote_web_search", "web"}, "web_fetch": {"web_fetch", "web"}}
    for case in CASES:
        selector = cast(list[str], ask(policy, case)["tools"])
        granted = cast(list[str], case["tools"])
        assert selector[0] == "@hirearchy" and set(selector[1:]) <= set().union(*(tags[t] for t in granted), set())
        assert {"read", "write", "shell"} & set(selector) == {"read", "write", "shell"} & set(granted)


def test_write_reaches_only_the_workspace_and_never_the_organization(policy: ConfinementPolicy) -> None:
    for case in CASES:
        got = ask(policy, case)
        if "write" not in cast(list[str], case["tools"]):
            assert got["write"] is None and not [r for r in cast(list[dict[str, object]], got["rules"]) if r["capability"] == "fs_write" and r["effect"] == "allow"]
            continue
        allow = [r for r in cast(list[dict[str, object]], got["rules"]) if r["capability"] == "fs_write" and r["effect"] == "allow"]
        assert [r["match"] for r in allow] == ([[f"{case['workspace']}/**"]] if case["workspace"] else [])  # rule 3
        deny = {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS}
        inside = case["workspace"] in ("/golden/org", "/golden/org/ws")
        assert (deny in cast(list[dict[str, object]], got["rules"])) is (not inside)  # rule 4
        rule6 = [r for r in cast(list[dict[str, object]], got["rules"]) if r["capability"] == "fs_write" and r["match"] == ["/**"]]
        assert rule6 == [{"capability": "fs_write", "effect": "deny", "match": ["/**"], **({"exclude": [f"{case['workspace']}/**"]} if case["workspace"] else {})}]


def test_a_workspace_inside_the_organization_lifts_the_deny(policy: ConfinementPolicy) -> None:
    got = rules(policy, ["write"], "/golden/org/ws")
    assert {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS} not in got
    assert {"capability": "fs_write", "effect": "allow", "match": ["/golden/org/ws/**"]} in got
    assert {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS} in rules(policy, ["write"], "/golden/ws")


def test_read_reaches_the_workspace_the_inputs_and_the_organization_each_with_its_subtree(policy: ConfinementPolicy) -> None:
    got = rules(policy, ["read"], "/golden/ws", ["/golden/in-a"])
    reach = ["/golden/ws", "/golden/ws/**", "/golden/in-a", "/golden/in-a/**", *ORG_PATTERNS]
    assert got[1] == {"capability": "fs_read", "effect": "allow", "match": reach}  # rule 2
    assert got[2] == {"capability": "fs_read", "effect": "deny", "match": ["/**"], "exclude": reach}  # rule 5


def test_a_path_named_twice_is_listed_once(policy: ConfinementPolicy) -> None:
    got = rules(policy, ["read"], None, ["/golden/in-a", "/golden/in-a"])
    assert got[1]["match"] == ["/golden/in-a", "/golden/in-a/**", *ORG_PATTERNS]


def test_shell_is_allowed_by_rule_8_and_has_no_path_rule(policy: ConfinementPolicy) -> None:
    got = rules(policy, ["shell"], "/golden/ws", ["/golden/in-a"])
    assert {"capability": "shell", "match": ["*"], "effect": "allow"} in got
    assert not [r for r in got if str(r["capability"]).startswith("fs_")]


def test_the_organization_root_is_resolved(policy: ConfinementPolicy, tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    c = policy.file_confinement(tmp_path / "link", ["write"], None, [])
    assert {"capability": "fs_write", "effect": "deny", "match": [str(real.resolve()), f"{real.resolve()}/**"]} in [dict(r) for r in c.rules]


def test_the_arguments_are_not_changed(policy: ConfinementPolicy) -> None:
    tools, inputs = ["write", "read"], [Path("/golden/in-a")]
    policy.file_confinement(ORG, tools, Path("/golden/ws"), inputs)
    assert tools == ["write", "read"] and inputs == [Path("/golden/in-a")]
