"""``FsEventSink``: the envelope, the defaults of actor and run, the file per process and day, and the promise never to raise.

These are the writer tests of ``tests/test_telemetry.py`` (which stay there until the end of the refactor) over the real sink with every
collaborator in the open: a fake clock, a dictionary environment, a fake ignore list."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from orgmcp.eventlog import ENVELOPE, EVENTS_REL, LINE_MAX, SCHEMA_VERSION
from orgmcp.kernel import EventSink
from orgmcp.kernel.testing import T0
from orgmcp.snapshots.testing import MemoryIgnoreList
from orgmcp.telemetry.testing import ORG_MD, SinkKit, build_sink, sink_kit


def test_it_is_an_event_sink(tmp_path: Path) -> None:
    assert isinstance(sink_kit(tmp_path).sink, EventSink)


# ------------------------------------------------------------------------------------------------- layout and envelope


def test_events_go_to_one_file_per_process_and_day_with_the_envelope(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", trace="T1", thing=1)
    kit.sink.emit("custom.kind", thing=2)
    (file,) = kit.files()
    assert file.parent.name == "2026-10-18" and file.parent.parent == tmp_path / EVENTS_REL
    assert re.fullmatch(rf"cli-{os.getpid()}-\d{{13}}\.jsonl", file.name)
    first, second = kit.events()
    assert tuple(first)[:9] == ENVELOPE and list(first)[9:] == ["thing"]
    assert (first["v"], first["seq"], first["proc"], first["pid"], first["kind"]) == (SCHEMA_VERSION, 1, "cli", os.getpid(), "custom.kind")
    assert (first["actor"], first["run"], first["trace"]) == ("root", None, "T1")
    assert (second["seq"], second["trace"], second["thing"]) == (2, None, 2)


def test_the_timestamp_is_the_clock_in_utc_with_microseconds(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind")
    assert kit.events()[0]["ts"] == "2026-10-18T10:00:00.000001+00:00" == (T0.replace(microsecond=1)).isoformat(timespec="microseconds")


def test_the_line_is_byte_for_byte_what_the_legacy_writer_wrote(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", x=1, text="é✓")
    expected = ('{"v":1,"ts":"2026-10-18T10:00:00.000001+00:00","seq":1,"proc":"cli","pid":%d,"kind":"custom.kind","actor":"root",'
                '"run":null,"trace":null,"x":1,"text":"é✓"}\n' % os.getpid())
    assert kit.files()[0].read_bytes() == expected.encode()


def test_a_free_field_never_replaces_an_envelope_field(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", v=99, ts="x", seq=7, pid=1, kind="k", actor_x=1)
    event = kit.events()[0]
    assert (event["v"], event["seq"], event["pid"], event["kind"]) == (1, 1, os.getpid(), "custom.kind") and event["actor_x"] == 1
    assert event["ts"] != "x"


def test_a_none_free_field_is_written_as_null(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", error=None)
    assert kit.events()[0]["error"] is None


# ------------------------------------------------------------------------------------------------------ actor and run


def test_actor_and_run_come_from_the_environment_at_the_time_of_the_emission(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.environment.set("ORG_AGENT", "ceo/eng")  # set after the sink was built: read at emission time
    kit.environment.set("ORG_RUN_ID", "ceo/eng@20260101T000000000000")
    kit.sink.emit("custom.kind")
    kit.sink.emit("custom.kind", actor="runtime", run="other@1")
    a, b = kit.events()
    assert (a["actor"], a["run"]) == ("ceo/eng", "ceo/eng@20260101T000000000000")
    assert (b["actor"], b["run"]) == ("runtime", "other@1")


def test_an_empty_variable_is_no_variable(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.environment.set("ORG_AGENT", "")
    kit.environment.set("ORG_RUN_ID", "")
    kit.sink.emit("custom.kind")
    assert (kit.events()[0]["actor"], kit.events()[0]["run"]) == ("root", None)


def test_in_the_scheduler_the_actor_is_the_runtime_unless_the_environment_names_one(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.label.set("scheduler")
    kit.sink.emit("custom.kind")
    kit.environment.set("ORG_AGENT", "ceo")
    kit.sink.emit("custom.kind")
    kit.sink.emit("custom.kind", proc="cli")
    assert [e["actor"] for e in kit.events()] == ["runtime", "ceo", "ceo"]


def test_an_event_for_the_scheduler_has_the_runtime_as_actor_even_from_another_process(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", proc="scheduler")
    assert (kit.events()[0]["proc"], kit.events()[0]["actor"]) == ("scheduler", "runtime")


# ------------------------------------------------------------------------------------------------------ the process


def test_the_process_name_is_in_the_file_name_and_an_explicit_one_has_its_own_file(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.label.set("mcp")
    kit.sink.emit("custom.kind")
    kit.sink.emit("custom.kind", proc="scheduler")
    assert sorted(f.name.split("-")[0] for f in kit.files()) == ["mcp", "scheduler"]
    assert {e["proc"] for e in kit.events()} == {"mcp", "scheduler"}


def test_the_label_is_read_at_each_emission(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("a")
    kit.label.set("mcp")
    kit.sink.emit("b")
    assert sorted((e["kind"], e["proc"]) for e in kit.events()) == [("a", "cli"), ("b", "mcp")]


def test_two_sinks_of_the_same_root_and_pool_share_the_file_and_the_numbering(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    other = kit.sink_for_root()
    kit.sink.emit("one")
    other.emit("two")
    kit.sink.emit("three")
    (file,) = kit.files()
    assert [(e["kind"], e["seq"]) for e in kit.events()] == [("one", 1), ("two", 2), ("three", 3)] and file.exists()


def test_the_next_day_is_a_new_file_and_the_numbering_starts_again(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind")
    kit.sink.emit("custom.kind")
    kit.clock.advance(86400)
    kit.sink.emit("custom.kind")
    kit.sink.emit("custom.kind")
    days = sorted(f.parent.name for f in kit.files())
    assert days == ["2026-10-18", "2026-10-19"]
    for f in kit.files():
        assert [json.loads(line)["seq"] for line in f.read_text().splitlines()] == [1, 2]


# ------------------------------------------------------------------------------------------------------ line size


def test_a_long_line_is_shrunk_to_8kb_and_marked(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", text="x" * 50_000, items=[f"item-{i}" * 40 for i in range(500)], nested={"a": "y" * 20_000})
    (line,) = kit.files()[0].read_text().splitlines()
    assert len(line.encode()) <= LINE_MAX
    event = json.loads(line)
    assert event["truncated"] is True and event["kind"] == "custom.kind" and event["seq"] == 1 and event["text"].endswith("…")


def test_an_enormous_payload_of_many_fields_still_fits(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("custom.kind", **{f"field{i}": "z" * 3000 for i in range(40)})
    (line,) = kit.files()[0].read_text().splitlines()
    assert len(line.encode()) <= LINE_MAX and json.loads(line)["truncated"] is True


# ---------------------------------------------------------------------------------------------------- never raises


def test_a_failing_serializer_and_circular_values_are_swallowed_and_counted(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    loop: dict[str, object] = {}
    loop["self"] = loop

    class Bad:
        def __str__(self) -> str:
            raise RuntimeError("no string for you")

    kit.sink.emit("custom.kind", loop=loop)
    kit.sink.emit("custom.kind", bad=Bad())
    kit.sink.emit("custom.kind", fine=1)
    assert kit.pool.dropped() == 2
    assert [e.get("fine") for e in kit.events()] == [1]


def test_an_events_path_that_is_a_file_never_fails_the_caller_and_is_reported_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    kit = sink_kit(tmp_path)
    (tmp_path / ".runtime").mkdir()
    (tmp_path / EVENTS_REL).write_text("a file where the directory should be")
    for _ in range(3):
        kit.sink.emit("custom.kind")
    assert kit.pool.dropped() == 3
    assert capsys.readouterr().err.count("event log is unavailable") == 1


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_a_read_only_day_directory_never_fails_the_caller(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    kit = sink_kit(tmp_path)
    kit.label.set("mcp")
    kit.sink.emit("custom.kind")
    day = kit.files()[0].parent
    kit.label.set("scheduler")  # another process name: its own file has to be created in the read-only directory
    day.chmod(0o500)
    try:
        kit.sink.emit("custom.kind")
        kit.sink.emit("custom.kind")
    finally:
        day.chmod(0o700)
    assert kit.pool.dropped() >= 2 and capsys.readouterr().err.count("event log is unavailable") == 1


def test_nothing_is_written_where_there_is_no_organization(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path / "nowhere" / "org", org_md=None)
    kit.sink.emit("custom.kind")
    assert not (tmp_path / "nowhere").exists() and kit.pool.dropped() == 0


def test_events_false_switches_emission_off_and_on_again(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.org_md.put("---\nevents: false\n---\nrules\n")
    kit.sink.emit("custom.kind")
    assert not (tmp_path / EVENTS_REL).exists()
    kit.org_md.put(ORG_MD)
    kit.sink.emit("custom.kind")
    assert [e["kind"] for e in kit.events()] == ["custom.kind"]


def test_the_switch_is_asked_for_every_event(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    kit.sink.emit("a")
    kit.org_md.put("---\nevents: no\n---\n")
    kit.sink.emit("b")
    kit.org_md.put(ORG_MD)
    kit.sink.emit("c")
    assert [e["kind"] for e in kit.events()] == ["a", "c"]


# ---------------------------------------------------------------------------------------------------- retry window


def block(kit: SinkKit) -> Path:
    (kit.root / ".runtime").mkdir(exist_ok=True)
    blocker = kit.root / EVENTS_REL
    blocker.write_text("x")
    return blocker


def test_the_log_recovers_when_the_directory_becomes_writable_after_the_retry_window(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path, retry_after=5.0)
    blocker = block(kit)
    kit.sink.emit("custom.kind")
    blocker.unlink()
    kit.sink.emit("custom.kind", early=True)  # inside the window: not even tried
    assert not blocker.exists() and kit.pool.dropped() == 2
    kit.clock.advance(5.1)
    kit.sink.emit("custom.kind", after=True)
    (event,) = kit.events()
    assert event["after"] is True and event["seq"] == 1


def test_a_retry_window_of_zero_tries_again_at_once(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path, retry_after=0.0)
    blocker = block(kit)
    kit.sink.emit("custom.kind")
    blocker.unlink()
    kit.sink.emit("custom.kind", after=True)
    (event,) = kit.events()
    assert event["after"] is True and event["seq"] == 1


# ---------------------------------------------------------------------------------------------------- git hygiene


def test_the_first_event_of_a_new_events_directory_asks_to_keep_the_events_out_of_git(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    assert kit.ignore.text is None
    kit.sink.emit("custom.kind")
    assert kit.ignore.text is not None and ".runtime/events/" in kit.ignore.text.split()


def test_an_existing_events_directory_is_not_asked_about_again(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    (tmp_path / EVENTS_REL).mkdir(parents=True)
    kit.sink.emit("custom.kind")
    assert kit.ignore.text is None


def test_an_ignore_list_that_fails_does_not_lose_the_event(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)

    class Failing(MemoryIgnoreList):
        def ensure_runtime_files(self) -> None:
            raise RuntimeError("cannot write .gitignore")

    sink = build_sink(kit.root, kit.pool, kit.clock, kit.environment, kit.label, Failing(), kit.org_md.switch, 5.0)
    sink.emit("custom.kind")
    assert [e["kind"] for e in kit.events()] == ["custom.kind"] and kit.pool.dropped() == 0


def test_the_default_retry_window_of_the_sink_is_five_seconds() -> None:  # moved from test_legacy_surface.py (deleted with the legacy names)
    from orgmcp.telemetry._sink import RETRY_AFTER

    assert RETRY_AFTER == 5.0
