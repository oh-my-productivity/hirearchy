"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6)."""

from __future__ import annotations

from hirearchy.health import HealthAnalyzer, HealthReport, HealthRenderer, HealthThresholds, OrgHealth
from hirearchy.health._analyzer import FileHealthAnalyzer
from hirearchy.health._hired import CharterHireDates
from hirearchy.health._ports import CharterStamp, ClientRework, FsCharterStamp, HireDates
from hirearchy.health._render import TextHealthRenderer
from hirearchy.health._rework import MailClientRework
from hirearchy.health._thresholds import SettingsHealthThresholds
from hirearchy.health.testing import FixedHealthAnalyzer, MemoryCharterStamps, StateWords
from hirearchy.eligibility import AgentStates


def test_the_report_subclasses_its_port() -> None:
    assert HealthReport in OrgHealth.__mro__


def test_each_class_subclasses_the_port_it_implements() -> None:
    assert HealthAnalyzer in FileHealthAnalyzer.__mro__ and HealthAnalyzer in FixedHealthAnalyzer.__mro__
    assert HealthRenderer in TextHealthRenderer.__mro__
    assert HealthThresholds in SettingsHealthThresholds.__mro__
    assert ClientRework in MailClientRework.__mro__
    assert HireDates in CharterHireDates.__mro__
    assert CharterStamp in FsCharterStamp.__mro__ and CharterStamp in MemoryCharterStamps.__mro__
    assert AgentStates in StateWords.__mro__


def test_the_classes_are_instances_of_their_ports() -> None:
    from hirearchy.agents.testing import MemoryAgents
    from hirearchy.mail.testing import MemoryMailbox

    assert isinstance(MailClientRework(MemoryAgents(), MemoryMailbox()), ClientRework)
    assert isinstance(TextHealthRenderer(), HealthRenderer)
