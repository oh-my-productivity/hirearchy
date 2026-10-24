"""Contract of ``ServiceSteps``: what root is told to do next after a rejection, an amendment or a rework is advice, never an error for a case it cannot place.

Every implementation is built over an organization with no service at all: each method answers ``""`` for what they cannot place. The texts of
a populated world are ``test_steps.py``'s."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection import ServiceSteps
from hirearchy.reflection.testing import IMPLEMENTATIONS

from ._support import SERVICE, implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceSteps]))
def steps(request: pytest.FixtureRequest, tmp_path: Path) -> ServiceSteps:
    made = request.param(tmp_path)
    assert isinstance(made, ServiceSteps)
    return made


def test_a_note_it_cannot_place_has_no_feedback_step(steps: ServiceSteps) -> None:
    lost = Message(sender="root", to="ceo", type="note", body="x", feedback="reject", source="human", reply_to="20260101T000000000000-root-0001")
    assert steps.feedback_step(lost) == ""


def test_service_steps_offer_the_feedback_and_rework_steps_only(steps: ServiceSteps) -> None:
    """An amendment can no longer precede the user's yes (the gate refuses it), so no step follows one."""
    assert sorted(name for name in dir(ServiceSteps) if not name.startswith("_")) == ["feedback_step", "rework_step"]
    assert not hasattr(steps, "amendment_step")


def test_an_accept_has_no_feedback_step(steps: ServiceSteps) -> None:
    accept = Message(sender="root", to="ceo", type="note", body="x", feedback="accept", source="human", reply_to="20260101T000000000000-root-0001")
    assert steps.feedback_step(accept) == ""


def test_a_rework_the_user_asked_for_that_it_cannot_place_has_no_rework_step(steps: ServiceSteps) -> None:
    """The top-up step of a rework the user asked for (0a.3) needs the case and the contract; without them it is advice about nothing."""
    human = Message(sender="root", to="ceo", type="task", body="x", service=SERVICE, revises="20260101T000000000000-root-0001", source="human", budget=1)
    assert steps.rework_step(human) == ""
    assert steps.rework_step(Message(sender="root", to="ceo", type="task", body="x", revises="20260101T000000000000-root-0001", source="human")) == ""


def test_a_rework_it_cannot_place_has_no_rework_step(steps: ServiceSteps) -> None:
    lost = Message(sender="root", to="ceo", type="task", body="x", service=SERVICE, revises="20260101T000000000000-root-0001", source="relayed")
    assert steps.rework_step(lost) == ""
    assert steps.rework_step(Message(sender="root", to="ceo", type="task", body="x", service=SERVICE, source="relayed")) == ""
