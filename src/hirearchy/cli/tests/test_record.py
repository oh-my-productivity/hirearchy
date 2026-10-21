"""``EventCommandRecorder``: the ``cli.command`` event of a finished command, in the organization the command was about to work on; never an error."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from hirearchy.cli.testing import RecordedWorld, recorded_world
from hirearchy.kernel import OrgError
from hirearchy.kernel.testing import FakeClock



@pytest.fixture
def w(tmp_path: Path) -> RecordedWorld:
    return recorded_world(tmp_path)


def line(cmd: str = "status", **given: object) -> argparse.Namespace:
    return argparse.Namespace(**{"cmd": cmd, "root": None, "path": None, **given})


def test_a_success_is_an_event_of_root_in_the_process_cli(w: RecordedWorld, tmp_path: Path) -> None:
    clock: FakeClock = w.clock
    started = clock.monotonic()
    clock.advance(0.0125)
    w.recorder.record(line(), started, None)
    (event,) = w.sinks.events(tmp_path / "org")
    assert (event.kind, event.actor, event.proc, event.run, event.trace) == ("cli.command", "root", "cli", None, None)
    assert event.fields == {"command": "status", "ok": True, "ms": 12.5, "error": None, "error_type": None}


def test_an_org_error_is_recorded_with_its_text_and_its_type(w: RecordedWorld, tmp_path: Path) -> None:
    w.recorder.record(line("send"), w.clock.monotonic(), OrgError("no such agent: nobody"))
    (event,) = w.sinks.events(tmp_path / "org")
    assert event.fields["ok"] is False and event.fields["error"] == "no such agent: nobody" and event.fields["error_type"] == "OrgError"


def test_a_failure_without_a_message_is_recorded_as_its_type(w: RecordedWorld, tmp_path: Path) -> None:
    w.recorder.record(line(), w.clock.monotonic(), KeyError())
    (event,) = w.sinks.events(tmp_path / "org")
    assert event.fields["error"] == "KeyError" and event.fields["error_type"] == "KeyError"


def test_a_long_error_is_cut_at_500_characters(w: RecordedWorld, tmp_path: Path) -> None:
    w.recorder.record(line(), w.clock.monotonic(), RuntimeError("x" * 900))
    (event,) = w.sinks.events(tmp_path / "org")
    error = str(event.fields["error"])
    assert len(error) == 500 and error.endswith("…")


def test_the_event_goes_to_the_organization_the_command_line_names(w: RecordedWorld, tmp_path: Path) -> None:
    w.session.root = tmp_path / "elsewhere"
    w.recorder.record(line(root=None), w.clock.monotonic(), None)
    assert len(w.sinks.events(tmp_path / "elsewhere")) == 1 and w.sinks.events(tmp_path / "org") == []


def test_init_records_into_the_new_organization(w: RecordedWorld, tmp_path: Path) -> None:
    new = tmp_path / "brand-new"
    w.recorder.record(argparse.Namespace(cmd="init", root=None, path=str(new)), w.clock.monotonic(), None)
    (event,) = w.sinks.events(new.resolve())
    assert event.fields["command"] == "init" and w.session.calls == []  # (it asked no session: the path is the root)


@pytest.mark.parametrize("command", ["mcp", "dash"])
def test_a_server_and_the_read_only_dashboard_record_nothing(w: RecordedWorld, tmp_path: Path, command: str) -> None:
    w.recorder.record(line(command), w.clock.monotonic(), None)
    assert w.sinks.sinks == {}


def test_a_root_that_cannot_be_found_is_no_error(w: RecordedWorld) -> None:
    class Lost(Exception):
        pass

    def lost(args: argparse.Namespace) -> Path:
        raise OrgError("no organization found")

    w.session.named = lost  # type: ignore[method-assign]
    w.recorder.record(line(), w.clock.monotonic(), None)
    assert w.sinks.sinks == {}


def test_a_log_that_cannot_be_written_is_no_error(w: RecordedWorld, tmp_path: Path) -> None:
    w.sinks.broken = True
    w.recorder.record(line(), w.clock.monotonic(), None)
    assert w.sinks.events(tmp_path / "org") == []
