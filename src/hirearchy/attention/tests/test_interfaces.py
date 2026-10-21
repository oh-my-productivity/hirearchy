"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6), and the data is plain data."""

from __future__ import annotations

import dataclasses

import pytest

from hirearchy.attention import HumanQueue, OpenWork, Waiting, WaitingOnUser
from hirearchy.attention._queue import InboxHumanQueue
from hirearchy.attention._waiting import RootTaskWaitingOnUser
from hirearchy.attention._work import RunnableOpenWork


def test_each_class_subclasses_the_port_it_implements() -> None:
    assert WaitingOnUser in RootTaskWaitingOnUser.__mro__
    assert HumanQueue in InboxHumanQueue.__mro__
    assert OpenWork in RunnableOpenWork.__mro__


def test_waiting_is_settled_unless_it_is_said_otherwise() -> None:
    assert Waiting("t", "o").settled is True


def test_waiting_is_a_frozen_value() -> None:
    value = Waiting("t", "o", False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.text = "other"  # type: ignore[misc]
    assert value == Waiting("t", "o", False) and hash(value) == hash(Waiting("t", "o", False))
