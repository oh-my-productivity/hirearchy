"""The old module-level functions are thin adapters of the classes of the package, over the ports of the ``Org`` they are given *now* (until step E3).

They are what ``progress``, the dashboard, the server and the CLI still call. The ``Org`` here is a stand-in with the ports in ``runtime`` (the facade is
not importable from a feature); the dashboard's lenient ``Org`` replaces some of those ports and its ``config``, and the functions must follow."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest

import orgmcp.reflection as reflection
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.reflection.testing import ReflectionWorld, fs_world, memory_world

from . import _stories
from ._golden import expected
from ._support import SERVICE, STEPS, define, org_of, populated

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-reflection")


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


def test_the_cases_are_those_of_the_history(w: ReflectionWorld) -> None:
    _stories.rejected_then_accepted(w)
    assert reflection.cases(org_of(w), "ceo", SERVICE) == w.history.cases("ceo", SERVICE) != []


def test_the_case_of_a_task_is_that_of_the_history(w: ReflectionWorld) -> None:
    story = _stories.rejected_then_accepted(w)
    assert reflection.case_of(org_of(w), story.asks[1]) == w.history.case_of(story.asks[1]) is not None


def test_the_timeline_is_that_of_the_history(w: ReflectionWorld) -> None:
    _stories.three_playbook_versions(w)
    timeline = reflection.playbook_timeline(org_of(w), "ceo", SERVICE)
    assert [v for v, _ in timeline] == [1, 2] and timeline == w.history.playbook_timeline("ceo", SERVICE)


def test_the_timeline_of_the_playbook_is_made_of_the_history_of_the_store(w: ReflectionWorld) -> None:
    """(moved from ``services/tests/test_legacy_adapters.py``; the playbooks are written through the commands of the world)"""
    org = org_of(w)
    define(w)
    w.s.commands.revise_playbook("ceo", SERVICE, STEPS, "one")
    w.s.d.clock.advance(60)
    w.s.commands.revise_playbook("ceo", SERVICE, STEPS + "\n4. More.", "two")
    timeline = reflection.playbook_timeline(org, "ceo", SERVICE)
    assert [v for v, _ in timeline] == [1, 2] and timeline[0][1] < timeline[1][1]
    assert reflection.version_at(timeline, None) == 2 and reflection.version_at(timeline, timeline[0][1]) == 1
    assert reflection.version_at(timeline, timeline[0][1].replace(year=2000)) == 0


def test_the_digest_is_the_text_services_py_printed(w: ReflectionWorld) -> None:
    story = _stories.rejected_then_accepted(w)
    assert reflection.reflection_digest(org_of(w), "ceo", SERVICE) == expected("digest_rejected_then_accepted.txt", story)


def test_the_listing_and_the_totals_are_the_text_services_py_printed(w: ReflectionWorld) -> None:
    story = _stories.rejected_then_accepted(w)
    org = org_of(w)
    assert reflection.services_text(org, "root") == expected("services_root_rejected_then_accepted.txt", story)
    assert reflection.case_total(org, story.asks[0]).startswith("case total: 5 runs used of 16 handed down")


def test_the_sections_are_the_text_services_py_printed(w: ReflectionWorld) -> None:
    story = _stories.rejection_and_rework(w)
    assert reflection.prompt_sections(org_of(w), "ceo", w.s.d.inbox("ceo")) == expected("sections_rejection_and_rework.txt", story)


def test_the_functions_use_the_ports_the_org_has_now(w: ReflectionWorld) -> None:
    _stories.delivered_and_accepted(w)
    org = org_of(w)
    assert len(reflection.cases(org, "ceo", SERVICE)) == 1
    org.runtime.mailbox = MemoryMailbox(w.s.d.agents) if isinstance(w.s.d.mail, MemoryMailbox) else SimpleNamespace(sent=lambda addr: [], received=lambda addr: [])
    assert reflection.cases(org, "ceo", SERVICE) == []  # a lenient org with other mailboxes is not ignored


def test_the_longest_playbook_is_read_from_the_config_the_org_has_now(w: ReflectionWorld) -> None:
    _stories.history_then_new_request(w)
    org = org_of(w, config={"playbook_max_words": 123})
    assert "(at most 123 words)" in reflection.prompt_sections(org, "ceo", w.s.d.inbox("ceo"))


def test_the_private_names_the_dashboard_and_the_tests_use_are_the_lines_of_the_digest(w: ReflectionWorld) -> None:
    _stories.rejected_then_accepted(w)
    (case,) = w.history.cases("ceo", SERVICE)
    assert reflection._verdict_chain(case) == 'reject "Sam\'s \'before Friday\' needs a date." -> accept "this version is right"'
    assert reflection._case_line(case).startswith(f'- case {case.id} "weekly-brief: ai": done, playbook v0, 5 of 16 runs, 1 rework(s)')
