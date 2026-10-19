"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6)."""

from __future__ import annotations

from orgmcp.health import HealthAnalyzer, HealthReport, HealthRenderer, HealthThresholds, OrgHealth
from orgmcp.health._analyzer import FileHealthAnalyzer
from orgmcp.health._hired import CharterHireDates
from orgmcp.health._ports import CharterStamp, ClientRework, FsCharterStamp, HireDates
from orgmcp.health._render import TextHealthRenderer
from orgmcp.health._rework import MailClientRework
from orgmcp.health._thresholds import SettingsHealthThresholds
from orgmcp.health.testing import FixedHealthAnalyzer, MemoryCharterStamps, StateWords
from orgmcp.eligibility import AgentStates


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
    from orgmcp.agents.testing import MemoryAgents
    from orgmcp.mail.testing import MemoryMailbox

    assert isinstance(MailClientRework(MemoryAgents(), MemoryMailbox()), ClientRework)
    assert isinstance(TextHealthRenderer(), HealthRenderer)
