# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import re

import pytest
from testkit.kiro_world import ensure_kiro_profile, kiro_home_agents_dir, kiro_part, kiro_profile_name, kiro_runner
from testkit.reach.hirearchy.core import ROOT, Org


def profile_of(org, name):
    """A profile of the organization: they are in its kiro home, not in ``~/.kiro/agents``."""
    return json.loads((kiro_home_agents_dir(org.root) / f"{name}.json").read_text())


def rules(prof):
    return prof["permissions"]["rules"]


def rule(prof, capability, effect, *, exclude=None):
    """The one rule of ``capability``/``effect``; ``exclude=True``/``False`` picks the one with/without an ``exclude`` key."""
    found = [r for r in rules(prof) if r["capability"] == capability and r["effect"] == effect and (exclude is None or ("exclude" in r) == exclude)]
    assert len(found) == 1, (capability, effect, found)
    return found[0]


def run_profile(org, isolated_kiro, addr):
    argv, cwd, env = kiro_runner()(org, addr, "P")
    cmd = kiro_part(argv)
    return profile_of(org, cmd[cmd.index("--agent") + 1]), cmd, cwd, env


@pytest.fixture
def dirs(tmp_path):
    d = {n: (tmp_path / n).resolve() for n in ("proj", "proj/out", "handbook", "handbook/hr", "elsewhere")}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    (d["handbook"] / "a.md").write_text("one two three\n")
    (d["handbook/hr"] / "b.md").write_text("four five\n")
    return d


@pytest.fixture
def team(tmp_path, dirs):
    """root -> lead (ws proj, inputs handbook) -> writer (ws proj/out, inputs handbook/hr); root -> other (ws elsewhere)."""
    o = Org.init(tmp_path / "org", "confinement", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "shell", "write"], workspace=str(dirs["proj"]),
           inputs=[str(dirs["handbook"])])
    o.hire("lead", "writer", "Writer", "Write.", tools=["read", "write"], workspace=str(dirs["proj/out"]),
           inputs=[str(dirs["handbook/hr"])])
    o.hire(ROOT, "other", "Other", "Other.", tools=["write"], workspace=str(dirs["elsewhere"]))
    return o


# ------------------------------------------------------------------------------------------ profiles
def test_agent_with_file_tools_gets_a_confining_profile(team, dirs, isolated_kiro):
    prof, cmd, cwd, env = run_profile(team, isolated_kiro, "lead/writer")
    name = cmd[cmd.index("--agent") + 1]
    assert re.fullmatch(rf"{re.escape(kiro_profile_name(team.root, ['read', 'write']))}-x[0-9a-f]{{8}}", name)
    assert prof["name"] == name and prof["description"].startswith(f"internal: used by the hirearchy scheduler for {team.root}")
    assert prof["tools"] == ["@hirearchy", "read", "write"] and "permissions" in prof
    out, hb, org = dirs["proj/out"], dirs["handbook/hr"], team.root
    assert rule(prof, "fs_write", "allow")["match"] == [f"{out}/**"]
    assert {"capability": "fs_write", "effect": "deny", "match": [str(org), f"{org}/**"]} in rules(prof)
    # read also reaches the organization itself (read-only), exactly what hirearchy `read` may open
    reach = [str(out), f"{out}/**", str(hb), f"{hb}/**", str(org), f"{org}/**"]
    assert rule(prof, "fs_read", "allow")["match"] == reach
    assert rule(prof, "fs_read", "deny")["match"] == ["/**"] and rule(prof, "fs_read", "deny")["exclude"] == reach
    assert rule(prof, "fs_write", "deny", exclude=True) == {"capability": "fs_write", "effect": "deny", "match": ["/**"], "exclude": [f"{out}/**"]}
    # the env contract is unchanged
    assert prof["mcpServers"]["hirearchy"]["env"] == {"ORG_ROOT": str(team.root), "ORG_REQUIRE_AGENT": "1"}
    assert prof["includeMcpJson"] is False and cwd == team.runtime.kiro_places.scratch("lead/writer") != out  # kiro starts in an empty scratch directory
    assert env["ORG_AGENT"] == "lead/writer" and env["ORG_ROOT"] == str(team.root)


def test_inputs_are_readable_but_never_writable(team, dirs, isolated_kiro):
    prof, *_ = run_profile(team, isolated_kiro, "lead")
    hb = dirs["handbook"]
    assert str(hb) in rule(prof, "fs_read", "allow")["match"] and f"{hb}/**" in rule(prof, "fs_read", "allow")["match"]
    assert not any(str(hb) in p for p in rule(prof, "fs_write", "allow")["match"])
    assert rule(prof, "fs_write", "allow")["match"] == [f"{dirs['proj']}/**"]


