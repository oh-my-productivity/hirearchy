"""Unit tests of the in-memory fakes in ``testing.py`` (the parts the contract suites do not cover).

A consumer's test may only rely on a fake whose behaviour is pinned here and in the contract suites."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.kernel._system import FsAtomicWriter, FsLedgerStore
from orgmcp.kernel.testing import (
    T0,
    DictEnvironment,
    FailingAtomicWriter,
    FakeClock,
    ListEventSink,
    MemoryAtomicWriter,
    MemoryLedgerStore,
    RecordedEvent,
    RecordingTraceTap,
    SequenceIdGenerator,
)

pytestmark = pytest.mark.xfail(strict=True, reason="red: K1")


def test_fake_clock_starts_at_t0_and_ticks_one_microsecond_per_reading() -> None:
    clock = FakeClock()
    assert clock.now() == T0 + timedelta(microseconds=1)
    assert clock.now() == T0 + timedelta(microseconds=2)
    assert clock.time() == (T0 + timedelta(microseconds=2)).timestamp()  # reading the epoch does not tick


def test_fake_clock_moves_only_when_told() -> None:
    clock = FakeClock()
    clock.advance(30)
    assert clock.now() == T0 + timedelta(seconds=30, microseconds=1)
    clock.sleep(5)
    assert clock.monotonic() == pytest.approx(35.000001)
    clock.advance(0)
    assert clock.monotonic() == pytest.approx(35.000001)


def test_fake_clock_at_jumps_forward_and_never_back() -> None:
    clock = FakeClock()
    assert clock.at(100) == T0 + timedelta(seconds=100)
    assert clock.at(10) == T0 + timedelta(seconds=100)
    assert clock.monotonic() == 100


def test_fake_clock_accepts_any_start() -> None:
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    clock = FakeClock(start)
    assert clock.now() == start + timedelta(microseconds=1) and clock.monotonic() == pytest.approx(0.000001)


def test_sequence_ids_count_and_use_the_clock() -> None:
    clock = FakeClock()
    ids = SequenceIdGenerator(clock)
    assert [ids.message_id("ceo/eng"), ids.message_id("root")] == [
        "20261018T100000000001-ceo.eng-0000", "20261018T100000000002-root-0001",
    ]
    clock.advance(1)
    assert ids.message_id("a") == "20261018T100001000003-a-0002"


def test_the_event_sink_records_every_event_with_its_envelope_and_fields() -> None:
    sink = ListEventSink()
    sink.emit("agent.hire", actor="ceo", run="r1", trace="t1", proc="cli", agent="eng", budget=3)
    sink.emit("tick")
    assert sink.events == [
        RecordedEvent("agent.hire", "ceo", "r1", "t1", "cli", {"agent": "eng", "budget": 3}),
        RecordedEvent("tick", None, None, None, None, {}),
    ]


def test_the_trace_tap_remembers_the_notes_in_order() -> None:
    tap = RecordingTraceTap()
    tap.note("a")
    tap.note(None)
    tap.note("b")
    assert tap.notes == ["a", None, "b"]


def test_memory_atomic_writer_keeps_files_by_path() -> None:
    writer = MemoryAtomicWriter()
    writer.write(Path("/x/a"), "1")
    writer.write(Path("/x/a"), "2")
    assert writer.files == {Path("/x/a"): "2"}


def test_failing_writer_fails_everything_by_default_like_a_full_disk() -> None:
    inner = MemoryAtomicWriter()
    writer = FailingAtomicWriter(inner)
    with pytest.raises(OSError) as raised:
        writer.write(Path("/x/a"), "1")
    assert raised.value.errno == 28 and inner.files == {} and writer.attempts == [Path("/x/a")]


def test_failing_writer_can_fail_selected_paths_with_a_chosen_error() -> None:
    inner = MemoryAtomicWriter()
    writer = FailingAtomicWriter(inner, fails=lambda p: p.name == "bad", error=PermissionError("denied"))
    writer.write(Path("/x/good"), "ok")
    with pytest.raises(PermissionError, match="denied"):
        writer.write(Path("/x/bad"), "no")
    writer.write(Path("/x/good2"), "ok2")
    assert inner.files == {Path("/x/good"): "ok", Path("/x/good2"): "ok2"}
    assert writer.attempts == [Path("/x/good"), Path("/x/bad"), Path("/x/good2")]


def test_memory_ledgers_keep_the_text_the_real_store_writes(tmp_path: Path) -> None:
    data = {"ceo": 2, "names": ["é"], "nested": {"a": None}}
    memory = MemoryLedgerStore()
    memory.write("failures", data)
    FsLedgerStore(OrgPaths(tmp_path), FsAtomicWriter()).write("failures", data)
    assert memory.texts == {"failures": (tmp_path / ".runtime" / "failures.json").read_text(encoding="utf-8")}


def test_memory_ledgers_refuse_what_json_refuses() -> None:
    with pytest.raises(TypeError):
        MemoryLedgerStore().write("failures", {"when": datetime(2026, 1, 1)})


def test_dict_environment() -> None:
    env = DictEnvironment({"A": "1"}, cwd=Path("/w"), home=Path("/h"))
    env.set("B", "2")
    assert (env.get("A"), env.get("B"), env.get("C")) == ("1", "2", None)
    assert dict(env.variables()) == {"A": "1", "B": "2"} and (env.cwd(), env.home()) == (Path("/w"), Path("/h"))
    assert DictEnvironment().variables() == {}
