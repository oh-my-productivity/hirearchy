"""``RuleMessageSender``: the checks every message passes before it is delivered, in their order, with the texts agents are shown.

Run over the three worlds that check (disk, memory, numbers for budgets); the recording fake checks nothing."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.delivery.testing import RecordingDelivery
from orgmcp.dispatch import MessageSender
from orgmcp.dispatch._protocols import RoutePolicy
from orgmcp.dispatch._sender import RuleMessageSender
from orgmcp.dispatch.testing import IMPLEMENTATIONS, DispatchWorld, FixedReworkContext
from orgmcp.kernel import Message, OrgError
from orgmcp.kernel.testing import SequenceIdGenerator

from ._support import grant, implementations, make


@pytest.fixture(params=[p for p in implementations(IMPLEMENTATIONS[MessageSender]) if p.id != "recording_world"])
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    return make(request, tmp_path)


def refused(w: DispatchWorld, *args: str, **kw: object) -> str:
    with pytest.raises(OrgError) as e:
        w.sender.send(*args, **kw)  # type: ignore[arg-type]
    return str(e.value)


# ------------------------------------------------------------------------------ the size of the body


CAP = (
    "message is {n} characters; the limit is {cap} (max_message_chars). Messages are read in full by the recipient's next run, so keep them "
    "short: write the detail to a file inside your own directory and send a short message that gives its path."
)


def test_a_body_over_the_limit_is_refused_with_the_way_out(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_message_chars: 50\n---\nrules\n")
    assert refused(w, "ceo", "ceo/eng", "x" * 51) == CAP.format(n=51, cap=50)
    assert w.sender.send("ceo", "ceo/eng", "x" * 50).body == "x" * 50


def test_the_size_is_that_of_the_stripped_body(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_message_chars: 50\n---\nrules\n")
    assert w.sender.send("ceo", "ceo/eng", "  " + "x" * 50 + " \n\n").body == "x" * 50


def test_the_human_may_paste(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_message_chars: 50\n---\nrules\n")
    assert len(w.sender.send("root", "ceo", "x" * 500).body) == 500
    assert len(w.sender.send(" /root/ ", "ceo", "x" * 500).body) == 500


def test_the_limit_is_checked_before_anything_else(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_message_chars: 50\n---\nrules\n")
    assert refused(w, "ghost", "nobody", "x" * 51, type="bogus") == CAP.format(n=51, cap=50)


def test_a_malformed_limit_means_the_default(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_message_chars: lots\n---\nrules\n")
    assert refused(w, "ceo", "ceo/eng", "x" * 20001) == CAP.format(n=20001, cap=20000)


# ------------------------------------------------------------------------------ who, what, and whether there is anything to say


def test_both_addresses_must_exist(w: DispatchWorld) -> None:
    assert refused(w, "ghost", "ceo", "hi") == "no such agent: ghost"
    assert refused(w, "ceo", "ghost", "hi") == "no such agent: ghost"


def test_the_type_is_task_result_or_note(w: DispatchWorld) -> None:
    assert refused(w, "ceo", "ceo/eng", "hi", type="memo") == "type must be one of ('task', 'result', 'note')"


@pytest.mark.parametrize("body", ["", "   ", "\n\t\n"])
def test_a_body_of_blanks_is_no_message(w: DispatchWorld, body: str) -> None:
    assert refused(w, "ceo", "ceo/eng", body) == "message body is empty"


def test_the_type_is_checked_before_the_body_and_the_body_before_the_route(w: DispatchWorld) -> None:
    assert refused(w, "ceo", "ceo/ops/dev", "", type="memo") == "type must be one of ('task', 'result', 'note')"
    assert refused(w, "ceo", "ceo/ops/dev", " ") == "message body is empty"


# ------------------------------------------------------------------------------ the route


def route_text(sender: str, to: str) -> str:
    return (
        f"{sender} cannot message {to}: you may message your parent, your direct reports, "
        "your siblings, or whoever sent you the message you are replying to (reply_to)."
    )


@pytest.mark.parametrize(("sender", "to"), [("ceo", "ceo/ops/dev"), ("ceo/ops/dev", "ceo"), ("ceo/eng", "ceo/ops/dev"), ("ceo", "ceo")])
def test_a_message_off_the_tree_is_refused(w: DispatchWorld, sender: str, to: str) -> None:
    assert refused(w, sender, to, "hi") == route_text(sender, to)


@pytest.mark.parametrize(("sender", "to"), [("ceo", "root"), ("ceo", "ceo/eng"), ("ceo/eng", "ceo/qa"), ("ceo/eng", "ceo"), ("root", "ceo/ops/dev")])
def test_the_parent_the_reports_the_siblings_and_the_human_are_reachable(w: DispatchWorld, sender: str, to: str) -> None:
    assert w.sender.send(sender, to, "hi").to == to


def test_whoever_sent_a_message_can_be_answered_with_reply_to(w: DispatchWorld) -> None:
    ask = w.post(Message(sender="ceo/ops/dev", to="ceo", type="note", body="question?"))
    w.begin_run("ceo")
    assert refused(w, "ceo", "ceo/ops/dev", "answer") == route_text("ceo", "ceo/ops/dev")
    assert w.sender.send("ceo", "ceo/ops/dev", "answer", reply_to=ask.id).reply_to == ask.id


def test_the_route_check_can_be_skipped(w: DispatchWorld) -> None:
    assert w.sender.send("ceo", "ceo/ops/dev", "hi", type="result", skip_route_check=True).to == "ceo/ops/dev"


def test_a_message_that_is_refused_is_not_delivered(w: DispatchWorld) -> None:
    refused(w, "ceo", "ceo/ops/dev", "hi")
    assert w.inbox("ceo/ops/dev") == [] and w.sent("ceo") == []


# ------------------------------------------------------------------------------ the budget


def test_a_budget_cannot_be_negative(w: DispatchWorld) -> None:
    assert refused(w, "ceo", "ceo/eng", "hi", budget=-1) == "budget cannot be negative"


def test_the_route_is_checked_before_the_budget(w: DispatchWorld) -> None:
    assert refused(w, "ceo", "ceo/ops/dev", "hi", budget=-1) == route_text("ceo", "ceo/ops/dev")


NOT_THERE = "budget can only be handed to your direct reports, or returned to your parent"


def test_a_budget_goes_to_a_direct_report_or_back_to_the_parent_only(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 10)
    grant(w, "root", "ceo/eng", 4)
    assert refused(w, "ceo/eng", "ceo/qa", "runs for you", budget=1) == NOT_THERE  # a sibling
    assert w.sender.send("ceo", "ceo/eng", "runs", budget=2).budget == 2  # a direct report
    assert w.sender.send("ceo/eng", "ceo", "runs back", budget=1).budget == 1  # the parent


def test_the_human_may_hand_runs_to_anyone(w: DispatchWorld) -> None:
    assert w.sender.send("root", "ceo/ops/dev", "runs", budget=3).budget == 3
    assert w.query.budget("ceo/ops/dev") == 3


def test_the_runs_move_with_the_message(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 10)
    w.sender.send("ceo", "ceo/eng", "runs", budget=4)
    assert (w.query.budget("ceo"), w.query.budget("ceo/eng")) == (6, 4)


def test_an_agent_cannot_hand_down_runs_it_does_not_have(w: DispatchWorld) -> None:
    assert refused(w, "ceo", "ceo/eng", "runs", budget=1) == (
        "not enough budget: you have 0 run(s) and must keep 0 in reserve (one per outstanding delegation, to process its result), "
        "so you can hand down at most 0. Ask your parent for more budget or do less."
    )


def test_a_task_keeps_one_run_in_reserve_for_its_result_and_a_note_does_not(w: DispatchWorld) -> None:
    grant(w, "root", "ceo", 5)
    assert "must keep 1 in reserve" in refused(w, "ceo", "ceo/eng", "work", type="task", budget=5)
    assert w.sender.send("ceo", "ceo/eng", "runs", budget=5).budget == 5


def test_a_message_without_a_budget_is_never_held_to_the_reserve(w: DispatchWorld) -> None:
    assert w.sender.send("ceo", "ceo/eng", "hi", type="task", budget=0).budget == 0


# ------------------------------------------------------------------------------ the hops


HOPS = (
    "message chain is {hops} hops long (limit {limit}); this looks like a loop. Report blocked to whoever assigned your task instead."
)


def chain(w: DispatchWorld, hops: int) -> None:
    """``ceo`` is working on a batch whose longest chain is ``hops`` messages long."""
    w.post(Message(sender="root", to="ceo", type="task", body="b", title="t", hops=hops))
    w.begin_run("ceo")


def test_a_message_starts_one_hop_after_the_longest_chain_of_the_batch(w: DispatchWorld) -> None:
    chain(w, 5)
    assert w.sender.send("ceo", "ceo/eng", "hi").hops == 6


def test_a_message_of_an_agent_without_a_batch_has_one_hop(w: DispatchWorld) -> None:
    assert w.sender.send("ceo", "ceo/eng", "hi").hops == 1


def test_a_chain_longer_than_the_limit_is_refused_as_a_loop(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_hops: 3\n---\nrules\n")
    chain(w, 3)
    assert refused(w, "ceo", "ceo/eng", "hi") == HOPS.format(hops=4, limit=3)
    assert w.inbox("ceo/eng") == []


def test_a_chain_as_long_as_the_limit_is_allowed(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_hops: 3\n---\nrules\n")
    chain(w, 2)
    assert w.sender.send("ceo", "ceo/eng", "hi").hops == 3


def test_a_result_always_gets_through(w: DispatchWorld) -> None:
    w.configure("---\nmission: test\nmax_hops: 3\n---\nrules\n")
    chain(w, 30)
    assert w.sender.send("ceo", "root", "done", type="result").hops == 31


def test_the_human_and_the_runtime_start_chains(w: DispatchWorld) -> None:
    chain(w, 30)
    assert w.sender.send("root", "ceo", "hi").hops == 0


# ------------------------------------------------------------------------------ the collaborators


class Routes(RoutePolicy):
    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str, str | None]] = []

    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        self.asked.append((sender, to, reply_to))
        return self.answer


def over(w: DispatchWorld, routes: RoutePolicy) -> tuple[RuleMessageSender, RecordingDelivery]:
    delivery = RecordingDelivery(w.clock, SequenceIdGenerator(w.clock))
    return RuleMessageSender(w.agents, w.settings, routes, w.policy, w.hops, delivery), delivery


def test_the_route_is_asked_with_the_normalized_addresses_and_the_reply_to(w: DispatchWorld) -> None:
    routes = Routes(True)
    sender, _ = over(w, routes)
    sender.send(" /ceo/ ", " ceo/eng ", "hi", reply_to="some-id")
    assert routes.asked == [("ceo", "ceo/eng", "some-id")]


def test_the_route_is_not_asked_when_it_is_skipped(w: DispatchWorld) -> None:
    routes = Routes(False)
    sender, delivery = over(w, routes)
    sender.send("ceo", "ceo/eng", "hi", skip_route_check=True)
    assert routes.asked == [] and len(delivery.messages) == 1


def test_a_refusing_route_stops_the_message_before_the_delivery(w: DispatchWorld) -> None:
    sender, delivery = over(w, Routes(False))
    with pytest.raises(OrgError, match="ceo cannot message ceo/eng"):
        sender.send("ceo", "ceo/eng", "hi")
    assert delivery.messages == []


def test_the_delivered_message_is_the_one_that_is_returned(w: DispatchWorld) -> None:
    sender, delivery = over(w, Routes(True))
    msg = sender.send("ceo", "ceo/eng", "hi", wake=False)
    assert delivery.messages == [msg] and msg.wake is False and msg.hops == 1
