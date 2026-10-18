"""Contract of ``RunLogReader``: the filesystem reader, the in-memory fake and the caching decorator read logs the same way."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import stamp_of
from orgmcp.runs import RunLogFile, RunLogReader, RunOutcomes, RunWindow
from orgmcp.runs.testing import IMPLEMENTATIONS, RunsHarness


T1, T2, T3 = "20261018T100000000001", "20261018T110000000002", "20261018T120000000003"
START = {t: cast(datetime, stamp_of(t)) for t in (T1, T2, T3)}
HEADER = "# run of ceo, 1 message(s)\n# senders: root\n# cwd: /work\n# cmd: kiro-cli chat <prompt on stdin>\n"
PROMPT = "# ---- prompt ----\nDo the thing.\n# ---- output ----\n"
OK = HEADER + PROMPT + "all good\n\n# exit 0 after 3s\n"


@pytest.fixture(params=IMPLEMENTATIONS[RunLogReader], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RunsHarness:
    made = cast(Callable[[Path], RunsHarness], request.param)(tmp_path)
    assert isinstance(made.reader, RunLogReader)
    return made


def whole(t: datetime) -> int:
    """The second the time falls in (mtimes are set in whole seconds, so that no float rounding is involved)."""
    return int(t.timestamp())


def at(seconds: int) -> datetime:
    return datetime.fromtimestamp(seconds, timezone.utc)


def log(h: RunsHarness, stamp: str, content: str, addr: str = "ceo") -> Path:
    return h.put_log(addr, f"{stamp}.log", content)


# ------------------------------------------------------------------------------------------------------------------ count


def test_an_agent_without_a_runs_directory_has_used_no_runs(h: RunsHarness) -> None:
    h.add_agent("ceo")
    assert h.reader.count("ceo") == 0 and h.reader.count("nobody/at/all") == 0


def test_only_visible_log_files_count(h: RunsHarness) -> None:
    log(h, T1, OK)
    log(h, T2, OK)
    h.put_log("ceo", ".hidden.log", OK)
    h.put_log("ceo", "notes.txt", "not a log")
    h.put_log("ceo", f"{T3}.log.tmp", "not a log")
    assert h.reader.count("ceo") == 2


def test_every_agent_has_its_own_logs(h: RunsHarness) -> None:
    log(h, T1, OK)
    log(h, T1, OK, "ceo/eng")
    log(h, T2, OK, "ceo/eng")
    assert (h.reader.count("ceo"), h.reader.count("ceo/eng"), h.reader.count("root")) == (1, 2, 0)


# ------------------------------------------------------------------------------------------------------------------ files


def test_files_are_listed_oldest_first_with_the_time_in_their_names(h: RunsHarness) -> None:
    p2, p1 = log(h, T2, OK), log(h, T1, OK)
    assert h.reader.files("ceo") == [RunLogFile(T1, p1, START[T1]), RunLogFile(T2, p2, START[T2])]


def test_a_log_whose_name_is_no_timestamp_is_listed_without_a_start(h: RunsHarness) -> None:
    p1, manual = log(h, T1, OK), h.put_log("ceo", "manual.log", OK)
    assert h.reader.files("ceo") == [RunLogFile(T1, p1, START[T1]), RunLogFile("manual", manual, None)]


def test_hidden_and_foreign_files_are_not_logs(h: RunsHarness) -> None:
    h.put_log("ceo", ".hidden.log", OK)
    h.put_log("ceo", "readme.md", "x")
    assert h.reader.files("ceo") == [] and h.reader.files("nobody") == []


# ---------------------------------------------------------------------------------------------------------------- windows


def test_a_window_starts_at_the_name_and_ends_at_the_mtime(h: RunsHarness) -> None:
    p = log(h, T1, OK)
    h.set_mtime(p, whole(START[T1]) + 90)
    assert h.reader.windows("ceo") == [RunWindow(START[T1], at(whole(START[T1]) + 90))]


def test_a_window_never_ends_before_it_starts(h: RunsHarness) -> None:
    p = log(h, T1, OK)
    h.set_mtime(p, whole(START[T1]) - 600)
    assert h.reader.windows("ceo") == [RunWindow(START[T1], START[T1])]


def test_windows_are_oldest_first_and_skip_hidden_logs_and_names_without_a_time(h: RunsHarness) -> None:
    for stamp in (T3, T1, T2):
        h.set_mtime(log(h, stamp, OK), whole(START[stamp]) + 10)
    h.put_log("ceo", "manual.log", OK)
    h.put_log("ceo", f".{T1}.log", OK)
    windows = h.reader.windows("ceo")
    assert [w.start for w in windows] == [START[T1], START[T2], START[T3]]
    assert [w.end for w in windows] == [at(whole(START[t]) + 10) for t in (T1, T2, T3)]
    assert h.reader.windows("nobody") == []


def test_a_window_is_a_pair(h: RunsHarness) -> None:
    log(h, T1, OK)
    start, end = h.reader.windows("ceo")[0]
    assert start == START[T1] and end >= start and start.tzinfo == timezone.utc


# --------------------------------------------------------------------------------------------------------------- outcomes


def outcomes(h: RunsHarness, content: str, stamp: str = T1) -> RunOutcomes:
    log(h, stamp, content)
    return h.reader.outcomes("ceo")


def test_a_run_that_exited_with_zero_is_ordinary(h: RunsHarness) -> None:
    assert outcomes(h, OK) == RunOutcomes(frozenset(), frozenset())


@pytest.mark.parametrize("footer", [
    "\n# exit 1 after 3s\n",
    "\n# exit -9 after 3s\n",
    "\n# failed to start: [Errno 2] No such file or directory: 'kiro-cli'\n",
    "\n# killed after 3600s timeout\n\n# exit -9 after 3600s\n",
    "\n# interrupted by scheduler shutdown\n",
], ids=["exit 1", "killed by signal", "failed to start", "timeout", "interrupted"])
def test_runs_that_failed_are_found_by_the_closing_lines(h: RunsHarness, footer: str) -> None:
    assert outcomes(h, HEADER + PROMPT + "some output" + footer) == RunOutcomes(frozenset({START[T1]}), frozenset())


def test_the_last_exit_line_decides(h: RunsHarness) -> None:
    assert outcomes(h, OK + "# exit 1 after 1s\n# exit 0 after 2s\n").failed == frozenset()


def test_a_closing_line_must_start_a_line(h: RunsHarness) -> None:
    assert outcomes(h, HEADER + PROMPT + "the agent said: # killed after 5s timeout\n# exit 0 after 1s\n").failed == frozenset()


def test_a_log_without_closing_lines_counts_as_an_ordinary_run(h: RunsHarness) -> None:
    assert outcomes(h, HEADER + PROMPT + "still going") == RunOutcomes(frozenset(), frozenset())
    assert outcomes(h, "hand-made log\n", T2) == RunOutcomes(frozenset(), frozenset())


@pytest.mark.parametrize("senders, runtime_only", [
    ("runtime", True), ("runtime, runtime", True), (" runtime ", True), ("root", False), ("runtime, root", False), ("", False),
    ("ceo/eng, runtime", False),
])
def test_a_run_woken_only_by_the_runtime_is_found_by_the_senders_header(h: RunsHarness, senders: str, runtime_only: bool) -> None:
    content = f"# run of ceo, 1 message(s)\n# senders: {senders}\n" + PROMPT + "\n# exit 0 after 1s\n"
    assert (START[T1] in outcomes(h, content).runtime_only) is runtime_only


def test_senders_are_read_from_the_header_only(h: RunsHarness) -> None:
    prompt = "# ---- prompt ----\n# senders: runtime\n# ---- output ----\n"
    assert outcomes(h, "# run of ceo, 1 message(s)\n# senders: root\n" + prompt).runtime_only == frozenset()


def test_a_failed_run_woken_by_the_runtime_is_both(h: RunsHarness) -> None:
    content = "# run of ceo, 1 message(s)\n# senders: runtime\n" + PROMPT + "\n# exit 2 after 1s\n"
    assert outcomes(h, content) == RunOutcomes(frozenset({START[T1]}), frozenset({START[T1]}))


def test_every_log_is_judged_by_itself(h: RunsHarness) -> None:
    log(h, T1, OK)
    log(h, T2, HEADER + PROMPT + "\n# exit 1 after 1s\n")
    log(h, T3, "# run of ceo, 1 message(s)\n# senders: runtime\n" + PROMPT + "\n# exit 0 after 1s\n")
    assert h.reader.outcomes("ceo") == RunOutcomes(frozenset({START[T2]}), frozenset({START[T3]}))


def test_logs_that_are_hidden_or_have_no_time_in_their_name_are_not_judged(h: RunsHarness) -> None:
    h.put_log("ceo", "manual.log", HEADER + PROMPT + "\n# exit 1 after 1s\n")
    h.put_log("ceo", f".{T1}.log", HEADER + PROMPT + "\n# exit 1 after 1s\n")
    assert h.reader.outcomes("ceo") == RunOutcomes(frozenset(), frozenset())
    assert h.reader.outcomes("nobody") == RunOutcomes(frozenset(), frozenset())


def test_only_the_last_2_kb_are_searched_for_closing_lines(h: RunsHarness) -> None:
    failing = HEADER + PROMPT + "\n# exit 1 after 1s\n" + "x" * 3000 + "\n"
    assert outcomes(h, failing).failed == frozenset()
    log(h, T2, HEADER + PROMPT + "x" * 3000 + "\n# exit 1 after 1s\n")
    assert h.reader.outcomes("ceo").failed == frozenset({START[T2]})


def test_only_the_first_4_kb_are_searched_for_the_senders(h: RunsHarness) -> None:
    late = "# run of ceo, 1 message(s)\n" + "# filler\n" * 600 + "# senders: runtime\n" + PROMPT
    assert outcomes(h, late).runtime_only == frozenset()


def test_the_decoding_of_a_log_cannot_fail(h: RunsHarness) -> None:
    content = HEADER.encode() + PROMPT.encode() + b"binary \xff\xfe junk\n\n# exit 1 after 1s\n"
    h.put_log("ceo", f"{T1}.log", content)
    assert h.reader.outcomes("ceo").failed == frozenset({START[T1]})


# ---------------------------------------------------------------------------------------------------------------- last_end


def test_the_end_of_the_last_run_is_the_latest_mtime(h: RunsHarness) -> None:
    h.set_mtime(log(h, T1, OK), 1_000_000.0)
    h.set_mtime(log(h, T2, OK), 2_500_000.5)
    h.set_mtime(log(h, T3, OK), 1_500_000.0)
    h.set_mtime(h.put_log("ceo", "notes.txt", "x"), 9_000_000.0)
    assert h.reader.last_end("ceo") == 2_500_000.5


def test_without_logs_the_last_end_is_zero(h: RunsHarness) -> None:
    h.add_agent("ceo")
    assert h.reader.last_end("ceo") == 0.0 and h.reader.last_end("nobody") == 0.0


def test_a_hidden_log_counts_for_the_last_end_as_it_always_did_for_the_stall_check(h: RunsHarness) -> None:
    h.set_mtime(log(h, T1, OK), 1_000_000.0)
    h.set_mtime(h.put_log("ceo", ".odd.log", OK), 3_000_000.0)
    assert h.reader.last_end("ceo") == 3_000_000.0


# -------------------------------------------------------------------------------------------------------------------- facts


def test_a_finished_run_reports_its_exit_code_and_seconds(h: RunsHarness) -> None:
    assert h.reader.facts(log(h, T1, OK)) == {"exit_code": 0, "seconds": 3}
    assert h.reader.facts(log(h, T2, HEADER + PROMPT + "\n# exit -15 after 125s\n")) == {"exit_code": -15, "seconds": 125}


def test_the_last_exit_line_is_the_one_reported(h: RunsHarness) -> None:
    assert h.reader.facts(log(h, T1, "\n# exit 1 after 1s\n\n# exit 0 after 9s\n")) == {"exit_code": 0, "seconds": 9}


def test_a_timeout_is_reported(h: RunsHarness) -> None:
    path = log(h, T1, HEADER + PROMPT + "\n# killed after 3600s timeout\n\n# exit -9 after 3600s\n")
    assert h.reader.facts(path) == {"exit_code": -9, "seconds": 3600, "timed_out": True}


@pytest.mark.parametrize("footer", [
    "\n# killed: the agent was retired during its run\n\n# exit -9 after 2s\n",
    "\n# interrupted by scheduler shutdown\n",
    "\n# killed: orphaned run of a scheduler that died\n",
])
def test_a_run_that_was_killed_is_reported(h: RunsHarness, footer: str) -> None:
    assert h.reader.facts(log(h, T1, HEADER + PROMPT + footer)).get("killed") is True


def test_a_start_that_failed_is_reported(h: RunsHarness) -> None:
    path = log(h, T1, HEADER + "\n# failed to start: [Errno 2] No such file or directory\n")
    assert h.reader.facts(path) == {"failed_start": True}


def test_a_run_still_going_has_no_facts(h: RunsHarness) -> None:
    assert h.reader.facts(log(h, T1, HEADER + PROMPT + "working...\n")) == {}


def test_closing_lines_must_start_a_line_to_count(h: RunsHarness) -> None:
    assert h.reader.facts(log(h, T1, "the agent wrote # exit 0 after 3s and # failed to start\n")) == {}


def test_only_the_last_4_kb_are_searched_for_facts(h: RunsHarness) -> None:
    assert h.reader.facts(log(h, T1, "\n# exit 0 after 3s\n" + "x" * 5000 + "\n")) == {}
    assert h.reader.facts(log(h, T2, "x" * 5000 + "\n# exit 0 after 3s\n")) == {"exit_code": 0, "seconds": 3}


def test_a_log_that_cannot_be_read_has_no_facts(h: RunsHarness) -> None:
    assert h.reader.facts(h.root / "ceo" / "runs" / f"{T1}.log") == {}


def test_facts_come_back_as_a_new_object_every_time(h: RunsHarness) -> None:
    path = log(h, T1, OK)
    h.reader.facts(path)["exit_code"] = 99
    assert h.reader.facts(path) == {"exit_code": 0, "seconds": 3}


# --------------------------------------------------------------------------------------------------------------------- tail


def test_a_short_log_comes_back_whole(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "a\nb\nc\n"), 1000, 10) == ("a\nb\nc\n", False)
    assert h.reader.tail(log(h, T2, "a\nb"), 1000, 10) == ("a\nb", False)
    assert h.reader.tail(log(h, T3, ""), 1000, 10) == ("", False)


def test_the_bytes_from_the_end_are_read_and_the_partial_first_line_dropped(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "line1\nline2\nline3\n"), 10, 100) == ("line3\n", True)


def test_a_cut_drops_the_first_line_even_when_the_window_starts_on_a_line(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "line1\nline2\nline3\n"), 12, 100) == ("line3\n", True)


def test_a_cut_window_without_a_newline_is_kept_as_it_is(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "x" * 50), 10, 100) == ("x" * 10, True)


def test_lines_beyond_the_limit_are_dropped_from_the_start(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "1\n2\n3\n4\n5\n"), 1000, 3) == ("3\n4\n5\n", True)
    assert h.reader.tail(log(h, T2, "1\n2\n3"), 1000, 2) == ("2\n3", True)


def test_exactly_as_many_lines_as_allowed_is_not_a_cut(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "1\n2\n3\n"), 1000, 3) == ("1\n2\n3\n", False)


def test_empty_lines_are_lines(h: RunsHarness) -> None:
    assert h.reader.tail(log(h, T1, "a\n\n\nb\n"), 1000, 2) == ("\nb\n", True)
    assert h.reader.tail(log(h, T2, "\n"), 1000, 5) == ("\n", False)


def test_the_two_limits_work_together(h: RunsHarness) -> None:
    content = "".join(f"line {i:02d}\n" for i in range(20))
    text, cut = h.reader.tail(log(h, T1, content), 8 * 6 + 3, 4)
    assert (text, cut) == ("line 16\nline 17\nline 18\nline 19\n", True)


def test_undecodable_bytes_are_replaced(h: RunsHarness) -> None:
    assert h.reader.tail(h.put_log("ceo", f"{T1}.log", b"ok \xff\n"), 100, 10) == ("ok \ufffd\n", False)


def test_a_log_that_cannot_be_read_raises_oserror_for_the_tail(h: RunsHarness) -> None:
    with pytest.raises(OSError):
        h.reader.tail(h.root / "ceo" / "runs" / f"{T1}.log", 100, 10)


# --------------------------------------------------------------------------------------------------------------------- head


def test_the_head_is_the_first_bytes(h: RunsHarness) -> None:
    path = log(h, T1, "hello world")
    assert h.reader.head(path, 5) == "hello" and h.reader.head(path, 100) == "hello world"


def test_the_head_of_an_empty_log_is_empty(h: RunsHarness) -> None:
    assert h.reader.head(log(h, T1, ""), 100) == ""


def test_a_character_cut_in_the_middle_is_replaced(h: RunsHarness) -> None:
    assert h.reader.head(log(h, T1, "éa"), 1) == "\ufffd"


def test_a_log_that_cannot_be_read_raises_oserror_for_the_head(h: RunsHarness) -> None:
    with pytest.raises(OSError):
        h.reader.head(h.root / "ceo" / "runs" / f"{T1}.log", 100)
