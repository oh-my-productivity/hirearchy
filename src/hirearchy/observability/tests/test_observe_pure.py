# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from datetime import timedelta

import pytest
from testkit import observability_world as observe
from testkit.reach.hirearchy.core import ROOT, Org, OrgError
from testkit.obs_fixtures import Story, stamp
from testkit.observability_world import freeze

NOW = stamp(200)


@pytest.fixture
def org(tmp_path):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(org):
    return freeze(org)


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


# ------------------------------------------------------------------------------------------------ helpers
def test_percentile_is_nearest_rank_and_exact():
    vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert observe.percentile(vals, 50) == 50
    assert observe.percentile(vals, 95) == 100
    assert observe.percentile(vals, 10) == 10
    assert observe.percentile([7], 95) == 7
    assert observe.percentile([], 50) is None
    assert observe.percentile([3, 1, 2], 50) == 2  # unsorted input


def test_parse_when_accepts_durations_and_iso():
    now = stamp(0)
    assert observe.parse_when("15m", now) == now - timedelta(minutes=15)
    assert observe.parse_when("24h", now) == now - timedelta(hours=24)
    assert observe.parse_when("7d", now) == now - timedelta(days=7)
    assert observe.parse_when("2026-10-18T09:00:00Z", now) == stamp(-3600)
    assert observe.parse_when("2026-10-18T09:00:00", now) == stamp(-3600)  # naive = UTC
    assert observe.parse_when(None, now) is None and observe.parse_when("", now) is None
    with pytest.raises(OrgError, match="cannot read 'soon'"):
        observe.parse_when("soon", now)


def test_duration_and_relative_formats():
    assert [observe.fmt_dur(x) for x in (850, 4200, 42_000, 65_000, 7_380_000)] == ["850ms", "4.2s", "42s", "1m05s", "2h03m"]
    assert [observe.fmt_rel(x) for x in (0, 42_000, 65_000, 7_380_000)] == ["+0s", "+42s", "+1m05s", "+2h03m"]


def test_refusals_are_normalized_so_reasons_group():
    a = observe.normalize_refusal('not enough budget: you have 5 run(s); task 20261018T100003000001-root-ab12 "Ship it" in ceo/work/x.md')
    b = observe.normalize_refusal('not enough budget: you have 9 run(s); task 20261018T110003000001-root-cd34 "Other" in ceo/work/y.md')
    assert a == b and "5" not in a and "Ship" not in a and "ceo/work" not in a
    assert observe.normalize_refusal("zz " * 200).endswith("…")


# ------------------------------------------------------------------------------------------------ surfaces
def test_observe_text_dispatch_and_caps(org, story):
    assert observe.observe_text(org, "check", now=NOW).endswith("all checks passed")
    assert "runs 3" in observe.observe_text(org, "trace", story.task.id, now=NOW)
    assert observe.observe_text(org, "metrics", since="2026-10-18T00:00:00Z", now=NOW).startswith("metrics ")
    with pytest.raises(OrgError, match="trace needs target"):
        observe.observe_text(org, "trace")
    with pytest.raises(OrgError, match="view must be one of"):
        observe.observe_text(org, "weather")
    # events: target is a trace id, an agent or a kind
    since = "2026-10-18T00:00:00Z"
    by_trace = observe.observe_text(org, "events", story.task.id, since=since, now=NOW)
    by_agent = observe.observe_text(org, "events", "ceo/eng", since=since, now=NOW)
    by_kind = observe.observe_text(org, "events", "scheduler", since=since, now=NOW)
    assert "tool.call" in by_trace and "scheduler.start" in by_kind and "ceo/eng" in by_agent and "scheduler.start" not in by_agent
    assert "not enough budget" in observe.observe_text(org, "events", since=since, errors_only=True, now=NOW)
    capped = observe.observe_text(org, "trace", story.task.id, now=NOW, max_lines=3)
    assert "more line(s), narrow with" in capped
