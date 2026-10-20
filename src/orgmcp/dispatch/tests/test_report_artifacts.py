# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os

import pytest
from testkit.reach.orgmcp.core import ROOT, Org, OrgError


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


ENG = "ceo/eng"


# ------------------------------------------------------------------- QA-15: artifact scope
def _task(org):
    org.send(ROOT, "ceo", "budget", budget=5)
    return org.delegate("ceo", ENG, "t", "g", "a", budget=1)


def test_report_refuses_artifacts_outside_the_org_in_every_spelling(org, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("not part of the org")
    (org.dir(ENG) / "work" / "link.txt").symlink_to(outside)  # a symlink must not smuggle it in either
    task = _task(org)
    escaping = ["../" * 12 + str(outside).lstrip("/"), str(outside), "~/", "ceo/eng/work/link.txt", "/etc/hosts", "/nonexistent/xyz", "/"]
    for art in escaping:
        with pytest.raises(OrgError, match="inside the organization"):
            org.report(ENG, task.id, "done", "ok", [art])
    assert org.outstanding("ceo")[0].id == task.id  # nothing was reported


def test_report_accepts_artifacts_inside_the_org(org):
    org.write(ENG, "ceo/eng/work/out.md", "# Title\n\n- one two\n- three\n")
    task = _task(org)
    result = org.report(ENG, task.id, "done", "ok", ["work/out.md", "ceo/eng/work", str(org.dir(ENG) / "work" / "out.md")])
    assert "ceo/eng/work/out.md (4 words" in result.body and "ceo/eng/work/ (directory)" in result.body


def test_report_missing_artifact_inside_the_org_is_still_not_found(org):
    task = _task(org)
    with pytest.raises(OrgError, match="not found"):
        org.report(ENG, task.id, "done", "ok", ["work/missing.md"])


def test_read_and_report_artifacts_share_the_markup_free_count(org):
    body = "# Blurb\n\n- alpha beta\n- gamma\n1. delta\n"
    org.write(ENG, "ceo/eng/work/blurb.md", body)
    assert len(body.split()) == 9
    assert "5 words" in org.read("ceo/eng/work/blurb.md").splitlines()[0]
    task = _task(org)
    assert "(5 words" in org.report(ENG, task.id, "done", "ok", ["ceo/eng/work/blurb.md"]).body
