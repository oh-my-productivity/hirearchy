"""Contract of ``ServiceQuery``: the services of the organization and the record of each. Over the strict ports and over the dashboard's."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import ServiceQuery, doc_text
from orgmcp.dashdata.testing import IMPLEMENTATIONS, DashWorld
from orgmcp.kernel import Message
from orgmcp.reflection import Case, Verdict
from orgmcp.services import Playbook

from ._support import make_world, stamp, team


@pytest.fixture(params=IMPLEMENTATIONS[ServiceQuery], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.services, ServiceQuery)
    return made


def case(owner: str, service: str, n: int, state: str, runs: int, verdicts: tuple[str, ...] = (), used: int = 1) -> Case:
    task = Message(sender="root", to=owner, type="task", title=f"Brief {n}", body="goal", budget=6, id=f"2026101810000{n}-root-000{n}")
    marks = [Verdict(v, "", None, task.id, step, task) for step, v in enumerate(verdicts)]
    return Case(
        id=task.id, service=service, owner=owner, tasks=[task], result=None, state=state, playbook=1, used=used, reworks=max(0, len(verdicts) - 1), budget=6,
        runs=runs, lessons=[], verdicts=marks, started=stamp(n), finished=stamp(n + 5) if state in ("done", "failed") else None,
    )


def brief(w: DashWorld) -> None:
    team(w)
    w.catalog.define(
        "ceo", "brief", Playbook(version=2, by="ceo", reason="initial playbook", body="# Playbook\nStart from the sources.\n"),
        description="A one-page brief.", budget=6, version=3, defined_by="root", locked=True,
        inputs=[{"name": "topic", "required": True}, {"name": "week", "required": False}], acceptance=["At most 600 words"],
        deliverable={"format": "markdown", "max_words": 600},
    )


def test_an_organization_without_services_has_none(w: DashWorld) -> None:
    team(w)
    assert w.services.services() == []


def test_a_service_is_a_row_with_its_versions_and_its_record(w: DashWorld) -> None:
    brief(w)
    w.history.all += [case("ceo", "brief", 1, "done", 4, ("reject", "accept")), case("ceo", "brief", 2, "open", 1)]
    (row,) = w.services.services()
    assert (row.owner, row.name, row.contract_version, row.playbook_version, row.locked) == ("ceo", "brief", 3, 2, True)
    assert (row.playbook_reason, row.description) == ("initial playbook", "A one-page brief.")
    assert (row.stats.requests, row.stats.done, row.stats.open, row.stats.accept_after_reject) == (2, 1, 1, 1)


def test_a_service_that_cannot_be_read_is_a_row_that_says_so(w: DashWorld) -> None:
    brief(w)
    w.catalog.unreadable.add(("ceo", "brief"))
    (row,) = w.services.services()
    assert (row.contract_version, row.playbook_version, row.playbook_reason) == (0, 0, "unreadable: OrgError") and row.stats.requests == 0


def test_the_services_are_kept_while_nothing_changes_and_listed_again_after_a_while(w: DashWorld) -> None:
    brief(w)
    snap = w.snapshots.snapshot()
    first = w.services.services(snap)
    w.catalog.define("ceo", "extra", Playbook(), description="x")
    assert w.services.services(snap) is first
    w.clock.advance(5.5)
    assert [r.name for r in w.services.services(snap)] == ["brief", "extra"]


def test_a_service_in_detail_has_its_contract_its_playbook_and_its_cases(w: DashWorld) -> None:
    brief(w)
    w.history.all += [case("ceo", "brief", 1, "done", 4, ("reject", "accept")), case("ceo", "brief", 2, "open", 1, used=2)]
    text = doc_text(w.services.service_detail("ceo", "brief"))
    assert text.startswith("## brief (owner ceo)\nA one-page brief.\ncontract v3 (locked), budget 6 per request, defined by root\nplaybook v2 revised by ceo: initial playbook\n")
    assert "## Record\n2 request(s): 1 done, 0 failed, 1 open; 1 reworked; avg 4 runs; feedback 1 accept (1 after a reject), 0 reject\n" in text
    assert "## By playbook version\nv1: 1 request(s)" in text and "\nv2: 1 request(s)" in text
    assert '## Cases (2)\n' in text and 'Brief 2"  open, playbook v2, 1 of 6 runs' in text
    assert "Brief 1\"  done, playbook v1, 4 of 6 runs, 1 rework(s), feedback: reject -> accept" in text
    assert "## Contract\ninputs: topic*, week\n  accept: At most 600 words\ndeliverable: format=markdown, max_words=600\n" in text
    assert "## Playbook v2\n# Playbook\nStart from the sources." in text


def test_a_service_that_is_not_there_is_told(w: DashWorld) -> None:
    team(w)
    assert doc_text(w.services.service_detail("ceo", "ghost")) == "ceo/ghost: no such service (retired?)\n"


def test_a_service_that_cannot_be_read_is_told_in_detail(w: DashWorld) -> None:
    brief(w)
    w.catalog.unreadable.add(("ceo", "brief"))
    assert doc_text(w.services.service_detail("ceo", "brief")).startswith("cannot read the service: OrgError: ceo/brief: SERVICE.md cannot be read")


def test_a_service_without_a_playbook_or_cases_says_so(w: DashWorld) -> None:
    team(w)
    w.catalog.define("ops", "audit", description="")
    text = doc_text(w.services.service_detail("ops", "audit"))
    assert "(no description)" in text and "playbook v0 (none yet)" in text and "## Cases (0)\nnone yet" in text and "## Playbook\n(none)" in text
