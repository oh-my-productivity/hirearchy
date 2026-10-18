"""Contract of ``EventSink``: whatever the implementation, emitting never raises.

Only the fake is registered in the kernel; the real sink (``telemetry``) registers itself in the step that moves it, and
adds its own, filesystem-specific tests there."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import EventSink
from orgmcp.kernel.tests._red import impls


@pytest.fixture(params=impls(EventSink))
def sink(request: pytest.FixtureRequest, tmp_path: Path) -> EventSink:
    made = cast(Callable[[Path], EventSink], request.param)(tmp_path)
    assert isinstance(made, EventSink)
    return made


def test_emit_takes_a_kind_the_envelope_fields_and_free_fields(sink: EventSink) -> None:
    sink.emit("agent.hire", actor="ceo", run="r1", trace="t1", proc="cli", agent="eng", budget=3, nested={"a": [1, 2]})
    sink.emit("tick")


def test_the_kind_is_positional_only(sink: EventSink) -> None:
    with pytest.raises(TypeError):
        sink.emit(kind="agent.hire")  # type: ignore[call-arg]
    sink.emit("agent.hire")


def test_emitting_odd_values_does_not_raise(sink: EventSink) -> None:
    sink.emit("odd", value=object(), text="é✓", none=None, big="x" * 100_000)
