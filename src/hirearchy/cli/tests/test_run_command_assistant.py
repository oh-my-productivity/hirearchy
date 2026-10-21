# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.cli_world import main


def scheduler_line(org):
    """The status line of the organization's scheduler."""
    return org.runtime.scheduler_status.describe()


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    (work / "<folder-with-your-files>").mkdir(parents=True)  # the documents example's input folder
    (work / "<folder-with-your-data>").mkdir()  # the analysis example's input folder
    monkeypatch.chdir(work)
    return work


def test_cli_run_until_done_exits_and_logs_the_reason(org, capsys):
    main(["--root", str(org.root), "run", "--until-done"])  # nothing to do: returns at once
    assert "scheduler exiting: finished: no open tasks" in capsys.readouterr().out
    assert scheduler_line(org) == "scheduler: stopped (finished: no open tasks)"
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "run", "--until-done", "--once"])
