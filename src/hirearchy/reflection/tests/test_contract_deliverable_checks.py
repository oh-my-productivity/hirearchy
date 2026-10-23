"""Contract of ``DeliverableChecks``: the real checks over the fs world (real files in a deliverable folder) and the fixed findings of a test."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import ROOT
from hirearchy.reflection import DeliverableChecks, DeliverableFinding
from hirearchy.reflection.testing import IMPLEMENTATIONS, DeliverableHarness


@pytest.fixture(params=IMPLEMENTATIONS[DeliverableChecks], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> DeliverableHarness:
    made = cast(Callable[[Path], DeliverableHarness], request.param)(tmp_path)
    assert isinstance(made.checks, DeliverableChecks)
    return made


def test_an_actor_without_services_has_no_findings(h: DeliverableHarness) -> None:
    assert h.checks.findings(ROOT) == []  # nothing is there yet
    assert h.checks.findings("ceo/eng") == [] and h.checks.findings("ceo/eng", "weekly-brief") == []
    h.populate()
    assert h.checks.findings("ceo/eng") == []  # an agent that requests no service


def test_findings_are_deliverable_findings(h: DeliverableHarness) -> None:
    h.populate()
    (found,) = h.checks.findings(ROOT)
    assert isinstance(found, DeliverableFinding)
    assert (found.name, found.kind, found.services, found.file) == ("x.md", "unknown", (h.service,), False)
    assert h.checks.findings(ROOT, h.service) == [found]  # the folder of that service
    assert h.checks.findings(ROOT, "other-service") == []
    assert h.checks.findings(ROOT) == h.checks.findings(ROOT)  # asking again changes nothing
