"""Contract of ``MessageSender``: the sender that checks the protocol (over the mailboxes on disk, in memory and over numbers for budgets) and the
recording fake deliver alike.

What the callers rely on: ``send`` returns the message it delivered, completed; the addresses are normalized, the body and the title are stripped; every
field it is given is on the delivered message; the human's messages start a chain (0 hops); a message the route check is skipped for still arrives.
(The refusals are the rules of the checking sender: ``test_rule_message_sender``.)"""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dispatch import MessageSender
from orgmcp.dispatch.testing import IMPLEMENTATIONS, DispatchWorld

from ._support import implementations, make


@pytest.fixture(params=implementations(IMPLEMENTATIONS[MessageSender]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    made = make(request, tmp_path)
    assert isinstance(made.sender, MessageSender)
    return made


def test_it_returns_the_message_it_delivered_completed(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "hello", title="Hi")
    assert msg.id and msg.created
    assert (msg.sender, msg.to, msg.type, msg.body, msg.title) == ("root", "ceo", "note", "hello", "Hi")


def test_the_message_arrives_in_the_inbox_of_the_recipient(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "hello")
    assert [m.id for m in w.inbox("ceo")] == [msg.id]


def test_the_body_and_the_title_are_stripped(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "  \n hello there \n\n", title="  A title \n")
    assert (msg.body, msg.title) == ("hello there", "A title")


def test_the_addresses_are_normalized(w: DispatchWorld) -> None:
    msg = w.sender.send(" /root/ ", " /ceo/ ", "hello")
    assert (msg.sender, msg.to) == ("root", "ceo")


def test_what_is_not_given_is_left_out(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "hello")
    assert (msg.reply_to, msg.status, msg.budget, msg.revises, msg.supersedes) == (None, None, 0, None, None)
    assert (msg.service, msg.contract, msg.playbook, msg.feedback, msg.wake) == (None, None, None, None, True)


def test_every_field_that_is_given_is_on_the_delivered_message(w: DispatchWorld) -> None:
    msg = w.sender.send(
        "root", "ceo", "all of it", type="task", title="Work", reply_to="20260101T000000000001-ceo-aaaa", status="done", budget=3,
        revises="20260101T000000000002-root-bbbb", supersedes="20260101T000000000003-ceo-cccc", service="weekly-brief", contract=2,
        playbook=1, feedback="accept", wake=False,
    )
    assert (msg.type, msg.reply_to, msg.status, msg.budget) == ("task", "20260101T000000000001-ceo-aaaa", "done", 3)
    assert (msg.revises, msg.supersedes) == ("20260101T000000000002-root-bbbb", "20260101T000000000003-ceo-cccc")
    assert (msg.service, msg.contract, msg.playbook, msg.feedback, msg.wake) == ("weekly-brief", 2, 1, "accept", False)


def test_a_zero_contract_and_playbook_are_kept(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "x", type="task", service="s", contract=0, playbook=0)
    assert (msg.contract, msg.playbook) == (0, 0)


def test_a_message_of_the_human_starts_a_chain(w: DispatchWorld) -> None:
    assert w.sender.send("root", "ceo", "hello").hops == 0


def test_a_message_the_route_check_is_skipped_for_is_delivered(w: DispatchWorld) -> None:
    msg = w.sender.send("ceo/eng", "ceo/ops/dev", "not my cousin", type="result", skip_route_check=True)
    assert [m.id for m in w.inbox("ceo/ops/dev")] == [msg.id]
