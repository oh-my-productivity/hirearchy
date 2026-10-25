"""Every ``QualityReport`` says the same of an organization: the text and the JSON of the quality view, with or without a service."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from testkit.quality_schema import problems

from hirearchy.kernel import OrgError
from hirearchy.progress import QualityReport
from hirearchy.progress.testing import IMPLEMENTATIONS, QualityHarness


@pytest.fixture(params=IMPLEMENTATIONS[QualityReport], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> QualityHarness:
    made = cast(Callable[[Path], QualityHarness], request.param)(tmp_path)
    assert isinstance(made.report, QualityReport)
    return made


def test_an_empty_org_reads_no_cases_yet(h: QualityHarness) -> None:
    text = h.report.quality_text()
    assert "No cases yet: you have requested no service and given no task." in text
    assert text.endswith("Blocked tasks moved past without a verdict: none.")
    data = h.report.quality_data()
    assert data["services"] == [] and data["one_off"] is None and data["moved_past"] == []


def test_service_x_shows_only_x(h: QualityHarness) -> None:
    h.populate()
    text = h.report.quality_text(h.service)
    assert f"{h.service} (offered by {h.owner}; client: you, human;" in text
    assert f"{h.other} (offered by" not in text and "One-off tasks" not in text and "No cases yet" not in text
    assert [s["service"] for s in h.report.quality_data(h.service)["services"]] == [h.service]  # type: ignore[attr-defined]
    everything = h.report.quality_text()
    assert f"{h.service} (offered by" in everything and f"{h.other} (offered by" in everything and "One-off tasks you gave: none." in everything


def test_an_unknown_service_is_an_org_error_listing_the_names(h: QualityHarness) -> None:
    h.populate()
    for ask in (h.report.quality_text, h.report.quality_data):
        with pytest.raises(OrgError) as refused:
            ask("nope")
        assert str(refused.value).startswith("no service named `nope`: the services are ")
        assert h.service in str(refused.value) and h.other in str(refused.value)
        assert str(refused.value).endswith("Call quality() without a service for everything.")


def test_a_service_name_longer_than_80_is_an_org_error(h: QualityHarness) -> None:
    for ask in (h.report.quality_text, h.report.quality_data):
        with pytest.raises(OrgError) as refused:
            ask("x" * 81)
        assert str(refused.value).startswith("service is a service name (at most 80 characters): ")


def test_an_empty_service_means_everything(h: QualityHarness) -> None:
    h.populate()
    assert h.report.quality_text("  ") == h.report.quality_text()
    assert h.report.quality_text(f" {h.service} ") == h.report.quality_text(h.service)


def test_text_and_data_agree(h: QualityHarness) -> None:
    h.populate()
    data = h.report.quality_data()
    assert problems(data) == []
    text = h.report.quality_text()
    named = [f"{s['service']} (offered by {s['owner']};" for s in data["services"]]  # type: ignore[attr-defined]
    assert len(named) == 2 and all(n in text for n in named)
    assert data["thresholds"]["cost_ratio"] in text  # type: ignore[index]
