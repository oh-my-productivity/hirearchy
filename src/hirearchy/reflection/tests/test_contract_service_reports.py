"""Contract of ``ServiceReports``: the ``services`` listing and the totals of a case, text for text as ``services.py`` printed them."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message, OrgError
from hirearchy.reflection import ServiceReports
from hirearchy.reflection.testing import IMPLEMENTATIONS, ReflectionWorld, fs_world, memory_world

from . import _stories
from ._golden import expected
from ._support import SERVICE, STEPS, ask, define, deliver, implementations, populated, revise

NO_SERVICES = (
    "No services yet. A parent defines a standing service for a direct report with define_service(owner, "
    "name, description, acceptance, deliverable, budget, inputs): the contract. Then request(service, inputs) "
    "asks for it, and feedback(task_id, verdict) tells the owner how it went."
)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceReports]))
def reports(request: pytest.FixtureRequest, tmp_path: Path) -> ServiceReports:
    made = request.param(tmp_path)
    assert isinstance(made, ServiceReports)
    return made


# ------------------------------------------------------------------------------ services_text


def test_without_services_the_text_says_how_to_define_one(w: ReflectionWorld) -> None:
    assert w.reports.services_text("root") == NO_SERVICES == w.reports.services_text("ceo")


def test_an_unknown_actor_is_refused(w: ReflectionWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.reports.services_text("ghost")


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_client_sees_the_services_of_its_reports(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert w.reports.services_text("root") == expected(f"services_root_{name}.txt", story)


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_owner_sees_the_services_it_offers(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert w.reports.services_text("ceo") == expected(f"services_ceo_{name}.txt", story)


def test_a_service_without_requests_says_so(w: ReflectionWorld) -> None:
    define(w, playbook=STEPS)
    text = w.reports.services_text("root")
    assert "  record: no requests yet" in text and '  playbook v1 (2026-10-18): "' in text


def test_a_locked_service_is_marked_to_its_owner_only(w: ReflectionWorld) -> None:
    define(w, locked=True)
    assert "- weekly-brief (contract v1, playbook v0, locked): " in w.reports.services_text("ceo")
    assert "locked" not in w.reports.services_text("root")


def test_each_owner_is_listed_with_its_own_services(w: ReflectionWorld) -> None:
    define(w)
    define(w, owner="ops", name="ops-brief")
    text = w.reports.services_text("root")
    assert "- weekly-brief (offered by ceo; " in text and "- ops-brief (offered by ops; " in text
    assert "ops-brief" not in w.reports.services_text("ceo")


# ------------------------------------------------------------------------------ case_total


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_total_of_every_request_of_a_story(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert "\n".join(f"ask{n}: {w.reports.case_total(a) or '<empty>'}" for n, a in enumerate(story.asks)) == expected(f"totals_{name}.txt", story)


def test_a_plain_task_has_no_total(w: ReflectionWorld) -> None:
    plain = w.s.d.post(Message(sender="root", to="ceo", type="task", body="b", title="plain", budget=2))
    assert w.reports.case_total(plain) == ""


def test_a_case_within_its_budget_does_not_ask_to_tell_the_user(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, runs=3)
    assert w.reports.case_total(task) == "case total: 3 runs used of 10 handed down (contract: 10 per request)"


def test_a_case_handed_down_more_than_the_contract_gives_says_so(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first)
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=5)
    assert w.reports.case_total(again) == (
        "case total: 1 runs used of 15 handed down (contract: 10 per request). "
        "This case now exceeds the per-request budget of 10: tell the user."
    )


def test_a_request_of_a_retired_service_has_no_total(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    assert w.reports.case_total(task) == ""


def test_the_implementations_agree_on_an_empty_organization(reports: ServiceReports) -> None:
    assert reports.services_text("root") == NO_SERVICES
