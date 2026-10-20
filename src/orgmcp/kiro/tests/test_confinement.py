# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import re

import pytest
from testkit.kiro_world import ensure_kiro_profile, kiro_profile_name, kiro_runner
from testkit.reach.orgmcp.core import ROOT, Org


def profile_of(isolated_kiro, name):
    return json.loads((isolated_kiro / ".kiro" / "agents" / f"{name}.json").read_text())


def run_profile(org, isolated_kiro, addr):
    cmd, cwd, env = kiro_runner()(org, addr, "P")
    return profile_of(isolated_kiro, cmd[cmd.index("--agent") + 1]), cmd, cwd, env


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
    assert prof["name"] == name and prof["description"].startswith(f"internal: used by the orgmcp scheduler for {team.root}")
    # read/write are NOT in allowedTools (kiro ignores allowedPaths for a trusted tool); orgmcp is
    assert prof["tools"] == ["@orgmcp", "read", "write"] and prof["allowedTools"] == ["@orgmcp"]
    out, hb = dirs["proj/out"], dirs["handbook/hr"]
    deny = [str(team.root), f"{team.root}/**"]
    assert prof["toolsSettings"]["write"] == {"allowedPaths": [f"{out}/**"], "deniedPaths": deny}
    # read also reaches the organization itself (read-only), exactly what orgmcp `read` may open: no deny to beat the allow
    org = team.root
    assert prof["toolsSettings"]["read"] == {
        "allowedPaths": [str(out), f"{out}/**", str(hb), f"{hb}/**", str(org), f"{org}/**"], "deniedPaths": []}
    # the env contract is unchanged
    assert prof["mcpServers"]["orgmcp"]["env"] == {"ORG_ROOT": str(team.root), "ORG_REQUIRE_AGENT": "1"}
    assert prof["includeMcpJson"] is False and cwd == out
    assert env["ORG_AGENT"] == "lead/writer" and env["ORG_ROOT"] == str(team.root)


def test_inputs_are_readable_but_never_writable(team, dirs, isolated_kiro):
    prof, *_ = run_profile(team, isolated_kiro, "lead")
    hb = dirs["handbook"]
    assert str(hb) in prof["toolsSettings"]["read"]["allowedPaths"] and f"{hb}/**" in prof["toolsSettings"]["read"]["allowedPaths"]
    assert not any(str(hb) in p for p in prof["toolsSettings"]["write"]["allowedPaths"])
    assert prof["toolsSettings"]["write"]["allowedPaths"] == [f"{dirs['proj']}/**"]


def test_profiles_are_per_access_not_per_tool_set(team, dirs, isolated_kiro):
    a = run_profile(team, isolated_kiro, "lead")[1]
    b = run_profile(team, isolated_kiro, "lead/writer")[1]
    assert a[a.index("--agent") + 1] != b[b.index("--agent") + 1]  # same tools, different access
    team.hire("lead", "twin", "Twin", "x", tools=["read", "write"], workspace=str(dirs["proj/out"]), inputs=[str(dirs["handbook/hr"])])
    t = run_profile(team, isolated_kiro, "lead/twin")[1]
    assert t[t.index("--agent") + 1] == b[b.index("--agent") + 1]  # same tools and access: shared profile


def test_shell_stays_trusted_and_is_not_confined(team, dirs, isolated_kiro):
    team.hire("lead", "dev", "Dev", "x", tools=["read", "write", "shell"], workspace=str(dirs["proj/out"]))
    prof, *_ = run_profile(team, isolated_kiro, "lead/dev")
    assert prof["allowedTools"] == ["@orgmcp"] + ["shell"] and "shell" in prof["tools"]
    assert "shell" not in prof["toolsSettings"]  # kiro has no path rule for it


def test_write_without_workspace_is_allowed_nowhere(team, isolated_kiro):
    team.hire("lead", "scribe", "Scribe", "x", tools=["write"])
    prof, _, cwd, _ = run_profile(team, isolated_kiro, "lead/scribe")
    assert prof["toolsSettings"]["write"]["allowedPaths"] == [] and cwd == team.dir("lead/scribe")


def test_read_with_empty_inputs_reads_nothing(team, isolated_kiro):
    team.hire("lead", "peek", "Peek", "x", tools=["read"], inputs=[])
    prof, *_ = run_profile(team, isolated_kiro, "lead/peek")
    # nothing outside the organization; the organization itself is readable (it is what orgmcp `read` serves)
    assert prof["toolsSettings"]["read"]["allowedPaths"] == [str(team.root), f"{team.root}/**"]
    assert prof["allowedTools"] == ["@orgmcp"]


def test_agents_without_built_in_file_tools_keep_the_shared_profile(team, isolated_kiro):
    team.hire(ROOT, "web", "Web", "x", tools=["web_fetch", "web_search"])
    prof, cmd, *_ = run_profile(team, isolated_kiro, "web")
    assert cmd[cmd.index("--agent") + 1] == kiro_profile_name(team.root, ["web_fetch", "web_search"])
    assert prof["allowedTools"] == prof["tools"] == ["@orgmcp", "web_fetch", "web_search"] and "toolsSettings" not in prof
    team.hire("lead", "plain", "Plain", "x")
    assert run_profile(team, isolated_kiro, "lead/plain")[1][4] == kiro_profile_name(team.root, [])  # shared with web-less agents


def test_legacy_read_only_charter_keeps_todays_profile(team, isolated_kiro):
    """No workspace and no `inputs` key: nothing new in the charter, nothing new in the profile."""
    (team.dir("lead") / "legacy").mkdir()
    (team.dir("lead") / "legacy" / "AGENT.md").write_text("---\nrole: Old\ntools: [read]\n---\nOld.\n")
    prof, cmd, *_ = run_profile(team, isolated_kiro, "lead/legacy")
    assert cmd[cmd.index("--agent") + 1] == kiro_profile_name(team.root, ["read"])
    assert prof["allowedTools"] == ["@orgmcp", "read"] and "toolsSettings" not in prof


def test_workspace_inside_the_org_is_not_denied(team, isolated_kiro):
    ws = team.dir("lead") / "work" / "site"
    ws.mkdir(parents=True)
    team.hire(ROOT, "inorg", "In", "x", tools=["write"], workspace=str(ws))
    prof, *_ = run_profile(team, isolated_kiro, "inorg")
    assert prof["toolsSettings"]["write"]["deniedPaths"] == []


def test_ensure_kiro_profile_is_idempotent_for_confined_profiles(team, dirs, tmp_path):
    d = tmp_path / "agents"
    kw = dict(org=team, workspace=dirs["proj"], inputs=[dirs["handbook"]], confine=True)
    name = ensure_kiro_profile(["read", "write"], d, **kw)
    path = d / f"{name}.json"
    mtime = path.stat().st_mtime_ns
    assert ensure_kiro_profile(["write", "read"], d, **kw) == name and path.stat().st_mtime_ns == mtime
    assert ensure_kiro_profile(["read", "write"], d, **{**kw, "inputs": []}) != name
    assert len(list(d.iterdir())) == 2
