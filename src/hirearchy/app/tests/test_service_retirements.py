"""``FsServiceRetirements``: the retired copies of services, read from ``<owner>/services/.retired/<name>-<stamp>/RETIRED.md`` of every agent (design 4.5, L22).

``retro`` names the port because no public port of ``services`` lists the copies; the composition root implements it over the layout and the agent directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hirearchy.app import Org
from hirearchy.app._service_retirements import FsServiceRetirements
from hirearchy.kernel import ROOT
from hirearchy.retro._ports import ServiceRetirements
from hirearchy.retro._views import ServiceRetired

BRIEF: dict[str, Any] = dict(
    description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}], acceptance=["Short"],
    deliverable={"description": "one file"}, budget=4,
)


def retirements(org: Org) -> FsServiceRetirements:
    return FsServiceRetirements(org.runtime.agents, org.runtime.paths)


def org_with_services(tmp_path: Path) -> Org:
    org = Org.init(tmp_path / "org", "mission")
    org.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build.")
    return org


def test_it_is_a_service_retirements(tmp_path: Path) -> None:
    assert isinstance(retirements(org_with_services(tmp_path)), ServiceRetirements)


def test_an_organization_without_retired_services_has_none(tmp_path: Path) -> None:
    org = org_with_services(tmp_path)
    org.define_service(ROOT, "ceo", "weekly-brief", **BRIEF)
    assert retirements(org).retired() == ()


def test_a_retired_service_is_read_with_its_owner_its_name_and_the_record(tmp_path: Path) -> None:
    org = org_with_services(tmp_path)
    org.define_service(ROOT, "ceo", "weekly-brief", **BRIEF)
    org.retire_service(ROOT, "ceo", "weekly-brief", "done with it")
    (found,) = retirements(org).retired()
    assert isinstance(found, ServiceRetired)
    assert (found.owner, found.name, found.by, found.reason, found.approved_in) == ("ceo", "weekly-brief", ROOT, "done with it", "")
    assert found.retired is not None and found.retired.tzinfo is not None


def test_a_service_of_a_nested_agent_and_a_name_with_dashes_are_read_whole(tmp_path: Path) -> None:
    org = org_with_services(tmp_path)
    org.define_service("ceo", "ceo/eng", "action-list-for", **BRIEF)
    org.retire_service("ceo", "ceo/eng", "action-list-for", "not needed")
    (found,) = retirements(org).retired()
    assert (found.owner, found.name, found.by, found.reason) == ("ceo/eng", "action-list-for", "ceo", "not needed")


def test_every_retired_copy_is_listed_in_order_of_owner_and_name(tmp_path: Path) -> None:
    org = org_with_services(tmp_path)
    for owner, name in (("ceo", "b-service"), ("ceo", "a-service")):
        org.define_service(ROOT, owner, name, **BRIEF)
        org.retire_service(ROOT, owner, name, "x")
    assert [(r.owner, r.name) for r in retirements(org).retired()] == [("ceo", "a-service"), ("ceo", "b-service")]


def test_a_copy_with_no_record_or_with_an_unreadable_one_is_left_out(tmp_path: Path) -> None:
    org = org_with_services(tmp_path)
    retired = org.dir("ceo") / "services" / ".retired"
    (retired / "no-record-20261102T090000").mkdir(parents=True)
    (retired / "broken-20261102T090000").mkdir()
    (retired / "broken-20261102T090000" / "RETIRED.md").write_bytes(b"\xff\xfe not text")
    (retired / "not-a-copy").mkdir()  # no stamp in the name
    (retired / "stray-file.md").write_text("x", encoding="utf-8")
    assert retirements(org).retired() == ()


def test_the_approval_of_the_record_is_kept(tmp_path: Path) -> None:
    org = org_with_services(tmp_path)
    copy = org.dir("ceo") / "services" / ".retired" / "weekly-brief-20261102T090000"
    copy.mkdir(parents=True)
    (copy / "RETIRED.md").write_text("---\nretired: 2026-11-02T09:00:00Z\nby: root\nreason: replaced\napproved_in: change plan-7\n---\n", encoding="utf-8")
    (found,) = retirements(org).retired()
    assert (found.name, found.reason, found.approved_in) == ("weekly-brief", "replaced", "change plan-7")
    assert found.retired is not None and (found.retired.year, found.retired.hour) == (2026, 9)
