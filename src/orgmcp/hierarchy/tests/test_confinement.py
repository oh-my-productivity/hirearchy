# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

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


def test_a_confined_hirer_never_hands_down_an_unconfined_read(team):
    team.hire("lead", "reader", "R", "x", tools=["read"])  # no workspace, no inputs given
    meta, _ = team.charter("lead/reader")
    assert meta["inputs"] == [] and not Org.unconfined_read(meta)
    team.hire(ROOT, "old", "Old", "x", tools=["read"])  # root's own hire keeps the legacy shape
    assert "inputs" not in team.charter("old")[0]
