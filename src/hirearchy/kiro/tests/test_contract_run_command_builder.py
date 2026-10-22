"""Contract of ``RunCommandBuilder``: ``kiro-cli chat --no-interactive --agent <profile> --model <model>``, where the agent works, and its environment."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.kiro import KiroRunRefused, RunCommand, RunCommandBuilder
from hirearchy.kiro.testing import IMPLEMENTATIONS, BuilderHarness
from hirearchy.settings import DEFAULT_MODEL

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[RunCommandBuilder], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> BuilderHarness:
    made = make(request, tmp_path, BuilderHarness)
    assert isinstance(made.builder, RunCommandBuilder)
    return made


def outside(h: BuilderHarness, *parts: str) -> Path:
    """A path that is neither inside the organization nor contains it (and does not need to exist)."""
    return h.root.parent / f"{h.root.name}-elsewhere" / Path(*parts)


def profile_of(command: RunCommand) -> str:
    return command.argv[command.argv.index("--agent") + 1]


def test_the_command_line_is_kiro_chat_without_interaction_for_the_profile_and_the_model(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": []})
    command = h.builder.build("dev", "THE PROMPT")
    assert isinstance(command, RunCommand)
    assert command.argv == ("kiro-cli", "chat", "--no-interactive", "--agent", h.provisioner.profile_name([]), "--model", DEFAULT_MODEL)


def test_the_prompt_is_not_in_the_command_line(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": []})
    assert "THE PROMPT" not in " ".join(h.builder.build("dev", "THE PROMPT").argv)


def test_the_model_is_the_charters_then_the_organizations_then_the_built_in_one(h: BuilderHarness) -> None:
    h.put_agent("plain", {"role": "R"})
    assert h.builder.build("plain", "P").argv[-1] == DEFAULT_MODEL
    h.put_config("---\ndefault_model: m-org\n---\n# Organization\n")
    assert h.builder.build("plain", "P").argv[-2:] == ("--model", "m-org")
    h.put_agent("own", {"role": "R", "model": "m-charter"})
    assert h.builder.build("own", "P").argv[-2:] == ("--model", "m-charter")


def test_the_agent_works_in_its_own_directory(h: BuilderHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    h.put_agent("ceo/eng", {"role": "R"})
    assert h.builder.build("ceo", "P").cwd == h.root / "ceo"
    assert h.builder.build("ceo/eng", "P").cwd == h.root / "ceo" / "eng"
    assert h.builder.build("root", "P").cwd == h.root


def test_the_agent_works_in_its_workspace_when_it_has_one(h: BuilderHarness) -> None:
    workspace = outside(h, "ws")
    h.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(workspace)})
    assert h.builder.build("dev", "P").cwd == workspace


def test_the_workspace_of_the_charter_is_used_as_written_with_only_the_home_expanded(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": [], "workspace": "~/ws"})
    assert h.builder.build("dev", "P").cwd == Path("~/ws").expanduser()


def test_the_environment_is_the_one_of_the_process_plus_the_organization_and_the_agent(h: BuilderHarness) -> None:
    h.put_agent("ceo/eng", {"role": "R"})
    command = h.builder.build("ceo/eng", "P")
    assert dict(command.env) == {**h.environment.variables(), "ORG_ROOT": str(h.root), "ORG_AGENT": "ceo/eng"}


def test_the_environment_of_the_process_is_read_on_every_run(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    h.environment.set("LATE", "1")
    assert h.builder.build("dev", "P").env["LATE"] == "1"


def test_the_organization_and_the_agent_beat_the_environment(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    h.environment.set("ORG_AGENT", "someone-else")
    h.environment.set("ORG_ROOT", "/elsewhere")
    command = h.builder.build("dev", "P")
    assert command.env["ORG_AGENT"] == "dev" and command.env["ORG_ROOT"] == str(h.root)


def test_the_profile_is_written_and_named_on_the_command_line(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["web_search", "shell"]})
    profile = profile_of(h.builder.build("dev", "P"))
    assert profile == h.provisioner.profile_name(["shell", "web_search"])
    assert h.names() == [f"{profile}.json"] and h.profile(profile) is not None


def test_agents_with_the_same_tools_share_a_profile(h: BuilderHarness) -> None:
    h.put_agent("a", {"role": "R", "tools": ["shell"]})
    h.put_agent("b", {"role": "R", "tools": ["shell"]})
    assert profile_of(h.builder.build("a", "P")) == profile_of(h.builder.build("b", "P"))
    assert len(h.names()) == 1


def test_an_agent_without_tools_runs_with_the_shared_profile_of_the_organization(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    assert profile_of(h.builder.build("dev", "P")) == h.provisioner.profile_name([])


# ------------------------------------------------------------------------------------------------------------- confinement


def rules_of(data: dict[str, object] | None) -> list[dict[str, object]]:
    assert data is not None
    return cast("list[dict[str, object]]", cast("dict[str, object]", data["permissions"])["rules"])


def rule(rules: list[dict[str, object]], capability: str, effect: str) -> dict[str, object]:
    (found,) = [r for r in rules if r["capability"] == capability and r["effect"] == effect]
    return found


def test_built_in_write_gets_a_profile_confined_to_the_workspace(h: BuilderHarness) -> None:
    workspace = outside(h, "ws")
    h.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": str(workspace), "inputs": []})
    profile = profile_of(h.builder.build("dev", "P"))
    data = h.profile(profile)
    assert data is not None and profile.startswith(h.provisioner.profile_name(["write"]) + "-x")
    assert data["tools"] == ["@hirearchy", "write"] and "permissions" in data
    rules = rules_of(data)
    assert rule(rules, "fs_write", "allow")["match"] == [f"{workspace.resolve()}/**"]
    org_deny = {"capability": "fs_write", "effect": "deny", "match": [str(h.root.resolve()), f"{h.root.resolve()}/**"]}
    assert org_deny in rules  # the organization is never written with kiro's tools
    assert not [r for r in rules if r["capability"] == "fs_read" and r["effect"] == "allow"]  # a write-only agent reads nothing


def test_built_in_read_gets_the_workspace_the_inputs_and_the_organization(h: BuilderHarness) -> None:
    workspace, inputs = outside(h, "ws"), outside(h, "in")
    h.put_agent("dev", {"role": "R", "tools": ["read"], "workspace": str(workspace), "inputs": [str(inputs)]})
    rules = rules_of(h.profile(profile_of(h.builder.build("dev", "P"))))
    expected = [p for base in (workspace.resolve(), inputs.resolve(), h.root.resolve()) for p in (str(base), f"{base}/**")]
    assert rule(rules, "fs_read", "allow")["match"] == expected
    assert rule(rules, "fs_read", "deny")["exclude"] == expected and rule(rules, "fs_read", "deny")["match"] == ["/**"]


def test_a_former_legacy_charter_is_confined_to_the_org(h: BuilderHarness) -> None:
    h.put_agent("old", {"role": "R", "tools": ["read"]})  # built-in read only, no workspace, no ``inputs`` key
    profile = profile_of(h.builder.build("old", "P"))
    assert profile.startswith(h.provisioner.profile_name(["read"]) + "-x")
    rules = rules_of(h.profile(profile))
    org = [str(h.root.resolve()), f"{h.root.resolve()}/**"]
    assert rule(rules, "fs_read", "allow")["match"] == org and rule(rules, "fs_read", "deny")["exclude"] == org
    assert rule(rules, "fs_write", "deny") == {"capability": "fs_write", "effect": "deny", "match": ["/**"]}  # writes nowhere


def test_a_charter_with_write_is_confined(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["read", "write"]})  # no workspace and no inputs key
    assert "-x" in profile_of(h.builder.build("dev", "P"))


def test_a_charter_with_an_empty_inputs_list_is_confined(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["read"], "inputs": []})
    assert "-x" in profile_of(h.builder.build("dev", "P"))


def test_shell_alone_has_no_fs_rules(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(outside(h, "ws")), "inputs": []})
    profile = profile_of(h.builder.build("dev", "P"))
    assert profile == h.provisioner.profile_name(["shell"])
    assert not [r for r in rules_of(h.profile(profile)) if str(r["capability"]).startswith("fs_")]


def test_an_unknown_tool_refuses_the_run(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["read", "Shell"]})
    with pytest.raises(KiroRunRefused, match="^kiro: the charter's tools name 'Shell', which is not one of read, write, shell, web_search, web_fetch"):
        h.builder.build("dev", "P")
    assert h.names() == []


@pytest.mark.parametrize("tools", ["read", {"read": True}, [1], ["read", None], [["read"]]])
def test_tools_that_are_not_a_list_refuse_the_run(h: BuilderHarness, tools: object) -> None:
    h.put_agent("dev", {"role": "R", "tools": tools})
    with pytest.raises(KiroRunRefused, match=r"^kiro: the charter's tools must be a list of names \(read, write, shell, web_search, web_fetch\)$"):
        h.builder.build("dev", "P")
    assert h.names() == []


def test_a_workspace_kiro_cannot_match_refuses_the_run(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": str(outside(h, "w{s"))})
    with pytest.raises(KiroRunRefused, match=r'contains "\{"'):
        h.builder.build("dev", "P")
    assert h.names() == []


def test_an_agent_that_does_not_exist_is_the_error_of_the_charter_reader(h: BuilderHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.builder.build("nobody", "P")
