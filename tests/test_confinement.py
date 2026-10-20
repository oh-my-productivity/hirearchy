"""Workspace confinement and path semantics (workstream X1).

What kiro enforces (profiles): built-in ``write`` only under the workspace, ``read`` under workspace + inputs, never the
org directory; ``shell`` is not confinable. What orgmcp enforces itself: ``report``/``read`` path scope, authority
narrowing for ``inputs``. What is only instructed: the prompt's Files section and shell rule.
"""

import json
import os
import re
from pathlib import Path

import pytest

from orgmcp.core import ROOT, Org, OrgError, atomic_write
from orgmcp.scheduler import ensure_kiro_profile, kiro_profile_name, kiro_runner


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


# ----------------------------------------------------------------------------------- authority
def test_a_reports_inputs_must_be_inside_its_managers_inputs_or_workspace(team, dirs):
    team.hire("lead", "a", "A", "x", inputs=[str(dirs["handbook/hr"])])  # inside the manager's inputs
    team.hire("lead", "b", "B", "x", inputs=[str(dirs["proj/out"])])  # inside the manager's workspace
    with pytest.raises(OrgError, match="inputs must be inside your inputs or workspace"):
        team.hire("lead", "c", "C", "x", inputs=[str(dirs["elsewhere"])])
    with pytest.raises(OrgError, match="absolute"):
        team.hire("lead", "d", "D", "x", inputs=["handbook"])
    assert not team.exists("lead/c") and not team.exists("lead/d")


def test_inputs_need_something_to_be_inside_and_stay_out_of_the_org(team, dirs):
    team.hire(ROOT, "bare", "Bare", "x", can_hire=True)
    with pytest.raises(OrgError, match="no workspace or inputs"):
        team.hire("bare", "kid", "Kid", "x", inputs=[str(dirs["handbook"])])
    with pytest.raises(OrgError, match="overlap the organization"):
        team.hire(ROOT, "intruder", "I", "x", inputs=[str(team.dir("lead"))])
    with pytest.raises(OrgError, match="overlap the organization"):
        team.hire(ROOT, "intruder", "I", "x", inputs=[str(team.root.parent)])


def test_a_manager_cannot_widen_a_charter_by_editing_it(team, dirs):
    ok = f"---\nrole: Writer\ntools: [read]\ninputs: ['{dirs['handbook/hr']}']\n---\nW.\n"
    team.write("lead", "lead/writer/AGENT.md", ok)
    wide = f"---\nrole: Writer\ntools: [read]\ninputs: ['{dirs['elsewhere']}']\n---\nW.\n"
    with pytest.raises(OrgError, match="inputs must be inside"):
        team.write("lead", "lead/writer/AGENT.md", wide)
    omitted = "---\nrole: Writer\ntools: [read]\n---\nW.\n"  # leaving `inputs` out keeps the old (confined) list
    team.write("lead", "lead/writer/AGENT.md", omitted)
    assert team.charter("lead/writer")[0]["inputs"] == [str(dirs["handbook/hr"])]
    # a legacy charter (read, no workspace, no `inputs` key) cannot be rewritten by a confined manager
    legacy = "---\nrole: Writer\ntools: [read]\n---\nW.\n"
    atomic_write(team.dir("lead/writer") / "AGENT.md", legacy)
    with pytest.raises(OrgError, match="needs an `inputs:` list"):
        team.write("lead", "lead/writer/AGENT.md", omitted)


def test_a_confined_hirer_never_hands_down_an_unconfined_read(team):
    team.hire("lead", "reader", "R", "x", tools=["read"])  # no workspace, no inputs given
    meta, _ = team.charter("lead/reader")
    assert meta["inputs"] == [] and not Org.unconfined_read(meta)
    team.hire(ROOT, "old", "Old", "x", tools=["read"])  # root's own hire keeps the legacy shape
    assert "inputs" not in team.charter("old")[0]


# -------------------------------------------------------------------------------------- report
def task_for(org, to, frm=ROOT):
    return org.delegate(frm, to, "T", "g", "a", budget=5)


def test_report_accepts_an_absolute_path_in_its_own_workspace(team, dirs):
    t = task_for(team, "lead")
    f = dirs["proj"] / "guide.md"
    f.write_text("# Title\none two three four five\n")
    msg = team.report("lead", t.id, "done", "ok", artifacts=[str(f), str(dirs["proj"])])
    assert f"- {f} (6 words, modified " in msg.body and "NOT modified" not in msg.body
    assert f"- {dirs['proj']}/ (directory)" in msg.body


def test_report_still_accepts_org_paths_and_annotates_staleness(team):
    t = task_for(team, "lead")
    team.write("lead", "lead/work/x.md", "a b c")
    msg = team.report("lead", t.id, "done", "ok", artifacts=["lead/work/x.md"])
    assert "- lead/work/x.md (3 words, modified " in msg.body


def test_report_marks_a_workspace_file_not_modified_since_the_task(team, dirs):
    f = dirs["proj"] / "old.md"
    f.write_text("old")
    os.utime(f, (1_000_000_000, 1_000_000_000))
    t = task_for(team, "lead")
    msg = team.report("lead", t.id, "done", "ok", artifacts=[str(f)])
    assert "NOT modified since this task was assigned" in msg.body


