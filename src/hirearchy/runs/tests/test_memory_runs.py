"""``MemoryRuns``: what the in-memory fake does beyond the contract suites (they run it against the filesystem implementations)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel.testing import FakeClock
from hirearchy.runs import RunLogReader, RunLogWriter, RunRegistry
from hirearchy.runs.testing import MemoryRuns


def test_one_object_is_the_writer_the_reader_and_the_registry(tmp_path: Path) -> None:
    memory = MemoryRuns(FakeClock(), tmp_path)
    assert isinstance(memory, RunLogWriter) and isinstance(memory, RunLogReader) and isinstance(memory, RunRegistry)


def test_a_log_is_stamped_with_the_time_it_was_last_written(tmp_path: Path) -> None:
    clock = FakeClock()
    memory = MemoryRuns(clock, tmp_path)
    memory.add_agent("ceo")
    log = memory.create("ceo")
    created = clock.time()
    assert memory.last_end("ceo") == created
    clock.advance(60)
    sink = memory.open_sink(log)
    sink.write("output")
    assert memory.last_end("ceo") == clock.time() == created + 60
    clock.advance(5)
    memory.append_note(str(log.relative_to(tmp_path)), "killed: x")
    assert memory.last_end("ceo") == clock.time()


def test_two_fakes_do_not_share_anything(tmp_path: Path) -> None:
    one, other = MemoryRuns(FakeClock(), tmp_path), MemoryRuns(FakeClock(), tmp_path)
    one.add_agent("ceo")
    one.create("ceo")
    one.record("ceo", {"pgid": 1})
    assert other.count("ceo") == 0 and other.all() == {}


def test_the_fake_has_defaults_for_a_quick_unit_test() -> None:
    memory = MemoryRuns()
    memory.add_agent("ceo")
    path = memory.create("ceo")
    assert path.parent == Path("/org/ceo/runs") and memory.count("ceo") == 1


def test_a_log_can_be_put_where_the_scheduler_may_have_left_it(tmp_path: Path) -> None:
    memory = MemoryRuns(FakeClock(), tmp_path)
    path = memory.put_log("ceo", "20261018T100000000001.log", "# run of ceo\n\n# exit 1 after 2s\n")
    memory.set_mtime(path, 1_792_317_700.0)
    assert memory.read_log(path) == b"# run of ceo\n\n# exit 1 after 2s\n" and memory.last_end("ceo") == 1_792_317_700.0
    assert memory.read_log(tmp_path / "nowhere.log") is None
    assert memory.facts(path) == {"exit_code": 1, "seconds": 2}
