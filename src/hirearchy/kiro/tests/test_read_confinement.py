# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import hashlib
import json
from pathlib import Path

import pytest
from testkit.kiro_world import ensure_kiro_profile, file_confinement, kiro_profile_name, kiro_runner
from testkit.reach.hirearchy.core import ROOT, Org


def profile_of(isolated_kiro, name):
    return json.loads((isolated_kiro / ".kiro" / "agents" / f"{name}.json").read_text())


def run_profile(org, isolated_kiro, addr):
    cmd, cwd, env = kiro_runner()(org, addr, "P")
    name = cmd[cmd.index("--agent") + 1]
    return name, profile_of(isolated_kiro, name), cwd


@pytest.fixture
def org(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "proj").mkdir()
    o = Org.init(tmp_path / "org", "f-read", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "write", "web_search"],
           workspace=str(tmp_path / "proj"), inputs=[str(tmp_path / "inputs")])
    o.hire("lead", "writer", "Writer", "Write.", tools=["read"], inputs=[str(tmp_path / "inputs")])
    return o


# ------------------------------------------------------------------------------------------ profiles
def test_an_agent_with_built_in_read_may_read_the_org_and_its_inputs_only(org, tmp_path, isolated_kiro):
    _, prof, _ = run_profile(org, isolated_kiro, "lead/writer")
    inputs = tmp_path / "inputs"
    assert prof["toolsSettings"]["read"] == {
        "allowedPaths": [str(inputs), f"{inputs}/**", str(org.root), f"{org.root}/**"],
        "deniedPaths": [],  # a deny on the org would beat the allow
    }
    assert prof["allowedTools"] == ["@hirearchy"]  # read stays out of allowedTools, or kiro would ignore allowedPaths
    assert prof["tools"] == ["@hirearchy", "read"]


def test_the_org_is_read_only_for_kiro_tools(org, tmp_path, isolated_kiro):
    ws = tmp_path / "proj"
    org.hire("lead", "dev", "Dev", "x", tools=["read", "write"], workspace=str(ws))
    _, prof, _ = run_profile(org, isolated_kiro, "lead/dev")
    assert prof["toolsSettings"]["write"] == {"allowedPaths": [f"{ws}/**"], "deniedPaths": [str(org.root), f"{org.root}/**"]}
    read = prof["toolsSettings"]["read"]["allowedPaths"]
    assert f"{org.root}/**" in read and f"{ws}/**" in read
    assert str(tmp_path) not in read and f"{tmp_path}/**" not in read  # nothing wider than the org, workspace, inputs


def test_nothing_else_outside_the_org_is_reachable(org, tmp_path):
    _, settings = file_confinement(org.root, ["read"], None, [tmp_path / "inputs"])
    allowed = settings["read"]["allowedPaths"]
    assert {Path(p[:-3] if p.endswith("/**") else p) for p in allowed} == {tmp_path / "inputs", org.root}


def test_an_agent_without_built_in_read_is_unchanged(org, tmp_path, isolated_kiro):
    org.hire("lead", "web", "Web", "x", tools=["web_search"])
    name, prof, _ = run_profile(org, isolated_kiro, "lead/web")
    assert name == kiro_profile_name(org.root, ["web_search"]) and "toolsSettings" not in prof
    org.hire("lead", "scribe", "Scribe", "x", tools=["write"], workspace=str(tmp_path / "proj"))
    _, prof, _ = run_profile(org, isolated_kiro, "lead/scribe")
    assert set(prof["toolsSettings"]) == {"write"}  # no read rule: it has no built-in read, hirearchy `read` serves the org


def test_a_legacy_read_only_charter_keeps_its_unconfined_profile(org, isolated_kiro):
    (org.dir("lead") / "old").mkdir()
    (org.dir("lead") / "old" / "AGENT.md").write_text("---\nrole: Old\ntools: [read]\n---\nOld.\n")
    name, prof, _ = run_profile(org, isolated_kiro, "lead/old")
    assert name == kiro_profile_name(org.root, ["read"])
    assert prof["allowedTools"] == ["@hirearchy", "read"] and "toolsSettings" not in prof


def test_a_workspace_inside_the_org_still_works(org, isolated_kiro):
    ws = org.dir("lead") / "work" / "site"
    ws.mkdir(parents=True)
    org.hire(ROOT, "inorg", "In", "x", tools=["read", "write"], workspace=str(ws))
    _, prof, _ = run_profile(org, isolated_kiro, "inorg")
    assert prof["toolsSettings"]["write"]["deniedPaths"] == [] and prof["toolsSettings"]["read"]["deniedPaths"] == []
    assert f"{org.root}/**" in prof["toolsSettings"]["read"]["allowedPaths"]


# --------------------------------------------------------------------------------- existing profiles
def old_read_settings(org, tmp_path):
    """What the profile of `lead/writer` said before: workspace + inputs, the org denied."""
    p = tmp_path / "inputs"
    return {"read": {"allowedPaths": [str(p), f"{p}/**"], "deniedPaths": [str(org.root), f"{org.root}/**"]}}


def test_an_existing_per_org_profile_is_replaced_by_one_with_the_new_access(org, tmp_path, isolated_kiro):
    agents = isolated_kiro / ".kiro" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    old = old_read_settings(org, tmp_path)
    old_name = kiro_profile_name(org.root, ["read"]) + "-x" + hashlib.sha1(json.dumps(old, sort_keys=True).encode()).hexdigest()[:8]
    old_text = json.dumps({"name": old_name, "toolsSettings": old}) + "\n"
    (agents / f"{old_name}.json").write_text(old_text)
    legacy = agents / "hirearchy-read.json"  # the legacy global profile: never touched
    legacy.write_text('{"name": "hirearchy-read"}\n')
    name, prof, _ = run_profile(org, isolated_kiro, "lead/writer")
    assert name != old_name  # the profile name carries a hash of the access, so new access = new profile
    assert prof["toolsSettings"]["read"]["deniedPaths"] == [] and f"{org.root}/**" in prof["toolsSettings"]["read"]["allowedPaths"]
    assert (agents / f"{old_name}.json").read_text() == old_text and legacy.read_text() == '{"name": "hirearchy-read"}\n'


def test_a_profile_file_with_stale_content_is_rewritten(org, tmp_path, isolated_kiro):
    d = tmp_path / "agents"
    kw = dict(org=org, workspace=None, inputs=[tmp_path / "inputs"], confine=True)
    name = ensure_kiro_profile(["read"], d, **kw)
    path = d / f"{name}.json"
    stale = json.loads(path.read_text())
    stale["toolsSettings"]["read"] = old_read_settings(org, tmp_path)["read"]  # same file name, the old rule inside
    path.write_text(json.dumps(stale))
    assert ensure_kiro_profile(["read"], d, **kw) == name
    assert json.loads(path.read_text())["toolsSettings"]["read"]["deniedPaths"] == []
    assert f"{org.root}/**" in json.loads(path.read_text())["toolsSettings"]["read"]["allowedPaths"]
