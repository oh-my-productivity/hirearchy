"""``ParentSiblingRoutePolicy``: parent, direct reports, siblings, and whoever sent the message that is answered."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from hirearchy.dispatch._protocols import RoutePolicy
from hirearchy.dispatch._routes import ParentSiblingRoutePolicy
from hirearchy.dispatch.testing import DispatchWorld, fs_world, memory_world
from hirearchy.kernel import Message

from ._support import populated


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    make: Callable[[Path], DispatchWorld] = request.param
    return populated(make(tmp_path))


def policy(w: DispatchWorld) -> RoutePolicy:
    return ParentSiblingRoutePolicy(w.mail)


@pytest.mark.parametrize("sender", ["root", "runtime"])
def test_the_human_and_the_runtime_may_message_anyone(w: DispatchWorld, sender: str) -> None:
    assert all(policy(w).can_message(sender, to) for to in ("ceo", "ceo/ops/dev", "root", "nobody"))


@pytest.mark.parametrize(
    ("sender", "to", "allowed"),
    [
        ("ceo", "root", True),  # the parent (the human)
        ("ceo/eng", "ceo", True),  # the parent
        ("ceo", "ceo/eng", True),  # a direct report
        ("ceo/eng", "ceo/qa", True),  # a sibling
        ("ceo", "ceo/ops/dev", False),  # a grandchild
        ("ceo/ops/dev", "ceo", False),  # a grandparent
        ("ceo/eng", "ceo/ops/dev", False),  # a cousin
        ("ceo", "ceo", False),  # itself
        ("root", "root", True),
        ("ceo/eng", "root", False),  # the human is not eng's parent
    ],
)
def test_the_tree_decides(w: DispatchWorld, sender: str, to: str, allowed: bool) -> None:
    assert policy(w).can_message(sender, to) is allowed


def test_nobody_but_the_human_and_the_runtime_may_message_itself(w: DispatchWorld) -> None:
    assert not any(policy(w).can_message(a, a) for a in ("ceo", "ceo/eng"))


def test_whoever_sent_a_message_can_be_answered(w: DispatchWorld) -> None:
    ask = w.post(Message(sender="ceo/ops/dev", to="ceo", type="note", body="question?"))
    assert policy(w).can_message("ceo", "ceo/ops/dev", ask.id) is True


def test_only_the_sender_of_that_message_can_be_answered(w: DispatchWorld) -> None:
    ask = w.post(Message(sender="ceo/ops/dev", to="ceo", type="note", body="question?"))
    assert policy(w).can_message("ceo", "ceo/ops", ask.id) is True  # its parent is reachable anyway
    assert policy(w).can_message("ceo/qa", "ceo/ops/dev", ask.id) is False  # eng did not receive it


def test_an_unknown_reply_to_opens_nothing(w: DispatchWorld) -> None:
    assert policy(w).can_message("ceo", "ceo/ops/dev", "20260101T000000000001-ceo-aaaa") is False


def test_a_message_that_is_replied_to_is_one_the_sender_received_not_one_it_sent(w: DispatchWorld) -> None:
    mine = w.post(Message(sender="ceo", to="ceo/ops/dev", type="note", body="hello"))
    assert policy(w).can_message("ceo", "ceo/ops/dev", mine.id) is False
