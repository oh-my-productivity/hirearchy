"""The legacy functions (``agent_health``, ``org_health``, ``thresholds``) over an ``Org`` that is not the plain one.

The dashboard hands them its ``LenientOrg``: unreadable messages are skipped and a damaged ORG.md means the defaults. The functions read the
ports and the settings of the ``Org`` they are given - not those of the runtime it was first opened with - so they keep going where a strict
reader would raise."""

from __future__ import annotations

from typing import Any

import pytest

from orgmcp.health import HEALTH_DEFAULTS, agent_health, org_health, thresholds
from orgmcp.kernel import OrgError

from . import _scenario
from ._legacy import legacy

NOW = _scenario.at(4000)


def lenient(org: Any) -> Any:
    return legacy("app.tests._lenient_org").LenientOrg(org.root)


def test_a_lenient_org_reports_the_same_as_the_plain_one_when_nothing_is_damaged(scenario: Any) -> None:
    assert org_health(lenient(scenario), "root", NOW) == org_health(scenario, "root", NOW)


def test_a_message_that_cannot_be_read_is_skipped_by_a_lenient_org(scenario: Any) -> None:
    (scenario.dir("ceo/eng") / "inbox" / "20260101T000500000000-root-ffff.md").write_text("---\nid: [unclosed\n---\nbody\n", encoding="utf-8")
    with pytest.raises(Exception):  # noqa: B017 - the plain Org does not hide a damaged message
        org_health(scenario, "root", NOW)
    soft = lenient(scenario)
    report = org_health(soft, "root", NOW)
    assert [h.addr for h in report.agents] == ["ceo", "ceo/eng", "ceo/qa", "ceo/spare", "dormant", "ops", "ops/dev"]
    assert soft.bad  # the dashboard shows what it skipped
    assert agent_health(soft, "ceo/eng", NOW).tasks_received >= 1


def test_a_damaged_org_md_means_the_default_thresholds_for_a_lenient_org_and_an_error_for_the_plain_one(scenario: Any) -> None:
    (scenario.root / "ORG.md").write_text("---\nmission: [unclosed\nhealth: {\n---\nrules\n", encoding="utf-8")
    assert thresholds(lenient(scenario)) == HEALTH_DEFAULTS
    with pytest.raises(Exception):  # noqa: B017 - whatever the YAML reader raises; the point is that the plain Org does not hide it
        thresholds(scenario)


def test_the_thresholds_of_org_md_reach_the_legacy_function(scenario: Any) -> None:
    text = (scenario.root / "ORG.md").read_text(encoding="utf-8")
    (scenario.root / "ORG.md").write_text(text.replace("poll_seconds: 0.05\n", "poll_seconds: 0.05\nhealth:\n  idle_after_seconds: 60\n", 1), encoding="utf-8")
    assert thresholds(scenario)["idle_after_seconds"] == 60 and thresholds(scenario)["stuck_after_seconds"] == 1800


def test_the_legacy_guards_are_the_analyzers(scenario: Any) -> None:
    with pytest.raises(OrgError, match="root is the human"):
        agent_health(scenario, "root", NOW)
    with pytest.raises(OrgError, match="no such agent: ghost"):
        org_health(scenario, "ghost", NOW)
