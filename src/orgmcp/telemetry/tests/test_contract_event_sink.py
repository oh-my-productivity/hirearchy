"""Contract of ``EventSink`` (the kernel's port) for the real sink and the recording one: emitting never raises, and what is emitted
can be read back. The envelope, the files and the failure handling of the real sink are in ``test_fs_event_sink.py``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import EventSink
from orgmcp.telemetry.testing import IMPLEMENTATIONS, SinkHarness



@pytest.fixture(params=IMPLEMENTATIONS[EventSink], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> SinkHarness:
    made = cast(Callable[[Path], SinkHarness], request.param)(tmp_path)
    assert isinstance(made.sink, EventSink)
    return made


def test_emit_takes_a_kind_the_envelope_fields_and_free_fields(h: SinkHarness) -> None:
    h.sink.emit("agent.hire", actor="ceo", run="r1", trace="t1", proc="cli", agent="eng", budget=3, nested={"a": [1, 2]})
    h.sink.emit("tick")
    first, second = h.written()
    assert first["kind"] == "agent.hire" and first["actor"] == "ceo" and first["run"] == "r1" and first["trace"] == "t1"
    assert first["proc"] == "cli" and first["agent"] == "eng" and first["budget"] == 3 and first["nested"] == {"a": [1, 2]}
    assert second["kind"] == "tick"


def test_the_kind_is_positional_only(h: SinkHarness) -> None:
    with pytest.raises(TypeError):
        h.sink.emit(kind="agent.hire")  # type: ignore[call-arg]
    h.sink.emit("agent.hire")
    assert [e["kind"] for e in h.written()] == ["agent.hire"]


def test_events_are_kept_in_the_order_they_were_emitted(h: SinkHarness) -> None:
    for i in range(20):
        h.sink.emit("tick", i=i)
    assert [e["i"] for e in h.written()] == list(range(20))


def test_emitting_odd_values_does_not_raise(h: SinkHarness) -> None:
    loop: dict[str, object] = {}
    loop["self"] = loop

    class Bad:
        def __str__(self) -> str:
            raise RuntimeError("no string for you")

    h.sink.emit("odd", value=object(), text="é✓ \ud800", none=None, big="x" * 100_000, loop=loop, bad=Bad())
    h.sink.emit("fine", n=1)
    assert [e["n"] for e in h.written() if e["kind"] == "fine"] == [1]
