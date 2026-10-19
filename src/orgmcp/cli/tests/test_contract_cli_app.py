"""Contract of ``CliApp``: the line names the command, the command runs, its end is recorded, an ``OrgError`` is a message and the status 1.
Over the program made of three commands (ok, bad, exit) and fakes of its ports."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.cli import CliApp
from orgmcp.cli._ports import Arguments
from orgmcp.cli.testing import IMPLEMENTATIONS, CliWorld



@pytest.fixture(params=IMPLEMENTATIONS[CliApp], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> CliWorld:
    made = cast(CliWorld, request.param(tmp_path))
    assert isinstance(made.app, CliApp)
    return made


def test_the_command_the_line_names_runs_with_the_arguments_of_the_line(w: CliWorld) -> None:
    w.app.main(["--root", "/some/org", "ok", "--code", "7"])
    ran = w.commands["ok"].ran
    assert len(ran) == 1 and ran[0].root == "/some/org" and ran[0].cmd == "ok" and ran[0].code == "7"
    assert w.commands["exit"].ran == [] and w.commands["bad"].ran == []


def test_the_process_is_named_cli_and_the_end_of_a_command_is_recorded(w: CliWorld) -> None:
    w.label.set("mcp")
    w.clock.advance(5)
    w.app.main(["ok"])
    assert w.label.get() == "cli" and w.recorder.records == [("ok", 5.0, None)]  # started at the time of the clock, no failure
    assert w.out.events == []


def test_an_org_error_is_a_message_on_the_standard_error_and_the_status_1(w: CliWorld) -> None:
    with pytest.raises(SystemExit) as exit:
        w.app.main(["bad"])
    assert exit.value.code == 1
    assert w.out.stderr == "error: no such agent: nobody\n" and w.out.stdout == ""
    ((name, _, failure),) = w.recorder.records
    assert name == "bad" and type(failure).__name__ == "OrgError" and str(failure) == "no such agent: nobody"


@pytest.mark.parametrize("code", [None, "0"])
def test_a_command_that_exits_with_success_is_a_success(w: CliWorld, code: str | None) -> None:
    with pytest.raises(SystemExit) as exit:
        w.app.main(["exit", *([] if code is None else ["--code", code])])
    assert not exit.value.code and w.recorder.records[0][2] is None and w.out.events == []


def test_a_command_that_exits_with_a_status_keeps_it_and_is_a_failure(w: CliWorld) -> None:
    with pytest.raises(SystemExit) as exit:
        w.app.main(["exit", "--code", "3"])
    assert exit.value.code == 3
    failure = w.recorder.records[0][2]
    assert isinstance(failure, RuntimeError) and str(failure) == "exit 3" and w.out.events == []


def test_another_exception_is_recorded_and_raised_again(w: CliWorld) -> None:
    def explode(args: Arguments) -> None:
        raise KeyError("boom")

    w.commands["ok"].action = explode
    with pytest.raises(KeyError):
        w.app.main(["ok"])
    failure = w.recorder.records[0][2]
    assert isinstance(failure, KeyError) and w.out.events == []


def test_a_line_that_does_not_parse_is_the_status_2_and_is_not_recorded(w: CliWorld) -> None:
    with pytest.raises(SystemExit) as exit:
        w.app.main(["frobnicate"])
    assert exit.value.code == 2 and w.recorder.records == [] and w.label.get() == "cli"


def test_no_command_is_an_error(w: CliWorld) -> None:
    with pytest.raises(SystemExit) as exit:
        w.app.main([])
    assert exit.value.code == 2 and w.recorder.records == []


def test_help_lists_the_commands_in_the_order_they_were_given(w: CliWorld, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit:
        w.app.main(["--help"])
    text = capsys.readouterr().out
    assert exit.value.code == 0 and "{ok,bad,exit}" in text and "usage: orgmcp" in text and w.recorder.records == []
