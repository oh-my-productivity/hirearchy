# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from pathlib import Path

import pytest
from testkit.legacy.orgmcp.core import ROOT, Org, OrgError


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
