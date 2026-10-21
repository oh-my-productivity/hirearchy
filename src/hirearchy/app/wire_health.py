"""Providers of the ``health`` ports (ARCHITECTURE.md 6.1).

The analyzer is built from the ports of the organization it measures; the small collaborators that are not ports of the package's api
(who counts as the client's rework, what the client's verdicts count as escapes, when an agent was hired) are built here too, as the composition root builds everything.
"""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates, PauseStore
from ..health import HealthAnalyzer, HealthRenderer, HealthThresholds
from ..health._analyzer import FileHealthAnalyzer
from ..health._escapes import MailEscapeCounter
from ..health._hired import CharterHireDates
from ..health._ports import FsCharterStamp
from ..health._render import TextHealthRenderer
from ..health._rework import MailClientRework
from ..health._thresholds import SettingsHealthThresholds
from ..kernel import Clock, OrgLayout
from ..mail import MailboxReader
from ..runs import RunLogReader
from ..settings import OrgSettings
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(HealthThresholds, lambda b: SettingsHealthThresholds(b.get(OrgSettings)))
    b.provide(
        HealthAnalyzer,
        lambda b: FileHealthAnalyzer(
            b.get(AgentDirectory), b.get(MailboxReader), b.get(RunLogReader), b.get(RunLogReader), b.get(BudgetQuery), b.get(PauseStore),
            b.get(AgentStates), b.get(HealthThresholds), MailClientRework(b.get(AgentDirectory), b.get(MailboxReader)),
            MailEscapeCounter(
                b.get(AgentDirectory), b.get(MailboxReader), b.get(RunLogReader), MailClientRework(b.get(AgentDirectory), b.get(MailboxReader)),
            ),
            CharterHireDates(b.get(CharterReader), FsCharterStamp(b.get(OrgLayout))), b.get(Clock),
        ),
    )
    b.provide(HealthRenderer, lambda b: TextHealthRenderer())
