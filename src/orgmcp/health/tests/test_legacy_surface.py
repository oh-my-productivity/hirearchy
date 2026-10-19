"""The names ``orgmcp.health`` kept exporting when the module became a package (``LEGACY_EXPORTS``, until step E3).

Characterization: these tests passed on the module ``health.py`` and must keep passing on the package. The private time helpers and the
numeric readers stay for the legacy modules that import them (``dashboard_data observe progress review services scheduler``) until their own
steps."""

from __future__ import annotations

import importlib

import orgmcp.kernel as kernel
import orgmcp.settings as settings
from orgmcp.health import AgentHealth, BranchHealth, OrgHealth

health = importlib.import_module("orgmcp.health")  # as a module object: the tests read its attributes by name


def test_the_old_names_are_still_exported() -> None:
    for name in ("HEALTH_DEFAULTS", "FLAGS", "AgentHealth", "BranchHealth", "OrgHealth", "thresholds", "agent_health", "org_health", "render_text"):
        assert hasattr(health, name), name
    assert health.AgentHealth is AgentHealth and health.BranchHealth is BranchHealth and health.OrgHealth is OrgHealth
    assert health.FLAGS == ("stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle")


def test_the_private_helpers_the_legacy_modules_import_are_the_kernels_and_the_settings() -> None:
    assert health._aware is kernel.aware and health._parse_time is kernel.parse_time and health._stamp is kernel.stamp_of
    assert health._msg_time is kernel.msg_time and health._duration is kernel.fmt_duration
    assert health._number is settings.finite_number and health.config_number is settings.config_number


def test_the_module_no_longer_reads_the_clock_itself() -> None:
    assert not hasattr(health, "utcnow")  # the time comes from the clock of the runtime (core.utcnow, while the tests patch it)
