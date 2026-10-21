"""Contract of ``ServiceHints``: what the ``report`` tool adds for a request for a service, and the client's words in a feedback note."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.services import FEEDBACK_HEADER, ServiceHints
from hirearchy.services.testing import IMPLEMENTATIONS, ServicesWorld, fs_world, memory_world

from ._support import STEPS, define, implementations, populated, request


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceHints]))
def hints(request: pytest.FixtureRequest, tmp_path: Path) -> ServiceHints:
    made = request.param(tmp_path)
    assert isinstance(made, ServiceHints)
    return made


# ------------------------------------------------------------------------------ report_hint


def test_an_ordinary_task_gets_no_hint(w: ServicesWorld) -> None:
    task = Message(sender="root", to="ceo", type="task", body="b", id="T1")
    assert w.hints.report_hint("ceo", task, "done") == ""


@pytest.mark.parametrize("status", ["blocked", "", "open"])
def test_only_a_final_result_gets_a_hint(w: ServicesWorld, status: str) -> None:
    define(w)
    assert w.hints.report_hint("ceo", request(w), status) == ""


def test_an_owner_without_a_playbook_is_told_to_write_one(w: ServicesWorld) -> None:
    define(w)
    for status in ("done", "failed"):
        assert w.hints.report_hint("ceo", request(w), status) == (
            "This service has no playbook yet: write v1 now with revise_playbook - the steps your team followed and what you would change."
        )


def test_an_owner_with_a_playbook_is_told_the_lessons_are_recorded(w: ServicesWorld) -> None:
    define(w, playbook=STEPS)
    assert w.hints.report_hint("ceo", request(w), "done") == (
        "Lessons recorded. If they call for a playbook change now, use revise_playbook; otherwise they are reviewed before the next request."
    )


def test_a_locked_contract_gets_no_hint(w: ServicesWorld) -> None:
    define(w, locked=True)
    assert w.hints.report_hint("ceo", request(w), "done") == ""


def test_a_service_that_is_gone_or_not_the_reporters_gets_no_hint(w: ServicesWorld) -> None:
    define(w)
    task = request(w)
    assert w.hints.report_hint("ops", task, "done") == ""
    w.commands.retire_service("root", "ceo", "weekly-brief", "gone")
    assert w.hints.report_hint("ceo", task, "done") == ""


# ------------------------------------------------------------------------------ feedback_text


def note(body: str) -> Message:
    return Message(sender="root", to="ceo", type="note", body=body, feedback="reject")


def test_the_clients_words_are_what_follows_the_header(hints: ServiceHints) -> None:
    assert hints.feedback_text(note(FEEDBACK_HEADER + "\n\n  deliver as is  ")) == "deliver as is"


def test_a_bare_accept_has_no_words(hints: ServiceHints) -> None:
    assert hints.feedback_text(note(FEEDBACK_HEADER + "\n\naccepted")) == ""


def test_a_body_without_the_header_is_the_words_as_they_are(hints: ServiceHints) -> None:
    assert hints.feedback_text(note("  plain words ")) == "plain words"
    assert hints.feedback_text(note("")) == ""


def test_the_words_may_be_the_word_accepted_only_when_they_are_all_there_is(hints: ServiceHints) -> None:
    assert hints.feedback_text(note(FEEDBACK_HEADER + "\n\nnot accepted")) == "not accepted"
