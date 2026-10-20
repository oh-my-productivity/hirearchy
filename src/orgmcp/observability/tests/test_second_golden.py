"""Characterization: what ``now`` and ``check`` say about the scenario organizations, key for key and character for character, and the text of every view.

The expected files were captured from ``observe.py`` before the second half moved (``_scenario.SCENARIOS``, the scheduler and the judge as the scenario
says)."""

from __future__ import annotations

from typing import Any

import pytest

from orgmcp.observability import IntegrityChecks, NowQueries, ObservabilityRenderer, ObservabilityText

from ._scenario import NOW, SCENARIOS, SINCE, follow_ports, settle
from ._second import Second, dump
from ._support import expected



@pytest.fixture(params=list(SCENARIOS))
def scene(request: pytest.FixtureRequest, built: Any) -> tuple[str, Any, Second]:
    setup, state, verdict = SCENARIOS[request.param]
    setup(built)
    settle(built.org)
    return request.param, built, Second(follow_ports(built.org, state, verdict))


def test_the_now_view(scene: tuple[str, Any, Second]) -> None:
    name, _, second = scene
    assert isinstance(second.now, NowQueries)
    assert dump(second.now.now_view(NOW)) == expected(f"now_{name}.json")


def test_the_text_of_the_now_view(scene: tuple[str, Any, Second]) -> None:
    name, _, second = scene
    assert isinstance(second.renderer, ObservabilityRenderer)
    assert second.renderer.render_now(second.now.now_view(NOW)) + "\n" == expected(f"now_{name}.txt")


def test_the_checks(scene: tuple[str, Any, Second]) -> None:
    name, _, second = scene
    assert isinstance(second.checks, IntegrityChecks)
    assert dump(second.checks.check(NOW)) == expected(f"check_{name}.json")


def test_the_text_of_the_checks(scene: tuple[str, Any, Second]) -> None:
    name, _, second = scene
    assert second.renderer.render_check(second.checks.check(NOW)) + "\n" == expected(f"check_{name}.txt")


def test_the_now_view_of_an_organization_nothing_happened_in(bare: Any) -> None:
    second = Second(follow_ports(bare, ("stopped", None, None, ""), "gone"))
    assert dump(second.now.now_view(NOW)) == expected("now_bare.json")
    assert second.renderer.render_now(second.now.now_view(NOW)) + "\n" == expected("now_bare.txt")
    assert dump(second.checks.check(NOW)) == expected("check_bare.json")
    assert second.renderer.render_check(second.checks.check(NOW)) + "\n" == expected("check_bare.txt")


def test_the_now_view_capped_to_a_few_lines(built: Any) -> None:
    setup, state, verdict = SCENARIOS["busy"]
    setup(built)
    second = Second(follow_ports(built.org, state, verdict))
    assert second.renderer.render_now(second.now.now_view(NOW), 12) + "\n" == expected("now_busy_capped.txt")


TEXTS: dict[str, dict[str, Any]] = {
    "now": dict(view="now"), "check": dict(view="check"), "metrics": dict(view="metrics"), "metrics_agent": dict(view="metrics", target="ceo", by="tool"),
    "events": dict(view="events"), "events_agent": dict(view="events", target="ceo/eng"), "events_kind": dict(view="events", target="tool.call"),
    "events_errors": dict(view="events", errors_only=True, limit=3), "events_root": dict(view="events", target="root"), "now_small": dict(view="now", limit=2),
}


@pytest.mark.parametrize("label", list(TEXTS))
def test_the_text_of_a_view(built: Any, label: str) -> None:
    setup, state, verdict = SCENARIOS["busy"]
    setup(built)
    settle(built.org)
    text = Second(follow_ports(built.org, state, verdict)).text
    assert isinstance(text, ObservabilityText)
    assert text.observe_text(since=SINCE, now=NOW, **TEXTS[label]) + "\n" == expected(f"text_{label}.txt")


def test_the_text_of_the_trace_of_a_task_and_of_the_events_of_a_trace(built: Any) -> None:
    setup, state, verdict = SCENARIOS["busy"]
    setup(built)
    settle(built.org)
    text = Second(follow_ports(built.org, state, verdict)).text
    assert text.observe_text("trace", built.task.id, since=SINCE, now=NOW) + "\n" == expected("text_trace.txt")
    assert text.observe_text("events", built.task.id, since=SINCE, now=NOW) + "\n" == expected("text_events_trace.txt")


def test_the_name_of_the_view_is_stripped_and_lowercased_and_none_means_now(built: Any) -> None:
    setup, state, verdict = SCENARIOS["busy"]
    setup(built)
    settle(built.org)
    text = Second(follow_ports(built.org, state, verdict)).text
    assert text.observe_text(" NOW ", since=SINCE, now=NOW) + "\n" == expected("text_view_upper.txt")
    assert text.observe_text(None, since=SINCE, now=NOW) + "\n" == expected("text_view_none.txt")  # type: ignore[arg-type]


def test_the_events_of_an_organization_without_event_files_say_so(bare: Any) -> None:
    text = Second(follow_ports(bare, ("stopped", None, None, ""), "gone")).text
    assert text.observe_text("events", since=SINCE, now=NOW) + "\n" == expected("text_events_none.txt")
