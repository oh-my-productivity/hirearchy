"""Contract of ``SnapshotRenderer``: the plain text of ``hirearchy dash --once`` - whole lines, a section for each thing the dashboard shows. Over the strict ports and over the dashboard's."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.dashdata import SnapshotRenderer
from hirearchy.dashdata.testing import IMPLEMENTATIONS, DashWorld
from hirearchy.reflection import Stats
from hirearchy.services import Playbook

from ._support import bad_message, make_world, running_scheduler, team


@pytest.fixture(params=IMPLEMENTATIONS[SnapshotRenderer], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.renderer, SnapshotRenderer)
    return made


def test_an_empty_organization_is_a_header_and_empty_sections(w: DashWorld) -> None:
    text = w.renderer.render_once()
    assert text.splitlines() == [
        f"hirearchy dash - {w.root.name} ({w.root})  2026-10-18 10:03:20Z", "scheduler stopped | running 0/3 · queued 0 · waiting on you 0 · errors 15m 0", "",
        "AGENTS", "★ root (you)", "", "REQUESTS", "  none", "", "SERVICES", "  none",
    ]


def test_the_header_and_the_agent_tree_say_what_the_dashboard_shows(w: DashWorld) -> None:
    team(w)
    running_scheduler(w)
    w.obs.send("root", "ops", "note", 10, title="Hello")
    lines = w.renderer.render_once().splitlines()
    assert lines[1] == "scheduler running pid 7000 (until_done, up 3m20s, heartbeat 3.0s ago) | running 0/2 · queued 1 · waiting on you 0 · errors 15m 0"
    assert "  ○ ceo [Worker]  idle  budget 3  claude-sonnet-5.5" in lines and "    ○ analyst [Worker]  idle  budget 4  claude-sonnet-5.5" in lines
    assert "  ◔ ops [Worker]  queued: starts on the next tick, 1 unread  budget 2  claude-sonnet-5.5" in lines


def test_what_needs_the_user_requests_and_services_are_listed(w: DashWorld) -> None:
    team(w)
    w.obs.waiting.entries.append(("m1", "Needs you: note from ceo"))
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=3, trace="self")
    w.facts.states[task.id] = ("working", "running: ceo")
    w.facts.runs[task.id] = "runs 1 of 3"
    w.catalog.define("ceo", "brief", Playbook(version=1, reason="initial playbook"), description="x")
    text = w.renderer.render_once()
    assert "★ root (you)  needs you: 1" in text and "\nNEEDS YOU\n  Needs you: note from ceo\n" in text
    assert '\nREQUESTS\n  "Ship it" -> ceo: working (running: ceo); runs 1 of 3\n' in text
    assert f"\nSERVICES\n  ceo/brief  contract v1 playbook v1  {Stats().line()}" in text


def test_a_long_title_is_clipped_and_nothing_else_is_cut(w: DashWorld) -> None:
    team(w)
    long = "A very long title " * 8
    w.obs.send("root", "ceo", "task", 10, title=long.strip(), budget=1, trace="self")
    request = next(line for line in w.renderer.render_once(width=40).splitlines() if "-> ceo" in line)
    assert request == '  "A very long title A very long title A v…" -> ceo: working (running: ceo); runs 0 of 0'  # width is not a limit: the line is whole


def test_the_requests_are_the_newest_twenty(w: DashWorld) -> None:
    team(w)
    for n in range(23):
        w.obs.send("root", "ceo", "task", 10 + n, title=f"Task {n}", budget=1, trace="self")
    lines = [line for line in w.renderer.render_once().splitlines() if line.startswith('  "Task')]
    assert len(lines) == 20 and lines[0].startswith('  "Task 22"')


def test_the_files_that_could_not_be_read_are_listed_when_the_ports_are_lenient(tmp_path: Path) -> None:
    from hirearchy.dashdata.testing import caching_world

    w = caching_world(tmp_path)
    team(w)
    w.obs.send("root", "ceo", "note", 10, title="Good")
    bad_message(w, "ceo")
    text = w.renderer.render_once()
    assert "\nUNREADABLE FILES (1)\n  ceo/inbox/" in text and "ParserError" in text.splitlines()[-1]
