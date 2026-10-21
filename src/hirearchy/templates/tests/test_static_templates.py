"""The two real implementations: stateless renderers that subclass their Protocol."""

from __future__ import annotations

from hirearchy.templates import DocumentTemplates, Notices
from hirearchy.templates._documents import DEFAULT_MISSION, StaticDocumentTemplates
from hirearchy.templates._notices import REVIEW_ACTIONS, StaticNotices

def test_they_subclass_the_protocol_they_implement() -> None:
    assert DocumentTemplates in StaticDocumentTemplates.__mro__ and Notices in StaticNotices.__mro__


def test_they_hold_no_state() -> None:
    assert vars(StaticDocumentTemplates()) == {} and vars(StaticNotices()) == {}


def test_two_instances_render_the_same_text() -> None:
    assert StaticDocumentTemplates().org_rules("m") == StaticDocumentTemplates().org_rules("m")
    assert StaticNotices().nudge("T-1", "t") == StaticNotices().nudge("T-1", "t")


def test_the_default_mission_and_the_flags_with_a_suggested_action_are_unchanged() -> None:
    assert DEFAULT_MISSION == "(Describe the mission of this organization here.)"
    assert list(REVIEW_ACTIONS) == ["stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle"]
