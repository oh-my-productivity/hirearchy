"""``obs now|trace|metrics|events`` and ``check`` over a fake of the views, a clock that moves when told and an event tail that is scripted."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orgmcp.cli._commands_obs import CheckCommand, EventsCommand, MetricsCommand, NowCommand, ObsCommand, TraceCommand
from orgmcp.cli.testing import ScriptedEventTails, ScriptedTerminal, StaticJson
from orgmcp.kernel import OrgError
from orgmcp.kernel.testing import FakeClock

from ._fakes import FakeViews, new_views
from ._support import Fixture, go, parse, view



class InterruptedClock(FakeClock):
    """A clock whose sleep is ended by Ctrl-C after ``sleeps`` sleeps."""

    def __init__(self, sleeps: int = 0) -> None:
        super().__init__()
        self.sleeps = sleeps
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        if len(self.slept) > self.sleeps:
            raise KeyboardInterrupt


def now_world(tmp_path: Path, tty: bool = False, sleeps: int = 0) -> tuple[Fixture, FakeViews, InterruptedClock, NowCommand]:
    f, views, clock = Fixture(tmp_path), new_views(), InterruptedClock(sleeps)
    return f, views, clock, NowCommand(f.session, lambda: views, lambda: views, StaticJson(), ScriptedTerminal(tty), clock, f.out)


def test_now_shows_the_view_once(tmp_path: Path) -> None:
    f, views, clock, command = now_world(tmp_path)
    view(command, "now")
    assert f.session.calls == [("open", False)] and views.names() == ["now_view"]
    assert f.out.stdout == "render_now: ['scheduler']\n" and clock.slept == []


def test_now_as_json_is_the_dump_of_the_view(tmp_path: Path) -> None:
    f, views, clock, command = now_world(tmp_path)
    view(command, "now", "--json")
    assert f.out.stdout == json.dumps({"scheduler": "stopped"}) + "\n"


def test_now_watch_repeats_until_ctrl_c_and_marks_each_round_when_piped(tmp_path: Path) -> None:
    f, views, clock, command = now_world(tmp_path, tty=False, sleeps=1)
    view(command, "now", "--watch", "5")
    assert clock.slept == [5.0, 5.0] and views.names() == ["now_view", "now_view"]
    assert f.out.stdout == "render_now: ['scheduler']\n" + "-" * 40 + "\n" + "render_now: ['scheduler']\n"


def test_now_watch_clears_the_screen_on_a_terminal(tmp_path: Path) -> None:
    f, views, clock, command = now_world(tmp_path, tty=True, sleeps=0)
    view(command, "now", "--watch", "5")
    assert f.out.stdout == "\033[2J\033[Hrender_now: ['scheduler']\n"


def test_now_watch_json_prints_no_separator(tmp_path: Path) -> None:
    f, views, clock, command = now_world(tmp_path, tty=False, sleeps=1)
    view(command, "now", "--watch", "1", "--json")
    assert f.out.stdout == (json.dumps({"scheduler": "stopped"}) + "\n") * 2


def test_trace_of_a_task(tmp_path: Path) -> None:
    f, views = Fixture(tmp_path), new_views()
    command = TraceCommand(f.session, lambda: views, lambda: views, StaticJson(), f.out)
    view(command, "trace", "t-1")
    assert views.last("trace") == (("t-1",), {}) and f.out.stdout == "render_trace: ['task', 'when']\n"
    view(command, "trace", "t-1", "--json")
    assert json.loads(f.out.stdout.splitlines()[-1])["task"] == "t-1"


def test_an_unknown_task_is_the_error_of_the_view(tmp_path: Path) -> None:
    f, views = Fixture(tmp_path), new_views()
    views.refuse = OrgError("no message nope")
    with pytest.raises(OrgError, match="no message nope"):
        view(TraceCommand(f.session, lambda: views, lambda: views, StaticJson(), f.out), "trace", "nope")


def test_metrics_pass_the_window_the_grouping_and_the_agent(tmp_path: Path) -> None:
    f, views = Fixture(tmp_path), new_views()
    command = MetricsCommand(f.session, lambda: views, lambda: views, StaticJson(), f.out)
    view(command, "metrics", "--since", "7d", "--by", "tool", "--agent", "ceo", "--limit", "5")
    assert views.last("metrics") == (("7d", "tool"), {"agent": "ceo"}) and f.out.stdout == "render_metrics: ['runs'] limit 5\n"
    view(command, "metrics")
    assert views.last("metrics") == (("24h", None), {"agent": None})
    with pytest.raises(SystemExit):
        parse(ObsCommand([command]), "obs", "metrics", "--by", "colour")


def events_world(tmp_path: Path, tails: ScriptedEventTails, clock: InterruptedClock | None = None) -> tuple[Fixture, FakeViews, EventsCommand]:
    f, views = Fixture(tmp_path), new_views()
    return f, views, EventsCommand(f.session, lambda: views, lambda: views, lambda: tails, StaticJson(), clock or InterruptedClock(), f.out)


def test_events_pass_the_filter_and_say_whether_there_are_event_files(tmp_path: Path) -> None:
    tails = ScriptedEventTails(has_events=False)
    f, views, command = events_world(tmp_path, tails)
    view(command, "events", "--since", "2h", "--until", "now", "--agent", "ceo", "--kind", "run", "--trace", "t-1", "--errors", "--limit", "7")
    assert views.last("events_view") == (("2h", "now", "ceo", "run", "t-1", True, 7), {})
    assert f.out.stdout == "render_events: ['any', 'events', 'shown', 'total']\n" and tails.follows == []


def test_events_as_json_are_one_object_per_line(tmp_path: Path) -> None:
    f, views, command = events_world(tmp_path, ScriptedEventTails())
    view(command, "events", "--json")
    assert [json.loads(line)["n"] for line in f.out.stdout.splitlines()] == [1, 2]


def test_events_follow_starts_the_tail_before_the_listing_and_prints_new_events_until_ctrl_c(tmp_path: Path) -> None:
    tails = ScriptedEventTails(polls=[[{"kind": "run.start", "n": 3}], [], [{"kind": "run.end", "n": 4}]])
    clock = InterruptedClock(sleeps=3)
    f, views, command = events_world(tmp_path, tails, clock)
    view(command, "events", "--follow", "--poll", "0.25", "--agent", "ceo")
    assert tails.follows == [("ceo", None, None, False)] and clock.slept == [0.25] * 4
    lines = f.out.stdout.splitlines()
    assert lines[0].startswith("render_events") and len(lines) == 3 and "run.start" in lines[1] and "run.end" in lines[2]


def test_events_follow_as_json(tmp_path: Path) -> None:
    tails = ScriptedEventTails(polls=[[{"kind": "run.start", "n": 3}]])
    f, views, command = events_world(tmp_path, tails, InterruptedClock(sleeps=1))
    view(command, "events", "--follow", "--json")
    assert [json.loads(line)["n"] for line in f.out.stdout.splitlines()] == [1, 2, 3]


def test_check_prints_the_verdict_and_exits_1_when_an_invariant_fails(tmp_path: Path) -> None:
    f, views = Fixture(tmp_path), new_views()
    command = CheckCommand(f.session, lambda: views, lambda: views, StaticJson(), f.out)
    go(command, "check")
    assert f.out.stdout == "render_check: ok=True\n" and f.session.calls == [("open", False)]
    go(command, "check", "--json")
    assert json.loads(f.out.stdout.splitlines()[-1]) == {"checks": [], "ok": True}
    views.checks = {"ok": False, "checks": []}
    with pytest.raises(SystemExit) as exit:
        go(command, "check")
    assert exit.value.code == 1 and f.out.stdout.endswith("render_check: ok=False\n")


def test_obs_is_a_group_with_a_required_view(tmp_path: Path) -> None:
    f, views = Fixture(tmp_path), new_views()
    group = ObsCommand([TraceCommand(f.session, lambda: views, lambda: views, StaticJson(), f.out)])
    with pytest.raises(SystemExit):
        parse(group, "obs")
