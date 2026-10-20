# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.cli_world import main
from testkit.legacy.orgmcp.core import ROOT


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
