"""The ``org:`` line on the standard error: the commands that change the organization say which one before anything is read, also when the path is no
organization; the commands that only read say nothing (characterization over the real command line)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.cli import main
from orgmcp.kernel import ROOT

from ._org import Org, facade

CHANGING = [
    ["hire", "ceo", "dev", "--role", "Dev", "--charter", "Code."],
    ["task", "ceo", "--title", "T", "--goal", "g", "--acceptance", "a"],
    ["send", "ceo", "hello"],
    ["resume", "ceo"],
    ["inbox"],
    ["review"],
    ["upgrade-rules"],
    ["run", "--until-done"],
    ["kiro-profile"],
    ["define-service", "ceo", "weekly", "--description", "d"],
    ["request", "weekly"],
    ["feedback", "t-1", "accept"],
    ["retire-service", "ceo", "weekly", "--reason", "r"],
]
READING = [
    ["status"], ["health"], ["progress"], ["services"], ["inbox", "--keep"], ["review", "--dry-run"], ["upgrade-rules", "--dry-run"],
    ["check"], ["obs", "now"], ["obs", "events"], ["dash", "--once"],
]


@pytest.fixture
def org(tmp_path: Path) -> Org:
    org = facade().init(tmp_path / "org", "A mission.")
    org.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True)
    return org


def org_lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [line for line in capsys.readouterr().err.splitlines() if line.startswith("org: ")]


@pytest.mark.parametrize("argv", CHANGING, ids=lambda argv: " ".join(argv[:2]))
def test_a_command_that_changes_the_organization_names_it_first(org: Org, argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    try:
        main(["--root", str(org.root), *argv])
    except SystemExit:
        pass  # (the arguments need not make a valid change: the announcement comes before anything is looked at)
    assert org_lines(capsys) == [f"org: {org.root}"]


@pytest.mark.parametrize("argv", CHANGING, ids=lambda argv: " ".join(argv[:2]))
def test_it_names_a_path_that_is_no_organization_and_then_fails(tmp_path: Path, argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    nowhere = tmp_path / "nowhere"
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(nowhere), *argv])
    err = capsys.readouterr().err
    assert exit.value.code == 1 and err.splitlines()[0] == f"org: {nowhere}" and f"error: not an organization (no ORG.md): {nowhere}" in err


@pytest.mark.parametrize("argv", READING, ids=lambda argv: " ".join(argv[:2]))
def test_a_command_that_only_reads_says_nothing(org: Org, argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    main(["--root", str(org.root), *argv])
    assert org_lines(capsys) == []


def test_init_names_the_new_organization_before_it_makes_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "new"
    main(["init", str(target), "--mission", "m"])
    assert org_lines(capsys) == [f"org: {target.resolve()}"]


def test_the_organization_found_from_the_working_directory_is_the_one_named(org: Org, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(org.root)
    monkeypatch.delenv("ORG_ROOT", raising=False)
    main(["send", "ceo", "hi"])
    assert org_lines(capsys) == [f"org: {org.root}"]


def test_install_skill_names_no_organization(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["install-skill", "--dest", str(tmp_path / "skills")])
    assert org_lines(capsys) == []
