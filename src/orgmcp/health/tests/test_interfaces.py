"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6)."""

from __future__ import annotations

from orgmcp.health import HealthReport, OrgHealth


def test_the_report_subclasses_its_port() -> None:
    assert HealthReport in OrgHealth.__mro__
