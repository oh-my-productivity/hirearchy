"""Contract of ``RunCommandBuilder``: the V3 command (the launcher, then ``kiro-cli chat ... --v3 ...``), the empty directory the agent works in, and its environment."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.kiro import KiroRunRefused, RunCommand, RunCommandBuilder
from hirearchy.kiro._env import run_environment
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


def test_the_command_line_is_the_launcher_then_kiro_chat_on_the_v3_engine_for_the_profile_and_the_model(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": []})
    command = h.builder.build("dev", "THE PROMPT")
    assert isinstance(command, RunCommand)
    assert command.argv == (
        *h.launcher, "--start-deadline", "60", "--",
        "kiro-cli", "chat", "--no-interactive", "--agent", h.provisioner.profile_name([]), "--model", DEFAULT_MODEL,
        "--effort", "high", "--v3", "--require-mcp-startup", "--output-format", "stream-json",
    )


def test_no_trust_flag_is_ever_passed(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["read", "write", "shell", "web_search", "web_fetch"]})
    argv = h.builder.build("dev", "P").argv
    assert not [a for a in argv if a.startswith("--trust")]  # neither --trust-all-tools nor --trust-tools


def test_the_prompt_is_not_in_the_command_line(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": []})
    assert "THE PROMPT" not in " ".join(h.builder.build("dev", "THE PROMPT").argv)


def model_of(command: RunCommand) -> str:
    return command.argv[command.argv.index("--model") + 1]


def test_the_model_is_the_charters_then_the_organizations_then_the_built_in_one(h: BuilderHarness) -> None:
    h.put_agent("plain", {"role": "R"})
    assert model_of(h.builder.build("plain", "P")) == DEFAULT_MODEL
    h.put_config("---\ndefault_model: m-org\n---\n# Organization\n")
    assert model_of(h.builder.build("plain", "P")) == "m-org"
    h.put_agent("own", {"role": "R", "model": "m-charter"})
    assert model_of(h.builder.build("own", "P")) == "m-charter"


def effort_of(command: RunCommand) -> str:
    return command.argv[command.argv.index("--effort") + 1]


@pytest.mark.parametrize("effort", ["high", "xhigh", "max"])
def test_the_effort_of_ORG_md_follows_the_model(h: BuilderHarness, effort: str) -> None:
    h.put_agent("dev", {"role": "R"})
    h.put_config(f"---\neffort: {effort}\n---\n# Organization\n")
    argv = h.builder.build("dev", "P").argv
    assert argv[argv.index("--model") + 2 :][:2] == ("--effort", effort)  # right after the model, once
    assert argv.count("--effort") == 1


@pytest.mark.parametrize("effort", ["low", "medium"])
def test_an_effort_below_high_refuses_the_run_before_anything_is_written(h: BuilderHarness, effort: str) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["shell"]})
    h.put_config(f"---\neffort: {effort}\n---\n# Organization\n")
    with pytest.raises(KiroRunRefused) as refused:
        h.builder.build("dev", "P")
    assert str(refused.value) == f'kiro: effort "{effort}" is not allowed for org agents; allowed: high, xhigh, max'
    assert h.names() == [] and not h.state.is_empty_dir(h.places.scratch("dev"))


def test_a_model_below_the_floor_is_passed_as_it_is(h: BuilderHarness) -> None:
    """An agent that existed before the floor keeps running on its model: nothing is substituted (docs/design/org-agent-model-floor.md 5)."""
    h.put_agent("old", {"role": "R", "model": "claude-haiku-4.5"})
    argv = h.builder.build("old", "P").argv
    assert argv[argv.index("--model") :][:4] == ("--model", "claude-haiku-4.5", "--effort", "high")


def test_the_agent_works_in_its_own_empty_scratch_directory(h: BuilderHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    h.put_agent("ceo/eng", {"role": "R"})
    for addr in ("ceo", "ceo/eng", "root"):
        cwd = h.builder.build(addr, "P").cwd
        assert cwd == h.places.scratch(addr) and h.state.is_empty_dir(cwd)
    assert len({h.places.scratch(a) for a in ("ceo", "ceo/eng", "root")}) == 3


def test_the_scratch_directory_is_neither_the_agents_directory_nor_inside_the_organization(h: BuilderHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    cwd = h.builder.build("ceo", "P").cwd
    assert cwd != h.root / "ceo" and h.root not in cwd.parents and cwd.parent != h.root


def test_a_workspace_is_not_the_working_directory(h: BuilderHarness) -> None:
    workspace = outside(h, "ws")
    h.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(workspace)})
    assert h.builder.build("dev", "P").cwd == h.places.scratch("dev") != workspace


def test_the_scratch_directory_is_made_fresh_on_every_run(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    scratch = h.builder.build("dev", "P").cwd
    h.state.plant(scratch, "left-over.txt")
    assert h.builder.build("dev", "P").cwd == scratch and h.state.is_empty_dir(scratch)


def test_the_environment_is_run_environment_of_the_process_plus_the_organization_and_the_agent(h: BuilderHarness) -> None:
    h.put_agent("ceo/eng", {"role": "R"})
    command = h.builder.build("ceo/eng", "P")
    expected = {**run_environment(h.environment.variables(), h.places.home()), "ORG_ROOT": str(h.root), "ORG_AGENT": "ceo/eng"}
    assert dict(command.env) == expected and command.env["KEEP"] == "me"


def test_kiro_home_is_the_one_of_the_organization_whatever_the_process_says(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    h.environment.set("KIRO_HOME", "/somewhere/else")
    assert h.builder.build("dev", "P").env["KIRO_HOME"] == str(h.places.home())


def test_variables_that_would_change_what_kiro_loads_or_writes_are_not_passed(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    for name in ("KIRO_DUMP_REQUESTS", "ASBX_KIRO_MANDATORY_MCPS", "KIRO_FEATURE_X"):
        h.environment.set(name, "1")
    env = h.builder.build("dev", "P").env
    assert not [name for name in env if name in ("KIRO_DUMP_REQUESTS", "ASBX_KIRO_MANDATORY_MCPS") or name.startswith("KIRO_FEATURE_")]


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


def test_the_profile_is_in_the_kiro_home_of_the_organization(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["shell"]})
    h.builder.build("dev", "P")
    assert h.state.is_private_dir(h.places.home())


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


def test_a_workspace_that_holds_the_kiro_state_refuses_the_run(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(h.places.roots()[0].parent)})
    with pytest.raises(KiroRunRefused, match=r"^kiro: hirearchy's kiro state .* is inside the workspace of dev "):
        h.builder.build("dev", "P")
    assert h.names() == []


def test_a_workspace_inside_the_kiro_state_refuses_the_run(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["shell"], "workspace": str(h.places.home() / "ws")})
    with pytest.raises(KiroRunRefused, match=r"^kiro: the workspace of dev .* is inside hirearchy's kiro state "):
        h.builder.build("dev", "P")
    assert h.names() == []


def test_an_input_that_holds_the_kiro_state_refuses_the_run_of_that_agent_only(h: BuilderHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["read"], "inputs": [str(h.places.roots()[1].parent)]})
    h.put_agent("ops", {"role": "R", "tools": ["read"]})
    with pytest.raises(KiroRunRefused, match="is inside the input of dev "):
        h.builder.build("dev", "P")
    assert h.builder.build("ops", "P").cwd == h.places.scratch("ops")


@pytest.mark.parametrize("planted", ["settings/mcp.json", "skills", "steering", "hooks", "settings/permissions.yaml", "workspace-roots", "AGENTS.md"])
def test_configuration_planted_in_the_kiro_home_refuses_the_run(h: BuilderHarness, planted: str) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["shell"]})
    h.state.plant(h.places.home(), planted)
    with pytest.raises(KiroRunRefused, match=rf"^kiro: the kiro home .* holds configuration kiro-cli would load into every agent: {planted}; remove it"):
        h.builder.build("dev", "P")
    assert h.names() == []


def test_a_synced_cloud_cache_refuses_the_run(h: BuilderHarness) -> None:
    """A1: configuration kiro-cli synced for the account (admin hooks, steering, powers) cannot be confined: the message says so."""
    h.put_agent("dev", {"role": "R", "tools": ["shell"]})
    h.state.plant(h.places.home(), "cloud-cache")
    with pytest.raises(KiroRunRefused, match=r"^kiro: the kiro home .* holds cloud-cache/, configuration kiro-cli synced for this account .*cannot run hirearchy agents confined$"):
        h.builder.build("dev", "P")
    assert h.names() == []


def test_an_agent_that_does_not_exist_is_the_error_of_the_charter_reader(h: BuilderHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.builder.build("nobody", "P")
