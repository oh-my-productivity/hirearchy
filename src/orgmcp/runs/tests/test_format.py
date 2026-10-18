"""The text format of a run log: what the pure ``log_*`` functions write is what the parsers read back."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from orgmcp.runs import (
    log_exit,
    log_failed_start,
    log_header,
    log_interrupted,
    log_invocation,
    log_note,
    log_prompt,
    log_retired,
    log_timeout,
    run_id_of,
    run_record,
)
from orgmcp.runs._format import cut_tail, is_failed, is_runtime_only, parse_facts

from ._red import red

pytestmark = red


# ---------------------------------------------------------------------------------------------------- what is written


def test_the_header_names_the_agent_the_batch_and_its_senders() -> None:
    assert log_header("ceo/eng", 2, ["root", "ceo", "root"]) == "# run of ceo/eng, 2 message(s)\n# senders: ceo, root\n"


def test_the_senders_are_sorted_and_listed_once() -> None:
    assert log_header("a", 3, iter(["z", "runtime", "z", "b"])) == "# run of a, 3 message(s)\n# senders: b, runtime, z\n"
    assert log_header("a", 0, []) == "# run of a, 0 message(s)\n# senders: \n"


def test_the_invocation_names_the_directory_and_the_command() -> None:
    assert log_invocation(Path("/work/ceo"), ["kiro-cli", "chat", "--agent", "x"]) == (
        "# cwd: /work/ceo\n# cmd: kiro-cli chat --agent x <prompt on stdin>\n"
    )
    assert log_invocation("/w", ("python", "agent.py")) == "# cwd: /w\n# cmd: python agent.py <prompt on stdin>\n"


def test_the_prompt_sits_between_two_marks() -> None:
    assert log_prompt("Do it.\nNow.") == "# ---- prompt ----\nDo it.\nNow.\n# ---- output ----\n"


def test_the_closing_lines() -> None:
    assert log_exit(0, 3.4) == "\n# exit 0 after 3s\n"
    assert log_exit(-9, 12.6) == "\n# exit -9 after 13s\n"
    assert log_timeout(3600) == "\n# killed after 3600s timeout\n"
    assert log_timeout(0.5) == "\n# killed after 0s timeout\n"
    assert log_retired() == "\n# killed: the agent was retired during its run\n"
    assert log_interrupted() == "\n# interrupted by scheduler shutdown\n"
    assert log_failed_start(FileNotFoundError(2, "No such file or directory: 'kiro-cli'")) == (
        "\n# failed to start: [Errno 2] No such file or directory: 'kiro-cli'\n"
    )
    assert log_failed_start("plain text") == "\n# failed to start: plain text\n"


def test_a_note_is_a_comment_on_a_line_of_its_own() -> None:
    assert log_note("killed: orphaned run of a scheduler that died") == "\n# killed: orphaned run of a scheduler that died\n"


def test_the_id_of_a_run_is_the_agent_and_the_stem_of_its_log() -> None:
    assert run_id_of("ceo/eng", Path("/org/ceo/eng/runs/20261018T100000000001.log")) == "ceo/eng@20261018T100000000001"
    assert run_id_of("ceo", "ceo/runs/20261018T100000000001.log") == "ceo@20261018T100000000001"
    assert run_id_of("root", "x.log") == "root@x"


def test_the_record_of_a_run_in_flight() -> None:
    record = run_record(pgid=4711, lstart="Sun Oct 18 10:00:00 2026", started=1_792_317_600.25, scheduler=42, log="ceo/runs/x.log")
    assert record == {"pgid": 4711, "lstart": "Sun Oct 18 10:00:00 2026", "started": 1_792_317_600.25, "scheduler": 42, "log": "ceo/runs/x.log"}
    assert list(record) == ["pgid", "lstart", "started", "scheduler", "log"]  # the order of the keys is the order in running.json
    assert run_record(pgid=1, lstart=None, started=0.0, scheduler=2, log="l")["lstart"] is None


# --------------------------------------------------------------------------------------------- what is read back


def head() -> str:
    return log_header("ceo", 1, ["root"]) + log_invocation("/w", ["kiro"]) + log_prompt("Do it.") + "the output\n"


@pytest.mark.parametrize("footer, failed, facts", [
    (lambda: log_exit(0, 3), False, {"exit_code": 0, "seconds": 3}),
    (lambda: log_exit(1, 2), True, {"exit_code": 1, "seconds": 2}),
    (lambda: log_exit(-15, 0), True, {"exit_code": -15, "seconds": 0}),
    (lambda: log_timeout(60) + log_exit(-9, 60), True, {"exit_code": -9, "seconds": 60, "timed_out": True}),
    (lambda: log_retired() + log_exit(-9, 4), True, {"exit_code": -9, "seconds": 4, "killed": True}),
    (lambda: log_interrupted(), True, {"killed": True}),
    (lambda: log_failed_start("no such file"), True, {"failed_start": True}),
    (lambda: log_note("killed: orphaned run of a scheduler that died"), False, {"killed": True}),
    (lambda: "", False, {}),
], ids=["ok", "exit 1", "signal", "timeout", "retired", "interrupted", "failed start", "orphan note", "still going"])
def test_what_is_written_at_the_end_is_what_the_parsers_find(
    footer: Callable[[], str], failed: bool, facts: dict[str, object]
) -> None:
    text = head() + footer()
    assert is_failed(text) is failed
    assert parse_facts(text) == facts


def test_the_senders_header_is_read_back() -> None:
    assert is_runtime_only(log_header("ceo", 1, ["runtime"]) + log_prompt("x")) is True
    assert is_runtime_only(log_header("ceo", 2, ["runtime", "root"]) + log_prompt("x")) is False
    assert is_runtime_only(log_header("ceo", 1, ["root"])) is False
    assert is_runtime_only("") is False


def test_a_mark_inside_a_line_is_no_closing_line() -> None:
    assert is_failed("said: # failed to start\n") is False
    assert parse_facts("said: # exit 0 after 3s\n") == {}


def test_the_facts_are_a_new_object() -> None:
    assert parse_facts("") is not parse_facts("")


# ----------------------------------------------------------------------------------------------------------- the tail


def test_cut_tail_of_a_whole_file_is_the_file() -> None:
    assert cut_tail(b"a\nb\n", 3, 10) == ("a\nb\n", False)
    assert cut_tail(b"", 0, 10) == ("", False)


def test_cut_tail_drops_the_partial_first_line_when_the_file_is_longer_than_the_window() -> None:
    assert cut_tail(b"ne2\nline3\n", 18, 10) == ("line3\n", True)
    assert cut_tail(b"xxxx", 99, 10) == ("xxxx", True)


def test_cut_tail_keeps_the_last_lines() -> None:
    assert cut_tail(b"1\n2\n3\n4\n", 8, 2) == ("3\n4\n", True)
    assert cut_tail(b"1\n2\n3\n4", 7, 2) == ("3\n4", True)
    assert cut_tail(b"1\n2\n", 4, 2) == ("1\n2\n", False)
