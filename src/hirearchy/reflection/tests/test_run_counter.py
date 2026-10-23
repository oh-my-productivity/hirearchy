"""``LogRunCounter``: the runs of a team between two moments are the run logs whose name falls in the window."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import RUNTIME, Message, run_credit_title
from hirearchy.mail.testing import MailHarness, memory_mailbox
from hirearchy.reflection._ports import RunCounter
from hirearchy.reflection._runs import LogRunCounter
from hirearchy.runs.testing import RunsHarness, fs_runs, memory_runs

A, B, C, D = "20260101T000001000000", "20260101T000002000000", "20260101T000003000000", "20260101T000004000000"


@pytest.fixture(params=[fs_runs, memory_runs], ids=lambda f: f.__name__)
def runs(request: pytest.FixtureRequest, tmp_path: Path) -> RunsHarness:
    harness: RunsHarness = request.param(tmp_path)
    for addr in ("ceo", "ceo/eng", "ops"):
        harness.add_agent(addr)
    return harness


@pytest.fixture
def mail(tmp_path: Path) -> MailHarness:
    return memory_mailbox(tmp_path)


def credit(mail: MailHarness, addr: str, stem: str) -> None:
    """The runtime returned the run of ``addr`` whose log is ``<stem>.log``."""
    mail.writer.store(Message(
        sender=RUNTIME, to=addr, type="note", budget=1, wake=False, title=run_credit_title(addr, stem), body="returned", id=f"{stem[:-1]}9-runtime-aaaa",
    ))


def log(runs: RunsHarness, addr: str, stamp: str, suffix: str = ".log") -> None:
    runs.put_log(addr, stamp + suffix, "# run\n")


def test_it_is_a_run_counter(runs: RunsHarness, mail: MailHarness) -> None:
    assert isinstance(LogRunCounter(runs.reader, mail.reader), RunCounter)


def test_the_logs_of_every_agent_of_the_team_in_the_window_are_counted(runs: RunsHarness, mail: MailHarness) -> None:
    for addr, stamp in (("ceo", B), ("ceo/eng", C), ("ops", C)):
        log(runs, addr, stamp)
    assert LogRunCounter(runs.reader, mail.reader).runs_between(["ceo", "ceo/eng"], A, D) == 2


def test_a_window_without_an_end_runs_to_now(runs: RunsHarness, mail: MailHarness) -> None:
    for stamp in (A, B, C):
        log(runs, "ceo", stamp)
    assert LogRunCounter(runs.reader, mail.reader).runs_between(["ceo"], B, None) == 2


def test_the_window_edges_are_compared_on_the_first_21_characters(runs: RunsHarness, mail: MailHarness) -> None:
    for stamp in (A, B, C):
        log(runs, "ceo", stamp)
    counter = LogRunCounter(runs.reader, mail.reader)
    assert counter.runs_between(["ceo"], B, B) == 1 and counter.runs_between(["ceo"], A, C) == 3 and counter.runs_between(["ceo"], C, A) == 0


def test_hidden_logs_and_other_files_are_not_runs(runs: RunsHarness, mail: MailHarness) -> None:
    log(runs, "ceo", B)
    log(runs, "ceo", "." + B)
    log(runs, "ceo", B, ".txt")
    assert LogRunCounter(runs.reader, mail.reader).runs_between(["ceo"], A, D) == 1


def test_an_agent_without_logs_adds_none(runs: RunsHarness, mail: MailHarness) -> None:
    assert LogRunCounter(runs.reader, mail.reader).runs_between(["ceo", "ghost"], A, None) == 0


def test_nobody_in_the_team_made_no_runs(runs: RunsHarness, mail: MailHarness) -> None:
    log(runs, "ceo", B)
    assert LogRunCounter(runs.reader, mail.reader).runs_between([], A, None) == 0


def test_a_credited_log_is_not_counted(runs: RunsHarness, mail: MailHarness) -> None:
    for stamp in (B, C):
        log(runs, "ceo", stamp)
    credit(mail, "ceo", C)
    assert LogRunCounter(runs.reader, mail.reader).runs_between(["ceo"], A, D) == 1


def test_a_credit_for_another_agents_stem_changes_nothing(runs: RunsHarness, mail: MailHarness) -> None:
    for addr in ("ceo", "ops"):
        log(runs, addr, B)
    credit(mail, "ops", B)  # the same stem, another agent's run
    counter = LogRunCounter(runs.reader, mail.reader)
    assert counter.runs_between(["ceo"], A, D) == 1 and counter.runs_between(["ops"], A, D) == 0 and counter.runs_between(["ceo", "ops"], A, D) == 1
