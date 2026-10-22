# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
from pathlib import Path

import pytest
from testkit.kiro_world import ensure_kiro_profile, file_confinement, kiro_home_agents_dir, kiro_part, kiro_profile_name, kiro_runner
from testkit.reach.hirearchy.core import ROOT, Org


def profile_of(org, name):
    """A profile of the organization: they are in its kiro home, not in ``~/.kiro/agents``."""
    return json.loads((kiro_home_agents_dir(org.root) / f"{name}.json").read_text())


def rules(prof):
    return prof["permissions"]["rules"]


def rule(prof, capability, effect):
    (found,) = [r for r in rules(prof) if r["capability"] == capability and r["effect"] == effect and r.get("match") != ["/**"]]
    return found


def catch_all(prof, capability):
    (found,) = [r for r in rules(prof) if r["capability"] == capability and r["effect"] == "deny" and r.get("match") == ["/**"]]
    return found


def run_profile(org, isolated_kiro, addr):
    argv, cwd, env = kiro_runner()(org, addr, "P")
    cmd = kiro_part(argv)
    name = cmd[cmd.index("--agent") + 1]
    return name, profile_of(org, name), cwd


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
    reach = [str(inputs), f"{inputs}/**", str(org.root), f"{org.root}/**"]
    assert rule(prof, "fs_read", "allow")["match"] == reach
    assert catch_all(prof, "fs_read")["exclude"] == reach  # every other read is a deny
    assert prof["tools"] == ["@hirearchy", "read"] and "permissions" in prof


def test_the_org_is_read_only_for_kiro_tools(org, tmp_path, isolated_kiro):
    ws = tmp_path / "proj"
    org.hire("lead", "dev", "Dev", "x", tools=["read", "write"], workspace=str(ws))
    _, prof, _ = run_profile(org, isolated_kiro, "lead/dev")
    assert rule(prof, "fs_write", "allow")["match"] == [f"{ws}/**"]
    assert {"capability": "fs_write", "effect": "deny", "match": [str(org.root), f"{org.root}/**"]} in rules(prof)
    read = rule(prof, "fs_read", "allow")["match"]
    assert f"{org.root}/**" in read and f"{ws}/**" in read
    assert str(tmp_path) not in read and f"{tmp_path}/**" not in read  # nothing wider than the org, workspace, inputs


def test_nothing_else_outside_the_org_is_reachable(org, tmp_path):
    c = file_confinement(org.root, ["read"], None, [tmp_path / "inputs"])
    assert set(c.read) == {tmp_path / "inputs", org.root} and c.write is None
    patterns = [r for r in c.rules if r["capability"] == "fs_read" and r["effect"] == "allow"][0]["match"]
    assert {Path(p[:-3] if p.endswith("/**") else p) for p in patterns} == {tmp_path / "inputs", org.root}


def test_an_agent_without_built_in_read_has_no_read_rule(org, tmp_path, isolated_kiro):
    org.hire("lead", "web", "Web", "x", tools=["web_search"])
    name, prof, _ = run_profile(org, isolated_kiro, "lead/web")
    assert name == kiro_profile_name(org.root, ["web_search"]) and not any(r["capability"].startswith("fs_") for r in rules(prof))
    org.hire("lead", "scribe", "Scribe", "x", tools=["write"], workspace=str(tmp_path / "proj"))
    _, prof, _ = run_profile(org, isolated_kiro, "lead/scribe")
    assert not [r for r in rules(prof) if r["capability"] == "fs_read" and r["effect"] == "allow"]  # it reads nothing with kiro's tools
    assert "exclude" not in catch_all(prof, "fs_read") and prof["tools"] == ["@hirearchy", "write"]


def test_a_legacy_read_only_charter_reads_only_the_org(org, isolated_kiro):
    (org.dir("lead") / "old").mkdir()
    (org.dir("lead") / "old" / "AGENT.md").write_text("---\nrole: Old\ntools: [read]\n---\nOld.\n")
    name, prof, _ = run_profile(org, isolated_kiro, "lead/old")
    assert name.startswith(kiro_profile_name(org.root, ["read"]) + "-x")
    assert rule(prof, "fs_read", "allow")["match"] == [str(org.root), f"{org.root}/**"]
    assert catch_all(prof, "fs_write") == {"capability": "fs_write", "effect": "deny", "match": ["/**"]}


def test_a_workspace_inside_the_org_still_works(org, isolated_kiro):
    ws = org.dir("lead") / "work" / "site"
    ws.mkdir(parents=True)
    org.hire(ROOT, "inorg", "In", "x", tools=["read", "write"], workspace=str(ws))
    _, prof, _ = run_profile(org, isolated_kiro, "inorg")
    assert {"capability": "fs_write", "effect": "deny", "match": [str(org.root), f"{org.root}/**"]} not in rules(prof)
    assert f"{org.root}/**" in rule(prof, "fs_read", "allow")["match"]


# --------------------------------------------------------------------------------- existing profiles
def test_an_existing_profile_of_another_name_is_left_alone_and_a_v3_one_is_written(org, tmp_path, isolated_kiro):
    agents = kiro_home_agents_dir(org.root)
    agents.mkdir(parents=True, exist_ok=True)
    old_name = kiro_profile_name(org.root, ["read"]) + "-x0ld0ld0"
    old_text = json.dumps({"name": old_name, "tools": ["@hirearchy", "read"], "hooks": {}}) + "\n"
    (agents / f"{old_name}.json").write_text(old_text)
    legacy = agents / "hirearchy-read.json"  # the legacy global profile: never touched
    legacy.write_text('{"name": "hirearchy-read"}\n')
    name, prof, _ = run_profile(org, isolated_kiro, "lead/writer")
    assert name != old_name and "permissions" in prof  # the profile name carries a hash of the rules, so new access = new profile
    assert (agents / f"{old_name}.json").read_text() == old_text and legacy.read_text() == '{"name": "hirearchy-read"}\n'


def test_a_profile_file_with_stale_content_is_rewritten(org, tmp_path, isolated_kiro):
    d = tmp_path / "agents"
    kw = dict(org=org, workspace=None, inputs=[tmp_path / "inputs"])
    name = ensure_kiro_profile(["read"], d, **kw)
    path = d / f"{name}.json"
    stale = json.loads(path.read_text())
    stale["permissions"]["rules"] = []  # same file name, other rules inside
    stale["hooks"] = {}
    path.write_text(json.dumps(stale))
    assert ensure_kiro_profile(["read"], d, **kw) == name
    fresh = json.loads(path.read_text())
    assert fresh["hooks"] == [] and rule(fresh, "fs_read", "allow")["match"][-1] == f"{org.root}/**"
