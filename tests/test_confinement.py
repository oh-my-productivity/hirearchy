"""Workspace confinement and path semantics (workstream X1).

What kiro enforces (profiles): built-in ``write`` only under the workspace, ``read`` under workspace + inputs, never the
org directory; ``shell`` is not confinable. What orgmcp enforces itself: ``report``/``read`` path scope, authority
narrowing for ``inputs``. What is only instructed: the prompt's Files section and shell rule.
"""

import copy
import json
import re
from pathlib import Path

import pytest
import yaml

from orgmcp import blueprint as bpm
from orgmcp.core import ROOT, Org, OrgError
from orgmcp.scheduler import ensure_kiro_profile, kiro_profile_name, kiro_runner

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "blueprint-research.yaml"


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


# -------------------------------------------------------------------------------------- report
def task_for(org, to, frm=ROOT):
    return org.delegate(frm, to, "T", "g", "a", budget=5)


def test_a_report_cannot_name_its_managers_workspace_files(team, dirs):
    (dirs["proj"] / "m.md").write_text("x")
    t = task_for(team, "lead/writer")
    with pytest.raises(OrgError, match="artifacts must be inside the organization"):
        team.report("lead/writer", t.id, "done", "ok", artifacts=[str(dirs["proj"] / "m.md")])


# --------------------------------------------------------------------------------------- prompt
def test_prompt_has_a_files_section_with_workspace_and_inputs(team, dirs):
    text = team.run_prompt("lead/writer", [])
    assert "- Files:" in text
    assert f"Workspace (kiro read/write/shell, and the working directory of kiro tools): `{dirs['proj/out']}`" in text
    assert f"Read-only inputs (kiro `read` or orgmcp `org_read` by absolute path): `{dirs['handbook/hr']}`" in text
    assert "`lead/writer/MEMORY.md`" in text and "`lead/writer/work/` (orgmcp `org_write` only)" in text
    assert "Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by absolute path." in text
    assert "kiro `write` is limited to the workspace" in text and "cannot confine" not in text.split("# New messages")[0].split("- Files:")[1]


def test_prompt_states_the_shell_rule_only_for_agents_with_shell(team, dirs):
    team.hire("lead", "dev", "Dev", "x", tools=["read", "write", "shell"], workspace=str(dirs["proj/out"]))
    assert "`shell`, which the runtime cannot confine" in team.run_prompt("lead/dev", [])
    assert "cannot confine" not in team.run_prompt("lead/writer", [])


def test_prompt_has_no_files_section_without_workspace_or_inputs(team):
    team.hire("lead", "plain", "Plain", "x")
    assert "- Files:" not in team.run_prompt("lead/plain", []) and "- Files:" not in team.whoami("lead/plain")
    assert "- Files:" in team.whoami("lead")


def test_inputs_only_agent_is_told_it_has_no_workspace(team, dirs):
    team.hire("lead", "ro", "RO", "x", inputs=[str(dirs["handbook/hr"])])
    text = team.state_summary("lead/ro")
    assert "You have no workspace" in text and f"`{dirs['handbook/hr']}`" in text


