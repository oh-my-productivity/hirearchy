# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest

from orgmcp.cli import main


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    (work / "<folder-with-your-files>").mkdir(parents=True)  # the documents example's input folder
    (work / "<folder-with-your-data>").mkdir()  # the analysis example's input folder
    monkeypatch.chdir(work)
    return work


def test_cli_status_shows_the_scheduler(org, capsys):
    main(["--root", str(org.root), "run", "--until-done"])
    capsys.readouterr()
    main(["--root", str(org.root), "status"])
    assert "scheduler: stopped (finished: no open tasks)" in capsys.readouterr().out
