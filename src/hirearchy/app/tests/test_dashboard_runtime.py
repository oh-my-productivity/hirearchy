"""The runtime of the dashboard (``wire_dashdata.dashboard_runtime``) skips what it cannot read and keeps going, where the plain runtime raises.

It is the place of what the dashboard's ``LenientOrg`` was: the decorators of the read ports (``agents``, ``mail``, ``settings``, ``runs``, ``eligibility``)
stand in the place of the strict ones, and everything derived from them - the budgets, the queue of what needs the user, the health of the agents - follows.
The decorators themselves are tested in their packages; here the composition is."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents._caching import CachingAgentDirectory, LenientCharterReader
from hirearchy.app import Org, wire_dashdata
from hirearchy.app.runtime import OrgRuntime
from hirearchy.eligibility._caching import CachingPauseStore
from hirearchy.health import HEALTH_DEFAULTS
from hirearchy.kernel import ROOT
from hirearchy.mail._caching import DirMtimeCachingMailbox
from hirearchy.runs._caching import CachingRunLogReader
from hirearchy.settings import DEFAULT_CONFIG
from hirearchy.settings._caching import CachingOrgSettings

DAMAGED = "---\nfrom: [oops\n---\nx\n"
BAD_NAME = "20260101T000000000000-root-bad0.md"


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Boss", "text")
    return made


def lenient(org: Org) -> OrgRuntime:
    return wire_dashdata.dashboard_runtime(org.root)


def test_the_read_ports_are_the_decorators_and_the_rest_are_the_plain_ones(org: Org) -> None:
    runtime = lenient(org)
    assert isinstance(runtime.agents, CachingAgentDirectory) and isinstance(runtime.charters, LenientCharterReader)
    assert isinstance(runtime.mailbox, DirMtimeCachingMailbox) and isinstance(runtime.settings, CachingOrgSettings)
    assert isinstance(runtime.run_log_reader, CachingRunLogReader) and isinstance(runtime.pause_store, CachingPauseStore)
    assert type(runtime.agent_registry) is type(org.runtime.agent_registry) and type(runtime.mailbox_writer) is type(org.runtime.mailbox_writer)


def test_a_message_that_cannot_be_read_is_skipped_and_reported(org: Org) -> None:
    org.send("root", "ceo", "good")
    (org.root / "ceo" / "inbox" / BAD_NAME).write_text(DAMAGED, encoding="utf-8")
    runtime = lenient(org)
    assert len(runtime.mailbox.messages("ceo", "inbox")) == 1 and runtime.mailbox.unread("ceo") == 2  # the unreadable file still counts as mail
    assert isinstance(runtime.mailbox, DirMtimeCachingMailbox)
    assert [k for k in runtime.mailbox.bad] == [f"ceo/inbox/{BAD_NAME}"]
    assert list(runtime.mailbox.bad.values())[0].startswith("ParserError:")
    with pytest.raises(Exception):  # noqa: B017, PT011 - the plain runtime raises on it (yaml error), as it always did
        org.messages("ceo", "inbox")


def test_the_task_views_are_derived_from_the_cached_boxes(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=1)
    (org.root / "ceo" / "inbox" / BAD_NAME).write_text(DAMAGED, encoding="utf-8")
    runtime = lenient(org)
    assert [t.id for t in runtime.task_query.open_tasks("ceo")] == [task.id] and runtime.task_query.outstanding("root")[0].id == task.id


def test_an_agent_is_running_when_its_batch_does_not_even_parse(org: Org) -> None:
    inflight = org.root / "ceo" / "inflight"
    inflight.mkdir(exist_ok=True)
    (inflight / BAD_NAME).write_text(DAMAGED, encoding="utf-8")
    assert lenient(org).mailbox.has_inflight("ceo") is True


def test_a_budget_is_added_up_without_the_message_it_cannot_read(org: Org) -> None:
    org.send("root", "ceo", "runs", budget=6)
    (org.root / "ceo" / "inbox" / BAD_NAME).write_text(DAMAGED, encoding="utf-8")
    with pytest.raises(Exception):  # noqa: B017, PT011 - the plain runtime raises on it
        org.budget("ceo")
    runtime = lenient(org)
    assert runtime.budget_query.budget("ceo") == 6 and runtime.budget_query.delegable("ceo") == (6, 0, 5)
    assert isinstance(runtime.mailbox, DirMtimeCachingMailbox) and f"ceo/inbox/{BAD_NAME}" in runtime.mailbox.bad


def test_a_charter_that_cannot_be_read_is_a_question_mark(org: Org) -> None:
    assert lenient(org).charters.charter("ceo")[0]["role"] == "Boss"
    (org.root / "ceo" / "AGENT.md").write_text("---\nrole: [oops\n---\n", encoding="utf-8")
    assert lenient(org).charters.charter("ceo") == ({"role": "?"}, "")


def test_the_queue_of_what_needs_the_user_skips_what_it_cannot_read(org: Org) -> None:
    good = org.send("ceo", ROOT, "I need 2 more runs", title="Budget request")
    (org.root / "inbox" / "20260101T000000000000-ceo-bad0.md").write_text(DAMAGED, encoding="utf-8")
    assert [mid for mid, _ in lenient(org).human_queue.items()] == [good.id]


def test_the_queue_of_the_plain_runtime_does_not_hide_a_damaged_message(org: Org) -> None:
    org.send("ceo", ROOT, "I need 2 more runs", title="Budget request")
    (org.root / "inbox" / "20260101T000000000000-ceo-bad0.md").write_text(DAMAGED, encoding="utf-8")
    with pytest.raises(Exception):  # noqa: B017, PT011 - the dashboard shows what it skipped; everyone else is told
        org.runtime.human_queue.items()


def test_a_damaged_org_md_means_the_defaults(org: Org) -> None:
    (org.root / "ORG.md").write_text("---\nmission: [unclosed\nhealth: {\n---\nrules\n", encoding="utf-8")
    runtime = lenient(org)
    assert runtime.settings.config() == DEFAULT_CONFIG
    assert runtime.health_thresholds.thresholds() == HEALTH_DEFAULTS
    with pytest.raises(Exception):  # noqa: B017, PT011 - whatever the YAML reader raises; the point is that the plain runtime does not hide it
        org.runtime.health_thresholds.thresholds()


def test_the_health_of_the_agents_is_reported_without_the_message_it_cannot_read(org: Org) -> None:
    org.delegate("root", "ceo", "T", "g", "a", budget=3)
    (org.root / "ceo" / "inbox" / BAD_NAME).write_text(DAMAGED, encoding="utf-8")
    with pytest.raises(Exception):  # noqa: B017, PT011 - the plain runtime does not hide a damaged message
        org.runtime.health_analyzer.org_health("root")
    report = lenient(org).health_analyzer.org_health("root")
    assert [h.addr for h in report.agents] == ["ceo"] and report.agents[0].tasks_received >= 1

