"""Contract of ``RunLogSink``: a sink appends text to a log, on disk or in memory."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest

from orgmcp.runs import RunLogSink
from orgmcp.runs.testing import IMPLEMENTATIONS, RunsHarness

from ._red import impls


@pytest.fixture(params=impls(IMPLEMENTATIONS[RunLogSink]), ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RunsHarness:
    return cast(Callable[[Path], RunsHarness], request.param)(tmp_path)


@pytest.fixture
def log(h: RunsHarness) -> Path:
    h.add_agent("ceo")
    return h.writer.create("ceo")


@pytest.fixture
def sink(h: RunsHarness, log: Path) -> Iterator[RunLogSink]:
    opened = h.writer.open_sink(log)
    yield opened
    opened.close()


def test_a_sink_is_a_sink_for_its_log(sink: RunLogSink, log: Path) -> None:
    assert isinstance(sink, RunLogSink) and sink.path == log


def test_what_was_written_and_flushed_is_in_the_log(h: RunsHarness, sink: RunLogSink, log: Path) -> None:
    sink.write("# run of ceo, 1 message(s)\n")
    sink.write("output")
    sink.flush()
    assert h.read_log(log) == b"# run of ceo, 1 message(s)\noutput"


def test_a_sink_appends_to_what_is_already_there(h: RunsHarness) -> None:
    path = h.put_log("ceo", "20261018T100000000001.log", "first line\n")
    sink = h.writer.open_sink(path)
    sink.write("second line\n")
    sink.close()
    assert h.read_log(path) == b"first line\nsecond line\n"


def test_text_is_written_as_utf8(h: RunsHarness, sink: RunLogSink, log: Path) -> None:
    sink.write("é → ✓\n")
    sink.close()
    assert h.read_log(log) == "é → ✓\n".encode("utf-8")


def test_closing_flushes(h: RunsHarness, sink: RunLogSink, log: Path) -> None:
    sink.write("done")
    sink.close()
    assert h.read_log(log) == b"done"


def test_closing_twice_is_harmless(sink: RunLogSink) -> None:
    sink.close()
    sink.close()


def test_writing_after_close_raises_like_a_file(sink: RunLogSink) -> None:
    sink.close()
    with pytest.raises(ValueError):
        sink.write("too late")


def test_written_text_counts_for_the_reader_of_the_log(h: RunsHarness, sink: RunLogSink, log: Path) -> None:
    sink.write("# run of ceo, 1 message(s)\n# senders: runtime\n# ---- prompt ----\nhi\n# ---- output ----\n")
    sink.write("\n# exit 1 after 4s\n")
    sink.close()
    assert h.reader.facts(log) == {"exit_code": 1, "seconds": 4}
    assert len(h.reader.outcomes("ceo").failed) == 1 and len(h.reader.outcomes("ceo").runtime_only) == 1
