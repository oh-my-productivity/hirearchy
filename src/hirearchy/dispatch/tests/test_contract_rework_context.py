"""Contract of ``ReworkContext``: every source of the service fields of a rework answers alike.

What the callers rely on: the answer is a mapping that holds at most ``service``, ``contract`` and ``playbook`` (a rework of a service request keeps its
case) and, for an agent, ``source`` (the tier of the work it does in that case: ``human`` or ``relayed``, never for root); it is empty for a task that is
not one of the actor's. (What the tier is made of: ``services/tests/test_service_rework_context``.)"""

from __future__ import annotations

from pathlib import Path
import pytest

from hirearchy.dispatch import ReworkContext
from hirearchy.dispatch.testing import IMPLEMENTATIONS, FixedReworkContext

from ._support import implementations

KNOWN = "20260101T000000000001-ceo-aaaa"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ReworkContext]))
def context(request: pytest.FixtureRequest, tmp_path: Path) -> ReworkContext:
    made = request.param(tmp_path)
    assert isinstance(made, ReworkContext)
    return made


def test_an_ordinary_task_inherits_nothing(context: ReworkContext) -> None:
    assert dict(context.fields_for("ceo", "20260101T000000000009-ceo-zzzz")) == {}


def test_the_answer_holds_only_the_service_fields_and_the_tier(context: ReworkContext) -> None:
    assert set(context.fields_for("ceo", KNOWN)) <= {"service", "contract", "playbook", "source"}


def test_root_never_gets_a_tier(context: ReworkContext) -> None:
    assert "source" not in context.fields_for("root", KNOWN)
    assert "source" not in context.fields_for("root", "20260101T000000000009-root-zzzz")


def test_a_tier_is_human_or_relayed(context: ReworkContext) -> None:
    assert context.fields_for("ceo", KNOWN).get("source") in (None, "human", "relayed")


def test_the_answer_for_a_task_is_the_same_every_time(context: ReworkContext) -> None:
    assert dict(context.fields_for("ceo", KNOWN)) == dict(context.fields_for("ceo", KNOWN))


def test_what_the_caller_does_with_the_answer_does_not_change_the_next_one(context: ReworkContext) -> None:
    answer = context.fields_for("ceo", KNOWN)
    if isinstance(answer, dict):
        answer["service"] = "changed"
    assert context.fields_for("ceo", KNOWN).get("service") != "changed"


def test_a_fixed_context_answers_with_what_it_was_given() -> None:
    fixed = FixedReworkContext({KNOWN: {"service": "weekly-brief", "contract": 3, "playbook": 2}})
    assert dict(fixed.fields_for("ceo", KNOWN)) == {"service": "weekly-brief", "contract": 3, "playbook": 2}