# ------------------------------------------------------------------------------------ blueprint
@pytest.fixture
def bp(tmp_path, dirs):
    (tmp_path / "deliverables").mkdir(exist_ok=True)
    out = yaml.safe_load(EXAMPLE.read_text())
    out["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "g.md")
    return out


def issues_of(bp, tmp_path, **kw):
    return bpm.validate(bp, allowed_roots=[tmp_path], **kw)


def codes(issues, level=None):
    return {i.code for i in issues if level is None or i.level == level}


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


def test_needs_inputs_reach_every_agent_and_are_validated(bp, tmp_path, dirs):
    bp = mutate(bp, lambda b: b["needs"].update(inputs=[str(dirs["handbook"])]))
    assert not bpm.errors(issues_of(bp, tmp_path))
    roots = [tmp_path]
    agents = bpm._resolve(bp, None, roots, [])
    assert [a.inputs for a in agents] == [[str(dirs["handbook"])]] * len(agents)


@pytest.mark.parametrize("value,code", [("handbook", "path"), ("/etc", "path-root"), ("{missing}", "inputs")])
def test_bad_inputs_are_errors(bp, tmp_path, value, code):
    value = value.format(missing=tmp_path / "missing-dir")
    issues = issues_of(mutate(bp, lambda b: b["needs"].update(inputs=[value])), tmp_path)
    assert code in codes(issues, "error")


def test_inputs_inside_the_org_are_refused(bp, tmp_path, dirs):
    o = Org.init(tmp_path / "org", "x")
    issues = issues_of(mutate(bp, lambda b: b["needs"].update(inputs=[str(o.root / "ceo")])), tmp_path, org=o)
    assert "path-root" in codes(issues, "error")


def test_an_input_overlapping_a_workspace_is_an_error_unless_allowed(bp, tmp_path, dirs):
    def with_ws(inp):
        return mutate(bp, lambda b: (b["needs"].update(workspace=str(dirs["proj"]), inputs=[inp]),
                                     b["agents"][0]["children"][0].update(tools=["read", "write"])))

    assert "inputs-overlap" in codes(issues_of(with_ws(str(dirs["proj/out"])), tmp_path), "error")  # inside the workspace
    assert "inputs-overlap" in codes(issues_of(with_ws(str(tmp_path)), tmp_path), "error")  # containing it
    ok = issues_of(with_ws({"path": str(dirs["proj/out"]), "allow_overlap": True}), tmp_path)
    assert "inputs-overlap" not in codes(ok)
    assert "inputs-overlap" not in codes(issues_of(with_ws(str(dirs["handbook"])), tmp_path))


def test_agent_inputs_must_be_inside_its_managers(bp, tmp_path, dirs):
    def f(b):
        b["needs"]["inputs"] = [str(dirs["handbook/hr"])]
        b["agents"][0]["inputs"] = [str(dirs["handbook/hr"])]
        b["agents"][0]["children"][0]["inputs"] = [str(dirs["handbook"])]  # wider than the manager's
    assert "authority" in codes(issues_of(mutate(bp, f), tmp_path), "error")


def test_a_code_reviewer_works_in_the_project_workspace_without_write(tmp_path, dirs):
    from testkit.blueprints import code_bp  # same code blueprint the other tests use
    agents = {a.addr: a for a in bpm._resolve(code_bp(tmp_path), None, [tmp_path], [])}
    ws = str((tmp_path / "proj").resolve())
    # the code-reviewer template holds `shell` (it runs the tests), so like the engineer it needs the workspace; it has
    # no built-in `write`, so kiro can only let it read there
    assert agents["lead/cr"].tools == ["read", "shell"]
    assert agents["lead/cr"].workspace == ws and agents["lead/cr"].inputs == []
    assert agents["lead/dev"].workspace == ws and agents["lead/dev"].inputs == []
    assert bpm._access(agents["lead/cr"]) == f"kiro read only in {ws} and in the organization's own files (read-only); shell NOT confined (instructed only)"


def test_a_reader_without_shell_sees_the_project_read_only(tmp_path, dirs):
    from testkit.blueprints import code_bp
    b = code_bp(tmp_path)
    b["agents"][0]["children"][2] = {"name": "cr", "template": "reviewer", "tools": ["read"]}
    agents = {a.addr: a for a in bpm._resolve(b, None, [tmp_path], [])}
    ws = str((tmp_path / "proj").resolve())
    assert agents["lead/cr"].workspace is None and agents["lead/cr"].inputs == [ws]


def test_warning_for_built_in_write_on_a_non_code_goal(bp, tmp_path, dirs):
    plain = issues_of(bp, tmp_path)
    assert "write-noncode" not in codes(plain) and "shell-unconfined" not in codes(plain)
    with_write = mutate(bp, lambda b: (b["needs"].update(workspace=str(dirs["proj"])),
                                       b["agents"][0]["children"][1].update(tools=["write"])))
    issues = issues_of(with_write, tmp_path)
    assert "write-noncode" in codes(issues, "warning") and not bpm.errors(issues)
    msg = next(i.message for i in issues if i.code == "write-noncode")
    assert "lead/writer" in msg and "orgmcp `write`" in msg


def test_warning_when_shell_is_granted(tmp_path):
    from testkit.blueprints import code_bp
    issues = bpm.validate(code_bp(tmp_path), allowed_roots=[tmp_path])
    warn = next(i for i in issues if i.code == "shell-unconfined")
    assert warn.level == "warning" and "lead/dev" in warn.message and "instructed in the charter and prompt, not enforced" in warn.message
    assert "write-noncode" not in codes(issues)  # a code goal needs write


def test_apply_writes_inputs_into_charters_and_confines_readers(bp, tmp_path, dirs):
    o = Org.init(tmp_path / "org", "x", {"poll_seconds": 0.05})
    bp = mutate(bp, lambda b: b["needs"].update(inputs=[str(dirs["handbook"])]))
    bpm.apply(o, bp, allowed_roots=[tmp_path])
    for a in o.agents():
        assert o.charter(a)[0].get("inputs") == [str(dirs["handbook"])], a
    assert o.inputs_of("lead/researcher") == [dirs["handbook"]]


def test_apply_confines_a_reader_to_the_authors_workspace_read_only(tmp_path):
    from testkit.blueprints import code_bp
    o = Org.init(tmp_path / "org", "x", {"poll_seconds": 0.05})
    b = code_bp(tmp_path)
    b["needs"].pop("workspace")
    b["agents"][0]["children"] = [{"name": "dev", "template": "engineer", "workspace": str(tmp_path / "proj")},
                                  {"name": "qa", "template": "tester", "workspace": str(tmp_path / "proj")},
                                  {"name": "cr", "template": "reviewer", "tools": ["read"]}]
    bpm.apply(o, b, allowed_roots=[tmp_path])
    meta, _ = o.charter("lead/cr")
    # confined (no legacy unconfined read) and a verifier reads what it reviews: the authors' workspace, read-only
    assert meta["inputs"] == [str((tmp_path / "proj").resolve())] and "workspace" not in meta


def test_plan_shows_an_access_line_per_agent(bp, tmp_path, dirs):
    bp = mutate(bp, lambda b: (b["needs"].update(workspace=str(dirs["proj"]), inputs=[str(dirs["handbook"])]),
                               b["agents"][0]["children"][1].update(tools=["read", "write", "shell"])))
    plan = bpm.render_plan(bp, bpm.validate(bp, allowed_roots=[tmp_path]), allowed_roots=[tmp_path])
    assert f"Access: kiro write only in {dirs['proj']}; kiro read only in {dirs['proj']}, {dirs['handbook']} and in the organization's own files (read-only); shell NOT confined (instructed only)" in plan
    assert f"Access: read-only inputs (orgmcp read): {dirs['handbook']}" in plan


def test_charter_states_inputs_and_the_shell_rule(tmp_path):
    from testkit.blueprints import code_bp
    o = Org.init(tmp_path / "org", "x", {"poll_seconds": 0.05})
    b = code_bp(tmp_path)
    hb = tmp_path / "docs"
    hb.mkdir()
    b["needs"]["inputs"] = [str(hb)]
    bpm.apply(o, b, allowed_roots=[tmp_path])
    body = o.charter("lead/dev")[1]
    assert f"Read-only inputs: {hb.resolve()}" in body and "shell is not confined by the runtime" in body
    assert "never into the workspace" in body
