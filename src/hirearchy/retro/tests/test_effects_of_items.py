# mypy: ignore-errors
"""What the files show of an item's effect (design 4.5, "effect of an item"), read over a real organization: a rejection answered, a criterion settled, runs taken back.

``FileBriefSources.read(since, after)`` gives ``Facts.effects`` for the changes made after ``after`` (the time of the last brief); ``taken_by`` says which recorded item each one is the effect of.
"""

from __future__ import annotations

import time

from testkit.reach.hirearchy.core import ROOT, Org
from testkit.services_world import define, deliver, request

from hirearchy.retro import RecordedItem
from hirearchy.retro._items import taken_by
from hirearchy.retro._views import EffectFacts

from .test_sources import sources_of


def effects(org: Org, after: object) -> EffectFacts:
    return sources_of(org).read(None, after).effects  # type: ignore[arg-type]


def a_rejection(org: Org, topic: str = "ai") -> tuple[object, str]:
    """A fresh delivery of weekly-brief that the user rejects (no answer yet): returns the task and the rejection's message id."""
    task = request(org, topic)
    deliver(org, "ceo", task)
    return task, org.feedback(ROOT, task.id, "reject", "Missing the sources.", source="human").id


def item(kind: str, **effect: str) -> RecordedItem:
    return RecordedItem(1, kind, f"{kind}|x", (), dict(effect), 0)


def test_a_rejection_the_user_answered_after_the_brief_is_answered_and_one_answered_before_it_is_not(org: Org) -> None:
    define(org)
    early, early_no = a_rejection(org)
    org.feedback(ROOT, early.id, "reject", "Yes, it is about that.", source="human", criterion=["C2"], confirms=early_no)  # answered before the brief
    late, late_no = a_rejection(org, "ml")
    after = org.runtime.clock.now()
    time.sleep(0.01)
    assert effects(org, after).answered == frozenset()  # R2 still waits
    org.feedback(ROOT, late.id, "reject", "Yes, it is about that.", source="human", criterion=["C2"], confirms=late_no)  # a human link, after the brief
    seen = effects(org, after)
    assert seen.answered == frozenset({"R2"})
    assert taken_by(item("answer", rejection="R2"), seen) == "R2 was answered" and taken_by(item("cause", rejection="R2"), seen) == "R2 was answered"
    assert taken_by(item("answer", rejection="R1"), seen) == ""  # R1's answer is older than the brief
    assert effects(org, None).answered == frozenset({"R1", "R2"})


def test_a_contract_version_that_answers_a_rejection_answers_it(org: Org) -> None:
    define(org)
    task, no = a_rejection(org)
    after = org.runtime.clock.now()
    time.sleep(0.01)
    org.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=["Owners are named in full"], answers=no, about="C2", words="Yes, add it.")
    assert effects(org, after).answered == frozenset({"R1"})


def test_a_criterion_replaced_in_a_contract_version_or_named_by_the_users_link_is_clarified(org: Org) -> None:
    define(org)
    task, no = a_rejection(org)
    after = org.runtime.clock.now()
    time.sleep(0.01)
    assert effects(org, after).clarified == frozenset()
    org.feedback(ROOT, task.id, "reject", "Yes, it is about that.", source="human", criterion=["C2"], confirms=no)  # the user's link names C2
    named = effects(org, after)
    assert named.clarified == frozenset({"weekly-brief/C2"})
    assert taken_by(item("clarify", service="weekly-brief", criterion="C2"), named) == "weekly-brief C2 was settled"
    assert taken_by(item("clarify", service="weekly-brief", criterion="C1"), named) == ""
    again, second = a_rejection(org, "ml")
    later = org.runtime.clock.now()
    time.sleep(0.01)
    org.define_service(
        ROOT, "ceo", "weekly-brief", remove_acceptance=["At most 600 words"], add_acceptance=["At most 500 words"], answers=second, about="C1", words="Make it 500.",
    )
    replaced = effects(org, later)
    assert "weekly-brief/C1" in replaced.clarified and taken_by(item("clarify", service="weekly-brief", criterion="C1"), replaced) == "weekly-brief C1 was settled"


def test_a_note_that_gives_runs_back_to_the_parent_after_the_brief_is_a_reclaim(org: Org) -> None:
    org.send(ROOT, "ceo", "some runs for the week", budget=5)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    after = org.runtime.clock.now()
    time.sleep(0.01)
    assert effects(org, after).reclaimed == frozenset()
    org.reclaim(ROOT, "ceo", 2)
    seen = effects(org, after)
    assert seen.reclaimed == frozenset({"ceo"}) and taken_by(item("reclaim", agent="ceo"), seen) == "ceo's runs came back"
    assert taken_by(item("reclaim", agent="ceo/eng"), seen) == ""
