"""The classes of ``dispatch`` implement the interfaces they are known by (the ports of the api, and the collaborators among them)."""

from __future__ import annotations

from hirearchy.dispatch import LESSONS_MAX_CHARS, MessageSender, ReworkContext, TaskAssigner, TaskReporter
from hirearchy.dispatch._artifacts import ArtifactAnnotator
from hirearchy.dispatch._assigner import RuleTaskAssigner
from hirearchy.dispatch._hops import InflightHopCounter
from hirearchy.dispatch._lessons import LessonsPolicy
from hirearchy.dispatch._protocols import ArtifactNormalizer, HopCounter, LessonsCheck, RoutePolicy
from hirearchy.dispatch._reporter import RuleTaskReporter
from hirearchy.dispatch._routes import ParentSiblingRoutePolicy
from hirearchy.dispatch._sender import RuleMessageSender
from hirearchy.dispatch.testing import FixedReworkContext, NoReworkContext, RecordingSender


def test_the_real_classes_are_known_by_their_interfaces() -> None:
    assert issubclass(RuleMessageSender, MessageSender)
    assert issubclass(RuleTaskAssigner, TaskAssigner)
    assert issubclass(RuleTaskReporter, TaskReporter)
    assert issubclass(ParentSiblingRoutePolicy, RoutePolicy)
    assert issubclass(InflightHopCounter, HopCounter)
    assert issubclass(ArtifactAnnotator, ArtifactNormalizer)
    assert issubclass(LessonsPolicy, LessonsCheck)


def test_the_fakes_are_known_by_their_interfaces() -> None:
    assert issubclass(RecordingSender, MessageSender)
    assert issubclass(NoReworkContext, ReworkContext) and issubclass(FixedReworkContext, ReworkContext)


def test_the_limit_of_the_lessons_is_eight_hundred_characters() -> None:
    assert LESSONS_MAX_CHARS == 800
