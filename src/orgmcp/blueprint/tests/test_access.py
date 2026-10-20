# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import copy

import pytest
import testkit
import yaml
from testkit.legacy.orgmcp.core import ROOT, Org, OrgError

from testkit.blueprint_world import bpm

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"


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


# -------------------------------------------------------------------------------------- report
def task_for(org, to, frm=ROOT):
    return org.delegate(frm, to, "T", "g", "a", budget=5)


def test_a_report_cannot_name_its_managers_workspace_files(team, dirs):
    (dirs["proj"] / "m.md").write_text("x")
    t = task_for(team, "lead/writer")
    with pytest.raises(OrgError, match="artifacts must be inside the organization"):
        team.report("lead/writer", t.id, "done", "ok", artifacts=[str(dirs["proj"] / "m.md")])


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
