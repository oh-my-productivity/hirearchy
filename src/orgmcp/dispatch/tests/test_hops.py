"""``InflightHopCounter``: one more than the longest chain among the messages of the sender's current batch."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dispatch._hops import InflightHopCounter
from orgmcp.dispatch.testing import DispatchWorld, fs_world, memory_world
from orgmcp.kernel import Message

from ._support import RED, populated

pytestmark = RED


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    return populated(request.param(tmp_path))


@pytest.mark.parametrize("actor", ["root", "runtime"])
def test_the_human_and_the_runtime_start_a_chain(w: DispatchWorld, actor: str) -> None:
    assert InflightHopCounter(w.mail).next_hops(actor) == 0


def test_an_agent_without_a_batch_sends_the_first_hop(w: DispatchWorld) -> None:
    assert InflightHopCounter(w.mail).next_hops("ceo") == 1


def test_the_longest_chain_of_the_batch_counts(w: DispatchWorld) -> None:
    for hops in (2, 7, 4):
        w.post(Message(sender="root", to="ceo", type="note", body="b", hops=hops))
    w.begin_run("ceo")
    assert InflightHopCounter(w.mail).next_hops("ceo") == 8


def test_mail_that_waits_in_the_inbox_or_was_read_does_not_count(w: DispatchWorld) -> None:
    w.post(Message(sender="root", to="ceo", type="note", body="b", hops=9))
    assert InflightHopCounter(w.mail).next_hops("ceo") == 1  # still in the inbox
    w.begin_run("ceo")
    w.end_run("ceo")
    assert InflightHopCounter(w.mail).next_hops("ceo") == 1  # read
