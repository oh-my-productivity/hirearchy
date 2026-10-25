"""Contract of ``CaseRecords``: the real records over the services world (disk and memory) and the fixed records of a test."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import ROOT, OrgError
from hirearchy.reflection import CaseRecords, OwnerDeliveries, ServiceRecord
from hirearchy.reflection.testing import IMPLEMENTATIONS, RecordsHarness, FixedCaseRecords


@pytest.fixture(params=IMPLEMENTATIONS[CaseRecords], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RecordsHarness:
    made = cast(Callable[[Path], RecordsHarness], request.param)(tmp_path)
    assert isinstance(made.records, CaseRecords)
    return made


def test_records_of_an_empty_org_have_no_service(h: RecordsHarness) -> None:
    found = h.records.records()
    assert [(r.owner, r.service, r.client, r.client_kind, r.cases) for r in found] == [("", "", ROOT, "human", ())]  # root's one-off record, last
    assert h.records.deliveries(h.owner) == OwnerDeliveries()


def test_the_records_of_a_service_and_the_one_off_record(h: RecordsHarness) -> None:
    h.populate()
    found = h.records.records()
    assert all(isinstance(r, ServiceRecord) for r in found)
    assert [(r.owner, r.service) for r in found] == [(h.owner, h.service), ("", "")]
    service = found[0]
    assert (service.client, service.client_kind, service.unit, service.error, service.contract) == (ROOT, "human", "case", "", 1)
    assert len(service.cases) == 1


def test_records_with_a_service_name_only(h: RecordsHarness) -> None:
    h.populate()
    assert [(r.owner, r.service) for r in h.records.records(h.service)] == [(h.owner, h.service)]  # no one-off record
    with pytest.raises(OrgError) as raised:
        h.records.records("nothing")
    assert h.service in str(raised.value) and "`nothing`" in str(raised.value)


def test_a_record_with_error_keeps_its_heading_only(h: RecordsHarness) -> None:
    h.populate()
    h.corrupt()
    found = h.records.records()
    (broken,) = [r for r in found if r.service == h.service]
    assert broken.error and (broken.owner, broken.client, broken.client_kind) == (h.owner, ROOT, "human")
    assert (broken.cases, broken.deliveries, broken.assertions, broken.escapes, broken.timeline, broken.contract, broken.budget) == ((), (), (), (), (), 0, 0)
    assert [r.service for r in found if r.service == ""] == [""] and not [r for r in found if r.service == ""][0].error  # the one-off record still builds


def test_deliveries_of_an_owner_with_an_unreadable_stored_version_are_untyped_and_unknown(h: RecordsHarness) -> None:
    h.populate()
    assert h.records.deliveries(h.owner).unknown == ""
    h.corrupt()
    found = h.records.deliveries(h.owner)
    assert h.service in found.unknown
    assert all(cause is None or (cause.type, cause.rule) == ("untyped", "unreadable") for cause in found.causes)  # every escape, if any, is counted
    assert len(found.causes) == len(found.deliveries)


def test_the_fixed_records_answer_what_was_put_in() -> None:
    record = ServiceRecord("ceo", "a", ROOT, "human")
    fixed = FixedCaseRecords([record], {"ceo": OwnerDeliveries(unknown="x")})
    assert fixed.records() == [record] and fixed.records("a") == [record] and fixed.deliveries("ceo").unknown == "x" and fixed.deliveries("ops") == OwnerDeliveries()
