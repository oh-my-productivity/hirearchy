"""The fakes of the three ports answer what they were told to and remember what they were asked; the worlds put a story where the queries look."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.observability import EventQueries, MetricQueries, TraceQueries
from orgmcp.observability.testing import FixedEventQueries, FixedMetricQueries, FixedTraceQueries, disk_world, memory_world, stamp

from ._support import implementations, items


def test_fixed_event_queries_answer_the_view_they_were_given() -> None:
    view = {"events": [{"kind": "a"}], "total": 4, "shown": 1, "since": None, "until": None}
    fake = FixedEventQueries(view, to_follow=[{"kind": "b"}, {"kind": "c"}])
    assert isinstance(fake, EventQueries)
    assert fake.events_view(since="1h", agent="ceo", limit=3) == view and fake.events() == [{"kind": "a"}]
    assert [e["kind"] for e in fake.follow(kind="b", poll=0.1, max_polls=2)] == ["b", "c"]
    assert [name for name, _ in fake.asked] == ["events_view", "events", "follow"]
    assert fake.asked[0][1]["since"] == "1h" and fake.asked[0][1]["agent"] == "ceo" and fake.asked[2][1]["poll"] == 0.1


def test_fixed_event_queries_without_a_view_have_no_events() -> None:
    fake = FixedEventQueries()
    assert fake.events() == [] and fake.events_view()["total"] == 0 and list(fake.follow()) == []


def test_fixed_event_queries_do_not_hand_out_their_own_view() -> None:
    fake = FixedEventQueries()
    fake.events_view()["total"] = 99
    assert fake.events_view()["total"] == 0


def test_fixed_trace_queries_know_the_traces_they_were_given_and_refuse_the_rest_like_the_real_ones() -> None:
    fake = FixedTraceQueries({"t1": {"task": "t1", "totals": {}}})
    assert isinstance(fake, TraceQueries)
    assert fake.trace("t1", stamp(5)) == {"task": "t1", "totals": {}} and fake.asked == [("t1", stamp(5))]
    with pytest.raises(OrgError, match=r"no message nope. Root's tasks \(latest\): t1"):
        fake.trace("nope")


def test_fixed_metric_queries_answer_their_result() -> None:
    fake = FixedMetricQueries({"runs": {"total": 3}})
    assert isinstance(fake, MetricQueries)
    assert fake.metrics(since="7d", by="tool", agent="ceo") == {"runs": {"total": 3}}
    assert fake.asked == [{"since": "7d", "by": "tool", "now": None, "agent": "ceo"}] and FixedMetricQueries().metrics() == {}


@pytest.mark.parametrize("make", implementations([disk_world, memory_world]))
def test_a_world_puts_events_messages_and_logs_where_the_queries_look(make: object, tmp_path: Path) -> None:
    w = make(tmp_path)  # type: ignore[operator]
    w.agent("ceo")
    task = w.send("root", "ceo", "task", 0, title="Ship", trace="self")
    assert task.trace == task.id and task.id.startswith("20261018T100000000000-root-")
    w.tool(1, "ceo", "read")
    stem = w.run_log("ceo", 5, "# exit 0 after 3s\n")
    assert stem == "20261018T100005000000"
    assert [e["kind"] for e in w.events.events(since="2026-10-18T00:00:00Z", now=stamp(100))] == ["tool.call"]
    assert items(w.traces.trace(task.id, now=stamp(100)), "items")[0]["id"] == task.id


# ------------------------------------------------------------------------------ the fakes of the second half (C-obs-2)


def test_fixed_now_queries_answer_the_view_they_were_given() -> None:
    from orgmcp.observability import NowQueries
    from orgmcp.observability.testing import FixedNowQueries

    fake = FixedNowQueries({"scheduler": {"state": "stopped"}})
    assert isinstance(fake, NowQueries)
    assert fake.now_view(stamp(5)) == {"scheduler": {"state": "stopped"}} and fake.now_view() == fake.view and fake.asked == [stamp(5), None]
    fake.now_view()["scheduler"] = 1
    assert fake.view == {"scheduler": {"state": "stopped"}} and FixedNowQueries().now_view() == {}


def test_fixed_integrity_checks_pass_unless_told_otherwise() -> None:
    from orgmcp.observability import IntegrityChecks
    from orgmcp.observability.testing import FixedIntegrityChecks

    fake = FixedIntegrityChecks()
    assert isinstance(fake, IntegrityChecks)
    assert fake.check(stamp(1)) == {"ok": True, "checks": []} and fake.asked == [stamp(1)]
    failing = FixedIntegrityChecks({"ok": False, "checks": [{"id": "a", "ok": False}]})
    assert failing.check()["ok"] is False


def test_fixed_observability_text_answers_what_it_was_told_and_remembers_the_questions() -> None:
    from orgmcp.observability import ObservabilityText
    from orgmcp.observability.testing import FixedObservabilityText

    fake = FixedObservabilityText("the text")
    assert isinstance(fake, ObservabilityText)
    assert fake.observe_text("trace", "T-1", limit=3, max_lines=9) == "the text"
    assert fake.asked == [dict(view="trace", target="T-1", since="24h", by=None, errors_only=False, limit=3, now=None, max_lines=9)]
    with pytest.raises(OrgError, match="no way"):
        FixedObservabilityText(fails=OrgError("no way")).observe_text("check")