def test_profiles_are_per_access_not_per_tool_set(team, dirs, isolated_kiro):
    a = run_profile(team, isolated_kiro, "lead")[1]
    b = run_profile(team, isolated_kiro, "lead/writer")[1]
    assert a[a.index("--agent") + 1] != b[b.index("--agent") + 1]  # same tools, different access
    team.hire("lead", "twin", "Twin", "x", tools=["read", "write"], workspace=str(dirs["proj/out"]), inputs=[str(dirs["handbook/hr"])])
    t = run_profile(team, isolated_kiro, "lead/twin")[1]
    assert t[t.index("--agent") + 1] == b[b.index("--agent") + 1]  # same tools and access: shared profile


def test_shell_is_allowed_by_one_rule_and_is_not_confined(team, dirs, isolated_kiro):
    team.hire("lead", "dev", "Dev", "x", tools=["read", "write", "shell"], workspace=str(dirs["proj/out"]))
    prof, *_ = run_profile(team, isolated_kiro, "lead/dev")
    assert prof["tools"] == ["@hirearchy", "read", "write", "shell"]
    assert rule(prof, "shell", "allow") == {"capability": "shell", "match": ["*"], "effect": "allow"}  # kiro has no path rule for it


def test_write_without_workspace_is_allowed_nowhere(team, isolated_kiro):
    team.hire("lead", "scribe", "Scribe", "x", tools=["write"])
    prof, _, cwd, _ = run_profile(team, isolated_kiro, "lead/scribe")
    assert not [r for r in rules(prof) if r["capability"] == "fs_write" and r["effect"] == "allow"]
    assert {"capability": "fs_write", "effect": "deny", "match": ["/**"]} in rules(prof) and cwd == team.runtime.kiro_places.scratch("lead/scribe")


def test_read_with_empty_inputs_reads_only_the_organization(team, isolated_kiro):
    team.hire("lead", "peek", "Peek", "x", tools=["read"], inputs=[])
    prof, *_ = run_profile(team, isolated_kiro, "lead/peek")
    # nothing outside the organization; the organization itself is readable (it is what hirearchy `read` serves)
    assert rule(prof, "fs_read", "allow")["match"] == [str(team.root), f"{team.root}/**"]
    assert prof["tools"] == ["@hirearchy", "read"]


def test_agents_without_built_in_file_tools_keep_the_shared_profile(team, isolated_kiro):
    team.hire(ROOT, "web", "Web", "x", tools=["web_fetch", "web_search"])
    prof, cmd, *_ = run_profile(team, isolated_kiro, "web")
    assert cmd[cmd.index("--agent") + 1] == kiro_profile_name(team.root, ["web_fetch", "web_search"])
    assert prof["tools"] == ["@hirearchy", "web"] and not any(r["capability"].startswith("fs_") for r in rules(prof))
    assert rule(prof, "web_fetch", "allow")["match"] == ["*"] and rule(prof, "web_search", "allow")["match"] == ["*"]
    team.hire("lead", "plain", "Plain", "x")
    plain = run_profile(team, isolated_kiro, "lead/plain")[1]
    assert plain[plain.index("--agent") + 1] == kiro_profile_name(team.root, [])  # shared with web-less agents


def test_legacy_read_only_charter_is_confined_to_the_org(team, isolated_kiro):
    """No workspace and no `inputs` key: it used to get the unconfined profile; under V3 it reads the organization only."""
    (team.dir("lead") / "legacy").mkdir()
    (team.dir("lead") / "legacy" / "AGENT.md").write_text("---\nrole: Old\ntools: [read]\n---\nOld.\n")
    prof, cmd, *_ = run_profile(team, isolated_kiro, "lead/legacy")
    assert re.fullmatch(rf"{re.escape(kiro_profile_name(team.root, ['read']))}-x[0-9a-f]{{8}}", cmd[cmd.index("--agent") + 1])
    assert rule(prof, "fs_read", "allow")["match"] == [str(team.root), f"{team.root}/**"]
    assert "permissions" in prof


def test_workspace_inside_the_org_is_not_denied(team, isolated_kiro):
    ws = team.dir("lead") / "work" / "site"
    ws.mkdir(parents=True)
    team.hire(ROOT, "inorg", "In", "x", tools=["write"], workspace=str(ws))
    prof, *_ = run_profile(team, isolated_kiro, "inorg")
    assert {"capability": "fs_write", "effect": "deny", "match": [str(team.root), f"{team.root}/**"]} not in rules(prof)
    assert rule(prof, "fs_write", "allow")["match"] == [f"{ws.resolve()}/**"]


def test_ensure_kiro_profile_is_idempotent_for_confined_profiles(team, dirs, tmp_path):
    d = tmp_path / "agents"
    kw = dict(org=team, workspace=dirs["proj"], inputs=[dirs["handbook"]])
    name = ensure_kiro_profile(["read", "write"], d, **kw)
    path = d / f"{name}.json"
    mtime = path.stat().st_mtime_ns
    assert ensure_kiro_profile(["write", "read"], d, **kw) == name and path.stat().st_mtime_ns == mtime
    assert ensure_kiro_profile(["read", "write"], d, **{**kw, "inputs": []}) != name
    assert len(list(d.iterdir())) == 2
