"""Workspace confinement and path semantics (workstream X1).

What kiro enforces (profiles): built-in ``write`` only under the workspace, ``read`` under workspace + inputs, never the
org directory; ``shell`` is not confinable. What orgmcp enforces itself: ``report``/``read`` path scope, authority
narrowing for ``inputs``. What is only instructed: the prompt's Files section and shell rule.
"""

import copy
import os
from pathlib import Path

import pytest
import yaml

from orgmcp import blueprint as bpm
from orgmcp.core import ROOT, Org, OrgError, atomic_write

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "blueprint-research.yaml"


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


def test_a_report_cannot_name_its_managers_workspace_files(team, dirs):
    (dirs["proj"] / "m.md").write_text("x")
    t = task_for(team, "lead/writer")
    with pytest.raises(OrgError, match="artifacts must be inside the organization"):
        team.report("lead/writer", t.id, "done", "ok", artifacts=[str(dirs["proj"] / "m.md")])


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
