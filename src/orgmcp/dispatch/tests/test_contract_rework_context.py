"""Contract of ``ReworkContext``: every source of the service fields of a rework answers alike.

What the callers rely on: the answer is a mapping that holds at most ``service``, ``contract`` and ``playbook``, and it is empty for a task that is not
a request for a service (or not known)."""

from __future__ import annotations

from pathlib import Path
import pytest

from orgmcp.dispatch import ReworkContext
from orgmcp.dispatch.testing import IMPLEMENTATIONS, FixedReworkContext

from ._support import implementations

KNOWN = "20260101T000000000001-ceo-aaaa"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ReworkContext]))
def context(request: pytest.FixtureRequest, tmp_path: Path) -> ReworkContext:
    made = request.param(tmp_path)
    assert isinstance(made, ReworkContext)
    return made


def test_an_ordinary_task_inherits_nothing(context: ReworkContext) -> None:
    assert dict(context.fields_for("ceo", "20260101T000000000009-ceo-zzzz")) == {}


def test_the_answer_holds_only_the_service_fields(context: ReworkContext) -> None:
    assert set(context.fields_for("ceo", KNOWN)) <= {"service", "contract", "playbook"}


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