def test_report_refuses_everything_else_outside_the_org(team, dirs, tmp_path):
    t = task_for(team, "lead")
    for target in (dirs["elsewhere"] / "f.md",  # another agent's workspace
                   dirs["handbook"] / "a.md",  # an input: read-only, not an artifact
                   tmp_path / "f.md"):  # anywhere else
        target.write_text("x")
        with pytest.raises(OrgError, match="artifacts must be inside the organization"):
            team.report("lead", t.id, "done", "ok", artifacts=[str(target)])


def test_report_accepts_files_in_a_subfolder_of_its_own_workspace(team, dirs):
    t = task_for(team, "lead")
    (dirs["proj/out"] / "w.md").write_text("x y")
    assert "w.md (2 words" in team.report("lead", t.id, "done", "ok", artifacts=[str(dirs["proj/out"] / "w.md")]).body


def test_report_refusal_does_not_probe_the_host(team, dirs):
    t = task_for(team, "lead")
    for p in ("/etc/passwd", "/etc/nope-" + "x" * 8, str(dirs["elsewhere"] / "missing.md")):
        with pytest.raises(OrgError, match="artifacts must be inside the organization"):  # same answer, exists or not
            team.report("lead", t.id, "done", "ok", artifacts=[p])


def test_report_workspace_paths_need_an_agent_with_a_workspace(team, dirs):
    team.hire("lead", "free", "Free", "x")
    t = task_for(team, "lead/free")
    f = dirs["proj"] / "f.md"
    f.write_text("x")
    with pytest.raises(OrgError, match="you have no workspace"):
        team.report("lead/free", t.id, "done", "ok", artifacts=[str(f)])


def test_report_refuses_a_symlink_that_leaves_the_workspace(team, dirs):
    t = task_for(team, "lead")
    secret = dirs["elsewhere"] / "secret.md"
    secret.write_text("s")
    (dirs["proj"] / "escape.md").symlink_to(secret)
    with pytest.raises(OrgError, match="artifacts must be inside"):
        team.report("lead", t.id, "done", "ok", artifacts=[str(dirs["proj"] / "escape.md")])


def test_report_not_found_points_at_the_workspace_copy(team, dirs):
    """The study-C failure: the agent wrote `lead/work/x.md` into the workspace with kiro's write, then reported it."""
    (dirs["proj"] / "lead" / "work").mkdir(parents=True)
    (dirs["proj"] / "lead" / "work" / "x.md").write_text("misplaced")
    t = task_for(team, "lead")
    with pytest.raises(OrgError, match=r"artifact not found.*exists in your workspace: report it by absolute path"):
        team.report("lead", t.id, "done", "ok", artifacts=["lead/work/x.md"])


# ---------------------------------------------------------------------------------------- read
def test_read_absolute_paths_in_workspace_inputs_and_reports_workspaces(team, dirs):
    (dirs["proj"] / "mine.md").write_text("a b\n")
    (dirs["proj/out"] / "theirs.md").write_text("a b c\n")
    assert "2 words" in team.read(str(dirs["proj"] / "mine.md"), actor="lead").splitlines()[0]
    assert "three" in team.read(str(dirs["handbook"] / "a.md"), actor="lead")  # its input
    assert "a.md" in team.read(str(dirs["handbook"]), actor="lead")  # a directory listing
    assert "3 words" in team.read(str(dirs["proj/out"] / "theirs.md"), actor="lead")  # its report's workspace
    assert "3 words" in team.read(str(dirs["proj/out"] / "theirs.md"), actor="lead/writer")  # its own
    assert "four five" in team.read(str(dirs["handbook/hr"] / "b.md"), actor="lead/writer")  # its own input


def test_read_refuses_the_rest_outside_the_org(team, dirs, tmp_path):
    (dirs["elsewhere"] / "x.md").write_text("x")
    (dirs["proj"] / "mine.md").write_text("m")
    for who, path in (
        ("lead", dirs["elsewhere"] / "x.md"),  # another agent's workspace, not in its subtree
        ("lead/writer", dirs["proj"] / "mine.md"),  # its manager's workspace is not its own
        ("lead/writer", dirs["handbook"] / "a.md"),  # a parent input it was not given
        ("lead", Path("/etc/hosts")),
        ("lead", dirs["proj"] / ".." / "elsewhere" / "x.md"),  # traversal out of the workspace
        ("other", dirs["proj"] / "mine.md"),
    ):
        with pytest.raises(OrgError, match="you can only read inside the organization"):
            team.read(str(path), actor=who)


def test_read_symlink_out_of_a_workspace_is_refused(team, dirs):
    (dirs["elsewhere"] / "s.md").write_text("s")
    (dirs["proj"] / "link.md").symlink_to(dirs["elsewhere"] / "s.md")
    with pytest.raises(OrgError, match="you can only read"):
        team.read(str(dirs["proj"] / "link.md"), actor="lead")


def test_read_relative_paths_and_root_are_unchanged(team, dirs):
    team.write("lead", "lead/work/n.md", "x y")
    assert "2 words" in team.read("lead/work/n.md", actor="lead/writer")  # the whole org is readable, as before
    assert "n.md" in team.read("lead/work", actor="lead")
    assert team.read("lead/work/n.md").startswith("[lead/work/n.md: 2 words")
    with pytest.raises(OrgError, match="only read inside the organization"):  # root: the organization only
        team.read(str(dirs["proj"] / "mine.md"))
    with pytest.raises(OrgError, match="you can only read"):
        team.read("../outside.md", actor="lead")
    (dirs["proj"] / "p.md").write_text("p")
    assert team.read(str(dirs["proj"] / "p.md"), actor="lead").startswith(f"[{dirs['proj'] / 'p.md'}: 1 words")


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
