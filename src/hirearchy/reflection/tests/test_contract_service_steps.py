"""Contract of ``ServiceSteps``: what root is told to do next after a rejection or an amendment is advice, never an error for a case it cannot place.

Every implementation is built over an organization with no service at all: both methods answer ``""`` for what they cannot place. The texts of
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


def test_a_service_without_a_contract_has_no_amendment_step(steps: ServiceSteps) -> None:
    assert steps.amendment_step("root", SERVICE) == ""
