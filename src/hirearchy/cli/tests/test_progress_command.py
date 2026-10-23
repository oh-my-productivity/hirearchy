# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.cli_world import main
from testkit.reach.hirearchy.core import ROOT


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


def test_cli_progress(org, task, capsys):
    main(["--root", str(org.root), "progress"])
    assert capsys.readouterr().out.startswith('"Write the report": working.')
    main(["--root", str(org.root), "progress", task.id])
    assert f"(task {task.id})" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "progress", "nope"])


def test_cli_progress_shows_the_deliverable_note(org, task, capsys, tmp_path):
    """A contract names a folder; a file there that the team never wrote is named by `hirearchy progress` and by nothing else the terminal shows."""
    folder = tmp_path / "deliverables"
    folder.mkdir()
    org.define_service(
        ROOT, "ceo", "weekly-brief", description="A brief.", inputs=[], acceptance=["At most 600 words"],
        deliverable={"description": "one markdown file", "path": str(folder)}, budget=10,
    )
    (folder / "notes.md").write_text("the user's own notes\n", encoding="utf-8")
    main(["--root", str(org.root), "progress"])
    out = capsys.readouterr().out
    assert f'Deliverable folder "{folder.resolve()}" (service `weekly-brief`): 1 file(s) the team did not deliver as checked.' in out
    assert '- "notes.md": never written by the team' in out
    main(["--root", str(org.root), "status"])
    assert "Deliverable" not in capsys.readouterr().out  # the terminal's status is the tree, the tasks and the scheduler
