"""Contract of ``MessageSender``: the sender that checks the protocol (over the mailboxes on disk, in memory and over numbers for budgets) and the
recording fake deliver alike.

What the callers rely on: ``send`` returns the message it delivered, completed; the addresses are normalized, the body and the title are stripped; every
field it is given is on the delivered message; the human's messages start a chain (0 hops); a message the route check is skipped for still arrives;
only root records where a rework, a verdict or a link comes from (``source``) and what a verdict is about (``criterion``, only on a verdict note or a
link note); a rework, a verdict note and a link note from root without a ``source`` are stamped ``relayed``.
(The other refusals are the rules of the checking sender: ``test_rule_message_sender``.)"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.dispatch import MessageSender
from hirearchy.dispatch.testing import IMPLEMENTATIONS, DispatchWorld
from hirearchy.kernel import OrgError

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


# ------------------------------------------------------------------------------ provenance: where a rework comes from

S1 = ("only root (the human's seat) records where a verdict, a link or a rework comes from (`source`, `criterion`); "
      "agents' messages carry neither")
S2 = 'source must be "human" (the user\'s own judgement, in their own words) or "relayed" (anything you concluded yourself)'
EARLIER = "20260101T000000000002-root-bbbb"


def test_an_agent_cannot_set_source(w: DispatchWorld) -> None:
    for source in ("human", "relayed", "garbage"):
        with pytest.raises(OrgError) as e:
            w.sender.send("ceo", "root", "hello", source=source)
        assert str(e.value) == S1


def test_source_must_be_human_or_relayed(w: DispatchWorld) -> None:
    for source in ("", "HUMAN", "assistant", "agent"):
        with pytest.raises(OrgError) as e:
            w.sender.send("root", "ceo", "hello", type="task", revises=EARLIER, source=source)
        assert str(e.value) == S2
    assert w.inbox("ceo") == []


def test_a_root_rework_without_source_is_stamped_relayed(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "again, please", type="task", revises=EARLIER)
    assert msg.source == "relayed"
    assert [m.source for m in w.inbox("ceo")] == ["relayed"]


def test_a_root_rework_keeps_source_human(w: DispatchWorld) -> None:
    msg = w.sender.send("root", "ceo", "again, please", type="task", revises=EARLIER, source="human")
    assert msg.source == "human" and [m.source for m in w.inbox("ceo")] == ["human"]
    assert w.sender.send("root", "ceo", "again", type="task", revises=EARLIER, source="relayed").source == "relayed"


def test_a_fresh_root_task_is_not_stamped(w: DispatchWorld) -> None:
    assert w.sender.send("root", "ceo", "new work", type="task").source is None
    assert w.sender.send("root", "ceo", "just a note").source is None
    assert w.sender.send("root", "ceo", "new work", type="task", source="human").source == "human"  # stamped only when the caller says


def test_an_agent_rework_is_never_stamped(w: DispatchWorld) -> None:
    msg = w.sender.send("ceo", "ceo/eng", "again, please", type="task", revises=EARLIER)
    assert msg.source is None


def test_send_accepts_inherited(w: DispatchWorld) -> None:
    msg = w.sender.send("ceo", "ceo/eng", "again, please", type="task", revises=EARLIER, inherited="relayed")
    assert msg.source == "relayed"


# ------------------------------------------------------------------------------ provenance: what a verdict is about

S3 = ("criterion goes only on a verdict (a note with `feedback`) or on a link note that replies to one: use `feedback(..., criterion=...)`.")


def test_an_agent_cannot_set_criterion(w: DispatchWorld) -> None:
    given: list[dict[str, Any]] = [
        {"criterion": "C1"}, {"criterion": "C1", "feedback": "reject", "reply_to": EARLIER}, {"criterion": "none", "reply_to": EARLIER},
    ]
    for kw in given:
        with pytest.raises(OrgError) as e:
            w.sender.send("ceo", "root", "hello", **kw)
        assert str(e.value) == S1
    assert w.inbox("root") == []


def test_criterion_on_a_task_or_a_plain_note_is_s3(w: DispatchWorld) -> None:
    plain: list[dict[str, Any]] = [
        {"type": "task"}, {"type": "task", "revises": EARLIER}, {"type": "note"}, {"type": "note", "reply_to": None},
        {"type": "result", "reply_to": EARLIER}, {"type": "note", "status": "done"},
    ]
    for kw in plain:
        with pytest.raises(OrgError) as e:
            w.sender.send("root", "ceo", "hello", criterion="C1", skip_route_check=True, **kw)
        assert str(e.value) == S3
    assert w.inbox("ceo") == []


def test_a_root_verdict_note_without_source_is_relayed(w: DispatchWorld) -> None:
    reject = w.sender.send("root", "ceo", "too long", feedback="reject", reply_to=EARLIER)
    accept = w.sender.send("root", "ceo", "fine", feedback="accept", reply_to=EARLIER)
    assert (reject.source, accept.source) == ("relayed", "relayed")
    assert [m.source for m in w.inbox("ceo")] == ["relayed", "relayed"]


def test_a_root_link_note_without_source_is_relayed(w: DispatchWorld) -> None:
    link = w.sender.send("root", "ceo", "yes, lasting", reply_to=EARLIER, criterion="C2")
    assert (link.source, link.criterion, link.feedback) == ("relayed", "C2", None)
    assert [(m.source, m.criterion) for m in w.inbox("ceo")] == [("relayed", "C2")]


def test_an_explicit_human_verdict_is_kept(w: DispatchWorld) -> None:
    verdict = w.sender.send("root", "ceo", "too long", feedback="reject", reply_to=EARLIER, source="human", criterion="C1, R2")
    link = w.sender.send("root", "ceo", "yes", reply_to=EARLIER, source="human", criterion="none")
    assert (verdict.source, verdict.criterion, link.source, link.criterion) == ("human", "C1, R2", "human", "none")
    assert [(m.source, m.criterion) for m in w.inbox("ceo")] == [("human", "C1, R2"), ("human", "none")]


def test_a_verdict_without_criterion_carries_none_and_a_plain_note_stays_unstamped(w: DispatchWorld) -> None:
    verdict = w.sender.send("root", "ceo", "fine", feedback="accept", reply_to=EARLIER, source="relayed")
    assert (verdict.source, verdict.criterion) == ("relayed", None)
    note = w.sender.send("root", "ceo", "just a note", reply_to=EARLIER)  # no feedback, no criterion: not a link
    assert (note.source, note.criterion) == (None, None)


# ------------------------------------------------------------------------------ the acknowledgement of a playbook change (design 9.2)

PLAIN_NOTE = "acknowledges goes only on a plain note"
ACKNOWLEDGES = "weekly-brief edit P3 0123456789ab"


def test_acknowledges_goes_only_on_a_plain_note(w: DispatchWorld) -> None:
    refused: list[tuple[str, dict[str, Any]]] = [
        ("root", {"type": "task"}),
        ("root", {"type": "note", "feedback": "accept", "reply_to": EARLIER}),
        ("root", {"type": "note", "criterion": "C1", "reply_to": EARLIER}),
        ("root", {"type": "note", "feedback": "reject", "criterion": "C1", "reply_to": EARLIER, "source": "human"}),
        ("ceo", {"type": "result", "reply_to": EARLIER, "skip_route_check": True}),
    ]
    for actor, kw in refused:
        with pytest.raises(OrgError) as e:
            w.sender.send(actor, "ceo" if actor == "root" else "root", "words", acknowledges=ACKNOWLEDGES, **kw)
        assert str(e.value) == PLAIN_NOTE
    assert w.inbox("ceo") == [] and w.inbox("root") == []


def test_a_plain_note_keeps_its_acknowledges(w: DispatchWorld) -> None:
    from_root = w.sender.send("root", "ceo", "yes, retire it", title="playbook acknowledgement: edit P3 of weekly-brief", acknowledges=ACKNOWLEDGES,
                              source="human", wake=False)
    from_manager = w.sender.send("ceo", "ceo/eng", "Acknowledged.", acknowledges="weekly-brief retire P3")
    assert (from_root.acknowledges, from_manager.acknowledges) == (ACKNOWLEDGES, "weekly-brief retire P3")
    assert [(m.acknowledges, m.source) for m in w.inbox("ceo")] == [(ACKNOWLEDGES, "human")]
    assert [m.acknowledges for m in w.inbox("ceo/eng")] == ["weekly-brief retire P3"]
    assert w.sender.send("root", "ceo", "just a note").acknowledges is None
