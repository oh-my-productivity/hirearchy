"""The test support of ``health``: the registry the contract suites iterate over (grown by the steps of the package)."""

from __future__ import annotations

PURE = {"HealthReport"}  # the report is data with two derived views: ``OrgHealth`` is its one implementation, there is no fake
