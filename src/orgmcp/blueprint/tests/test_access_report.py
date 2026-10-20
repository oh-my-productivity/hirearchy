"""``PolicyAccessReport``: what the runtime lets an agent reach with kiro's file tools, asked of the confinement policy with a stand-in org directory."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint._access import ORG_PLACEHOLDER, PolicyAccessReport
from orgmcp.blueprint._protocols import AccessReport
from orgmcp.blueprint.api import Agent
from orgmcp.blueprint.testing import ScriptedConfinementPolicy, access_over



ROOT_DIR = str(ORG_PLACEHOLDER)
OPEN = {"read": {"allowedPaths": [ROOT_DIR, f"{ROOT_DIR}/**"], "deniedPaths": []}}


def agent(**kw: object) -> Agent:
    values: dict[str, object] = {"addr": "lead/rev", "name": "rev", "parent": "lead", "where": "agents[lead/rev]", "kind": "verifier"}
    values.update(kw)
    return Agent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("tools", [[], ["web_search"], ["shell"], ["write", "shell"]])
def test_without_the_built_in_read_the_organization_is_read_with_orgmcp_read_and_the_policy_is_not_asked(tools: list[str]) -> None:
    policy = ScriptedConfinementPolicy()
    assert PolicyAccessReport(policy).org_files_readable(agent(tools=tools, workspace="/ws" if "shell" in tools else None))
    assert policy.calls == []


def test_with_the_built_in_read_the_policy_is_asked_about_a_stand_in_organization_directory() -> None:
    policy = ScriptedConfinementPolicy(OPEN)
    assert PolicyAccessReport(policy).org_files_readable(agent(tools=["read", "shell"], workspace="/ws", inputs=["/in1", "/in2"]))
    assert policy.calls == [(Path("/orgmcp-org-root"), ["read", "shell"], Path("/ws"), [Path("/in1"), Path("/in2")])]


def test_without_a_workspace_the_policy_is_asked_with_none() -> None:
    policy = ScriptedConfinementPolicy(OPEN)
    PolicyAccessReport(policy).org_files_readable(agent(tools=["read"]))
    assert policy.calls[0][2] is None


def test_the_organization_is_readable_when_the_policy_allows_it_and_does_not_deny_it() -> None:
    assert PolicyAccessReport(ScriptedConfinementPolicy(OPEN)).org_files_readable(agent(tools=["read"]))


@pytest.mark.parametrize("settings", [
    {},  # nothing allowed
    {"read": {"allowedPaths": [], "deniedPaths": []}},
    {"read": {"allowedPaths": [ROOT_DIR], "deniedPaths": []}},  # the directory but not what is in it
    {"read": {"allowedPaths": [f"{ROOT_DIR}/**"], "deniedPaths": [ROOT_DIR]}},
    {"read": {"allowedPaths": [f"{ROOT_DIR}/**"], "deniedPaths": ["/"]}},  # a denied parent
])
def test_the_organization_is_not_readable_when_the_policy_does_not_allow_it_or_denies_it(settings: dict[str, object]) -> None:
    assert not PolicyAccessReport(ScriptedConfinementPolicy(settings)).org_files_readable(agent(tools=["read"]))


def test_a_denial_of_the_glob_alone_does_not_hide_the_directory_itself() -> None:
    """What the flat function answered: a denied path hides the directory when it IS the directory or a parent of it (``root.startswith(parent + "/")``);
    the glob ``<root>/**`` is neither."""
    settings = {"read": {"allowedPaths": [f"{ROOT_DIR}/**"], "deniedPaths": [f"{ROOT_DIR}/**"]}}
    assert PolicyAccessReport(ScriptedConfinementPolicy(settings)).org_files_readable(agent(tools=["read"]))


def test_the_real_policy_lets_the_built_in_read_open_the_organization() -> None:
    assert access_over().org_files_readable(agent(tools=["read"], workspace="/ws", inputs=["/in"]))


def test_the_facts_of_an_agent_with_everything() -> None:
    a = agent(kind="author", tools=["read", "write", "shell", "web_fetch", "memory"], workspace="/ws", inputs=["/in"])
    assert access_over().facts(a) == {
        "write": (True, "/ws"), "read": (True, ["/ws", "/in"]), "org": True, "inputs": ["/in"], "inputs_via_orgmcp": False,
        "shell": (True, "/ws"), "web": ["web_fetch"]}


def test_inputs_without_the_built_in_read_are_reached_with_orgmcp_read() -> None:
    facts = access_over().facts(agent(tools=[], inputs=["/in"]))
    assert facts["inputs_via_orgmcp"] and facts["read"] == (False, ["/in"]) and facts["org"] and facts["write"] == (False, None)


def test_the_technical_line() -> None:
    report = access_over()
    assert report.line(agent(tools=[])) == ""
    assert report.line(agent(tools=["write"], workspace="/ws")) == "kiro write only in /ws"
    assert report.line(agent(tools=["write"])) == "kiro write nowhere"
    assert report.line(agent(tools=["read"])) == "kiro read only in the organization's own files (read-only)"
    assert report.line(agent(tools=["read", "shell"], workspace="/ws")) == \
        "kiro read only in /ws and in the organization's own files (read-only); shell NOT confined (instructed only)"
    assert report.line(agent(tools=[], inputs=["/a", "/b"])) == "read-only inputs (orgmcp read): /a, /b"
    assert report.line(agent(tools=["write", "read"], workspace="/ws")) == \
        "kiro write only in /ws; kiro read only in /ws and in the organization's own files (read-only)"


def test_a_policy_that_hides_the_organization_changes_the_line() -> None:
    hidden = PolicyAccessReport(ScriptedConfinementPolicy({"read": {"allowedPaths": ["/ws"], "deniedPaths": []}}))
    assert hidden.line(agent(tools=["read"], workspace="/ws")) == "kiro read only in /ws"
    assert hidden.line(agent(tools=["read"])) == "kiro read nowhere"
