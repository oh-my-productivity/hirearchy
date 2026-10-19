"""The ``cli.command`` event of a real command line, in the real log of a real organization: for a success, an ``OrgError``, a ``SystemExit`` and any other
exception (characterization: the event was the same before the command line was a package)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.cli import main
from orgmcp.kernel import ROOT

from ._org import facade

from ._events import read_events


@pytest.fixture
def root(tmp_path: Path) -> Path:
    org = facade().init(tmp_path / "org", "A mission.")
    org.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True)
    return Path(org.root)


def commands(root: Path) -> list[dict[str, object]]:
    return read_events(root, "cli.command")


def test_a_success_is_recorded_as_one(root: Path) -> None:
    main(["--root", str(root), "status"])
    (event,) = commands(root)
    assert (event["command"], event["ok"], event["error"], event["error_type"]) == ("status", True, None, None)
    assert (event["proc"], event["actor"], event["run"], event["trace"]) == ("cli", "root", None, None) and event["ms"] >= 0  # type: ignore[operator]


def test_an_org_error_is_recorded_with_its_message_and_exits_1(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(root), "send", "nobody", "hi"])
    assert exit.value.code == 1 and "error: no such agent: nobody" in capsys.readouterr().err
    (event,) = commands(root)
    assert (event["command"], event["ok"], event["error_type"]) == ("send", False, "OrgError") and "no such agent" in str(event["error"])


def test_a_command_that_exits_by_itself_is_a_failure_when_its_status_is_not_0(root: Path, tmp_path: Path) -> None:
    (tmp_path / "bp.yaml").write_text("mission: m\nagents: [{name: lead, template: no-such-template}]\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(root), "plan", str(tmp_path / "bp.yaml")])
    assert exit.value.code == 1
    (event,) = commands(root)
    assert (event["command"], event["ok"], event["error"], event["error_type"]) == ("plan", False, "exit 1", "RuntimeError")


def test_a_check_that_fails_is_a_failed_command(root: Path) -> None:
    (root / ".runtime").mkdir(exist_ok=True)
    (root / ".runtime" / "scheduler.pid").write_text("999999")  # a pid that names no scheduler: invariant (f) fails
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(root), "check"])
    assert exit.value.code == 1
    assert [e["ok"] for e in commands(root)] == [False]


def test_any_other_exception_is_recorded_and_raised(root: Path, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        main(["--root", str(root), "hire", "ceo", "dev", "--role", "Dev", "--charter", f"@{tmp_path / 'missing.md'}"])
    (event,) = commands(root)
    assert (event["command"], event["ok"], event["error_type"]) == ("hire", False, "FileNotFoundError") and "missing.md" in str(event["error"])


def test_init_records_its_command_in_the_new_organization(tmp_path: Path) -> None:
    main(["init", str(tmp_path / "brand-new"), "--mission", "m"])
    (event,) = commands(tmp_path / "brand-new")
    assert (event["command"], event["ok"]) == ("init", True)


def test_the_read_only_dashboard_records_nothing(root: Path) -> None:
    main(["--root", str(root), "dash", "--once"])
    assert commands(root) == []


def test_a_line_that_does_not_parse_records_nothing(root: Path) -> None:
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(root), "hire"])
    assert exit.value.code == 2 and commands(root) == []


def test_the_process_is_named_cli(root: Path) -> None:
    main(["--root", str(root), "status"])
    assert list((root / ".runtime" / "events").glob("*/cli-*.jsonl"))
