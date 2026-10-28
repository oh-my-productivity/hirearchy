# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, Org, OrgError, atomic_write


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


def test_a_manager_cannot_widen_a_charter_by_editing_it(team, dirs):
    ok = f"---\nrole: Writer\ntools: [read]\ninputs: ['{dirs['handbook/hr']}']\n---\nW.\n"
    with pytest.raises(OrgError, match="^refused: tools of lead/writer is the plan's"):  # (CHARTER-PLAN: a lead does not narrow the plan's tools either)
        team.write("lead", "lead/writer/AGENT.md", ok)
    atomic_write(team.dir("lead/writer") / "AGENT.md", ok)  # the user's own edit: the checks below are the confinement's, which run before the plan's
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
